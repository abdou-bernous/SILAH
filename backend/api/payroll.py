"""Simplified Algerian payroll engine.

Covers the common case of a monthly salaried employee:
  - base salary, bonuses (contributory or not, taxable or not), unpaid-leave deduction
  - CNAS social security: 9 % employee share, 26 % employer share
  - IRG on salaries: monthly scale from the 2022 finance law, 40 % allowance
    (between 1 000 and 1 500 DZD), full exemption up to 30 000 DZD and the
    smoothing formula between 30 000 and 35 000 DZD.

It is deliberately small and table-driven so rates can be adjusted in one place.
Special regimes (disabled workers, retirees, mutuelles, IRG on bonuses paid at
a flat 10 %...) are out of scope for the MVP.
"""
import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR

CNAS_EMPLOYEE_RATE = Decimal('0.09')
CNAS_EMPLOYER_RATE = Decimal('0.26')

# (upper bound of the bracket, rate) — monthly amounts in DZD.
IRG_BRACKETS = [
    (Decimal('20000'), Decimal('0')),
    (Decimal('40000'), Decimal('0.23')),
    (Decimal('80000'), Decimal('0.27')),
    (Decimal('160000'), Decimal('0.30')),
    (Decimal('320000'), Decimal('0.33')),
    (None, Decimal('0.35')),
]
IRG_ALLOWANCE_RATE = Decimal('0.40')
IRG_ALLOWANCE_MIN = Decimal('1000')
IRG_ALLOWANCE_MAX = Decimal('1500')
IRG_EXEMPTION_CEILING = Decimal('30000')
IRG_SMOOTHING_CEILING = Decimal('35000')

# Working days used to value one day of unpaid leave.
WORKING_DAYS_PER_MONTH = Decimal('22')

CENT = Decimal('0.01')


def money(value) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def compute_irg(taxable: Decimal) -> Decimal:
    taxable = Decimal(taxable)
    if taxable <= IRG_EXEMPTION_CEILING:
        return Decimal('0.00')
    # The taxable base is rounded down to the nearest ten dinars.
    base = (taxable / 10).to_integral_value(rounding=ROUND_FLOOR) * 10

    gross_tax = Decimal('0')
    lower = Decimal('0')
    for upper, rate in IRG_BRACKETS:
        if upper is None or base <= upper:
            gross_tax += (base - lower) * rate
            break
        gross_tax += (upper - lower) * rate
        lower = upper

    allowance = min(max(gross_tax * IRG_ALLOWANCE_RATE, IRG_ALLOWANCE_MIN), IRG_ALLOWANCE_MAX)
    tax = max(gross_tax - allowance, Decimal('0'))

    if base < IRG_SMOOTHING_CEILING:
        tax = tax * Decimal(137) / Decimal(51) - Decimal(27925) / Decimal(8)
    return money(max(tax, Decimal('0')))


@dataclass
class Bonus:
    label: str
    amount: Decimal
    contributory: bool = True   # subject to CNAS
    taxable: bool = True        # subject to IRG


@dataclass
class Line:
    code: str
    label: str
    kind: str
    employee_amount: Decimal = Decimal('0')
    employer_amount: Decimal = Decimal('0')
    base: Decimal | None = None
    rate: Decimal | None = None


@dataclass
class PayslipResult:
    lines: list = field(default_factory=list)
    gross_salary: Decimal = Decimal('0')
    social_contributions: Decimal = Decimal('0')
    taxable_salary: Decimal = Decimal('0')
    income_tax: Decimal = Decimal('0')
    net_salary: Decimal = Decimal('0')
    employer_contributions: Decimal = Decimal('0')
    employer_cost: Decimal = Decimal('0')


def compute_payslip(base_salary, bonuses=(), unpaid_days=0) -> PayslipResult:
    base_salary = money(base_salary)
    unpaid_days = Decimal(unpaid_days)
    r = PayslipResult()

    r.lines.append(Line('1000', 'Salaire de base', 'earning', base_salary, base=base_salary))
    contributory = base_salary
    taxable_extra = Decimal('0')       # taxable but not contributory
    non_taxable = Decimal('0')         # neither: paid on top of net

    for i, b in enumerate(bonuses):
        amount = money(b.amount)
        if amount == 0:
            continue
        if not b.contributory and not b.taxable:
            r.lines.append(Line(f'{1300 + i}', b.label, 'non_taxable', amount))
            non_taxable += amount
            continue
        r.lines.append(Line(f'{1100 + i}', b.label, 'earning', amount))
        if b.contributory:
            contributory += amount
        else:
            taxable_extra += amount

    if unpaid_days > 0:
        daily = base_salary / WORKING_DAYS_PER_MONTH
        deduction = money(min(daily * unpaid_days, base_salary))
        r.lines.append(Line('1500', 'Absence non rémunérée', 'deduction', -deduction,
                            base=unpaid_days, rate=money(daily)))
        contributory -= deduction

    r.gross_salary = money(contributory + taxable_extra)

    employee_cnas = money(contributory * CNAS_EMPLOYEE_RATE)
    employer_cnas = money(contributory * CNAS_EMPLOYER_RATE)
    r.lines.append(Line('3000', 'Cotisation sécurité sociale (CNAS)', 'contribution',
                        -employee_cnas, employer_cnas, base=money(contributory),
                        rate=CNAS_EMPLOYEE_RATE * 100))
    r.social_contributions = employee_cnas
    r.employer_contributions = employer_cnas

    r.taxable_salary = money(r.gross_salary - employee_cnas)
    r.income_tax = compute_irg(r.taxable_salary)
    r.lines.append(Line('4000', 'IRG / salaires', 'tax', -r.income_tax, base=r.taxable_salary))

    r.net_salary = money(r.taxable_salary - r.income_tax + non_taxable)
    r.employer_cost = money(r.gross_salary + non_taxable + employer_cnas)
    return r


def count_leave_days(start: date, end: date, weekend_days, start_half=False, end_half=False) -> Decimal:
    """Working days between two dates (inclusive), skipping the company weekend."""
    if end < start:
        return Decimal('0')
    days = Decimal('0')
    current = start
    while current <= end:
        if current.weekday() not in weekend_days:
            days += 1
        current += timedelta(days=1)
    if start_half and start.weekday() not in weekend_days:
        days -= Decimal('0.5')
    if end_half and end.weekday() not in weekend_days and (end != start or not start_half):
        days -= Decimal('0.5')
    return max(days, Decimal('0'))


def working_days_in_month(year: int, month: int, weekend_days) -> Decimal:
    last = calendar.monthrange(year, month)[1]
    return count_leave_days(date(year, month, 1), date(year, month, last), weekend_days)


def overlap_days(start, end, year, month, weekend_days, start_half=False, end_half=False) -> Decimal:
    """Working days of [start, end] that fall inside the given month."""
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    lo, hi = max(start, first), min(end, last)
    if hi < lo:
        return Decimal('0')
    return count_leave_days(lo, hi, weekend_days,
                            start_half=start_half and lo == start,
                            end_half=end_half and hi == end)
