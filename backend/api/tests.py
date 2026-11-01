from datetime import date, timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from .models import (
    Company, Document, ExpenseReport, LeaveBalance, LeaveRequest, Notification, Payslip, ProfileChangeRequest, User,
)
from .payroll import compute_irg, compute_payslip, count_leave_days, Bonus


class PayrollEngineTests(TestCase):
    def test_irg_exempt_up_to_30000(self):
        self.assertEqual(compute_irg(Decimal('30000')), Decimal('0.00'))
        self.assertEqual(compute_irg(Decimal('15000')), Decimal('0.00'))

    def test_irg_scale_and_allowance_cap(self):
        # 4600 + 20000*27% = 10000 gross tax, allowance capped at 1500
        self.assertEqual(compute_irg(Decimal('60000')), Decimal('8500.00'))
        self.assertEqual(compute_irg(Decimal('100000')), Decimal('19900.00'))

    def test_irg_smoothing_is_continuous_at_35000(self):
        self.assertEqual(compute_irg(Decimal('35000')), Decimal('2070.00'))
        self.assertLess(compute_irg(Decimal('34990')), Decimal('2070.00'))
        self.assertLess(compute_irg(Decimal('30010')), Decimal('20'))

    def test_full_payslip(self):
        r = compute_payslip(Decimal('68000'), [Bonus('Prime', Decimal('6000')),
                                               Bonus('Panier', Decimal('3000'), contributory=False, taxable=False)])
        self.assertEqual(r.gross_salary, Decimal('74000.00'))
        self.assertEqual(r.social_contributions, Decimal('6660.00'))
        self.assertEqual(r.taxable_salary, Decimal('67340.00'))
        self.assertEqual(r.income_tax, Decimal('10481.80'))
        self.assertEqual(r.net_salary, Decimal('59858.20'))
        self.assertEqual(r.employer_cost, Decimal('96240.00'))

    def test_unpaid_days_reduce_gross(self):
        r = compute_payslip(Decimal('44000'), unpaid_days=Decimal('2'))
        self.assertEqual(r.gross_salary, Decimal('40000.00'))

    def test_leave_day_count_skips_friday_saturday(self):
        # 2026-11-01 is a Sunday; Sun..Sat = 5 working days in Algeria
        self.assertEqual(count_leave_days(date(2026, 11, 1), date(2026, 11, 7), [4, 5]), Decimal('5'))
        self.assertEqual(count_leave_days(date(2026, 11, 1), date(2026, 11, 1), [4, 5], start_half=True),
                         Decimal('0.5'))
        self.assertEqual(count_leave_days(date(2026, 11, 1), date(2026, 11, 2), [4, 5], True, True), Decimal('1'))


class ApiTestCase(TestCase):
    password = 'Motdepasse-solide-42'

    def setUp(self):
        self.company = Company.objects.create(name='Test SARL')
        self.hr = self.make('rh', role=User.Role.HR)
        self.manager = self.make('chef', role=User.Role.MANAGER)
        self.emp = self.make('emp', manager=self.manager, base_salary=Decimal('50000'))
        self.other = self.make('autre', base_salary=Decimal('40000'))

    def make(self, username, **kw):
        u = User(username=username, company=self.company, email=f'{username}@test.dz', **kw)
        u.set_password(self.password)
        u.save()
        return u

    def client_for(self, user):
        c = APIClient()
        c.force_authenticate(user)
        return c


