from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.db import models


class Company(models.Model):
    """The employer. The MVP runs one company per deployment, but every
    employee points at it so payslip headers and the weekend rule come from data."""

    name = models.CharField(max_length=200)
    legal_form = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    nif = models.CharField('NIF', max_length=30, blank=True)
    nis = models.CharField('NIS', max_length=30, blank=True)
    rc = models.CharField('Registre du commerce', max_length=30, blank=True)
    cnas_number = models.CharField('N° employeur CNAS', max_length=30, blank=True)
    # ISO weekday numbers (Monday=0). Algeria rests on Friday/Saturday.
    weekend_days = models.JSONField(default=list)
    annual_leave_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('30'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'companies'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.weekend_days:
            self.weekend_days = [4, 5]
        super().save(*args, **kwargs)


class User(AbstractUser):
    class Role(models.TextChoices):
        EMPLOYEE = 'employee', 'Salarié'
        MANAGER = 'manager', 'Manager'
        HR = 'hr', 'Gestionnaire RH'

    class ContractType(models.TextChoices):
        CDI = 'cdi', 'CDI'
        CDD = 'cdd', 'CDD'
        INTERN = 'intern', 'Stage'
        OTHER = 'other', 'Autre'

    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.SET_NULL, related_name='employees')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    manager = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='team')

    employee_number = models.CharField('Matricule', max_length=30, blank=True)
    job_title = models.CharField('Poste', max_length=120, blank=True)
    department = models.CharField('Service', max_length=120, blank=True)
    contract_type = models.CharField(max_length=20, choices=ContractType.choices, default=ContractType.CDI)
    hire_date = models.DateField(null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    social_security_number = models.CharField('N° sécurité sociale', max_length=30, blank=True)

    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    emergency_contact = models.CharField(max_length=200, blank=True)

    bank_name = models.CharField(max_length=120, blank=True)
    iban = models.CharField('RIB / IBAN', max_length=40, blank=True)

    base_salary = models.DecimalField('Salaire de base mensuel', max_digits=12, decimal_places=2, default=Decimal('0'))

    @property
    def is_hr(self):
        return self.role == self.Role.HR or self.is_superuser

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER

    def __str__(self):
        return self.get_full_name() or self.username


class Payslip(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Brouillon'
        PUBLISHED = 'published', 'Publié'

    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payslips')
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    # Snapshot of the employee at generation time, so an old payslip keeps
    # showing the job/salary that applied that month.
    job_title = models.CharField(max_length=120, blank=True)
    department = models.CharField(max_length=120, blank=True)
    worked_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0'))
    unpaid_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0'))

    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    social_contributions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    taxable_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    income_tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    employer_contributions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    employer_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))

    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-year', '-month']
        constraints = [
            models.UniqueConstraint(fields=['employee', 'year', 'month'], name='unique_payslip_per_month'),
        ]

    def __str__(self):
        return f'{self.employee} {self.month:02d}/{self.year}'


class PayslipLine(models.Model):
    class Kind(models.TextChoices):
        EARNING = 'earning', 'Gain'
        DEDUCTION = 'deduction', 'Retenue'
        CONTRIBUTION = 'contribution', 'Cotisation'
        TAX = 'tax', 'Impôt'
        NON_TAXABLE = 'non_taxable', 'Indemnité non imposable'

    payslip = models.ForeignKey(Payslip, on_delete=models.CASCADE, related_name='lines')
    order = models.PositiveIntegerField(default=0)
    code = models.CharField(max_length=10)
    label = models.CharField(max_length=150)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    base = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    rate = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    employee_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    employer_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))

    class Meta:
        ordering = ['order']


class Document(models.Model):
    class Category(models.TextChoices):
        CONTRACT = 'contract', 'Contrat & avenants'
        CERTIFICATE = 'certificate', 'Attestations'
        PAYROLL = 'payroll', 'Paie & fiscalité'
        MEDICAL = 'medical', 'Médical'
        COMPANY = 'company', 'Documents entreprise'
        OTHER = 'other', 'Autre'

    # Null employee = a company-wide document every employee can see
    # (règlement intérieur, convention, notes de service...).
    employee = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name='documents')
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='documents/%Y/%m/')
    uploaded_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='uploaded_documents')
    created_at = models.DateTimeField(auto_now_add=True)
    viewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class LeaveType(models.TextChoices):
    ANNUAL = 'annual', 'Congé annuel'
    RECOVERY = 'recovery', 'Récupération'
    SICK = 'sick', 'Maladie'
    EXCEPTIONAL = 'exceptional', 'Absence exceptionnelle'
    UNPAID = 'unpaid', 'Congé sans solde'
    REMOTE = 'remote', 'Télétravail'


# Leave types that are counted against a yearly balance.
BALANCED_LEAVE_TYPES = [LeaveType.ANNUAL, LeaveType.RECOVERY]


class LeaveBalance(models.Model):
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_balances')
    leave_type = models.CharField(max_length=20, choices=LeaveType.choices)
    year = models.PositiveIntegerField()
    allotted = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0'))
    carried_over = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0'))

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['employee', 'leave_type', 'year'], name='unique_leave_balance'),
        ]


class RequestStatus(models.TextChoices):
    PENDING = 'pending', 'En attente'
    APPROVED = 'approved', 'Validée'
    REJECTED = 'rejected', 'Refusée'
    CANCELLED = 'cancelled', 'Annulée'


class LeaveRequest(models.Model):
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=LeaveType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    # Half-day flags: start in the afternoon / end at noon.
    start_half = models.BooleanField(default=False)
    end_half = models.BooleanField(default=False)
    days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0'))
    reason = models.TextField(blank=True)
    attachment = models.FileField(upload_to='leaves/%Y/%m/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=RequestStatus.choices, default=RequestStatus.PENDING)
    reviewer = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_leaves')
    review_comment = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date', '-created_at']


class ExpenseReport(models.Model):
    class Category(models.TextChoices):
        TRANSPORT = 'transport', 'Transport'
        MEALS = 'meals', 'Repas'
        LODGING = 'lodging', 'Hébergement'
        MILEAGE = 'mileage', 'Indemnités kilométriques'
        SUPPLIES = 'supplies', 'Fournitures'
        OTHER = 'other', 'Autre'

    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente'
        APPROVED = 'approved', 'Validée'
        REJECTED = 'rejected', 'Refusée'
        CANCELLED = 'cancelled', 'Annulée'
        PAID = 'paid', 'Remboursée'

    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')
    date = models.DateField()
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    receipt = models.FileField(upload_to='receipts/%Y/%m/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewer = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_expenses')
    review_comment = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']


class ProfileChangeRequest(models.Model):
    """Sensitive personal data (bank details, address...) is not edited directly:
    the employee submits the new values and HR applies them on approval."""

    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profile_requests')
    changes = models.JSONField()
    comment = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=RequestStatus.choices, default=RequestStatus.PENDING)
    reviewer = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_profile_requests')
    review_comment = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=200, blank=True)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
