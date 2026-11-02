"""Per-employee payroll, expenses in payroll, manager absences, certificates, password reset, audit."""
import re
from datetime import date
from decimal import Decimal

import arabic_reshaper
from bidi.algorithm import get_display
from django.core import mail
from django.test import override_settings
from rest_framework.test import APIClient

from .models import (
    AuditLog, CertificateRequest, Document, EmployeePayItem, ExpenseReport, LeaveRequest, MonthlyVariable, Payslip, User,
)
from .payroll import overtime_amount
from .pdf import certificate_text, render_certificate, render_payslip
from .test_coherence import TwoCompaniesTestCase


class PayItemTests(TwoCompaniesTestCase):
    def test_permanent_item_only_on_its_employee(self):
        hr = self.client_for(self.hr)
        r = hr.post('/api/pay-items/', {'employee': self.emp.id, 'label': 'Panier', 'label_ar': 'تعويض السلة',
                                        'amount': '3000', 'contributory': False, 'tax': 'scale'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        hr.post('/api/payslips/run/', {'year': 2026, 'month': 10}, format='json')
        p = Payslip.objects.get(employee=self.emp)
        self.assertEqual(p.gross_salary, Decimal('53000.00'))
        self.assertEqual(p.social_contributions, Decimal('4500.00'))   # 9 % of the 50 000 base only
        self.assertEqual(Payslip.objects.get(employee=self.other).gross_salary, Decimal('40000.00'))

    def test_inactive_item_is_ignored(self):
        EmployeePayItem.objects.create(employee=self.emp, label='IEP', amount=Decimal('1000'), is_active=False)
        self.client_for(self.hr).post('/api/payslips/run/', {'year': 2026, 'month': 10}, format='json')
        self.assertEqual(Payslip.objects.get(employee=self.emp).gross_salary, Decimal('50000.00'))

    def test_scoped_to_the_company(self):
        item = EmployeePayItem.objects.create(employee=self.other_emp, label='IEP', amount=Decimal('1000'))
        hr = self.client_for(self.hr)
        self.assertEqual(hr.get('/api/pay-items/').data, [])
        self.assertEqual(hr.delete(f'/api/pay-items/{item.id}/').status_code, 404)
        r = hr.post('/api/pay-items/', {'employee': self.other_emp.id, 'label': 'X', 'amount': '1'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_reserved_to_company_admins(self):
        for u in [self.emp, self.manager, self.admin]:
            self.assertEqual(self.client_for(u).get('/api/pay-items/').status_code, 403)

    def test_journal_tells_addition_change_and_removal_apart(self):
        hr = self.client_for(self.hr)
        item = hr.post('/api/pay-items/', {'employee': self.emp.id, 'label': 'IEP', 'amount': '1000'}, format='json').data
        hr.patch(f"/api/pay-items/{item['id']}/", {'amount': '1200'}, format='json')
        hr.delete(f"/api/pay-items/{item['id']}/")
        actions = list(AuditLog.objects.filter(action__startswith='payitem.').order_by('id').values_list('action', flat=True))
        self.assertEqual(actions, ['payitem.create', 'payitem.update', 'payitem.delete'])


class MonthlyVariableTests(TwoCompaniesTestCase):
    def save(self, rows, user=None):
        return self.client_for(user or self.hr).post('/api/payslips/variables/', {'year': 2026, 'month': 10, 'rows': rows},
                                                     format='json')

    def test_overtime_formula(self):
        # 50 000 / 173.33 h = 288.4671 DA/h, then +50 % on 10 hours.
        self.assertEqual(overtime_amount(Decimal('50000'), Decimal('10')), Decimal('4327.01'))
        self.assertEqual(overtime_amount(Decimal('50000'), Decimal('10'), Decimal('100')), Decimal('5769.34'))

    def test_overtime_and_bonus_reach_the_payslip(self):
        r = self.save([{'employee': self.emp.id, 'overtime_hours': '10', 'bonus_label': 'Prime projet', 'bonus_amount': '2000'}])
        self.assertEqual((r.status_code, r.data), (200, {'already_published': []}))
        self.client_for(self.hr).post('/api/payslips/run/', {'year': 2026, 'month': 10}, format='json')
        p = Payslip.objects.get(employee=self.emp)
        self.assertEqual(p.gross_salary, Decimal('56327.01'))
        self.assertIn('Prime projet', [l.label for l in p.lines.all()])
        self.assertTrue(any(l.label.startswith('Heures supplémentaires') for l in p.lines.all()))
        self.assertEqual(Payslip.objects.get(employee=self.other).gross_salary, Decimal('40000.00'))

    def test_other_month_is_not_affected(self):
        self.save([{'employee': self.emp.id, 'bonus_amount': '2000'}])
        self.client_for(self.hr).post('/api/payslips/run/', {'year': 2026, 'month': 11}, format='json')
        self.assertEqual(Payslip.objects.get(employee=self.emp).gross_salary, Decimal('50000.00'))

    def test_rate_below_the_legal_minimum_is_refused(self):
        self.assertEqual(self.save([{'employee': self.emp.id, 'overtime_hours': '5', 'overtime_rate': '25'}]).status_code, 400)

    def test_grid_lists_employees_and_clears_empty_rows(self):
        self.save([{'employee': self.emp.id, 'overtime_hours': '4'}])
        rows = self.client_for(self.hr).get('/api/payslips/variables/?year=2026&month=10').data
        self.assertEqual({r['employee'] for r in rows}, {self.emp.id, self.other.id})
        self.assertEqual(next(r for r in rows if r['employee'] == self.emp.id)['overtime_hours'], Decimal('4.00'))
        self.save([{'employee': self.emp.id, 'overtime_hours': '0'}])
        self.assertFalse(MonthlyVariable.objects.exists())

    def test_scoped_to_the_company(self):
        self.assertEqual(self.save([{'employee': self.other_emp.id, 'bonus_amount': '1'}]).status_code, 400)
        self.assertEqual(self.save([{'employee': self.emp.id, 'bonus_amount': '1'}], self.emp).status_code, 403)
        self.assertEqual(self.save([{'employee': self.emp.id, 'bonus_amount': '1'}], self.admin).status_code, 403)


class ExpenseInPayrollTests(TwoCompaniesTestCase):
    def setUp(self):
        super().setUp()
        self.expense = ExpenseReport.objects.create(employee=self.emp, date='2026-10-05', amount=Decimal('1500'),
                                                    description='Taxi', status=ExpenseReport.Status.APPROVED)

    def run_month(self, **extra):
        return self.client_for(self.hr).post('/api/payslips/run/', {'year': 2026, 'month': 10, **extra}, format='json')

    def test_repaid_with_the_payslip_on_top_of_net(self):
        self.run_month()
        p = Payslip.objects.get(employee=self.emp)
        self.assertEqual(p.gross_salary, Decimal('50000.00'))
        self.assertEqual(p.non_taxable, Decimal('1500.00'))
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.payslip, p)
        self.assertEqual(self.expense.status, ExpenseReport.Status.APPROVED)
        self.client_for(self.hr).post(f'/api/payslips/{p.id}/publish/')
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.status, ExpenseReport.Status.PAID)

    def test_regenerating_a_draft_does_not_count_it_twice(self):
        self.run_month()
        self.run_month()
        self.assertEqual(Payslip.objects.get(employee=self.emp).non_taxable, Decimal('1500.00'))

    def test_can_be_left_out_of_the_run(self):
        self.run_month(include_expenses=False)
        self.assertEqual(Payslip.objects.get(employee=self.emp).non_taxable, Decimal('0'))
        self.expense.refresh_from_db()
        self.assertIsNone(self.expense.payslip)

    def test_regenerating_without_expenses_releases_them(self):
        self.run_month()
        self.run_month(include_expenses=False)
        self.expense.refresh_from_db()
        self.assertIsNone(self.expense.payslip)

    def test_deleting_the_draft_releases_it(self):
        self.run_month()
        p = Payslip.objects.get(employee=self.emp)
        self.client_for(self.hr).delete(f'/api/payslips/{p.id}/')
        self.expense.refresh_from_db()
        self.assertIsNone(self.expense.payslip)
        self.assertEqual(self.expense.status, ExpenseReport.Status.APPROVED)

    def test_cannot_be_paid_by_hand_once_on_a_payslip(self):
        self.run_month()
        r = self.client_for(self.hr).post(f'/api/expenses/{self.expense.id}/mark_paid/')
        self.assertEqual(r.status_code, 400)


class AbsenceForEmployeeTests(TwoCompaniesTestCase):
    payload = {'leave_type': 'sick', 'start_date': '2030-03-03', 'end_date': '2030-03-04'}

    def post(self, user, employee):
        return self.client_for(user).post('/api/leaves/for_employee/', {**self.payload, 'employee': employee.id}, format='json')

    def test_manager_records_for_his_team_approved_at_once(self):
        r = self.post(self.manager, self.emp)
        self.assertEqual(r.status_code, 201, r.data)
        lr = LeaveRequest.objects.get(employee=self.emp)
        self.assertEqual((lr.status, lr.reviewer), ('approved', self.manager))
        self.assertGreater(lr.days, 0)

    def test_only_his_own_team(self):
        self.assertEqual(self.post(self.manager, self.other).status_code, 403)
        self.assertEqual(self.post(self.emp, self.other).status_code, 403)
        self.assertEqual(self.post(self.manager, self.manager).status_code, 403)

    def test_hr_covers_the_company_only(self):
        self.assertEqual(self.post(self.hr, self.other).status_code, 201)
        self.assertEqual(self.post(self.hr, self.other_emp).status_code, 403)
        self.assertEqual(self.post(self.admin, self.emp).status_code, 403)

    def test_overlap_is_still_refused(self):
        self.post(self.manager, self.emp)
        self.assertEqual(self.post(self.manager, self.emp).status_code, 400)

    def test_missing_employee_is_a_400(self):
        r = self.client_for(self.manager).post('/api/leaves/for_employee/', self.payload, format='json')
        self.assertEqual(r.status_code, 400)


class CertificateTests(TwoCompaniesTestCase):
    def setUp(self):
        super().setUp()
        self.emp.hire_date, self.emp.job_title = date(2022, 1, 10), 'Commercial'
        self.emp.save()

    def ask(self, kind='work', user=None):
        return self.client_for(user or self.emp).post('/api/certificates/', {'kind': kind}, format='json')

    def test_flow_ends_with_a_pdf_in_the_vault(self):
        r = self.ask('salary')
        self.assertEqual(r.status_code, 201, r.data)
        self.company.name_ar = 'شركة الاختبار'
        self.company.save()
        r = self.client_for(self.hr).post(f"/api/certificates/{r.data['id']}/approve/")
        self.assertEqual(r.status_code, 200, r.data)
        doc = Document.objects.get(id=r.data['document'])
        self.assertEqual((doc.employee, doc.category, doc.company), (self.emp, 'certificate', self.company))
        self.assertTrue(doc.file.read().startswith(b'%PDF'))
        self.assertEqual(self.client_for(self.emp).get(f'/api/documents/{doc.id}/download/').status_code, 200)

    def test_wording_follows_the_contract(self):
        self.emp.contract_type = 'cdi'
        fr, ar_text = certificate_text(CertificateRequest(employee=self.emp, kind='work'))
        self.assertIn('sous contrat à durée indéterminée (CDI)', fr)
        self.assertIn('بموجب عقد عمل غير محدد المدة', ar_text)
        self.assertNotIn('عقد عقد', ar_text)
        self.emp.contract_type = 'other'
        fr, ar_text = certificate_text(CertificateRequest(employee=self.emp, kind='work'))
        self.assertNotIn('contrat', fr)
        self.assertNotIn('عقد', ar_text)

    def test_markup_in_user_text_does_not_break_the_pdfs(self):
        # ReportLab paragraphs read a mini-markup: '</i>' or an unclosed '<b' used to raise ValueError.
        self.company.name, self.company.city = 'R&D </i> <b', '<font size="x">Alger'
        self.company.save()
        self.emp.job_title, self.emp.address = 'Chef <équipe>', 'Cité <b 12'
        self.emp.save()
        self.client_for(self.hr).post('/api/payslips/run/', {'year': 2026, 'month': 10, 'bonuses': [
            {'label': 'Prime </b> projet', 'amount': '1000'}]}, format='json')
        self.assertTrue(render_payslip(Payslip.objects.get(employee=self.emp)).startswith(b'%PDF'))
        self.assertTrue(render_certificate(CertificateRequest(employee=self.emp, kind='salary'),
                                           date(2026, 11, 2)).startswith(b'%PDF'))

    def test_salary_amount_survives_arabic_reordering(self):
        # A plain space lets the bidi algorithm print 68 000,00 as 000,00 68.
        self.assertEqual(get_display(arabic_reshaper.reshape('دج 68\u00a0000,00')).count('68\u00a0000,00'), 1)

    def test_one_pending_request_per_kind(self):
        self.ask('work')
        self.assertEqual(self.ask('work').status_code, 400)
        self.assertEqual(self.ask('salary').status_code, 201)

    def test_who_can_decide(self):
        rid = self.ask().data['id']
        self.assertEqual(self.client_for(self.emp).post(f'/api/certificates/{rid}/approve/').status_code, 403)
        self.assertEqual(self.client_for(self.manager).post(f'/api/certificates/{rid}/approve/').status_code, 404)
        self.assertEqual(self.client_for(self.other_hr).post(f'/api/certificates/{rid}/approve/').status_code, 404)
        self.assertEqual(self.client_for(self.admin).post(f'/api/certificates/{rid}/approve/').status_code, 404)

    def test_hr_cannot_approve_his_own(self):
        rid = self.ask(user=self.hr).data['id']
        self.assertEqual(self.client_for(self.hr).post(f'/api/certificates/{rid}/approve/').status_code, 403)

    def test_rejection_creates_no_document(self):
        rid = self.ask().data['id']
        self.client_for(self.hr).post(f'/api/certificates/{rid}/reject/', {'comment': 'Non'}, format='json')
        self.assertEqual(CertificateRequest.objects.get(id=rid).status, 'rejected')
        self.assertFalse(Document.objects.exists())

    def test_employee_only_sees_his_requests(self):
        self.ask()
        self.assertEqual(self.client_for(self.other).get('/api/certificates/').data, [])
        self.assertEqual(self.client_for(self.other).get('/api/certificates/?scope=all').status_code, 403)
        self.assertEqual(len(self.client_for(self.hr).get('/api/certificates/?scope=all').data), 1)

    def test_account_without_company_cannot_ask(self):
        self.assertEqual(self.ask(user=self.accountant).status_code, 400)


class PasswordResetTests(TwoCompaniesTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def ask(self, email):
        return self.client.post('/api/auth/password-reset/', {'email': email}, format='json')

    def link_params(self):
        match = re.search(r'/reinitialiser\?uid=([^&]+)&token=(\S+)', mail.outbox[-1].body)
        return match.group(1), match.group(2)

    @override_settings(FRONTEND_URL='https://paie.example')
    def test_full_flow(self):
        self.assertEqual(self.ask('emp@test.dz').status_code, 204)
        self.assertIn('https://paie.example/reinitialiser', mail.outbox[-1].body)
        uid, token = self.link_params()
        r = self.client.post('/api/auth/password-reset/confirm/', {'uid': uid, 'token': token,
                                                                   'new_password': 'Nouveau-mdp-2026'}, format='json')
        self.assertEqual(r.status_code, 204, getattr(r, 'data', None))
        self.assertEqual(self.client.post('/api/auth/login/', {'username': 'emp', 'password': 'Nouveau-mdp-2026'}).status_code, 200)
        # The link only works once: the token depends on the password.
        r = self.client.post('/api/auth/password-reset/confirm/', {'uid': uid, 'token': token,
                                                                   'new_password': 'Encore-un-autre-2026'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_unknown_address_answers_the_same_and_sends_nothing(self):
        self.assertEqual(self.ask('personne@test.dz').status_code, 204)
        self.assertEqual(mail.outbox, [])

    def test_deactivated_account_or_company_gets_nothing(self):
        self.emp.is_active = False
        self.emp.save()
        self.company.is_active = False
        self.company.save()
        self.ask('emp@test.dz')
        self.ask('rh@test.dz')
        self.assertEqual(mail.outbox, [])

    def test_bad_token_and_weak_password(self):
        self.ask('emp@test.dz')
        uid, token = self.link_params()
        url = '/api/auth/password-reset/confirm/'
        self.assertEqual(self.client.post(url, {'uid': uid, 'token': 'faux', 'new_password': 'Nouveau-mdp-2026'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(url, {'uid': '!!!', 'token': token, 'new_password': 'Nouveau-mdp-2026'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(url, {'uid': uid, 'token': token, 'new_password': '123'}, format='json').status_code, 400)


class AuditLogTests(TwoCompaniesTestCase):
    def test_sensitive_actions_are_recorded_without_amounts(self):
        hr = self.client_for(self.hr)
        hr.post('/api/payslips/run/', {'year': 2026, 'month': 10, 'publish': False}, format='json')
        hr.post('/api/payslips/publish_month/', {'year': 2026, 'month': 10}, format='json')
        hr.patch(f'/api/employees/{self.emp.id}/', {'base_salary': '77777'}, format='json')
        actions = set(AuditLog.objects.values_list('action', flat=True))
        self.assertLessEqual({'payroll.run', 'payroll.publish', 'employee.update'}, actions)
        entry = AuditLog.objects.get(action='employee.update')
        self.assertEqual(entry.actor, self.hr)
        self.assertIn('base_salary', entry.summary)
        self.assertNotIn('77777', entry.summary)

    def test_review_is_recorded(self):
        lr = LeaveRequest.objects.create(employee=self.emp, leave_type='sick', start_date='2030-03-03',
                                         end_date='2030-03-03', days=1)
        self.client_for(self.manager).post(f'/api/leaves/{lr.id}/approve/')
        self.assertEqual(AuditLog.objects.get(action='leave.approve').company, self.company)

    def test_journal_is_private_to_the_company(self):
        self.client_for(self.other_hr).post('/api/payslips/run/', {'year': 2026, 'month': 10}, format='json')
        self.assertEqual(self.client_for(self.hr).get('/api/audit/').data, [])
        self.assertEqual(len(self.client_for(self.other_hr).get('/api/audit/').data), 1)
        for u in [self.emp, self.manager, self.admin]:
            self.assertEqual(self.client_for(u).get('/api/audit/').status_code, 403)


class ApiVersionTests(TwoCompaniesTestCase):
    def test_v1_serves_the_same_api(self):
        self.assertEqual(APIClient().get('/api/v1/health/').data, {'status': 'ok'})
        self.assertEqual(self.client_for(self.hr).get('/api/v1/employees/').status_code, 200)