class AuthTests(ApiTestCase):
    def test_login_with_username_or_email(self):
        c = APIClient()
        r = c.post('/api/auth/login/', {'username': 'emp', 'password': self.password})
        self.assertEqual(r.status_code, 200)
        r = c.post('/api/auth/login/', {'username': 'emp@test.dz', 'password': self.password})
        self.assertEqual(r.status_code, 200)
        self.assertIn('access', r.data)

    def test_anonymous_is_rejected(self):
        self.assertEqual(APIClient().get('/api/dashboard/').status_code, 401)

    def test_me_only_updates_self_editable_fields(self):
        c = self.client_for(self.emp)
        r = c.patch('/api/auth/me/', {'phone': '0555', 'iban': 'HACK', 'role': 'hr'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.phone, '0555')
        self.assertEqual(self.emp.iban, '')
        self.assertEqual(self.emp.role, User.Role.EMPLOYEE)

    def test_change_password(self):
        c = self.client_for(self.emp)
        r = c.post('/api/auth/change-password/', {'current_password': 'faux', 'new_password': 'Nouveau-mdp-2026'})
        self.assertEqual(r.status_code, 400)
        r = c.post('/api/auth/change-password/', {'current_password': self.password, 'new_password': 'Nouveau-mdp-2026'})
        self.assertEqual(r.status_code, 204)


class PayslipApiTests(ApiTestCase):
    def run_month(self, publish=False):
        return self.client_for(self.hr).post('/api/payslips/run/', {'year': 2026, 'month': 10, 'publish': publish},
                                             format='json')

    def test_only_hr_can_run_payroll(self):
        r = self.client_for(self.emp).post('/api/payslips/run/', {'year': 2026, 'month': 10}, format='json')
        self.assertEqual(r.status_code, 403)

    def test_run_creates_drafts_hidden_from_employee_until_published(self):
        r = self.run_month()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.data['created']), 2)  # hr & manager have no salary -> skipped
        c = self.client_for(self.emp)
        self.assertEqual(c.get('/api/payslips/').data, [])
        p = Payslip.objects.get(employee=self.emp)
        self.client_for(self.hr).post(f'/api/payslips/{p.id}/publish/')
        self.assertEqual(len(c.get('/api/payslips/').data), 1)
        self.assertTrue(Notification.objects.filter(user=self.emp).exists())

    def test_published_payslip_is_not_regenerated(self):
        self.run_month(publish=True)
        r = self.run_month()
        self.assertEqual(r.data['created'], [])

    def test_employee_cannot_read_someone_elses_payslip(self):
        self.run_month(publish=True)
        p = Payslip.objects.get(employee=self.other)
        c = self.client_for(self.emp)
        self.assertEqual(c.get(f'/api/payslips/{p.id}/').status_code, 404)
        self.assertEqual(c.get(f'/api/payslips/{p.id}/pdf/').status_code, 404)

    def test_pdf_and_viewed_flag(self):
        self.run_month(publish=True)
        p = Payslip.objects.get(employee=self.emp)
        r = self.client_for(self.emp).get(f'/api/payslips/{p.id}/pdf/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertTrue(r.content.startswith(b'%PDF'))
        p.refresh_from_db()
        self.assertIsNotNone(p.viewed_at)

    def test_unpaid_leave_is_deducted(self):
        LeaveRequest.objects.create(employee=self.emp, leave_type='unpaid', start_date=date(2026, 10, 4),
                                    end_date=date(2026, 10, 5), days=2, status='approved')
        self.run_month()
        p = Payslip.objects.get(employee=self.emp)
        self.assertEqual(p.unpaid_days, Decimal('2'))
        self.assertLess(p.gross_salary, Decimal('50000'))


class LeaveApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.year = date.today().year + 1
        LeaveBalance.objects.create(employee=self.emp, leave_type='annual', year=self.year, allotted=5)

    def request(self, start, end, leave_type='annual'):
        return self.client_for(self.emp).post('/api/leaves/', {
            'leave_type': leave_type, 'start_date': start, 'end_date': end}, format='json')

    def test_request_computes_days_and_notifies_manager(self):
        r = self.request(f'{self.year}-03-01', f'{self.year}-03-03')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertGreater(Decimal(r.data['days']), 0)
        self.assertTrue(Notification.objects.filter(user=self.manager).exists())

    def test_insufficient_balance(self):
        r = self.request(f'{self.year}-03-01', f'{self.year}-03-31')
        self.assertEqual(r.status_code, 400)

    def test_overlap_rejected(self):
        self.request(f'{self.year}-03-01', f'{self.year}-03-02')
        r = self.request(f'{self.year}-03-02', f'{self.year}-03-03', leave_type='sick')
        self.assertEqual(r.status_code, 400)

    def test_manager_reviews_only_own_team(self):
        lr = LeaveRequest.objects.create(employee=self.other, leave_type='sick', start_date=date(2026, 3, 1),
                                         end_date=date(2026, 3, 1), days=1)
        r = self.client_for(self.manager).post(f'/api/leaves/{lr.id}/approve/')
        self.assertEqual(r.status_code, 404)
        r = self.request(f'{self.year}-03-01', f'{self.year}-03-01')
        r = self.client_for(self.manager).post(f"/api/leaves/{r.data['id']}/approve/", {'comment': 'OK'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['status'], 'approved')

    def test_employee_cannot_approve_own_request(self):
        r = self.request(f'{self.year}-03-01', f'{self.year}-03-01')
        r = self.client_for(self.emp).post(f"/api/leaves/{r.data['id']}/approve/")
        self.assertEqual(r.status_code, 403)

    def test_balance_and_team_list(self):
        self.request(f'{self.year}-03-01', f'{self.year}-03-01')
        b = self.client_for(self.emp).get(f'/api/leaves/balances/?year={self.year}').data
        annual = next(x for x in b if x['leave_type'] == 'annual')
        self.assertEqual(annual['pending'], Decimal('1'))
        team = self.client_for(self.manager).get('/api/leaves/?scope=team').data
        self.assertEqual(len(team), 1)
        self.assertEqual(self.client_for(self.emp).get('/api/leaves/?scope=all').status_code, 403)

    def test_calendar_hides_reason_from_colleagues(self):
        colleague = self.make('collegue', manager=self.manager)
        LeaveRequest.objects.create(employee=colleague, leave_type='sick', start_date=date(2026, 3, 1),
                                    end_date=date(2026, 3, 2), days=2, status='approved')
        data = self.client_for(self.emp).get('/api/leaves/calendar/?year=2026&month=3').data
        self.assertEqual(data['leaves'][0]['label'], 'Absent')
        data = self.client_for(self.manager).get('/api/leaves/calendar/?year=2026&month=3').data
        self.assertEqual(data['leaves'][0]['label'], 'Maladie')


class DocumentAndExpenseTests(ApiTestCase):
    def test_documents_visibility_and_download(self):
        hr = self.client_for(self.hr)
        f = SimpleUploadedFile('contrat.pdf', b'%PDF-1.4 test', content_type='application/pdf')
        r = hr.post('/api/documents/', {'employee': self.emp.id, 'title': 'Contrat', 'category': 'contract',
                                        'file': f}, format='multipart')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertNotIn('file', r.data)
        doc_id = r.data['id']
        hr.post('/api/documents/', {'title': 'Règlement', 'category': 'company',
                                    'file': SimpleUploadedFile('r.pdf', b'x')}, format='multipart')
        self.assertEqual(len(self.client_for(self.emp).get('/api/documents/').data), 2)
        self.assertEqual(len(self.client_for(self.other).get('/api/documents/').data), 1)
        self.assertEqual(self.client_for(self.other).get(f'/api/documents/{doc_id}/download/').status_code, 404)
        r = self.client_for(self.emp).get(f'/api/documents/{doc_id}/download/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b''.join(r.streaming_content), b'%PDF-1.4 test')
        self.assertIsNotNone(Document.objects.get(id=doc_id).viewed_at)
        r = self.client_for(self.emp).post('/api/documents/', {'title': 'x', 'file': SimpleUploadedFile('a', b'a')},
                                           format='multipart')
        self.assertEqual(r.status_code, 403)

    def test_expense_flow(self):
        c = self.client_for(self.emp)
        r = c.post('/api/expenses/', {'date': '2026-10-10', 'category': 'meals', 'amount': '1500',
                                      'description': 'Repas client'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        eid = r.data['id']
        self.assertEqual(self.client_for(self.hr).post(f'/api/expenses/{eid}/mark_paid/').status_code, 400)
        self.assertEqual(self.client_for(self.manager).post(f'/api/expenses/{eid}/approve/').status_code, 200)
        self.assertEqual(self.client_for(self.manager).post(f'/api/expenses/{eid}/mark_paid/').status_code, 403)
        r = self.client_for(self.hr).post(f'/api/expenses/{eid}/mark_paid/')
        self.assertEqual(r.data['status'], ExpenseReport.Status.PAID)

    def test_negative_expense_rejected(self):
        r = self.client_for(self.emp).post('/api/expenses/', {'date': '2026-10-10', 'amount': '-5',
                                                              'description': 'x'}, format='json')
        self.assertEqual(r.status_code, 400)


class ProfileRequestTests(ApiTestCase):
    def test_change_request_applied_on_approval(self):
        c = self.client_for(self.emp)
        r = c.post('/api/profile-requests/', {'changes': {'iban': 'DZ58 0001', 'city': 'Oran'}}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(c.post('/api/profile-requests/', {'changes': {'city': 'X'}}, format='json').status_code, 400)
        self.assertEqual(c.post(f"/api/profile-requests/{r.data['id']}/approve/").status_code, 403)
        self.client_for(self.hr).post(f"/api/profile-requests/{r.data['id']}/approve/")
        self.emp.refresh_from_db()
        self.assertEqual((self.emp.iban, self.emp.city), ('DZ58 0001', 'Oran'))

    def test_forbidden_fields_rejected(self):
        r = self.client_for(self.emp).post('/api/profile-requests/', {'changes': {'base_salary': '999999'}},
                                           format='json')
        self.assertEqual(r.status_code, 400)
        self.assertFalse(ProfileChangeRequest.objects.exists())


class EmployeeAdminTests(ApiTestCase):
    def test_hr_creates_and_deactivates_employee(self):
        hr = self.client_for(self.hr)
        r = hr.post('/api/employees/', {'username': 'nouveau', 'password': 'Un-mot-de-passe-42',
                                        'first_name': 'Sara', 'base_salary': '45000'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertNotIn('password', r.data)
        self.assertEqual(User.objects.get(username='nouveau').company, self.company)
        self.assertEqual(hr.delete(f"/api/employees/{r.data['id']}/").status_code, 204)
        self.assertFalse(User.objects.get(username='nouveau').is_active)

    def test_employee_cannot_list_employees(self):
        self.assertEqual(self.client_for(self.emp).get('/api/employees/').status_code, 403)

    def test_dashboard(self):
        r = self.client_for(self.manager).get('/api/dashboard/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('leaves', r.data['to_review'])
        self.assertEqual(r.data['balances'][0]['leave_type'], 'annual')
