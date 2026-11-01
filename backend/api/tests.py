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
        # Published worked example: gross 34 500 -> taxable 31 395 -> IRG 731.7
        self.assertEqual(compute_irg(Decimal('31395')), Decimal('731.72'))
        self.assertLess(compute_irg(Decimal('34990')), Decimal('2070.00'))
        self.assertLess(compute_irg(Decimal('30010')), Decimal('20'))

    def test_full_payslip(self):
        r = compute_payslip(Decimal('68000'), [Bonus('Prime', Decimal('6000')),
                                               Bonus('Allocations', Decimal('3000'), contributory=False, tax='exempt')])
        self.assertEqual(r.gross_salary, Decimal('74000.00'))
        self.assertEqual(r.social_contributions, Decimal('6660.00'))
        self.assertEqual(r.taxable_salary, Decimal('67340.00'))
        self.assertEqual(r.income_tax, Decimal('10481.80'))
        self.assertEqual(r.net_salary, Decimal('59858.20'))
        # 25 % CNAS + 0.5 % FNPOS on 74 000
        self.assertEqual(r.employer_contributions, Decimal('18870.00'))
        self.assertEqual(r.employer_cost, Decimal('95870.00'))
        self.assertEqual(r.warnings, [])

    def test_panier_is_taxable_but_not_contributory(self):
        r = compute_payslip(Decimal('68000'), [Bonus('Panier', Decimal('2400'), contributory=False, tax='scale')])
        self.assertEqual(r.social_contributions, Decimal('6120.00'))   # 9 % of 68 000 only
        self.assertEqual(r.taxable_salary, Decimal('64280.00'))        # 70 400 - 6 120

    def test_quarterly_bonus_flat_10_percent(self):
        r = compute_payslip(Decimal('68000'), [Bonus('PRC', Decimal('9000'), contributory=True, tax='flat')])
        self.assertEqual(r.flat_tax, Decimal('819.00'))                # 10 % of 9 000 net of 9 % CNAS
        self.assertEqual(r.taxable_salary, Decimal('61880.00'))        # scale base excludes the bonus
        self.assertEqual(r.income_tax, compute_irg(Decimal('61880')))

    def test_disabled_worker_extended_smoothing(self):
        # Standard: 40 300 -> 3 181; disabled: 3 181 x 93/61 - 81 213/41
        self.assertEqual(compute_irg(Decimal('40300')), Decimal('3181.00'))
        self.assertEqual(compute_irg(Decimal('40300'), disabled=True), Decimal('2868.92'))
        self.assertEqual(compute_irg(Decimal('30000'), disabled=True), Decimal('0.00'))
        self.assertEqual(compute_irg(Decimal('50000'), disabled=True), compute_irg(Decimal('50000')))

    def test_snmg_warning(self):
        self.assertTrue(compute_payslip(Decimal('20000')).warnings)
        self.assertFalse(compute_payslip(Decimal('24000')).warnings)

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


class MultiCompanyTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.other_co = Company.objects.create(name='Autre SARL')
        self.other_hr = User.objects.create_user('rh2', password=self.password, company=self.other_co, role=User.Role.HR)
        self.other_emp = User.objects.create_user('emp2', password=self.password, company=self.other_co,
                                                  base_salary=Decimal('60000'))
        self.accountant = User.objects.create_user('compta', password=self.password, role=User.Role.ACCOUNTANT)
        self.accountant.managed_companies.set([self.company])
        self.admin = User.objects.create_user('admin', password=self.password, role=User.Role.ADMIN)

    def test_hr_only_sees_own_company(self):
        ids = {e['id'] for e in self.client_for(self.hr).get('/api/employees/').data}
        self.assertIn(self.emp.id, ids)
        self.assertNotIn(self.other_emp.id, ids)
        # A forged X-Company header does not let HR into another company.
        r = self.client_for(self.hr).get('/api/employees/', HTTP_X_COMPANY=str(self.other_co.id))
        self.assertNotIn(self.other_emp.id, {e['id'] for e in r.data})
        self.assertEqual(self.client_for(self.hr).get(f'/api/employees/{self.other_emp.id}/').status_code, 404)

    def test_payroll_run_is_scoped(self):
        r = self.client_for(self.hr).post('/api/payslips/run/', {'year': 2026, 'month': 10}, format='json')
        self.assertEqual(len(r.data['created']), 2)
        self.assertFalse(Payslip.objects.filter(employee=self.other_emp).exists())
        r = self.client_for(self.hr).post('/api/payslips/run/', {'year': 2026, 'month': 10,
                                                                 'employees': [self.other_emp.id]}, format='json')
        self.assertEqual(r.data['created'], [])
        p = Payslip.objects.filter(company=self.company).first()
        self.assertEqual(self.client_for(self.other_hr).get(f'/api/payslips/{p.id}/').status_code, 404)

    def test_accountant_switches_between_managed_companies(self):
        c = self.client_for(self.accountant)
        ids = {e['id'] for e in c.get('/api/employees/', HTTP_X_COMPANY=str(self.company.id)).data}
        self.assertIn(self.emp.id, ids)
        # Not managed: falls back to a managed company, never the requested one.
        ids = {e['id'] for e in c.get('/api/employees/', HTTP_X_COMPANY=str(self.other_co.id)).data}
        self.assertNotIn(self.other_emp.id, ids)
        r = c.post('/api/companies/', {'name': 'Nouvelle EURL', 'city': 'Oran'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        new_id = r.data['id']
        self.assertIn(new_id, {x['id'] for x in c.get('/api/companies/').data})
        r = c.post('/api/employees/', {'username': 'recrue', 'password': 'Un-mot-de-passe-42', 'base_salary': '50000'},
                   format='json', HTTP_X_COMPANY=str(new_id))
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(User.objects.get(username='recrue').company_id, new_id)
        self.assertEqual(c.delete(f'/api/companies/{new_id}/').status_code, 403)

    def test_employee_cannot_create_company_or_see_platform(self):
        c = self.client_for(self.emp)
        self.assertEqual(c.post('/api/companies/', {'name': 'X'}, format='json').status_code, 403)
        self.assertEqual(c.get('/api/platform/stats/').status_code, 403)
        self.assertEqual(self.client_for(self.accountant).get('/api/platform/stats/').status_code, 403)

    def test_hr_cannot_grant_platform_roles(self):
        r = self.client_for(self.hr).patch(f'/api/employees/{self.emp.id}/', {'role': 'admin'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_admin_sees_everything(self):
        c = self.client_for(self.admin)
        r = c.get('/api/platform/stats/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['totals']['companies'], 2)
        self.assertEqual(len(c.get('/api/companies/').data), 2)
        ids = {e['id'] for e in c.get('/api/employees/', HTTP_X_COMPANY=str(self.other_co.id)).data}
        self.assertIn(self.other_emp.id, ids)
        r = c.post('/api/platform/users/', {'username': 'cab', 'password': 'Un-mot-de-passe-42', 'role': 'accountant',
                                            'companies': [self.other_co.id]}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(list(User.objects.get(username='cab').managed_companies.all()), [self.other_co])
        r = c.post('/api/platform/users/', {'username': 'x', 'password': 'Un-mot-de-passe-42', 'role': 'employee'},
                   format='json')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(c.delete(f'/api/companies/{self.other_co.id}/').status_code, 204)

    def test_company_documents_do_not_leak(self):
        self.client_for(self.other_hr).post('/api/documents/', {
            'title': 'Note interne', 'category': 'company', 'file': SimpleUploadedFile('n.pdf', b'x')}, format='multipart')
        self.assertEqual(self.client_for(self.emp).get('/api/documents/').data, [])
        self.assertEqual(len(self.client_for(self.other_emp).get('/api/documents/').data), 1)

    def test_manager_cannot_review_other_company(self):
        lr = LeaveRequest.objects.create(employee=self.other_emp, leave_type='sick', start_date=date(2026, 3, 1),
                                         end_date=date(2026, 3, 1), days=1)
        self.assertEqual(self.client_for(self.hr).post(f'/api/leaves/{lr.id}/approve/').status_code, 404)
