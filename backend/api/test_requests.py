"""Requests to process ("Demandes à traiter"): record changes, certificates, absences and expenses.

What the reviewers are told, what they find in their queues and what they can decide must always match,
and a request accepted today must not fail once approved."""
from datetime import date, timedelta
from decimal import Decimal

from .models import (
    AuditLog, CertificateRequest, Company, Document, ExpenseReport, LeaveRequest, Notification, ProfileChangeRequest,
    User,
)
from .test_coherence import TwoCompaniesTestCase

NEXT = date.today().year + 1


def sick_leave(day):
    return {'leave_type': 'sick', 'start_date': day, 'end_date': day}


class ProfileRequestRulesTests(TwoCompaniesTestCase):
    def ask(self, changes, user=None):
        return self.client_for(user or self.emp).post('/api/profile-requests/', {'changes': changes}, format='json')

    def test_only_real_changes_are_kept(self):
        self.emp.city = 'Oran'
        self.emp.save()
        r = self.ask({'city': 'Oran ', 'address': "12 rue Larbi Ben M'hidi"})
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['changes'], {'address': "12 rue Larbi Ben M'hidi"})

    def test_a_request_that_changes_nothing_is_refused(self):
        self.emp.city = 'Oran'
        self.emp.save()
        for changes in [{'city': 'Oran'}, {'marital_status': 'single'}, {'children_count': '0'}, {'address': ''}]:
            self.assertEqual(self.ask(changes).status_code, 400, changes)
        self.assertFalse(ProfileChangeRequest.objects.exists())

    def test_values_the_record_cannot_hold_are_refused_up_front(self):
        # On PostgreSQL a value longer than its column made the approval itself crash.
        for changes in [{'postal_code': '1' * 11}, {'iban': 'DZ' + '0' * 40}, {'first_name': ''}, {'last_name': '  '},
                        {'children_count': '31'}, {'children_count': '-1'}, {'children_count': 'deux'},
                        {'marital_status': 'pacsé'}, {'birth_date': '1990-02-30'}]:
            self.assertEqual(self.ask(changes).status_code, 400, changes)
        self.assertFalse(ProfileChangeRequest.objects.exists())

    def test_birth_date_must_be_plausible(self):
        today = date.today()
        for value in [today + timedelta(days=1), date(today.year - 10, 1, 1), date(1899, 12, 31)]:
            self.assertEqual(self.ask({'birth_date': value.isoformat()}).status_code, 400, value)
        self.assertEqual(self.ask({'birth_date': '1994-06-21'}).status_code, 201)

    def test_hr_form_checks_the_birth_date_the_same_way(self):
        hr = self.client_for(self.hr)
        future = (date.today() + timedelta(days=1)).isoformat()
        self.assertEqual(hr.patch(f'/api/employees/{self.emp.id}/', {'birth_date': future}, format='json').status_code, 400)
        self.assertEqual(hr.patch(f'/api/employees/{self.emp.id}/', {'children_count': 40}, format='json').status_code, 400)

    def test_approval_applies_typed_values(self):
        rid = self.ask({'birth_date': '1994-06-21', 'children_count': '03', 'marital_status': 'married'}).data['id']
        r = self.client_for(self.hr).post(f'/api/profile-requests/{rid}/approve/')
        self.assertEqual(r.status_code, 200, r.data)
        self.emp.refresh_from_db()
        self.assertEqual((self.emp.birth_date, self.emp.children_count, self.emp.marital_status),
                         (date(1994, 6, 21), 3, 'married'))

    def test_current_values_show_zero_children(self):
        r = self.ask({'children_count': '2'})
        self.assertEqual(r.data['current_values'], {'children_count': '0'})

    def test_review_comment_must_be_text(self):
        rid = self.ask({'city': 'Oran'}).data['id']
        hr = self.client_for(self.hr)
        for action in ['approve', 'reject']:
            r = hr.post(f'/api/profile-requests/{rid}/{action}/', {'comment': {'x': 1}}, format='json')
            self.assertEqual(r.status_code, 400, action)
        self.assertEqual(ProfileChangeRequest.objects.get(id=rid).status, 'pending')
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.city, '')

    def test_hr_request_goes_to_someone_else(self):
        rid = self.ask({'city': 'Oran'}, user=self.hr).data['id']
        hr = self.client_for(self.hr)
        self.assertEqual(hr.get('/api/profile-requests/?scope=team&status=pending').data, [])
        self.assertEqual(hr.post(f'/api/profile-requests/{rid}/approve/').status_code, 403)
        r = self.client_for(self.accountant).post(f'/api/profile-requests/{rid}/approve/', **self.header())
        self.assertEqual(r.status_code, 200, r.data)

    def test_manager_does_not_see_the_values_asked_for(self):
        self.ask({'iban': 'DZ58 0001 2345'})
        c = self.client_for(self.manager)
        self.assertEqual(c.get('/api/profile-requests/?scope=team').status_code, 403)
        self.assertEqual(c.get('/api/certificates/?scope=team').status_code, 403)
        self.assertEqual(c.get('/api/profile-requests/').data, [])


