"""Payroll consistency: hires during the month, unpaid days, the monthly grid, permanent items, unpaid leave
changed once the month is computed, and invariants of the engine on thousands of random payslips."""
import random
from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from .models import AuditLog, EmployeePayItem, ExpenseReport, LeaveRequest, MonthlyVariable, Notification, Payslip
from .payroll import Bonus, OVERTIME_MONTHLY_LIMIT, compute_payslip, money
from .test_coherence import TwoCompaniesTestCase


class PayrollTestCase(TwoCompaniesTestCase):
    def run_month(self, month=10, year=2026, **extra):
        r = self.client_for(self.hr).post('/api/payslips/run/', {'year': year, 'month': month, **extra}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return r

    def payslip(self, employee=None, month=10):
        return Payslip.objects.get(employee=employee or self.emp, year=2026, month=month, replaces__isnull=True)

    def messages(self, r):
        return ' '.join(w['message'] for w in r.data['warnings'])


class HireDuringTheMonthTests(PayrollTestCase):
    def hire(self, day):
        self.emp.hire_date = day
        self.emp.save()

    def test_not_paid_for_a_month_before_the_hire(self):
        self.hire(date(2026, 11, 3))
        r = self.run_month()
        reasons = {s['employee']: s['reason'] for s in r.data['skipped']}
        self.assertEqual(reasons[str(self.emp)], 'Embauché le 03/11/2026, après ce mois')
        self.assertFalse(Payslip.objects.filter(employee=self.emp).exists())
        self.assertTrue(Payslip.objects.filter(employee=self.other).exists())

    def test_a_draft_computed_before_the_hire_date_was_entered_is_removed(self):
        self.run_month()
        self.hire(date(2026, 11, 3))
        reasons = {s['employee']: s['reason'] for s in self.run_month().data['skipped']}
        self.assertTrue(reasons[str(self.emp)].endswith('brouillon supprimé'))
        self.assertFalse(Payslip.objects.filter(employee=self.emp).exists())

    def test_hired_mid_month_is_paid_from_the_first_day(self):
        self.hire(date(2026, 10, 15))   # 10 working days (Sunday to Thursday) before the 15th
        r = self.run_month()
        p = self.payslip()
        line = p.lines.get(code='R180')
        self.assertEqual((line.label, line.base, line.employee_amount),
                         ('Entrée en cours de mois', Decimal('10.00'), Decimal('-22727.27')))
        self.assertEqual(p.gross_salary, Decimal('27272.73'))
        self.assertEqual((p.worked_days, p.unpaid_days), (Decimal('11.0'), Decimal('0.0')))   # October: 21 working days
        self.assertIn('Entrée le 15/10/2026', self.messages(r))
        self.assertEqual(sum(l.employee_amount for l in p.lines.all()), p.net_salary)

    def test_hired_on_the_first_works_a_full_month(self):
        self.hire(date(2026, 10, 1))
        r = self.run_month()
        self.assertEqual(self.payslip().gross_salary, Decimal('50000.00'))
        self.assertNotIn('Entrée', self.messages(r))

    def test_hire_and_unpaid_leave_together_never_exceed_the_base(self):
        self.hire(date(2026, 10, 15))
        LeaveRequest.objects.create(employee=self.emp, leave_type='unpaid', start_date=date(2026, 10, 15),
                                    end_date=date(2026, 10, 31), days=11, status='approved')
        self.run_month()
        p = self.payslip()
        self.assertEqual(p.gross_salary, Decimal('0.00'))
        self.assertEqual(-sum(l.employee_amount for l in p.lines.filter(kind='deduction')), Decimal('50000.00'))
        self.assertEqual(p.worked_days, Decimal('0'))


class UnpaidDaysTests(PayrollTestCase):
    def test_absent_every_working_day_earns_no_base(self):
        # October 2026 has 21 working days: at base / 22 per day, 1/22 of the salary used to remain.
        LeaveRequest.objects.create(employee=self.emp, leave_type='unpaid', start_date=date(2026, 10, 1),
                                    end_date=date(2026, 10, 31), days=21, status='approved')
        self.run_month()
        p = self.payslip()
        self.assertEqual((p.gross_salary, p.net_salary, p.worked_hours), (Decimal('0.00'), Decimal('0.00'), Decimal('0.00')))

    def test_part_of_the_month_keeps_the_daily_rate(self):
        LeaveRequest.objects.create(employee=self.emp, leave_type='unpaid', start_date=date(2026, 10, 4),
                                    end_date=date(2026, 10, 5), days=2, status='approved')
        self.run_month()
        self.assertEqual(self.payslip().gross_salary, Decimal('45454.55'))   # 50 000 - 2 x 50 000 / 22


class RunTests(PayrollTestCase):
    def test_the_same_employee_sent_twice_is_paid_once(self):
        r = self.run_month(employees=[self.emp.id, self.emp.id])
        self.assertEqual(len(r.data['created']), 1)
        self.assertEqual(AuditLog.objects.get(action='payroll.run').summary, 'Octobre 2026 : 1 bulletin(s)')

    def test_overtime_beyond_the_legal_share_is_flagged(self):
        self.assertEqual(OVERTIME_MONTHLY_LIMIT, Decimal('34.67'))
        MonthlyVariable.objects.create(employee=self.emp, year=2026, month=10, overtime_hours=Decimal('34'))
        self.assertNotIn('dérogation', self.messages(self.run_month()))
        MonthlyVariable.objects.filter(employee=self.emp).update(overtime_hours=Decimal('40'))
        self.assertIn('dérogation', self.messages(self.run_month()))

    def test_every_payslip_reconciles_with_its_lines(self):
        EmployeePayItem.objects.create(employee=self.emp, label='IEP', amount=Decimal('2500'))
        EmployeePayItem.objects.create(employee=self.other, label='Panier', amount=Decimal('3000'), contributory=False)
        MonthlyVariable.objects.create(employee=self.emp, year=2026, month=10, overtime_hours=Decimal('8'),
                                       bonus_label='Prime projet', bonus_amount=Decimal('4000'))
        ExpenseReport.objects.create(employee=self.other, date='2026-10-05', amount=Decimal('1800'),
                                     description='Taxi', status='approved')
        LeaveRequest.objects.create(employee=self.other, leave_type='unpaid', start_date=date(2026, 10, 11),
                                    end_date=date(2026, 10, 11), start_half=True, days=Decimal('0.5'),
                                    status='approved')
        self.run_month(bonuses=[{'label': 'PRC', 'amount': '9000', 'tax': 'flat'},
                                {'label': 'Allocations', 'amount': '1500', 'contributory': False, 'tax': 'exempt'}])
        for p in Payslip.objects.all():
            lines = list(p.lines.all())
            self.assertEqual(sum(l.employee_amount for l in lines), p.net_salary, p)
            self.assertEqual(p.net_salary, p.gross_salary - p.social_contributions - p.income_tax - p.flat_tax
                             + p.non_taxable, p)
            self.assertEqual(p.employer_cost, p.gross_salary + p.non_taxable + p.employer_contributions, p)
        self.assertEqual(self.payslip(self.other).non_taxable, Decimal('3300.00'))   # expenses + allowances


class PayItemRulesTests(PayrollTestCase):
    def test_permanent_item_cannot_use_the_10_percent_rate(self):
        hr = self.client_for(self.hr)
        r = hr.post('/api/pay-items/', {'employee': self.emp.id, 'label': 'PRC', 'amount': '5000', 'tax': 'flat'},
                    format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('non mensuelles', str(r.data))
        item = hr.post('/api/pay-items/', {'employee': self.emp.id, 'label': 'IEP', 'amount': '5000'}, format='json').data
        self.assertEqual(hr.patch(f"/api/pay-items/{item['id']}/", {'tax': 'flat'}, format='json').status_code, 400)
        self.assertEqual(hr.patch(f"/api/pay-items/{item['id']}/", {'tax': 'exempt'}, format='json').status_code, 200)


class VariablesAfterPublicationTests(PayrollTestCase):
    def setUp(self):
        super().setUp()
        self.run_month(publish=True)

    def save(self, rows):
        r = self.client_for(self.hr).post('/api/payslips/variables/', {'year': 2026, 'month': 10, 'rows': rows},
                                          format='json')
        self.assertEqual(r.status_code, 200, r.data)
        return r.data['already_published']

    def test_changes_for_someone_already_paid_are_named(self):
        rows = [{'employee': self.emp.id, 'overtime_hours': '10'}, {'employee': self.other.id}]
        self.assertEqual(self.save(rows), [str(self.emp)])
        self.assertTrue(MonthlyVariable.objects.filter(employee=self.emp).exists())   # kept for the correction
        self.assertEqual(self.save(rows), [])                                           # nothing new
        # A rate without hours, or a label without amount, changes nothing on the payslip.
        self.assertEqual(self.save([{'employee': self.other.id, 'overtime_rate': '75', 'bonus_label': 'X'}]), [])

    def test_removing_them_is_named_too(self):
        self.save([{'employee': self.emp.id, 'bonus_amount': '2000'}])
        self.assertEqual(self.save([{'employee': self.emp.id}]), [str(self.emp)])
        self.assertFalse(MonthlyVariable.objects.exists())

    def test_a_correction_then_takes_them_into_account(self):
        self.save([{'employee': self.emp.id, 'overtime_hours': '10'}])
        r = self.client_for(self.hr).post(f'/api/payslips/{self.payslip().id}/correct/',
                                          {'reason': 'Heures oubliées'}, format='json')
        self.assertEqual(Decimal(r.data['gross_salary']), Decimal('54327.01'))


class UnpaidLeaveAfterPayrollTests(PayrollTestCase):
    """An unpaid leave decided after its month was computed: the payroll managers are told what to redo."""

    def setUp(self):
        super().setUp()
        self.run_month(publish=True)
        Notification.objects.all().delete()

    def ask(self, start='2026-10-20', end='2026-10-21', leave_type='unpaid'):
        r = self.client_for(self.emp).post('/api/leaves/', {'leave_type': leave_type, 'start_date': start,
                                                            'end_date': end}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['payroll_warnings'], [])   # nothing changes while it waits
        return r.data['id']

    def told(self):
        return Notification.objects.filter(title__startswith='Absence sans solde')

    def test_approval_on_a_paid_month_asks_for_a_correction(self):
        r = self.client_for(self.manager).post(f'/api/leaves/{self.ask()}/approve/')
        self.assertEqual(len(r.data['payroll_warnings']), 1)
        self.assertIn("Le bulletin d'octobre 2026 est déjà publié", r.data['payroll_warnings'][0])
        self.assertEqual({n.user for n in self.told()}, {self.hr, self.accountant})
        self.assertEqual(self.told().get(user=self.hr).link, f'/bulletins/{self.payslip().id}')
        # The accountant's link opens the client it is about.
        self.assertEqual(self.told().get(user=self.accountant).link,
                         f'/bulletins/{self.payslip().id}?client={self.company.id}')
        self.assertFalse(self.told().filter(user=self.manager).exists())
        # The correction now deducts the two days.
        r = self.client_for(self.hr).post(f'/api/payslips/{self.payslip().id}/correct/',
                                          {'reason': 'Absence sans solde validée après la paie'}, format='json')
        self.assertEqual(Decimal(r.data['unpaid_days']), Decimal('2.0'))

    def test_draft_month_asks_to_recompute(self):
        self.run_month(month=11)
        r = self.client_for(self.manager).post(f"/api/leaves/{self.ask('2026-11-10', '2026-11-11')}/approve/")
        self.assertIn('relancez le calcul', r.data['payroll_warnings'][0])
        self.assertEqual(self.told().get(user=self.hr).link, '/admin/paie')
        self.assertEqual(self.told().get(user=self.accountant).link, f'/admin/paie?client={self.company.id}')

    def test_a_leave_over_two_months_names_both(self):
        self.run_month(month=11)
        r = self.client_for(self.manager).post(f"/api/leaves/{self.ask('2026-10-28', '2026-11-03')}/approve/")
        self.assertEqual(len(r.data['payroll_warnings']), 2)

    def test_a_month_touched_only_on_rest_days_is_left_alone(self):
        self.run_month(month=11)
        # Friday 30 and Saturday 31 October are rest days: only November's pay changes.
        r = self.client_for(self.manager).post(f"/api/leaves/{self.ask('2026-10-30', '2026-11-02')}/approve/")
        self.assertEqual(len(r.data['payroll_warnings']), 1)
        self.assertIn('novembre', r.data['payroll_warnings'][0])

    def test_paid_leave_and_months_not_computed_change_nothing(self):
        r = self.client_for(self.manager).post(f"/api/leaves/{self.ask(leave_type='sick')}/approve/")
        self.assertEqual(r.data['payroll_warnings'], [])
        r = self.client_for(self.manager).post(f"/api/leaves/{self.ask('2026-12-06', '2026-12-07')}/approve/")
        self.assertEqual(r.data['payroll_warnings'], [])
        self.assertFalse(self.told().exists())

    def test_rejection_changes_nothing(self):
        r = self.client_for(self.manager).post(f'/api/leaves/{self.ask()}/reject/')
        self.assertEqual(r.data['payroll_warnings'], [])
        self.assertFalse(self.told().exists())

    def test_recorded_by_hr_or_cancelled_later_warns_too(self):
        r = self.client_for(self.hr).post('/api/leaves/for_employee/', {
            'employee': self.emp.id, 'leave_type': 'unpaid', 'start_date': '2026-10-20', 'end_date': '2026-10-21'},
            format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(len(r.data['payroll_warnings']), 1)
        r = self.client_for(self.hr).post(f"/api/leaves/{r.data['id']}/cancel/")
        self.assertEqual(len(r.data['payroll_warnings']), 1)
        self.assertEqual(self.told().filter(user=self.hr).count(), 2)


class SummaryTests(PayrollTestCase):
    def test_totals_say_how_many_drafts_they_include(self):
        self.run_month()
        hr = self.client_for(self.hr)
        self.assertEqual(hr.get('/api/payslips/summary/?year=2026&month=10').data['drafts'], 2)
        hr.post('/api/payslips/publish_month/', {'year': 2026, 'month': 10}, format='json')
        summary = hr.get('/api/payslips/summary/?year=2026&month=10').data
        self.assertEqual((summary['drafts'], summary['count']), (0, 2))


class EngineInvariantTests(SimpleTestCase):
    """Random payslips, from part-time to executive salaries: the figures always reconcile."""

    @staticmethod
    def random_case(rnd):
        base = Decimal(rnd.choice([0, rnd.randint(1000, 23999), rnd.randint(24000, 600000)]))
        bonuses = [Bonus(f'Prime {i}', Decimal(rnd.randint(0, 5_000_000)) / 100, rnd.random() < 0.6,
                         rnd.choice(['scale', 'flat', 'exempt'])) for i in range(rnd.randint(0, 5))]
        unpaid = Decimal(rnd.randint(0, 50)) / 2
        before_hire = Decimal(rnd.randint(0, 15)) if rnd.random() < 0.3 else Decimal('0')
        return base, bonuses, unpaid, before_hire, Decimal(rnd.randint(20, 23)), rnd.random() < 0.2

    def test_figures_always_reconcile(self):
        rnd = random.Random(2026)
        for _ in range(3000):
            base, bonuses, unpaid, before_hire, working, disabled = case = self.random_case(rnd)
            r = compute_payslip(base, bonuses, unpaid, disabled, days_before_hire=before_hire, working_days=working)
            self.assertEqual(r.net_salary, sum((l.employee_amount for l in r.lines), Decimal('0')), case)
            self.assertEqual(r.net_salary, r.gross_salary - r.social_contributions - r.income_tax - r.flat_tax
                             + r.non_taxable, case)
            self.assertEqual(r.employer_cost, r.gross_salary + r.non_taxable + r.employer_contributions, case)
            for value in [r.gross_salary, r.social_contributions, r.income_tax, r.flat_tax, r.net_salary,
                          r.employer_contributions, r.non_taxable]:
                self.assertGreaterEqual(value, 0, case)
                self.assertEqual(value, money(value), case)
            deducted = -sum((l.employee_amount for l in r.lines if l.kind == 'deduction'), Decimal('0'))
            self.assertLessEqual(deducted, money(base), case)
            if unpaid + before_hire >= working:
                self.assertEqual(deducted, money(base), case)

    def test_more_unpaid_days_never_raise_the_net(self):
        rnd = random.Random(7)
        for _ in range(200):
            base, bonuses, *_ = self.random_case(rnd)
            previous = None
            for days in range(0, 24):
                net = compute_payslip(base, bonuses, Decimal(days), working_days=Decimal('22')).net_salary
                if previous is not None:
                    self.assertLessEqual(net, previous, (base, bonuses, days))
                previous = net

    def test_a_bonus_never_lowers_the_net(self):
        rnd = random.Random(11)
        for _ in range(500):
            base, bonuses, unpaid, before_hire, working, disabled = self.random_case(rnd)
            extra = Bonus('Prime', Decimal(rnd.randint(100, 100_000)), rnd.random() < 0.6,
                          rnd.choice(['scale', 'flat', 'exempt']))
            args = dict(unpaid_days=unpaid, disabled=disabled, days_before_hire=before_hire, working_days=working)
            self.assertGreaterEqual(compute_payslip(base, bonuses + [extra], **args).net_salary,
                                    compute_payslip(base, bonuses, **args).net_salary, (base, bonuses, extra))
