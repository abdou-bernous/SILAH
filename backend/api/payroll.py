"""Algerian payroll engine (monthly salaried employees).

Rules implemented (checked against public 2026 sources, see README):
  - SNMG: 24 000 DA / month since 1 January 2026 (décret présidentiel 26-01), 40 h / week,
    173.33 h / month. Salaries below it are flagged, not blocked (part-time contracts exist).
  - CNAS on the contributory base ("salaire de poste" + contributory bonuses):
      employee 9 % (assurances sociales 1.5, retraite 6.75, retraite anticipée 0.25, chômage 0.5)
      employer 25 % (assurances sociales 11.5, AT/MP 1.25, retraite 11, retraite anticipée 0.25,
      chômage 1) + 0.5 % to the Fonds national de péréquation des œuvres sociales (FNPOS).
  - IRG on salaries: monthly scale of the 2022 finance law (still applied in 2026),
    taxable base rounded down to the ten dinars, 40 % allowance on the computed tax bounded
    to [1 000; 1 500] DA, full exemption up to 30 000 DA, smoothing formula between 30 000
    and 35 000 DA (IRG x 137/51 - 27 925/8). Disabled workers and retirees get the extended
    smoothing up to 42 500 DA (IRG x 93/61 - 81 213/41).
  - Non-monthly bonuses (quarterly / annual PRI-PRC, arrears "rappels"): flat 10 % IRG
    withholding on their amount net of CNAS, outside the monthly scale.
  - Allowances excluded from the CNAS base but taxable (panier, transport) and fully
    exempt ones (allocations familiales, prime de scolarité) are supported through flags.

Special sectors (CACOBATPH +0.375 %), CNAC hiring reductions and other regimes are not
covered. Rates live in one place below so they can be adjusted.
"""
import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR

SNMG = Decimal('24000')
MONTHLY_HOURS = Decimal('173.33')

CNAS_EMPLOYEE_RATE = Decimal('0.09')
CNAS_EMPLOYER_RATE = Decimal('0.25')
FNPOS_EMPLOYER_RATE = Decimal('0.005')

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
IRG_SMOOTHING_CEILING_DISABLED = Decimal('42500')
IRG_FLAT_RATE = Decimal('0.10')

# Working days used to value one day of unpaid leave.
WORKING_DAYS_PER_MONTH = Decimal('22')

CENT = Decimal('0.01')

# Law 90-11, art. 32: overtime pays at least 50 % more than the normal hourly rate.
OVERTIME_MIN_RATE = Decimal('50')


def money(value) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def overtime_amount(base_salary, hours, rate=OVERTIME_MIN_RATE) -> Decimal:
    hourly = Decimal(base_salary) / MONTHLY_HOURS
    return money(hourly * Decimal(hours) * (1 + Decimal(rate) / 100))


def compute_irg(taxable, disabled=False) -> Decimal:
    taxable = Decimal(taxable)
    if taxable <= IRG_EXEMPTION_CEILING:
        return Decimal('0.00')
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

    if disabled and base < IRG_SMOOTHING_CEILING_DISABLED:
        tax = tax * Decimal(93) / Decimal(61) - Decimal(81213) / Decimal(41)
    elif not disabled and base < IRG_SMOOTHING_CEILING:
        tax = tax * Decimal(137) / Decimal(51) - Decimal(27925) / Decimal(8)
    return money(max(tax, Decimal('0')))


# Common Algerian pay items with their usual treatment. `tax` is 'scale' (monthly IRG
# scale), 'flat' (10 % withholding) or 'exempt'. HR can still override the flags.
PRESETS = {
    'pri': {'label': 'Prime de rendement individuel (PRI)', 'label_ar': 'منحة المردودية الفردية', 'contributory': True, 'tax': 'scale'},
    'prc': {'label': 'Prime de rendement collectif trimestrielle (PRC)', 'label_ar': 'منحة المردودية الجماعية الفصلية', 'contributory': True, 'tax': 'flat'},
    'iep': {'label': "Indemnité d'expérience professionnelle (IEP)", 'label_ar': 'تعويض الخبرة المهنية', 'contributory': True, 'tax': 'scale'},
    'overtime': {'label': 'Heures supplémentaires', 'label_ar': 'الساعات الإضافية', 'contributory': True, 'tax': 'scale'},
    'nuisance': {'label': 'Indemnité de nuisance', 'label_ar': 'تعويض الضرر', 'contributory': True, 'tax': 'scale'},
    'panier': {'label': 'Indemnité de panier', 'label_ar': 'تعويض السلة', 'contributory': False, 'tax': 'scale'},
    'transport': {'label': 'Indemnité de transport', 'label_ar': 'تعويض النقل', 'contributory': False, 'tax': 'scale'},
    'rappel': {'label': 'Rappel sur salaire', 'label_ar': 'مخلفات الأجر', 'contributory': True, 'tax': 'flat'},
    'family': {'label': 'Allocations familiales', 'label_ar': 'المنح العائلية', 'contributory': False, 'tax': 'exempt'},
    'school': {'label': 'Prime de scolarité', 'label_ar': 'منحة التمدرس', 'contributory': False, 'tax': 'exempt'},
    'other': {'label': 'Autre prime', 'label_ar': 'منحة أخرى', 'contributory': True, 'tax': 'scale'},
}


@dataclass
class Bonus:
    label: str
    amount: Decimal
    contributory: bool = True   # subject to CNAS
    tax: str = 'scale'          # 'scale' | 'flat' | 'exempt'
    label_ar: str = ''