class CertificateRulesTests(TwoCompaniesTestCase):
    def ask(self, kind='work', user=None):
        return self.client_for(user or self.emp).post('/api/certificates/', {'kind': kind}, format='json')

    def approve(self, rid):
        return self.client_for(self.hr).post(f'/api/certificates/{rid}/approve/')

    def test_incomplete_record_says_what_is_missing(self):
        rid = self.ask().data['id']
        r = self.approve(rid)
        self.assertEqual(r.status_code, 400)
        self.assertIn("date d'embauche, poste", str(r.data))
        self.assertEqual(CertificateRequest.objects.get(id=rid).status, 'pending')
        self.assertFalse(Document.objects.exists())
        self.emp.hire_date, self.emp.job_title = date(2022, 1, 10), 'Commercial'
        self.emp.save()
        self.assertEqual(self.approve(rid).status_code, 200)

    def test_salary_certificate_needs_a_salary(self):
        self.manager.hire_date, self.manager.job_title = date(2020, 9, 15), 'Chef des ventes'
        self.manager.save()
        r = self.approve(self.ask('salary', user=self.manager).data['id'])
        self.assertEqual(r.status_code, 400)
        self.assertIn('salaire de base', str(r.data))
        self.assertEqual(self.approve(self.ask('work', user=self.manager).data['id']).status_code, 200)

    def test_not_before_the_hire_date(self):
        self.emp.hire_date, self.emp.job_title = date.today() + timedelta(days=10), 'Commercial'
        self.emp.save()
        r = self.approve(self.ask().data['id'])
        self.assertEqual(r.status_code, 400)
        self.assertIn('prend effet', str(r.data))

    def test_review_comment_must_be_text(self):
        rid = self.ask().data['id']
        r = self.client_for(self.hr).post(f'/api/certificates/{rid}/reject/', {'comment': ['x']}, format='json')
        self.assertEqual(r.status_code, 400)


