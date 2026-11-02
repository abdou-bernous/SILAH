"""Correcting a published payslip: a corrective payslip cancels and replaces it ("annule et remplace")."""
from decimal import Decimal

from django.db import IntegrityError, transaction

from .models import AuditLog, EmployeePayItem, ExpenseReport, MonthlyVariable, Notification, Payslip, PayslipLine
from .pdf import render_payslip
from .test_coherence import TwoCompaniesTestCase

PANIER = {'label': 'Indemnité de panier', 'label_ar': 'تعويض السلة', 'amount': '3000', 'contributory': False,
          'tax': 'scale'}


class CorrectionTests(TwoCompaniesTestCase):
    def setUp(self):
        super().setUp()
        self.hr_client = self.client_for(self.hr)
        r = self.hr_client.post('/api/payslips/run/', {'year': 2026, 'month': 10, 'bonuses': [PANIER], 'publish': True},
                                format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.original = Payslip.objects.get(employee=self.emp, year=2026, month=10)

    def correct(self, reason='Heures supplémentaires oubliées', client=None, payslip=None, **extra):
        return (client or self.hr_client).post(f'/api/payslips/{(payslip or self.original).id}/correct/',
                                                {'reason': reason, **extra}, format='json')

    def forget_overtime(self):
        MonthlyVariable.objects.create(employee=self.emp, year=2026, month=10, overtime_hours=Decimal('10'))

    def test_correction_is_a_draft_until_published(self):
        self.forget_overtime()
        r = self.correct()
        self.assertEqual(r.status_code, 201, r.data)
        draft = Payslip.objects.get(id=r.data['id'])
        self.assertEqual((draft.status, draft.replaces, draft.year, draft.month),
                         ('draft', self.original, 2026, 10))
        # 50 000 + 3 000 panier (kept from the run) + 10 h at +50 %.
        self.assertEqual(draft.gross_salary, Decimal('57327.01'))
        self.assertEqual(r.data['previous_net'], self.original.net_salary)
        self.original.refresh_from_db()
        self.assertEqual(self.original.status, 'published')
        # The employee still sees the original only.
        mine = self.client_for(self.emp).get('/api/payslips/').data
        self.assertEqual([p['id'] for p in mine], [self.original.id])

    def test_publishing_replaces_the_original(self):
        self.forget_overtime()
        draft_id = self.correct().data['id']
        r = self.hr_client.post(f'/api/payslips/{draft_id}/publish/')
        self.assertEqual(r.status_code, 200, r.data)
        self.original.refresh_from_db()
        draft = Payslip.objects.get(id=draft_id)
        self.assertEqual((self.original.status, draft.status), ('replaced', 'published'))
        emp = self.client_for(self.emp)
        self.assertEqual([p['id'] for p in emp.get('/api/payslips/').data], [draft_id])
        self.assertEqual(emp.get(f'/api/payslips/{self.original.id}/').status_code, 404)
        n = Notification.objects.filter(user=self.emp).latest('id')
        self.assertEqual(n.title, "Votre bulletin d'octobre 2026 a été corrigé")
        self.assertIn('Heures supplémentaires oubliées', n.message)
        detail = self.hr_client.get(f'/api/payslips/{self.original.id}/').data
        self.assertEqual(detail['replaced_by'], {'id': draft_id, 'status': 'published'})

    def test_totals_count_the_version_in_force_only(self):
        before = self.hr_client.get('/api/payslips/summary/?year=2026&month=10').data
        self.forget_overtime()
        draft_id = self.correct().data['id']
        during = self.hr_client.get('/api/payslips/summary/?year=2026&month=10').data
        self.assertEqual(during, before)
        self.hr_client.post(f'/api/payslips/{draft_id}/publish/')
        after = self.hr_client.get('/api/payslips/summary/?year=2026&month=10').data
        self.assertEqual(after['count'], before['count'])
        self.assertEqual(after['gross'] - before['gross'], Decimal('4327.01'))
        overview = self.client_for(self.accountant).get('/api/companies/overview/', **self.header()).data
        self.assertEqual(next(c for c in overview if c['id'] == self.company.id)['last_payroll']['count'], before['count'])

    def test_reason_is_required(self):
        self.assertEqual(self.correct(reason='').status_code, 400)
        self.assertEqual(self.correct(reason='   ').status_code, 400)

    def test_only_a_published_payslip_in_force_can_be_corrected(self):
        draft_id = self.correct().data['id']
        self.assertEqual(self.correct(payslip=Payslip.objects.get(id=draft_id)).status_code, 400)
        self.hr_client.post(f'/api/payslips/{draft_id}/publish/')
        self.original.refresh_from_db()
        self.assertEqual(self.correct().status_code, 400)          # replaced
        # The correction in force can itself be corrected.
        r = self.correct(payslip=Payslip.objects.get(id=draft_id), reason='Seconde erreur')
        self.assertEqual(r.status_code, 201, r.data)

    def test_correcting_again_redoes_the_same_draft(self):
        first = self.correct().data['id']
        self.forget_overtime()
        r = self.correct(reason='Motif précisé')
        self.assertEqual((r.status_code, r.data['id']), (200, first))
        self.assertEqual(Payslip.objects.filter(employee=self.emp, status='draft').count(), 1)
        self.assertEqual(Payslip.objects.get(id=first).correction_reason, 'Motif précisé')
        self.assertEqual(Payslip.objects.get(id=first).gross_salary, Decimal('57327.01'))

    def test_form_defaults_come_from_the_payslip(self):
        r = self.hr_client.get(f'/api/payslips/{self.original.id}/correct/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['draft'], None)
        self.assertEqual([i['label'] for i in r.data['items']], ['Indemnité de panier'])
        draft_id = self.correct(items=[{**PANIER, 'amount': '3500'}]).data['id']
        r = self.hr_client.get(f'/api/payslips/{self.original.id}/correct/')
        self.assertEqual((r.data['draft'], r.data['items'][0]['amount']), (draft_id, '3500.00'))

    def test_wrong_run_bonus_can_be_fixed(self):
        r = self.correct(reason='Panier à 2 000 DA', items=[{**PANIER, 'amount': '2000'}])
        self.assertEqual(Payslip.objects.get(id=r.data['id']).gross_salary, Decimal('52000.00'))

    def test_legacy_payslip_bonuses_are_rebuilt_from_its_lines(self):
        Payslip.objects.filter(id=self.original.id).update(run_items=None)
        EmployeePayItem.objects.create(employee=self.emp, label='IEP', amount=Decimal('1000'))
        PayslipLine.objects.create(payslip=self.original, order=9, code='R201', label='IEP', kind='earning',
                                   employee_amount=Decimal('1000'))
        items = self.hr_client.get(f'/api/payslips/{self.original.id}/correct/').data['items']
        self.assertEqual(items, [{**PANIER, 'amount': '3000.00'}])

    def test_run_leaves_published_payslips_and_corrections_alone(self):
        self.correct()
        r = self.hr_client.post('/api/payslips/run/', {'year': 2026, 'month': 10}, format='json')
        reasons = {s['employee']: s['reason'] for s in r.data['skipped']}
        self.assertIn('Correction en cours', reasons[str(self.emp)])
        self.assertIn('déjà publié', reasons[str(self.other)])
        r = self.hr_client.post('/api/payslips/publish_month/', {'year': 2026, 'month': 10}, format='json')
        self.assertEqual(r.data['published'], 0)

    def test_cancelling_a_correction_keeps_the_original(self):
        draft_id = self.correct().data['id']
        self.assertEqual(self.hr_client.delete(f'/api/payslips/{draft_id}/').status_code, 204)
        self.original.refresh_from_db()
        self.assertEqual(self.original.status, 'published')
        self.assertEqual(self.hr_client.delete(f'/api/payslips/{self.original.id}/').status_code, 400)
        actions = list(AuditLog.objects.filter(action__startswith='payroll.correct').order_by('id')
                       .values_list('action', flat=True))
        self.assertEqual(actions, ['payroll.correct', 'payroll.correction_cancel'])

    def test_repaid_expenses_follow_the_correction(self):
        ExpenseReport.objects.filter(employee=self.emp).delete()
        Payslip.objects.filter(employee=self.emp).delete()
        exp = ExpenseReport.objects.create(employee=self.emp, date='2026-10-05', category='transport',
                                           description='Taxi', amount=Decimal('1500'), status='approved')
        self.hr_client.post('/api/payslips/run/', {'year': 2026, 'month': 10, 'employees': [self.emp.id],
                                                   'publish': True}, format='json')
        original = Payslip.objects.get(employee=self.emp)
        exp.refresh_from_db()
        self.assertEqual((exp.status, exp.payslip), ('paid', original))
        draft_id = self.correct(payslip=original).data['id']
        draft = Payslip.objects.get(id=draft_id)
        self.assertEqual(draft.non_taxable, Decimal('1500.00'))
        self.hr_client.delete(f'/api/payslips/{draft_id}/')
        exp.refresh_from_db()
        self.assertEqual(exp.payslip, original)      # cancelling did not detach it
        draft_id = self.correct(payslip=original).data['id']
        self.hr_client.post(f'/api/payslips/{draft_id}/publish/')
        exp.refresh_from_db()
        self.assertEqual((exp.status, exp.payslip_id), ('paid', draft_id))

    def test_reserved_to_the_company_hr(self):
        for user in [self.emp, self.manager, self.admin, self.other_hr]:
            r = self.correct(client=self.client_for(user))
            self.assertIn(r.status_code, (403, 404), user.username)
        self.assertFalse(Payslip.objects.filter(status='draft').exists())
        r = self.client_for(self.accountant).post(f'/api/payslips/{self.original.id}/correct/', {'reason': 'x'},
                                                   format='json', **self.header())
        self.assertEqual(r.status_code, 201, r.data)

    def test_one_draft_and_one_payslip_in_force_per_month(self):
        draft_id = self.correct().data['id']
        with self.assertRaises(IntegrityError), transaction.atomic():
            Payslip.objects.create(employee=self.emp, year=2026, month=10, status='draft')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Payslip.objects.filter(id=draft_id).update(status='published')

    def test_pdfs_say_which_version_is_in_force(self):
        draft_id = self.correct(reason='Prime <oubliée> & co').data['id']
        self.hr_client.post(f'/api/payslips/{draft_id}/publish/')
        self.original.refresh_from_db()
        for p in [Payslip.objects.get(id=draft_id), self.original]:
            self.assertTrue(render_payslip(p).startswith(b'%PDF'))
        r = self.hr_client.get(f'/api/payslips/{self.original.id}/pdf/')
        self.assertEqual(r.status_code, 200)