@dataclass
class Line:
    code: str
    label: str
    label_ar: str
    kind: str
    employee_amount: Decimal = Decimal('0')
    employer_amount: Decimal = Decimal('0')
    base: Decimal | None = None
    rate: Decimal | None = None


@dataclass
class PayslipResult:
    lines: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    gross_salary: Decimal = Decimal('0')
    social_contributions: Decimal = Decimal('0')
    taxable_salary: Decimal = Decimal('0')
    income_tax: Decimal = Decimal('0')
    flat_tax: Decimal = Decimal('0')
    non_taxable: Decimal = Decimal('0')
    net_salary: Decimal = Decimal('0')
    employer_contributions: Decimal = Decimal('0')
    employer_cost: Decimal = Decimal('0')


def compute_payslip(base_salary, bonuses=(), unpaid_days=0, disabled=False) -> PayslipResult:
    base_salary = money(base_salary)
    unpaid_days = Decimal(unpaid_days)
    r = PayslipResult()
    if 0 < base_salary < SNMG:
        r.warnings.append(f'Salaire de base inférieur au SNMG ({SNMG} DA) : vérifiez le temps de travail.')

    r.lines.append(Line('R100', 'Salaire de base', 'الأجر القاعدي', 'earning', base_salary,
                        base=MONTHLY_HOURS, rate=money(base_salary / MONTHLY_HOURS)))

    contributory = base_salary        # CNAS base
    scale_items = base_salary         # gross items taxed on the monthly scale
    flat_items = Decimal('0')         # gross items taxed at 10 %
    flat_contributory = Decimal('0')  # part of flat_items also subject to CNAS
    exempt = Decimal('0')

    for i, b in enumerate(bonuses):
        amount = money(b.amount)
        if amount == 0:
            continue
        if b.tax == 'exempt' and not b.contributory:
            r.lines.append(Line(f'R{500 + i}', b.label, b.label_ar, 'non_taxable', amount))
            exempt += amount
            continue
        r.lines.append(Line(f'R{200 + i}', b.label, b.label_ar, 'earning', amount))
        if b.contributory:
            contributory += amount
        if b.tax == 'flat':
            flat_items += amount
            if b.contributory:
                flat_contributory += amount
        elif b.tax == 'scale':
            scale_items += amount
        else:  # exempt from IRG but contributory: still in gross and CNAS base
            exempt += amount

    if unpaid_days > 0:
        daily = base_salary / WORKING_DAYS_PER_MONTH
        deduction = money(min(daily * unpaid_days, base_salary))
        r.lines.append(Line('R190', 'Absence non rémunérée', 'غياب غير مدفوع الأجر', 'deduction', -deduction,
                            base=unpaid_days, rate=money(daily)))
        contributory -= deduction
        scale_items -= deduction

    # Exempt-but-contributory items sit in gross; fully exempt ones are paid on top of net.
    exempt_in_gross = sum((money(b.amount) for b in bonuses if b.tax == 'exempt' and b.contributory), Decimal('0'))
    r.gross_salary = money(scale_items + flat_items + exempt_in_gross)

    employee_cnas = money(contributory * CNAS_EMPLOYEE_RATE)
    employer_cnas = money(contributory * CNAS_EMPLOYER_RATE)
    fnpos = money(contributory * FNPOS_EMPLOYER_RATE)
    r.lines.append(Line('R300', 'Cotisation sécurité sociale (CNAS)', 'اشتراك الضمان الاجتماعي', 'contribution',
                        -employee_cnas, employer_cnas, base=money(contributory), rate=CNAS_EMPLOYEE_RATE * 100))
    r.lines.append(Line('R310', 'Œuvres sociales (FNPOS)', 'الصندوق الوطني لمعادلة الخدمات الاجتماعية', 'contribution',
                        Decimal('0'), fnpos, base=money(contributory), rate=FNPOS_EMPLOYER_RATE * 100))
    r.social_contributions = employee_cnas
    r.employer_contributions = employer_cnas + fnpos

    # Split the employee CNAS between the scale-taxed and the flat-taxed items.
    cnas_on_flat = money(flat_contributory * CNAS_EMPLOYEE_RATE)
    cnas_on_exempt = money(exempt_in_gross * CNAS_EMPLOYEE_RATE)
    cnas_on_scale = employee_cnas - cnas_on_flat - cnas_on_exempt

    r.taxable_salary = money(scale_items - cnas_on_scale)
    r.income_tax = compute_irg(r.taxable_salary, disabled)
    r.lines.append(Line('R400', 'IRG / salaires (barème)', 'الضريبة على الدخل الإجمالي (الأجور)', 'tax',
                        -r.income_tax, base=r.taxable_salary))
    if flat_items:
        flat_base = money(flat_items - cnas_on_flat)
        r.flat_tax = money(flat_base * IRG_FLAT_RATE)
        r.lines.append(Line('R410', 'IRG 10 % (primes non mensuelles)', 'الضريبة على الدخل الإجمالي 10% (المنح)', 'tax',
                            -r.flat_tax, base=flat_base, rate=IRG_FLAT_RATE * 100))

    fully_exempt = exempt - exempt_in_gross
    r.non_taxable = fully_exempt
    r.net_salary = money(r.gross_salary - employee_cnas - r.income_tax - r.flat_tax + fully_exempt)
    r.employer_cost = money(r.gross_salary + fully_exempt + r.employer_contributions)
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