class SoleReviewerTests(TwoCompaniesTestCase):
    """A company whose only HR user has no manager and no accountant: their own requests cannot wait for nobody."""

    def setUp(self):
        super().setUp()
        self.solo = Company.objects.create(name='Solo SARL')
        self.boss = User.objects.create_user('patron', password=self.password, company=self.solo, role=User.Role.HR,
                                             base_salary=Decimal('90000'), hire_date=date(2020, 1, 1),
                                             job_title='Gérant')
        self.staff = User.objects.create_user('staff', password=self.password, company=self.solo,
                                              base_salary=Decimal('40000'))
        self.c = self.client_for(self.boss)

    def test_own_leave_is_approved_at_once_and_journaled(self):
        r = self.c.post('/api/leaves/', {'leave_type': 'annual', 'start_date': f'{NEXT}-03-01',
                                         'end_date': f'{NEXT}-03-02'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['status'], 'approved')
        lr = LeaveRequest.objects.get(id=r.data['id'])
        self.assertEqual((lr.status, lr.reviewer), ('approved', self.boss))
        entry = AuditLog.objects.get(action='leave.approve')
        self.assertEqual(entry.company, self.solo)
        self.assertIn('aucun autre valideur', entry.summary)

    def test_balance_still_applies(self):
        r = self.c.post('/api/leaves/', {'leave_type': 'annual', 'start_date': f'{NEXT}-03-01',
                                         'end_date': f'{NEXT}-04-30'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_own_expense_record_change_and_certificate(self):
        r = self.c.post('/api/expenses/', {'date': date.today().isoformat(), 'amount': '1200', 'description': 'Taxi'},
                        format='json')
        self.assertEqual((r.status_code, r.data['status']), (201, 'approved'))
        r = self.c.post('/api/profile-requests/', {'changes': {'city': 'Blida'}}, format='json')
        self.assertEqual((r.status_code, r.data['status']), (201, 'approved'))
        self.boss.refresh_from_db()
        self.assertEqual(self.boss.city, 'Blida')
        r = self.c.post('/api/certificates/', {'kind': 'salary'}, format='json')
        self.assertEqual((r.status_code, r.data['status']), (201, 'approved'))
        self.assertTrue(Document.objects.filter(employee=self.boss, category='certificate').exists())
        self.assertEqual(AuditLog.objects.filter(company=self.solo, summary__contains='aucun autre valideur').count(), 3)

    def test_incomplete_record_blocks_the_automatic_certificate(self):
        self.boss.job_title = ''
        self.boss.save()
        r = self.c.post('/api/certificates/', {'kind': 'work'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertFalse(CertificateRequest.objects.exists())

    def test_waits_as_soon_as_someone_else_can_decide(self):
        self.accountant.managed_companies.add(self.solo)
        r = self.c.post('/api/profile-requests/', {'changes': {'city': 'Blida'}}, format='json')
        self.assertEqual(r.data['status'], 'pending')
        self.assertTrue(Notification.objects.filter(user=self.accountant).exists())

    def test_a_manager_above_reviews_the_leave(self):
        chief = User.objects.create_user('direction', password=self.password, company=self.solo,
                                         role=User.Role.MANAGER)
        self.boss.manager = chief
        self.boss.save()
        r = self.c.post('/api/leaves/', sick_leave(f'{NEXT}-03-01'), format='json')
        self.assertEqual(r.data['status'], 'pending')

    def test_an_employee_never_approves_alone(self):
        self.assertEqual(self.client_for(self.staff).post('/api/leaves/', sick_leave(f'{NEXT}-03-01'),
                                                          format='json').data['status'], 'pending')
        nobody = Company.objects.create(name='Sans RH')
        worker = User.objects.create_user('seul', password=self.password, company=nobody)
        self.assertEqual(self.client_for(worker).post('/api/leaves/', sick_leave(f'{NEXT}-03-01'),
                                                      format='json').data['status'], 'pending')


class DeactivationTests(TwoCompaniesTestCase):
    """Someone who leaves no longer has anything waiting in the reviewers' queues."""

    def setUp(self):
        super().setUp()
        today = date.today()

        def leave(offset, **kw):
            day = today + timedelta(days=offset)
            return LeaveRequest.objects.create(employee=self.emp, leave_type='sick', start_date=day, end_date=day,
                                               days=1, **kw)
        self.pending = leave(30)
        self.planned = leave(60, status='approved')
        self.past = leave(-60, status='approved')
        self.profile = ProfileChangeRequest.objects.create(employee=self.emp, changes={'city': 'Oran'})
        self.cert = CertificateRequest.objects.create(employee=self.emp, kind='work')
        self.expense = ExpenseReport.objects.create(employee=self.emp, date=today, amount=Decimal('900'),
                                                    description='Taxi')

    def statuses(self):
        return [type(o).objects.get(id=o.id).status
                for o in [self.pending, self.planned, self.past, self.profile, self.cert, self.expense]]

    def test_leaving_cancels_what_was_waiting(self):
        hr = self.client_for(self.hr)
        self.assertEqual(hr.delete(f'/api/employees/{self.emp.id}/').status_code, 204)
        # Past absences stay in the history; expenses already spent are still owed.
        self.assertEqual(self.statuses(), ['cancelled', 'cancelled', 'approved', 'cancelled', 'cancelled', 'pending'])
        self.assertIn('4 demande(s) en cours annulée(s)', AuditLog.objects.get(action='employee.deactivate').summary)
        to_review = hr.get('/api/dashboard/').data['to_review']
        self.assertEqual((to_review['leaves'], to_review['profile_requests'], to_review['certificates']), (0, 0, 0))

    def test_same_from_the_employee_form(self):
        r = self.client_for(self.hr).patch(f'/api/employees/{self.emp.id}/', {'is_active': False}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(self.statuses(), ['cancelled', 'cancelled', 'approved', 'cancelled', 'cancelled', 'pending'])

    def test_other_edits_cancel_nothing(self):
        self.client_for(self.hr).patch(f'/api/employees/{self.emp.id}/', {'city': 'Oran'}, format='json')
        self.assertEqual(self.statuses(), ['pending', 'approved', 'approved', 'pending', 'pending', 'pending'])

    def test_no_certificate_for_someone_who_left(self):
        self.emp.hire_date, self.emp.job_title, self.emp.is_active = date(2022, 1, 10), 'Commercial', False
        self.emp.save()
        r = self.client_for(self.hr).post(f'/api/certificates/{self.cert.id}/approve/')
        self.assertEqual(r.status_code, 400)
        self.assertIn("quitté l'entreprise", str(r.data))


class ReviewCountTests(TwoCompaniesTestCase):
    """What the dashboards announce is exactly what the reviewer finds in the queues, and can decide."""

    def setUp(self):
        super().setUp()
        self.client_for(self.emp).post('/api/leaves/', sick_leave(f'{NEXT}-03-01'), format='json')
        self.client_for(self.other).post('/api/expenses/', {'date': date.today().isoformat(), 'amount': '500',
                                                            'description': 'Bus'}, format='json')
        self.client_for(self.emp).post('/api/profile-requests/', {'changes': {'city': 'Oran'}}, format='json')
        self.client_for(self.other).post('/api/certificates/', {'kind': 'work'}, format='json')
        # The HR user's own requests go to the accountant.
        hr = self.client_for(self.hr)
        hr.post('/api/leaves/', sick_leave(f'{NEXT}-04-01'), format='json')
        hr.post('/api/profile-requests/', {'changes': {'city': 'Tipaza'}}, format='json')
        hr.post('/api/certificates/', {'kind': 'work'}, format='json')

    QUEUES = [('leaves', 'leaves'), ('expenses', 'expenses'), ('profile_requests', 'profile-requests'),
              ('certificates', 'certificates')]

    def queues(self, client, **extra):
        return {key: len(client.get(f'/api/{path}/?scope=team&status=pending', **extra).data)
                for key, path in self.QUEUES}

    def test_hr(self):
        hr = self.client_for(self.hr)
        to_review = hr.get('/api/dashboard/').data['to_review']
        self.assertEqual(to_review, {'leaves': 1, 'expenses': 1, 'profile_requests': 1, 'certificates': 1})
        self.assertEqual(to_review, self.queues(hr))

    def test_manager(self):
        c = self.client_for(self.manager)
        self.assertEqual(c.get('/api/dashboard/').data['to_review'], {'leaves': 1, 'expenses': 0})
        self.assertEqual(len(c.get('/api/leaves/?scope=team&status=pending').data), 1)
        self.assertEqual(len(c.get('/api/expenses/?scope=team&status=pending').data), 0)

    def test_accountant(self):
        c = self.client_for(self.accountant)
        to_review = c.get('/api/dashboard/', **self.header()).data['to_review']
        self.assertEqual(to_review, {'leaves': 2, 'expenses': 1, 'profile_requests': 2, 'certificates': 2})
        self.assertEqual(to_review, self.queues(c, **self.header()))
        row = next(r for r in c.get('/api/companies/overview/').data if r['id'] == self.company.id)
        self.assertEqual((row['pending_leaves'], row['pending_expenses'], row['pending_profile'],
                          row['pending_certificates']), (2, 1, 2, 2))

    def test_everything_announced_can_be_decided(self):
        hr = self.client_for(self.hr)
        for _, path in self.QUEUES:
            for item in hr.get(f'/api/{path}/?scope=team&status=pending').data:
                r = hr.post(f"/api/{path}/{item['id']}/reject/", {'comment': 'Test'}, format='json')
                self.assertEqual(r.status_code, 200, (path, r.data))
        self.assertEqual(hr.get('/api/dashboard/').data['to_review'],
                         {'leaves': 0, 'expenses': 0, 'profile_requests': 0, 'certificates': 0})
        # Each employee is told, with the reason.
        n = Notification.objects.filter(user=self.emp, title__icontains='refusée').order_by('id')
        self.assertEqual(n.count(), 2)


class LeaveCancellationTests(TwoCompaniesTestCase):
    def setUp(self):
        super().setUp()
        r = self.client_for(self.emp).post('/api/leaves/', {'leave_type': 'sick', 'start_date': f'{NEXT}-03-01',
                                                            'end_date': f'{NEXT}-03-02'}, format='json')
        self.lid = r.data['id']
        self.client_for(self.manager).post(f'/api/leaves/{self.lid}/approve/')
        Notification.objects.all().delete()

    def test_hr_cancelling_tells_the_employee_and_the_journal(self):
        r = self.client_for(self.hr).post(f'/api/leaves/{self.lid}/cancel/')
        self.assertEqual((r.status_code, r.data['status']), (200, 'cancelled'))
        self.assertEqual(Notification.objects.get(user=self.emp).title, 'Votre absence a été annulée')
        self.assertTrue(AuditLog.objects.filter(action='leave.cancel', company=self.company).exists())

    def test_employee_cancelling_an_approved_leave_tells_the_approver(self):
        self.client_for(self.emp).post(f'/api/leaves/{self.lid}/cancel/')
        self.assertTrue(Notification.objects.filter(user=self.manager, title__startswith='Absence annulée').exists())

    def test_cancelling_a_pending_request_bothers_nobody(self):
        r = self.client_for(self.emp).post('/api/leaves/', sick_leave(f'{NEXT}-05-03'), format='json')
        self.client_for(self.emp).post(f"/api/leaves/{r.data['id']}/cancel/")
        self.assertFalse(Notification.objects.filter(title__startswith='Absence annulée').exists())

    def test_manager_cannot_cancel(self):
        self.assertEqual(self.client_for(self.manager).post(f'/api/leaves/{self.lid}/cancel/').status_code, 403)

    def test_cannot_be_cancelled_twice(self):
        self.client_for(self.hr).post(f'/api/leaves/{self.lid}/cancel/')
        self.assertEqual(self.client_for(self.hr).post(f'/api/leaves/{self.lid}/cancel/').status_code, 400)


class ExpenseRulesTests(TwoCompaniesTestCase):
    def test_not_dated_in_the_future(self):
        r = self.client_for(self.emp).post('/api/expenses/', {
            'date': (date.today() + timedelta(days=1)).isoformat(), 'amount': '500', 'description': 'Bus'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_decided_once(self):
        r = self.client_for(self.emp).post('/api/expenses/', {'date': date.today().isoformat(), 'amount': '500',
                                                              'description': 'Bus'}, format='json')
        manager = self.client_for(self.manager)
        self.assertEqual(manager.post(f"/api/expenses/{r.data['id']}/approve/").status_code, 200)
        self.assertEqual(manager.post(f"/api/expenses/{r.data['id']}/reject/").status_code, 400)
        self.assertEqual(self.client_for(self.emp).post(f"/api/expenses/{r.data['id']}/cancel/").status_code, 400)
