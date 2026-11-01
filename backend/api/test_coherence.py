"""Cross-cutting rules: who may do what, and invariants of the payroll engine."""
from datetime import date
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import SimpleTestCase
from rest_framework.test import APIClient

from .models import Company, Document, LeaveRequest, Notification, Payslip, ProfileChangeRequest, User
from .payroll import (
    Bonus, compute_irg, compute_payslip, count_leave_days, overlap_days, working_days_in_month,
)
from .tests import ApiTestCase


class TwoCompaniesTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.other_co = Company.objects.create(name='Autre SARL')
        self.other_hr = User.objects.create_user('rh2', password=self.password, company=self.other_co, role=User.Role.HR)
        self.other_emp = User.objects.create_user('emp2', password=self.password, company=self.other_co,
                                                  base_salary=Decimal('60000'))
        self.accountant = User.objects.create_user('compta', password=self.password, role=User.Role.ACCOUNTANT)
        self.accountant.managed_companies.set([self.company])
        self.admin = User.objects.create_user('admin', password=self.password, role=User.Role.ADMIN)

    def header(self, company=None):
        return {'HTTP_X_COMPANY': str((company or self.company).id)}


class SystemAdminScopeTests(TwoCompaniesTestCase):
    """The platform admin runs the system: companies, accounts, global figures. Never HR data."""

    def setUp(self):
        super().setUp()
        self.client_for(self.hr).post('/api/payslips/run/', {'year': 2026, 'month': 10, 'publish': True}, format='json')
        self.payslip = Payslip.objects.get(employee=self.emp)
        self.doc = Document.objects.create(company=self.company, employee=self.emp, title='Contrat',
                                           file=SimpleUploadedFile('c.pdf', b'x'))
        self.leave = LeaveRequest.objects.create(employee=self.emp, leave_type='sick', start_date=date(2026, 3, 1),
                                                 end_date=date(2026, 3, 1), days=1)
        self.superuser = User.objects.create_superuser('root', password=self.password)

    def admins(self):
        return [self.client_for(self.admin), self.client_for(self.superuser)]

    def test_profile_exposes_no_hr_rights(self):
        for c in self.admins():
            me = c.get('/api/auth/me/').data
            self.assertTrue(me['is_platform_admin'])
            self.assertFalse(me['is_hr'])
            self.assertEqual(me['companies'], [])

    def test_employee_records_are_off_limits(self):
        for c in self.admins():
            self.assertEqual(c.get('/api/employees/', **self.header()).status_code, 403)
            self.assertEqual(c.get(f'/api/employees/{self.emp.id}/', **self.header()).status_code, 403)
            self.assertEqual(c.post('/api/employees/', {'username': 'x'}, format='json', **self.header()).status_code, 403)

    def test_employer_identity_is_off_limits(self):
        for c in self.admins():
            self.assertIsNone(c.get('/api/company/', **self.header()).data)
            self.assertEqual(c.patch('/api/company/', {'name': 'X'}, format='json', **self.header()).status_code, 403)

    def test_payroll_is_off_limits(self):
        for c in self.admins():
            self.assertEqual(c.post('/api/payslips/run/', {'year': 2026, 'month': 11}, format='json',
                                    **self.header()).status_code, 403)
            self.assertEqual(c.get('/api/payslips/?scope=all', **self.header()).data, [])
            self.assertEqual(c.get(f'/api/payslips/{self.payslip.id}/', **self.header()).status_code, 404)
            self.assertEqual(c.get(f'/api/payslips/{self.payslip.id}/pdf/', **self.header()).status_code, 404)
            self.assertEqual(c.get('/api/payslips/summary/?year=2026&month=10', **self.header()).status_code, 403)

    def test_documents_are_off_limits(self):
        for c in self.admins():
            self.assertEqual(c.get(f'/api/documents/{self.doc.id}/download/', **self.header()).status_code, 404)
            self.assertEqual(c.get('/api/documents/?scope=all', **self.header()).data, [])

    def test_requests_are_off_limits(self):
        for c in self.admins():
            self.assertEqual(c.get('/api/leaves/?scope=all', **self.header()).status_code, 403)
            self.assertEqual(c.post(f'/api/leaves/{self.leave.id}/approve/', **self.header()).status_code, 404)
            self.assertEqual(c.get('/api/profile-requests/?scope=all', **self.header()).status_code, 403)
            self.assertEqual(c.get('/api/leaves/calendar/?year=2026&month=3', **self.header()).data['people'], [])

    def test_keeps_supervision(self):
        c = self.client_for(self.admin)
        stats = c.get('/api/platform/stats/').data
        self.assertEqual(stats['totals']['companies'], 2)
        overview = c.get('/api/companies/overview/').data
        self.assertEqual(len(overview), 2)
        self.assertEqual(c.delete(f'/api/companies/{self.other_co.id}/').status_code, 204)
        self.assertEqual(c.post(f'/api/companies/{self.other_co.id}/reactivate/').status_code, 200)
        self.assertEqual(c.get('/api/platform/users/').status_code, 200)

    def test_does_not_create_or_edit_employers(self):
        c = self.client_for(self.admin)
        self.assertEqual(c.post('/api/companies/', {'name': 'X'}, format='json').status_code, 403)
        self.assertEqual(c.patch(f'/api/companies/{self.company.id}/', {'name': 'X'}, format='json').status_code, 403)

    def test_cannot_lock_himself_out(self):
        c = self.client_for(self.admin)
        url = f'/api/platform/users/{self.admin.id}/'
        self.assertEqual(c.patch(url, {'role': 'accountant'}, format='json').status_code, 400)
        self.assertEqual(c.patch(url, {'is_active': False}, format='json').status_code, 400)
        self.assertEqual(c.delete(url).status_code, 400)

    def test_promoting_to_admin_drops_company_assignments(self):
        r = self.client_for(self.admin).patch(f'/api/platform/users/{self.accountant.id}/', {'role': 'admin'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(self.accountant.managed_companies.count(), 0)


class CompanyLifecycleTests(TwoCompaniesTestCase):
    def deactivate(self):
        self.client_for(self.admin).delete(f'/api/companies/{self.company.id}/')
        self.company.refresh_from_db()

    def token(self, username):
        return APIClient().post('/api/auth/login/', {'username': username, 'password': self.password})

    def test_accountant_cannot_toggle_activation(self):
        self.deactivate()
        r = self.client_for(self.accountant).patch(f'/api/companies/{self.company.id}/', {'is_active': True}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.company.refresh_from_db()
        self.assertFalse(self.company.is_active)
        self.assertEqual(self.client_for(self.accountant).post(f'/api/companies/{self.company.id}/reactivate/').status_code, 403)

    def test_login_refused_once_deactivated(self):
        self.assertEqual(self.token('emp').status_code, 200)
        self.deactivate()
        self.assertEqual(self.token('emp').status_code, 401)
        self.assertEqual(self.token('emp2').status_code, 200)     # other companies are unaffected
        self.assertEqual(self.token('compta').status_code, 200)   # the accountant has other clients

    def test_open_session_stops_working_once_deactivated(self):
        access = self.token('emp').data['access']
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        self.assertEqual(c.get('/api/dashboard/').status_code, 200)
        self.deactivate()
        self.assertEqual(c.get('/api/dashboard/').status_code, 403)

    def test_accountant_cannot_work_on_it(self):
        self.deactivate()
        c = self.client_for(self.accountant)
        self.assertEqual(c.post('/api/payslips/run/', {'year': 2026, 'month': 10}, format='json',
                                **self.header()).status_code, 403)
        self.assertEqual(c.get('/api/auth/me/').data['companies'], [])
        self.assertEqual(len(c.get('/api/companies/').data), 1)   # still listed, marked inactive

    def test_reactivation_restores_access(self):
        self.deactivate()
        self.client_for(self.admin).post(f'/api/companies/{self.company.id}/reactivate/')
        self.assertEqual(self.token('emp').status_code, 200)


class TenantIsolationTests(TwoCompaniesTestCase):
    def test_document_cannot_be_reassigned_to_another_company(self):
        doc = Document.objects.create(company=self.company, employee=self.emp, title='Contrat',
                                      file=SimpleUploadedFile('c.pdf', b'x'))
        r = self.client_for(self.hr).patch(f'/api/documents/{doc.id}/', {'employee': self.other_emp.id}, format='json')
        self.assertEqual(r.status_code, 400)
        doc.refresh_from_db()
        self.assertEqual(doc.employee_id, self.emp.id)

    def test_foreign_document_cannot_be_edited_or_deleted(self):
        doc = Document.objects.create(company=self.other_co, employee=self.other_emp, title='Contrat',
                                      file=SimpleUploadedFile('c.pdf', b'x'))
        c = self.client_for(self.hr)
        self.assertEqual(c.patch(f'/api/documents/{doc.id}/', {'title': 'X'}, format='json').status_code, 404)
        self.assertEqual(c.delete(f'/api/documents/{doc.id}/').status_code, 404)

    def test_accountant_only_reaches_managed_companies(self):
        c = self.client_for(self.accountant)
        self.assertEqual(c.get(f'/api/companies/{self.other_co.id}/').status_code, 404)
        self.assertEqual(c.patch(f'/api/companies/{self.other_co.id}/', {'name': 'X'}, format='json').status_code, 404)
        p = Payslip.objects.create(employee=self.other_emp, company=self.other_co, year=2026, month=1)
        self.assertEqual(c.get(f'/api/payslips/{p.id}/', **self.header(self.other_co)).status_code, 404)

    def test_notifications_stay_inside_the_company(self):
        self.client_for(self.hr).post('/api/documents/', {'title': 'Note', 'category': 'company',
                                                          'file': SimpleUploadedFile('n.pdf', b'x')}, format='multipart')
        self.assertTrue(Notification.objects.filter(user=self.emp).exists())
        self.assertFalse(Notification.objects.filter(user=self.other_emp).exists())

    def test_publish_month_is_scoped(self):
        self.client_for(self.other_hr).post('/api/payslips/run/', {'year': 2026, 'month': 10}, format='json')
        r = self.client_for(self.hr).post('/api/payslips/publish_month/', {'year': 2026, 'month': 10}, format='json')
        self.assertEqual(r.data['published'], 0)
        self.assertFalse(Payslip.objects.filter(status='published').exists())


class InputValidationTests(TwoCompaniesTestCase):
    def test_bad_period_is_a_400_not_a_crash(self):
        hr = self.client_for(self.hr)
        for url in ['/api/leaves/calendar/?year=2026&month=13', '/api/leaves/calendar/?year=abc',
                    '/api/leaves/balances/?year=abc', f'/api/employees/{self.emp.id}/balances/?year=abc',
                    '/api/payslips/summary/?year=abc&month=1', '/api/payslips/summary/', '/api/payslips/?year=abc',
                    '/api/leaves/?year=abc', '/api/payslips/?scope=all&month=abc', '/api/payslips/?scope=all&employee=abc']:
            self.assertEqual(hr.get(url).status_code, 400, url)
        r = hr.post('/api/payslips/publish_month/', {'year': 'abc', 'month': 1}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_company_settings_are_validated(self):
        hr = self.client_for(self.hr)
        for payload in [{'weekend_days': [9]}, {'weekend_days': 'vendredi'}, {'weekend_days': [0, 1, 2, 3, 4, 5, 6]},
                        {'annual_leave_days': '-1'}]:
            self.assertEqual(hr.patch('/api/company/', payload, format='json').status_code, 400, payload)
        self.assertEqual(hr.patch('/api/company/', {'weekend_days': [4, 5]}, format='json').status_code, 200)

    def test_salary_cannot_be_negative(self):
        r = self.client_for(self.hr).patch(f'/api/employees/{self.emp.id}/', {'base_salary': '-100'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_manager_must_hold_a_managing_role(self):
        hr = self.client_for(self.hr)
        r = hr.patch(f'/api/employees/{self.emp.id}/', {'manager': self.other.id}, format='json')
        self.assertEqual(r.status_code, 400)
        r = hr.patch(f'/api/employees/{self.other.id}/', {'manager': self.manager.id}, format='json')
        self.assertEqual(r.status_code, 200, r.data)

    def test_empty_employee_list_pays_nobody(self):
        r = self.client_for(self.hr).post('/api/payslips/run/', {'year': 2026, 'month': 10, 'employees': []}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['created'], [])

    def test_hr_cannot_lock_himself_out(self):
        hr = self.client_for(self.hr)
        self.assertEqual(hr.patch(f'/api/employees/{self.hr.id}/', {'is_active': False}, format='json').status_code, 400)
        self.assertEqual(hr.patch(f'/api/employees/{self.hr.id}/', {'role': 'employee'}, format='json').status_code, 400)


class AccountWithoutCompanyTests(TwoCompaniesTestCase):
    def test_no_personal_requests(self):
        c = self.client_for(self.accountant)
        r = c.post('/api/profile-requests/', {'changes': {'city': 'Oran'}}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertFalse(ProfileChangeRequest.objects.exists())
        self.assertEqual(c.post('/api/leaves/', {'leave_type': 'sick', 'start_date': '2026-03-01',
                                                 'end_date': '2026-03-01'}, format='json').status_code, 400)
        self.assertEqual(c.post('/api/expenses/', {'date': '2026-10-10', 'amount': '10', 'description': 'x'},
                                format='json').status_code, 400)

    def test_calendar_does_not_list_other_accounts_without_company(self):
        other = User.objects.create_user('compta2', password=self.password, role=User.Role.ACCOUNTANT)
        data = self.client_for(self.admin).get('/api/leaves/calendar/?year=2026&month=3').data
        self.assertNotIn(other.id, [p['id'] for p in data['people']])
        self.assertEqual(data['people'], [])


class DemoSeedTests(ApiTestCase):
    def setUp(self):
        pass

    def test_seed_matches_the_role_model(self):
        call_command('seed_demo', verbosity=0, stdout=open('/dev/null', 'w'))
        admin = User.objects.get(username='admin')
        self.assertFalse(admin.is_superuser)
        self.assertFalse(admin.is_staff)
        self.assertFalse(admin.is_hr)
        self.assertEqual(self.client_for(admin).get('/api/platform/stats/').data['totals']['companies'], 2)
        comptable = self.client_for(User.objects.get(username='comptable'))
        self.assertEqual(len(comptable.get('/api/auth/me/').data['companies']), 2)
        self.assertTrue(Payslip.objects.filter(status='published').exists())


class PayrollInvariantTests(SimpleTestCase):
    SALARIES = ['24000', '30000', '33000', '35000', '38000', '44000', '68000', '120000', '250000', '500000']

    def test_net_always_reconciles_with_the_lines(self):
        for salary in self.SALARIES:
            for unpaid in ['0', '1.5', '10']:
                r = compute_payslip(Decimal(salary), [
                    Bonus('PRI', Decimal('6000')),
                    Bonus('Panier', Decimal('2400'), contributory=False),
                    Bonus('PRC', Decimal('9000'), tax='flat'),
                    Bonus('Famille', Decimal('1500'), contributory=False, tax='exempt'),
                ], unpaid_days=Decimal(unpaid))
                self.assertEqual(r.net_salary, r.gross_salary - r.social_contributions - r.income_tax
                                 - r.flat_tax + r.non_taxable)
                self.assertEqual(r.net_salary, sum((l.employee_amount for l in r.lines), Decimal('0')))
                self.assertEqual(r.employer_cost, r.gross_salary + r.non_taxable + r.employer_contributions)

    def test_a_raise_never_lowers_the_net(self):
        for disabled in (False, True):
            previous = Decimal('0')
            for salary in range(24000, 80000, 250):
                net = compute_payslip(Decimal(salary), disabled=disabled).net_salary
                self.assertGreaterEqual(net, previous, f'{salary} disabled={disabled}')
                previous = net

    def test_irg_rounds_the_base_down_to_ten_dinars(self):
        self.assertEqual(compute_irg(Decimal('60009.99')), compute_irg(Decimal('60000')))

    def test_irg_top_bracket(self):
        # 4 600 + 10 800 + 24 000 + 52 800 + 180 000 * 35 % = 155 200, minus the 1 500 cap
        self.assertEqual(compute_irg(Decimal('500000')), Decimal('153700.00'))

    def test_allowance_floor_and_cap(self):
        # 35 000: 3 450 of tax, 40 % = 1 380 is kept. 32 000 is smoothed from 2 760 - 1 104.
        self.assertEqual(compute_irg(Decimal('35000')), Decimal('2070.00'))
        self.assertEqual(compute_irg(Decimal('300000')), compute_irg(Decimal('300000.09')))

    def test_disabled_smoothing_is_continuous_at_its_ceiling(self):
        self.assertAlmostEqual(compute_irg(Decimal('42490'), disabled=True), compute_irg(Decimal('42500')),
                               delta=Decimal('5'))

    def test_employer_share_is_25_plus_half_percent(self):
        r = compute_payslip(Decimal('100000'))
        self.assertEqual(r.employer_contributions, Decimal('25500.00'))

    def test_unpaid_days_cannot_exceed_the_base_salary(self):
        r = compute_payslip(Decimal('44000'), unpaid_days=Decimal('40'))
        self.assertEqual(r.gross_salary, Decimal('0.00'))
        self.assertEqual(r.net_salary, Decimal('0.00'))

    def test_zero_bonus_prints_no_line(self):
        r = compute_payslip(Decimal('44000'), [Bonus('Rien', Decimal('0'))])
        self.assertNotIn('Rien', [l.label for l in r.lines])

    def test_flat_bonus_outside_cnas(self):
        r = compute_payslip(Decimal('68000'), [Bonus('Prime', Decimal('1000'), contributory=False, tax='flat')])
        self.assertEqual(r.flat_tax, Decimal('100.00'))
        self.assertEqual(r.social_contributions, Decimal('6120.00'))

    def test_exempt_but_contributory_stays_in_gross_only(self):
        r = compute_payslip(Decimal('68000'), [Bonus('Prime', Decimal('1000'), tax='exempt')])
        self.assertEqual(r.gross_salary, Decimal('69000.00'))
        self.assertEqual(r.social_contributions, Decimal('6210.00'))
        self.assertEqual(r.taxable_salary, Decimal('61880.00'))
        self.assertEqual(r.non_taxable, Decimal('0'))


class LeaveCountTests(SimpleTestCase):
    WEEKEND = [4, 5]

    def test_reversed_period(self):
        self.assertEqual(count_leave_days(date(2026, 11, 5), date(2026, 11, 1), self.WEEKEND), Decimal('0'))

    def test_weekend_only_period(self):
        self.assertEqual(count_leave_days(date(2026, 11, 6), date(2026, 11, 7), self.WEEKEND), Decimal('0'))

    def test_half_day_on_a_weekend_removes_nothing(self):
        self.assertEqual(count_leave_days(date(2026, 11, 7), date(2026, 11, 8), self.WEEKEND, start_half=True), Decimal('1'))

    def test_working_days_in_a_month(self):
        self.assertEqual(working_days_in_month(2026, 11, self.WEEKEND), Decimal('22'))

    def test_overlap_keeps_half_days_only_on_real_ends(self):
        # 29/10 (Thu) to 3/11 (Tue), half days on both ends.
        args = (date(2026, 10, 29), date(2026, 11, 3))
        self.assertEqual(overlap_days(*args, 2026, 10, self.WEEKEND, True, True), Decimal('0.5'))
        self.assertEqual(overlap_days(*args, 2026, 11, self.WEEKEND, True, True), Decimal('2.5'))
        self.assertEqual(overlap_days(*args, 2026, 12, self.WEEKEND, True, True), Decimal('0'))
