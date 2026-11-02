import calendar
import logging
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from . import payroll
from .models import (
    AuditLog, BALANCED_LEAVE_TYPES, CertificateRequest, Company, Document, EmployeePayItem, ExpenseReport,
    LeaveBalance, LeaveRequest, LeaveType, MonthlyVariable, Notification, Payslip, PayslipLine,
    ProfileChangeRequest, RequestStatus,
)
from .pdf import fmt, month_label, render_certificate, render_payslip
from .permissions import (
    CanManageCompanies, IsCompanyAdmin, IsPlatformAdmin, active_company, can_review, hr_recipients,
    is_company_admin, visible_companies,
)
from .serializers import (
    LEAVE_TYPE_CHOICES, REQUESTABLE_FIELDS, AuditLogSerializer, CertificateRequestSerializer,
    ChangePasswordSerializer, CompanyAdminSerializer, CompanySerializer, DocumentSerializer,
    EmployeePayItemSerializer, EmployeeSerializer, ExpenseSerializer, LeaveBalanceSerializer,
    LeaveRequestSerializer, MonthlyVariablesSerializer, NotificationSerializer, PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer, PayrollRunSerializer, PayslipCorrectionSerializer, PayslipDetailSerializer,
    PayslipListSerializer,
    PlatformUserSerializer, ProfileChangeRequestSerializer, ProfileSerializer, ReviewSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------- helpers

def notify(user, title, message='', link='', email=False, company=None):
    """`company`: the client a notification is about. An accountant belongs to none of his clients and works
    on one at a time, so his link names it (`?client=<id>`) and opens on that client."""
    if not user or not user.is_active:
        return
    if company and link and user.role == User.Role.ACCOUNTANT:
        link = f"{link}{'&' if '?' in link else '?'}client={company.id}"
    Notification.objects.create(user=user, title=title, message=message, link=link)
    if email and user.email:
        try:
            send_mail(f'[SILAH] {title}', message or title, settings.DEFAULT_FROM_EMAIL, [user.email])
        except Exception:  # an email outage must never block the HR action itself
            logger.exception('Notification email failed')


def audit(request, action, summary='', company=None):
    """Record a sensitive action. `summary` names people and fields, never amounts or personal values."""
    AuditLog.objects.create(company=company or active_company(request), actor=request.user,
                            actor_name=str(request.user), action=action, summary=summary[:255])


def hr_reviewers_for(employee):
    """Who handles requests only HR can decide (records, certificates): HR and accountants, never oneself."""
    return [u for u in hr_recipients(employee.company) if u.id != employee.id]


def reviewers_for(employee):
    """Who gets told about a new absence or expense: the manager, or the company's HR / accountants."""
    if employee.manager and employee.manager.is_active:
        return [employee.manager]
    return hr_reviewers_for(employee)


SOLE_REVIEWER_NOTE = "Validée automatiquement : aucun autre valideur dans l'entreprise."


def decides_alone(user, reviewers):
    """The only HR user of a company, with no manager and no accountant, has nobody to review their own
    requests: rather than waiting forever, they are approved at once and the journal says so."""
    return user.role == User.Role.HR and not reviewers


def of_month(year, month):
    """"de mars 2026", but "d'octobre 2026"."""
    period = month_label(year, month).lower()
    return f"d'{period}" if period[0] in 'aeiouy' else f'de {period}'


def months_between(start, end):
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def payroll_impact(lr):
    """Unpaid leave changes the pay of its months. When one of them is already computed, say what to redo."""
    if lr.leave_type != LeaveType.UNPAID:
        return []
    found = []
    weekend = lr.employee.company.weekend_days
    for y, m in months_between(lr.start_date, lr.end_date):
        if not payroll.overlap_days(lr.start_date, lr.end_date, y, m, weekend, lr.start_half, lr.end_half):
            continue   # only rest days fall in this month: its pay does not change
        month = in_force(Payslip.objects.filter(employee=lr.employee, year=y, month=m))
        published = month.filter(status=Payslip.Status.PUBLISHED).first()
        if published:
            found.append((f'Le bulletin {of_month(y, m)} est déjà publié : corrigez-le pour tenir compte de cette absence.',
                          f'/bulletins/{published.id}'))
        elif month.filter(status=Payslip.Status.DRAFT).exists():
            found.append((f'La paie {of_month(y, m)} est en brouillon : relancez le calcul pour tenir compte de cette absence.',
                          '/admin/paie'))
    return found


def warn_payroll(lr, what):
    """Tell the payroll managers that an unpaid leave changed after its month was computed."""
    found = payroll_impact(lr)
    for message, link in found:
        for u in hr_recipients(lr.employee.company):
            notify(u, f'Absence sans solde {what} : paie à revoir pour {lr.employee}', message, link,
                   company=lr.employee.company)
    return [message for message, _ in found]


def cancel_open_requests(emp):
    """When someone leaves: what was still waiting, and absences planned after today, are cancelled."""
    leaves = LeaveRequest.objects.filter(employee=emp).filter(
        Q(status=RequestStatus.PENDING) | Q(status=RequestStatus.APPROVED, start_date__gt=date.today()))
    return (leaves.update(status=RequestStatus.CANCELLED)
            + ProfileChangeRequest.objects.filter(employee=emp, status=RequestStatus.PENDING).update(
                status=RequestStatus.CANCELLED)
            + CertificateRequest.objects.filter(employee=emp, status=RequestStatus.PENDING).update(
                status=RequestStatus.CANCELLED))


def apply_profile_changes(emp, changes):
    for field, value in changes.items():
        if field not in REQUESTABLE_FIELDS:
            continue
        if field == 'birth_date':
            value = date.fromisoformat(value) if value else None
        elif field == 'children_count':
            value = int(value or 0)
        setattr(emp, field, value)
    emp.save()


def check_certificate(req):
    """A certificate is an official document: refuse to issue one that would print blanks or false facts."""
    e = req.employee
    if not e.is_active:
        raise ValidationError("Ce salarié a quitté l'entreprise : l'attestation ne peut plus être délivrée.")
    missing = [label for label, ok in [("date d'embauche", e.hire_date), ('poste', e.job_title),
                                       ('salaire de base', req.kind != CertificateRequest.Kind.SALARY or e.base_salary > 0)]
               if not ok]
    if missing:
        raise ValidationError(f"Fiche du salarié incomplète pour cette attestation : {', '.join(missing)}. "
                              f"Complétez-la, puis délivrez l'attestation.")
    if e.hire_date > date.today():
        raise ValidationError(f"L'embauche prend effet le {e.hire_date:%d/%m/%Y} : "
                              f"l'attestation ne peut pas être délivrée avant.")


def issue_certificate(req, reviewer, comment=''):
    check_certificate(req)
    emp = req.employee
    pdf = render_certificate(req, date.today())
    title = f'{req.get_kind_display()} — {date.today():%d/%m/%Y}'
    doc = Document(company=emp.company, employee=emp, category=Document.Category.CERTIFICATE,
                   title=title, uploaded_by=reviewer)
    doc.file.save(f'{req.kind}_{emp.username}.pdf', ContentFile(pdf), save=True)
    req.document = doc
    mark_reviewed(req, reviewer, RequestStatus.APPROVED, comment)
    notify(emp, 'Votre attestation est disponible', title, '/documents', email=True)


def employee_bonuses(emp, year, month):
    """Everything specific to one employee for one month: permanent items, overtime, individual bonus."""
    items = [payroll.Bonus(i.label, i.amount, i.contributory, i.tax, i.label_ar)
             for i in emp.pay_items.filter(is_active=True)]
    variable = MonthlyVariable.objects.filter(employee=emp, year=year, month=month).first()
    if variable and variable.overtime_hours > 0:
        preset = payroll.PRESETS['overtime']
        items.append(payroll.Bonus(f"{preset['label']} ({variable.overtime_hours} h, +{variable.overtime_rate} %)",
                                   payroll.overtime_amount(emp.base_salary, variable.overtime_hours, variable.overtime_rate),
                                   preset['contributory'], preset['tax'], preset['label_ar']))
    if variable and variable.bonus_amount > 0:
        items.append(payroll.Bonus(variable.bonus_label or 'Prime individuelle', variable.bonus_amount,
                                   label_ar='منحة فردية'))
    return items


EXPENSES_LABEL = 'Remboursement de frais'


def bonus_dicts(bonuses):
    """The run's bonuses as recorded on a payslip (JSON, amounts as strings)."""
    return [{'label': b.label, 'label_ar': b.label_ar, 'amount': str(b.amount), 'contributory': b.contributory,
             'tax': b.tax} for b in bonuses]


def bonuses_from_dicts(items):
    return [payroll.Bonus(i['label'], Decimal(str(i['amount'])), i.get('contributory', True), i.get('tax', 'scale'),
                          i.get('label_ar', '')) for i in items]


def legacy_run_items(p):
    """For payslips computed before the run's bonuses were recorded: rebuild them from the lines, leaving
    out what the employee's own items, the monthly grid and the expenses bring. Only a starting point,
    shown in the correction form for the HR to check."""
    emp = p.employee
    own = set(emp.pay_items.filter(is_active=True).values_list('label', flat=True))
    variable = MonthlyVariable.objects.filter(employee=emp, year=p.year, month=p.month).first()
    if variable and variable.bonus_amount > 0:
        own.add(variable.bonus_label or 'Prime individuelle')
    presets = {v['label']: v for v in payroll.PRESETS.values()}
    overtime = payroll.PRESETS['overtime']['label']
    items = []
    for line in p.lines.all():
        if line.kind not in ('earning', 'non_taxable') or line.code == 'R100':
            continue
        if line.label in own or line.label == EXPENSES_LABEL or line.label.startswith(overtime):
            continue
        preset = presets.get(line.label)
        if preset:
            contributory, tax = preset['contributory'], preset['tax']
        elif line.kind == 'non_taxable':
            contributory, tax = False, 'exempt'
        else:
            contributory, tax = True, 'scale'
        items.append({'label': line.label, 'label_ar': line.label_ar, 'amount': str(line.employee_amount),
                      'contributory': contributory, 'tax': tax})
    return items


def run_items_of(p):
    return p.run_items if p.run_items is not None else legacy_run_items(p)


def variable_key(v):
    """What a monthly grid row changes on the payslip (a rate without hours, or a label without amount, changes nothing)."""
    get = (lambda k: v.get(k)) if isinstance(v, dict) else (lambda k: getattr(v, k, None))
    hours, amount = Decimal(get('overtime_hours') or 0), Decimal(get('bonus_amount') or 0)
    return (hours, Decimal(get('overtime_rate') or 0) if hours else None, amount,
            (get('bonus_label') or '') if amount else '')


def in_force(qs):
    """The payslips that count for a month: replaced ones and corrections not yet published are left out."""
    return qs.exclude(status=Payslip.Status.REPLACED).exclude(status=Payslip.Status.DRAFT, replaces__isnull=False)


def compute_payslip_for(emp, company, year, month, run_items, expenses, payslip=None, link_expenses=True):
    """Compute one employee's month and save it as a draft: `payslip` when given, a new one otherwise.
    Returns the payslip and the engine's warnings."""
    first, last = date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    weekend = company.weekend_days
    working = payroll.working_days_in_month(year, month, weekend)
    unpaid = Decimal('0')
    for lr in LeaveRequest.objects.filter(employee=emp, leave_type=LeaveType.UNPAID, status=RequestStatus.APPROVED,
                                          start_date__lte=last, end_date__gte=first):
        unpaid += payroll.overlap_days(lr.start_date, lr.end_date, year, month, weekend, lr.start_half, lr.end_half)
    # Hired during the month: the days before the start are not paid.
    before_hire = Decimal('0')
    if emp.hire_date and first < emp.hire_date <= last:
        before_hire = payroll.count_leave_days(first, emp.hire_date - timedelta(days=1), weekend)
    items = bonuses_from_dicts(run_items) + employee_bonuses(emp, year, month)
    if expenses:
        items.append(payroll.Bonus(EXPENSES_LABEL, sum(e.amount for e in expenses), contributory=False, tax='exempt',
                                   label_ar='تسديد المصاريف'))
    result = payroll.compute_payslip(emp.base_salary, items, unpaid, disabled=emp.is_disabled,
                                     days_before_hire=before_hire, working_days=working)
    warnings = list(result.warnings)
    if before_hire:
        warnings.append(f'Entrée le {emp.hire_date:%d/%m/%Y} : salaire de base réduit de {before_hire} jour(s) '
                        f'ouvré(s) non travaillé(s).')
    variable = MonthlyVariable.objects.filter(employee=emp, year=year, month=month).first()
    if variable and variable.overtime_hours > payroll.OVERTIME_MONTHLY_LIMIT:
        warnings.append(f'{variable.overtime_hours} h supplémentaires : au-delà de {payroll.OVERTIME_MONTHLY_LIMIT} h '
                        f'par mois (20 % de la durée légale), une dérogation est nécessaire.')

    p = payslip or Payslip(employee=emp, year=year, month=month)
    p.company = company
    p.run_items = run_items
    p.job_title, p.department, p.qualification = emp.job_title, emp.department, emp.qualification
    p.unpaid_days = unpaid
    p.worked_days = max(working - unpaid - before_hire, Decimal('0'))
    p.worked_hours = payroll.MONTHLY_HOURS if not (unpaid or before_hire) else payroll.money(
        payroll.MONTHLY_HOURS * p.worked_days / working) if working else Decimal('0')
    for f in ['gross_salary', 'social_contributions', 'taxable_salary', 'income_tax', 'flat_tax',
              'non_taxable', 'net_salary', 'employer_contributions', 'employer_cost']:
        setattr(p, f, getattr(result, f))
    p.save()
    p.lines.all().delete()
    PayslipLine.objects.bulk_create([
        PayslipLine(payslip=p, order=i, code=l.code, label=l.label, label_ar=l.label_ar, kind=l.kind,
                    base=l.base, rate=l.rate, employee_amount=l.employee_amount, employer_amount=l.employer_amount)
        for i, l in enumerate(result.lines)])
    if link_expenses:
        p.expenses.exclude(id__in=[e.id for e in expenses]).filter(
            status=ExpenseReport.Status.APPROVED).update(payslip=None)
        ExpenseReport.objects.filter(id__in=[e.id for e in expenses]).update(payslip=p)
    return p, warnings


def weekend_of(user):
    return user.company.weekend_days if user.company else [4, 5]


def balance_summary(employee, year):
    company = employee.company
    result = []
    for lt in BALANCED_LEAVE_TYPES:
        bal = LeaveBalance.objects.filter(employee=employee, leave_type=lt, year=year).first()
        if bal is None and lt == LeaveType.ANNUAL and company:
            bal = LeaveBalance.objects.create(employee=employee, leave_type=lt, year=year,
                                              allotted=company.annual_leave_days)
        allotted = (bal.allotted + bal.carried_over) if bal else Decimal('0')
        qs = LeaveRequest.objects.filter(employee=employee, leave_type=lt, start_date__year=year)
        taken = qs.filter(status=RequestStatus.APPROVED).aggregate(s=Sum('days'))['s'] or Decimal('0')
        pending = qs.filter(status=RequestStatus.PENDING).aggregate(s=Sum('days'))['s'] or Decimal('0')
        result.append({
            'leave_type': lt.value, 'label': lt.label, 'year': year, 'allotted': allotted,
            'taken': taken, 'pending': pending, 'remaining': allotted - taken,
        })
    return result


def mark_reviewed(obj, user, new_status, comment):
    obj.status = new_status
    obj.reviewer = user
    obj.review_comment = comment
    obj.reviewed_at = timezone.now()
    obj.save()


def review_comment(request):
    s = ReviewSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    return s.validated_data['comment']


def require_company(request):
    company = active_company(request)
    if company is None:
        raise ValidationError("Aucune entreprise sélectionnée.")
    return company


def int_param(value, name, low=None, high=None):
    """A query or body parameter that must be an integer: bad input is a 400, not a crash."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValidationError({name: 'Valeur invalide.'})
    if (low is not None and number < low) or (high is not None and number > high):
        raise ValidationError({name: 'Valeur invalide.'})
    return number


def year_param(value):
    return int_param(value, 'year', 2000, 2100)


def month_param(value):
    return int_param(value, 'month', 1, 12)


def scoped_queryset(request, qs, hr_only=False):
    """?scope=mine (default) | team | all, always limited to the active company.
    team: a manager's direct reports, or everyone but oneself for a company admin.
    hr_only: requests a manager does not decide (records, certificates) stay private to HR."""
    user = request.user
    scope = request.query_params.get('scope', 'mine')
    if scope in ('team', 'all'):
        company = active_company(request)
        if is_company_admin(request):
            qs = qs.filter(employee__company=company)
            return qs.exclude(employee=user) if scope == 'team' else qs
        if scope == 'all' or hr_only:
            raise PermissionDenied('Réservé à la gestion RH.')
        return qs.filter(employee__manager=user)
    return qs.filter(employee=user)


def visible_to(request, qs):
    """Single-object access for requests (leaves, expenses): own, direct reports, or company admin."""
    user = request.user
    cond = Q(employee=user) | Q(employee__manager=user)
    if is_company_admin(request):
        cond |= Q(employee__company=active_company(request))
    return qs.filter(cond)


def file_download(field, filename=None):
    if not field:
        raise ValidationError('Aucun fichier.')
    try:
        handle = field.open('rb')
    except FileNotFoundError:
        raise ValidationError('Fichier introuvable sur le serveur.')
    return FileResponse(handle, as_attachment=True, filename=filename or field.name.rsplit('/', 1)[-1])


# ---------------------------------------------------------------- auth & profile

class LoginSerializer(TokenObtainPairSerializer):
    """Accepts either the username or the email address in the `username` field."""

    def validate(self, attrs):
        login = attrs.get(self.username_field, '')
        if '@' in login:
            user = User.objects.filter(email__iexact=login).first()
            if user:
                attrs[self.username_field] = user.username
        data = super().validate(attrs)
        company = self.user.company
        if company is not None and not company.is_active:
            raise AuthenticationFailed("Le compte de votre entreprise est désactivé.")
        return data


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_scope = 'login'


class MeView(RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    def post(self, request):
        s = ChangePasswordSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        request.user.set_password(s.validated_data['new_password'])
        request.user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetRequestView(APIView):
    """Always answers 204, so the form cannot be used to find out who has an account."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = 'password_reset'

    def post(self, request):
        s = PasswordResetRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        users = User.objects.filter(email__iexact=s.validated_data['email'], is_active=True).select_related('company')
        for user in users:
            if user.company and not user.company.is_active:
                continue
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            link = f'{settings.FRONTEND_URL}/reinitialiser?uid={uid}&token={default_token_generator.make_token(user)}'
            try:
                send_mail('[SILAH] Réinitialisation de votre mot de passe',
                          f'Bonjour,\n\nCe lien permet de choisir un nouveau mot de passe pour le compte '
                          f'{user.username} :\n{link}\n\nSi vous n\'êtes pas à l\'origine de cette demande, '
                          f'ignorez ce message.', settings.DEFAULT_FROM_EMAIL, [user.email])
            except Exception:  # never reveal a delivery problem to an anonymous caller
                logger.exception('Password reset email failed')
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = 'password_reset'

    def post(self, request):
        s = PasswordResetConfirmSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(s.validated_data['uid'])), is_active=True)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            user = None
        if user is None or not default_token_generator.check_token(user, s.validated_data['token']):
            raise ValidationError({'token': 'Ce lien est invalide ou a expiré.'})
        try:
            validate_password(s.validated_data['new_password'], user)
        except DjangoValidationError as e:
            raise ValidationError({'new_password': e.messages})
        user.set_password(s.validated_data['new_password'])
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CompanyView(APIView):
    """The active company."""

    def get(self, request):
        c = active_company(request)
        return Response(CompanySerializer(c).data if c else None)

    def patch(self, request):
        if not is_company_admin(request):
            raise PermissionDenied("Réservé à la gestion RH de l'entreprise.")
        c = require_company(request)
        s = CompanySerializer(c, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        audit(request, 'company.update', c.name, c)
        return Response(s.data)


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({'status': 'ok'})


# ---------------------------------------------------------------- companies (accountants & admin)

def payroll_month_totals(qs):
    return qs.aggregate(gross=Sum('gross_salary'), net=Sum('net_salary'), cost=Sum('employer_cost'),
                        irg=Sum('income_tax'), irg_flat=Sum('flat_tax'), cnas=Sum('social_contributions'),
                        cnas_employer=Sum('employer_contributions'), count=Count('id'))


class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanyAdminSerializer
    permission_classes = [CanManageCompanies]

    def get_queryset(self):
        qs = visible_companies(self.request.user).annotate(
            employee_count=Count('employees', filter=Q(employees__is_active=True), distinct=True))
        q = self.request.query_params.get('q')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(city__icontains=q) | Q(nif__icontains=q))
        return qs.order_by('name')

    def perform_create(self, serializer):
        company = serializer.save(created_by=self.request.user)
        company.managers.add(self.request.user)

    def destroy(self, request, *args, **kwargs):
        # Payroll history must be kept: deactivate instead of deleting.
        if not request.user.is_platform_admin:
            raise PermissionDenied("Seul l'administrateur peut désactiver une entreprise.")
        c = self.get_object()
        c.is_active = False
        c.save(update_fields=['is_active'])
        audit(request, 'company.deactivate', c.name, c)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        if not request.user.is_platform_admin:
            raise PermissionDenied()
        c = self.get_object()
        c.is_active = True
        c.save(update_fields=['is_active'])
        audit(request, 'company.reactivate', c.name, c)
        return Response(CompanyAdminSerializer(self.get_queryset().get(pk=c.pk)).data)

    @action(detail=False, methods=['get'])
    def overview(self, request):
        """One row per managed company with this month's payroll and pending work."""
        today = date.today()
        rows = []
        for c in self.get_queryset():
            last = Payslip.objects.filter(company=c).order_by('-year', '-month').first()
            month_qs = in_force(Payslip.objects.filter(company=c, year=last.year, month=last.month)) if last else Payslip.objects.none()
            totals = payroll_month_totals(month_qs)
            rows.append({
                **CompanyAdminSerializer(c).data,
                'last_payroll': {'year': last.year, 'month': last.month, **totals} if last else None,
                'drafts': Payslip.objects.filter(company=c, status=Payslip.Status.DRAFT).count(),
                'pending_leaves': LeaveRequest.objects.filter(employee__company=c, status=RequestStatus.PENDING).count(),
                'pending_expenses': ExpenseReport.objects.filter(employee__company=c, status=ExpenseReport.Status.PENDING).count(),
                'pending_profile': ProfileChangeRequest.objects.filter(employee__company=c, status=RequestStatus.PENDING).count(),
                'pending_certificates': CertificateRequest.objects.filter(employee__company=c,
                                                                          status=RequestStatus.PENDING).count(),
                'absent_today': LeaveRequest.objects.filter(employee__company=c, status=RequestStatus.APPROVED,
                                                            start_date__lte=today, end_date__gte=today).count(),
            })
        return Response(rows)


# ---------------------------------------------------------------- platform admin

class PlatformStatsView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        today = date.today()
        months = []
        y, m = today.year, today.month
        for _ in range(6):
            months.append((y, m))
            m -= 1
            if m == 0:
                y, m = y - 1, 12
        months.reverse()
        published = Payslip.objects.filter(status=Payslip.Status.PUBLISHED)
        trend = [{'year': y, 'month': m, **payroll_month_totals(published.filter(year=y, month=m))} for y, m in months]

        companies = Company.objects.annotate(
            employee_count=Count('employees', filter=Q(employees__is_active=True), distinct=True)).order_by('name')
        company_rows = []
        for c in companies:
            last = Payslip.objects.filter(company=c).order_by('-year', '-month').first()
            company_rows.append({
                'id': c.id, 'name': c.name, 'city': c.city, 'is_active': c.is_active,
                'employee_count': c.employee_count,
                'managers': [u.get_full_name() or u.username for u in c.managers.all()],
                'last_payroll': f'{last.month:02d}/{last.year}' if last else None,
                'last_net': payroll_month_totals(in_force(Payslip.objects.filter(company=c, year=last.year, month=last.month)))['net'] if last else None,
                'pending': (LeaveRequest.objects.filter(employee__company=c, status=RequestStatus.PENDING).count()
                            + ExpenseReport.objects.filter(employee__company=c, status=ExpenseReport.Status.PENDING).count()),
            })

        roles = dict(User.objects.filter(is_active=True).values_list('role').annotate(n=Count('id')))
        return Response({
            'totals': {
                'companies': Company.objects.filter(is_active=True).count(),
                'companies_inactive': Company.objects.filter(is_active=False).count(),
                'employees': User.objects.filter(is_active=True, company__isnull=False).count(),
                'accountants': roles.get(User.Role.ACCOUNTANT, 0),
                'admins': roles.get(User.Role.ADMIN, 0),
                'payslips_total': published.count(),
                'pending_leaves': LeaveRequest.objects.filter(status=RequestStatus.PENDING).count(),
                'pending_expenses': ExpenseReport.objects.filter(status=ExpenseReport.Status.PENDING).count(),
                'documents': Document.objects.count(),
            },
            'roles': roles,
            'trend': trend,
            'companies': company_rows,
            'recent_users': [{'id': u.id, 'full_name': u.get_full_name() or u.username, 'role': u.role,
                              'company': u.company.name if u.company else None, 'date_joined': u.date_joined}
                             for u in User.objects.select_related('company').order_by('-date_joined')[:6]],
        })


class PlatformUserViewSet(viewsets.ModelViewSet):
    serializer_class = PlatformUserSerializer
    permission_classes = [IsPlatformAdmin]

    def get_queryset(self):
        return (User.objects.filter(role__in=[User.Role.ACCOUNTANT, User.Role.ADMIN])
                .prefetch_related('managed_companies').order_by('role', 'last_name', 'username'))

    def destroy(self, request, *args, **kwargs):
        u = self.get_object()
        if u == request.user:
            raise ValidationError('Vous ne pouvez pas désactiver votre propre compte.')
        u.is_active = False
        u.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------- dashboard

class DashboardView(APIView):
    def get(self, request):
        user = request.user
        today = date.today()
        last = Payslip.objects.filter(employee=user, status=Payslip.Status.PUBLISHED).first()
        docs = Document.objects.filter(Q(employee=user) | Q(employee__isnull=True, company=user.company_id))[:4] \
            if user.company_id else Document.objects.none()
        upcoming = LeaveRequest.objects.filter(
            employee=user, end_date__gte=today,
            status__in=[RequestStatus.PENDING, RequestStatus.APPROVED]).order_by('start_date')[:3]

        to_review = {}
        company = active_company(request)
        admin = is_company_admin(request)
        if admin or user.is_manager:
            team_leaves = LeaveRequest.objects.filter(status=RequestStatus.PENDING).exclude(employee=user)
            team_expenses = ExpenseReport.objects.filter(status=ExpenseReport.Status.PENDING).exclude(employee=user)
            if admin:
                team_leaves = team_leaves.filter(employee__company=company)
                team_expenses = team_expenses.filter(employee__company=company)
            else:
                team_leaves = team_leaves.filter(employee__manager=user)
                team_expenses = team_expenses.filter(employee__manager=user)
            to_review = {'leaves': team_leaves.count(), 'expenses': team_expenses.count()}
            if admin:
                # Same rule as the queues: one's own requests are decided by someone else.
                to_review['profile_requests'] = ProfileChangeRequest.objects.filter(
                    employee__company=company, status=RequestStatus.PENDING).exclude(employee=user).count()
                to_review['certificates'] = CertificateRequest.objects.filter(
                    employee__company=company, status=RequestStatus.PENDING).exclude(employee=user).count()

        return Response({
            'has_employee_space': bool(user.company_id),
            'last_payslip': PayslipListSerializer(last).data if last else None,
            'balances': balance_summary(user, today.year) if user.company_id else [],
            'upcoming_leaves': LeaveRequestSerializer(upcoming, many=True).data,
            'recent_documents': DocumentSerializer(docs, many=True).data,
            'pending_requests': {
                'leaves': LeaveRequest.objects.filter(employee=user, status=RequestStatus.PENDING).count(),
                'expenses': ExpenseReport.objects.filter(employee=user, status=ExpenseReport.Status.PENDING).count(),
                'profile': ProfileChangeRequest.objects.filter(employee=user, status=RequestStatus.PENDING).count(),
            },
            'unread_notifications': Notification.objects.filter(user=user, read=False).count(),
            'to_review': to_review,
        })


# ---------------------------------------------------------------- employees (company admins)

class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = [IsCompanyAdmin]

    def get_queryset(self):
        company = active_company(self.request)
        qs = User.objects.filter(company=company).select_related('manager').order_by('last_name', 'first_name', 'username')
        q = self.request.query_params.get('q')
        if q:
            qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(username__icontains=q)
                           | Q(employee_number__icontains=q) | Q(department__icontains=q))
        if self.request.query_params.get('active') == '1':
            qs = qs.filter(is_active=True)
        return qs

    def get_serializer_context(self):
        return {**super().get_serializer_context(), 'company': active_company(self.request)}

    def get_permissions(self):
        # Managers need the directory to read names (team calendar, filters).
        if self.action == 'directory':
            return [IsAuthenticated()]
        return super().get_permissions()

    def perform_create(self, serializer):
        emp = serializer.save(company=require_company(self.request))
        audit(self.request, 'employee.create', str(emp))

    def perform_update(self, serializer):
        fields = ', '.join(sorted(serializer.validated_data))
        was_active = serializer.instance.is_active
        emp = serializer.save()
        audit(self.request, 'employee.update', f'{emp} : {fields}')
        if was_active and not emp.is_active:
            self._deactivated(emp)

    def destroy(self, request, *args, **kwargs):
        # Payroll records must be kept: deactivate instead of deleting.
        emp = self.get_object()
        if emp == request.user:
            raise ValidationError('Vous ne pouvez pas désactiver votre propre compte.')
        emp.is_active = False
        emp.save(update_fields=['is_active'])
        self._deactivated(emp)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _deactivated(self, emp):
        cancelled = cancel_open_requests(emp)
        audit(self.request, 'employee.deactivate',
              f'{emp}' + (f' : {cancelled} demande(s) en cours annulée(s)' if cancelled else ''))

    @action(detail=True, methods=['get', 'post'])
    def balances(self, request, pk=None):
        emp = self.get_object()
        year = year_param(request.query_params.get('year') or request.data.get('year') or date.today().year)
        if request.method == 'POST':
            lt = request.data.get('leave_type')
            if lt not in [t.value for t in BALANCED_LEAVE_TYPES]:
                raise ValidationError({'leave_type': 'Type de congé sans compteur.'})
            bal, _ = LeaveBalance.objects.get_or_create(employee=emp, leave_type=lt, year=year)
            s = LeaveBalanceSerializer(bal, data={'employee': emp.id, 'leave_type': lt, 'year': year,
                                                  'allotted': request.data.get('allotted', bal.allotted),
                                                  'carried_over': request.data.get('carried_over', bal.carried_over)})
            s.is_valid(raise_exception=True)
            s.save()
        return Response(balance_summary(emp, year))

    @action(detail=False, methods=['get'])
    def directory(self, request):
        company = active_company(request)
        qs = User.objects.filter(is_active=True, company=company).order_by('last_name', 'first_name') if company else []
        return Response([{'id': u.id, 'full_name': u.get_full_name() or u.username, 'job_title': u.job_title,
                          'department': u.department, 'manager': u.manager_id, 'role': u.role} for u in qs])


# ---------------------------------------------------------------- payslips

class PayslipViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin,
                     viewsets.GenericViewSet):

    def get_serializer_class(self):
        return PayslipDetailSerializer if self.action == 'retrieve' else PayslipListSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Payslip.objects.select_related('employee', 'employee__company', 'company', 'replaces', 'replaced_by').prefetch_related('lines')
        params = self.request.query_params
        admin = is_company_admin(self.request)
        company = active_company(self.request)
        if admin and params.get('scope') == 'all':
            qs = qs.filter(company=company)
            if params.get('employee'):
                qs = qs.filter(employee_id=int_param(params['employee'], 'employee'))
            if params.get('month'):
                qs = qs.filter(month=month_param(params['month']))
        elif admin and self.action not in ('list', 'years'):
            # Own payslips, plus any payslip of the managed company.
            qs = qs.filter(Q(company=company) | Q(employee=user, status=Payslip.Status.PUBLISHED))
        else:
            qs = qs.filter(employee=user, status=Payslip.Status.PUBLISHED)
        if params.get('year'):
            qs = qs.filter(year=year_param(params['year']))
        return qs

    def _mark_viewed(self, p):
        if p.employee_id == self.request.user.id and not p.viewed_at:
            p.viewed_at = timezone.now()
            p.save(update_fields=['viewed_at'])

    def retrieve(self, request, *args, **kwargs):
        p = self.get_object()
        self._mark_viewed(p)
        return Response(PayslipDetailSerializer(p).data)

    def destroy(self, request, *args, **kwargs):
        if not is_company_admin(request):
            raise PermissionDenied('Réservé à la gestion RH.')
        p = self.get_object()
        if p.status != Payslip.Status.DRAFT:
            raise ValidationError('Un bulletin publié ne peut pas être supprimé : utilisez « Corriger ».')
        audit(request, 'payroll.correction_cancel' if p.replaces_id else 'payroll.delete',
              f'{p.employee} {month_label(p.year, p.month)}')
        p.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        p = self.get_object()
        self._mark_viewed(p)
        response = HttpResponse(render_payslip(p), content_type='application/pdf')
        name = (p.employee.get_full_name() or p.employee.username).replace(' ', '_')
        response['Content-Disposition'] = f'attachment; filename="bulletin_{p.year}_{p.month:02d}_{name}.pdf"'
        return response

    @action(detail=False, methods=['get'])
    def years(self, request):
        qs = self.get_queryset().values_list('year', flat=True).distinct()
        return Response(sorted(set(qs), reverse=True))

    @action(detail=False, methods=['get'], permission_classes=[IsCompanyAdmin])
    def presets(self, request):
        return Response([{'key': k, **v} for k, v in payroll.PRESETS.items()])

    @action(detail=True, methods=['post'], permission_classes=[IsCompanyAdmin])
    def publish(self, request, pk=None):
        p = self.get_object()
        if p.company_id != active_company(request).id:
            raise PermissionDenied()
        self._publish(p)
        audit(request, 'payroll.publish', f'{p.employee} {month_label(p.year, p.month)}')
        return Response(PayslipListSerializer(p).data)

    @staticmethod
    def _publish(p):
        if p.status != Payslip.Status.DRAFT:
            return
        original = p.replaces
        with transaction.atomic():
            if original:
                if original.status != Payslip.Status.PUBLISHED:
                    raise ValidationError("Le bulletin d'origine n'est plus en vigueur.")
                # The original stays as issued, marked replaced; its expenses now belong to the correction.
                original.status = Payslip.Status.REPLACED
                original.save(update_fields=['status'])
                original.expenses.update(payslip=p)
            p.status = Payslip.Status.PUBLISHED
            p.published_at = timezone.now()
            p.save(update_fields=['status', 'published_at'])
            # Expenses carried by this payslip are repaid with it.
            p.expenses.filter(status=ExpenseReport.Status.APPROVED).update(status=ExpenseReport.Status.PAID)
        period = of_month(p.year, p.month)
        if original:
            diff = p.net_salary - original.net_salary
            notify(p.employee, f'Votre bulletin {period} a été corrigé',
                   f'Nouveau net à payer : {fmt(p.net_salary)} DA ({"+" if diff >= 0 else "-"}{fmt(abs(diff))} DA). '
                   f'Motif : {p.correction_reason}', f'/bulletins/{p.id}', email=True)
        else:
            notify(p.employee, f'Votre bulletin {period} est disponible',
                   f'Net à payer : {fmt(p.net_salary)} DA', f'/bulletins/{p.id}', email=True)

    @action(detail=True, methods=['get', 'post'], permission_classes=[IsCompanyAdmin])
    def correct(self, request, pk=None):
        """Prepare (or redo) the corrective payslip that will cancel and replace this published one.
        Nothing changes for the employee until the correction is published. GET gives the form's
        starting values: the correction in progress, or the bonuses of the payslip itself."""
        original = self.get_object()
        company = require_company(request)
        if original.company_id != company.id:
            raise PermissionDenied()
        if original.status != Payslip.Status.PUBLISHED:
            raise ValidationError('Seul un bulletin publié et en vigueur peut être corrigé.')
        emp = original.employee
        draft = Payslip.objects.filter(employee=emp, year=original.year, month=original.month,
                                       status=Payslip.Status.DRAFT).first()
        if draft and draft.replaces_id != original.id:
            raise ValidationError("Un brouillon existe déjà pour ce mois : publiez-le ou supprimez-le d'abord.")
        if request.method == 'GET':
            return Response({'draft': draft.id if draft else None, 'reason': draft.correction_reason if draft else '',
                             'items': draft.run_items if draft else run_items_of(original)})

        s = PayslipCorrectionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if emp.company_id != company.id:
            raise ValidationError("Ce salarié n'appartient plus à l'entreprise.")
        if emp.base_salary <= 0:
            raise ValidationError('Salaire de base non renseigné.')
        items = s.validated_data.get('items')
        run_items = bonus_dicts([payroll.Bonus(**b) for b in items]) if items is not None else run_items_of(original)
        p = draft or Payslip(employee=emp, year=original.year, month=original.month, replaces=original)
        p.correction_reason = s.validated_data['reason']
        with transaction.atomic():
            # Same expenses as the original: they were repaid with it, the correction must not drop them.
            p, warnings = compute_payslip_for(emp, company, original.year, original.month, run_items,
                                              list(original.expenses.all()), payslip=p, link_expenses=False)
        audit(request, 'payroll.correct', f'{emp} {month_label(original.year, original.month)}')
        data = PayslipDetailSerializer(p).data
        return Response({**data, 'warnings': warnings},
                        status=status.HTTP_200_OK if draft else status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], permission_classes=[IsCompanyAdmin])
    def run(self, request):
        """Generate (or regenerate drafts of) the payslips of a month for the active company."""
        company = require_company(request)
        s = PayrollRunSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        year, month = s.validated_data['year'], s.validated_data['month']
        employees = s.validated_data.get('employees')
        if employees is None:
            employees = list(User.objects.filter(company=company, is_active=True, base_salary__gt=0))
        employees = list(dict.fromkeys(employees))   # the same person sent twice is paid once
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        run_items = bonus_dicts([payroll.Bonus(**b) for b in s.validated_data.get('bonuses', [])])

        created, skipped, warnings = [], [], []
        with transaction.atomic():
            for emp in employees:
                if emp.company_id != company.id:
                    skipped.append({'employee': str(emp), 'reason': "N'appartient pas à l'entreprise"})
                    continue
                month_qs = Payslip.objects.filter(employee=emp, year=year, month=month)
                draft = month_qs.filter(status=Payslip.Status.DRAFT).first()
                if draft and draft.replaces_id:
                    skipped.append({'employee': str(emp), 'reason': 'Correction en cours : recalculez-la depuis le bulletin'})
                    continue
                if not draft and month_qs.filter(status=Payslip.Status.PUBLISHED).exists():
                    skipped.append({'employee': str(emp), 'reason': 'Bulletin déjà publié : utilisez « Corriger »'})
                    continue
                if emp.hire_date and emp.hire_date > last_day:
                    reason = f'Embauché le {emp.hire_date:%d/%m/%Y}, après ce mois'
                    if draft:   # computed before the hire date was entered
                        draft.delete()
                        reason += ' : brouillon supprimé'
                    skipped.append({'employee': str(emp), 'reason': reason})
                    continue
                if emp.base_salary <= 0:
                    skipped.append({'employee': str(emp), 'reason': 'Salaire de base non renseigné'})
                    continue
                expenses = []
                if s.validated_data['include_expenses']:
                    expenses = list(ExpenseReport.objects.filter(
                        Q(payslip__isnull=True) | Q(payslip=draft), employee=emp,
                        status=ExpenseReport.Status.APPROVED))
                p, engine_warnings = compute_payslip_for(emp, company, year, month, run_items, expenses, payslip=draft)
                warnings += [{'employee': str(emp), 'message': w} for w in engine_warnings]
                if s.validated_data['publish']:
                    self._publish(p)
                created.append(p)

        if created:
            audit(request, 'payroll.run', f'{month_label(year, month)} : {len(created)} bulletin(s)', company)
        return Response({'created': PayslipListSerializer(created, many=True).data, 'skipped': skipped,
                         'warnings': warnings}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], permission_classes=[IsCompanyAdmin])
    def publish_month(self, request):
        company = require_company(request)
        year, month = year_param(request.data.get('year')), month_param(request.data.get('month'))
        # A correction is published on its own, once its difference has been checked.
        drafts = Payslip.objects.filter(company=company, year=year, month=month, status=Payslip.Status.DRAFT,
                                        replaces__isnull=True)
        count = 0
        for p in drafts.select_related('employee'):
            self._publish(p)
            count += 1
        if count:
            audit(request, 'payroll.publish', f'{month_label(year, month)} : {count} bulletin(s)', company)
        return Response({'published': count})

    @action(detail=False, methods=['get', 'post'], permission_classes=[IsCompanyAdmin])
    def variables(self, request):
        """The monthly grid: one row per employee, overtime and individual bonus."""
        company = require_company(request)
        if request.method == 'GET':
            year, month = year_param(request.query_params.get('year')), month_param(request.query_params.get('month'))
            saved = {v.employee_id: v for v in MonthlyVariable.objects.filter(
                employee__company=company, year=year, month=month)}
            rows = []
            for emp in User.objects.filter(company=company, is_active=True, base_salary__gt=0).order_by('last_name', 'first_name'):
                v = saved.get(emp.id)
                rows.append({'employee': emp.id, 'full_name': str(emp),
                             'overtime_hours': v.overtime_hours if v else Decimal('0'),
                             'overtime_rate': v.overtime_rate if v else payroll.OVERTIME_MIN_RATE,
                             'bonus_label': v.bonus_label if v else '',
                             'bonus_amount': v.bonus_amount if v else Decimal('0')})
            return Response(rows)

        s = MonthlyVariablesSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        year, month = s.validated_data['year'], s.validated_data['month']
        published = set(in_force(Payslip.objects.filter(company=company, year=year, month=month,
                                                         status=Payslip.Status.PUBLISHED))
                        .values_list('employee_id', flat=True))
        # Changes for someone already paid only count once their payslip is corrected: say who.
        already_published = []
        with transaction.atomic():
            for row in s.validated_data['rows']:
                emp = row.pop('employee')
                if emp.company_id != company.id:
                    raise ValidationError({'employee': "Ce salarié n'appartient pas à l'entreprise."})
                current = MonthlyVariable.objects.filter(employee=emp, year=year, month=month).first()
                if emp.id in published and variable_key(current) != variable_key(row):
                    already_published.append(str(emp))
                if row['overtime_hours'] or row['bonus_amount']:
                    MonthlyVariable.objects.update_or_create(employee=emp, year=year, month=month, defaults=row)
                else:
                    MonthlyVariable.objects.filter(employee=emp, year=year, month=month).delete()
        audit(request, 'payroll.variables', month_label(year, month), company)
        return Response({'already_published': already_published})

    @action(detail=False, methods=['get'], permission_classes=[IsCompanyAdmin])
    def summary(self, request):
        """Monthly totals used for the G50 (IRG) and CNAS returns."""
        company = require_company(request)
        year, month = year_param(request.query_params.get('year')), month_param(request.query_params.get('month'))
        qs = in_force(Payslip.objects.filter(company=company, year=year, month=month))
        # Drafts are counted so the month can be checked before publishing: the figures stay provisional.
        return Response({**payroll_month_totals(qs), 'drafts': qs.filter(status=Payslip.Status.DRAFT).count()})


class EmployeePayItemViewSet(viewsets.ModelViewSet):
    """Permanent pay elements of the active company's employees."""
    serializer_class = EmployeePayItemSerializer
    permission_classes = [IsCompanyAdmin]

    def get_queryset(self):
        qs = EmployeePayItem.objects.filter(employee__company=active_company(self.request))
        if self.request.query_params.get('employee'):
            qs = qs.filter(employee_id=int_param(self.request.query_params['employee'], 'employee'))
        return qs

    def _save(self, serializer):
        employee = serializer.validated_data.get('employee')
        if employee and employee.company_id != require_company(self.request).id:
            raise ValidationError({'employee': "Ce salarié n'appartient pas à l'entreprise."})
        action = 'payitem.update' if serializer.instance else 'payitem.create'
        item = serializer.save()
        audit(self.request, action, f'{item.employee} : {item.label}')

    perform_create = _save
    perform_update = _save

    def perform_destroy(self, instance):
        audit(self.request, 'payitem.delete', f'{instance.employee} : {instance.label}')
        instance.delete()


class AuditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """The active company's journal, most recent first."""
    serializer_class = AuditLogSerializer
    permission_classes = [IsCompanyAdmin]

    def get_queryset(self):
        return AuditLog.objects.filter(company=active_company(self.request))[:200]


# ---------------------------------------------------------------- documents

class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        user = self.request.user
        qs = Document.objects.select_related('employee')
        params = self.request.query_params
        admin = is_company_admin(self.request)
        company = active_company(self.request)
        mine = Q(employee=user) | Q(employee__isnull=True, company_id=user.company_id)
        if admin and params.get('scope') == 'all':
            qs = qs.filter(company=company)
            if params.get('employee'):
                qs = qs.filter(employee_id=params['employee'])
        elif admin and self.action != 'list':
            qs = qs.filter(Q(company=company) | mine)
        else:
            qs = qs.filter(mine) if user.company_id else qs.filter(employee=user)
        if params.get('category'):
            qs = qs.filter(category=params['category'])
        return qs

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsCompanyAdmin()]
        return super().get_permissions()

    def _check_employee(self, serializer, company):
        employee = serializer.validated_data.get('employee')
        if employee and employee.company_id != company.id:
            raise ValidationError({'employee': "Ce salarié n'appartient pas à l'entreprise."})

    def perform_update(self, serializer):
        company = require_company(self.request)
        if serializer.instance.company_id != company.id:
            raise PermissionDenied()
        self._check_employee(serializer, company)
        doc = serializer.save()
        audit(self.request, 'document.update', doc.title)

    def perform_create(self, serializer):
        company = require_company(self.request)
        self._check_employee(serializer, company)
        doc = serializer.save(uploaded_by=self.request.user, company=company)
        audit(self.request, 'document.create', f'{doc.title} ({doc.employee or company})')
        if doc.employee:
            notify(doc.employee, 'Nouveau document dans votre coffre-fort', doc.title, '/documents', email=True)
        else:
            for u in User.objects.filter(is_active=True, company=company).exclude(id=self.request.user.id):
                notify(u, "Nouveau document de l'entreprise", doc.title, '/documents')

    def perform_destroy(self, instance):
        if instance.company_id != active_company(self.request).id:
            raise PermissionDenied()
        audit(self.request, 'document.delete', instance.title)
        instance.delete()

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        doc = self.get_object()
        if doc.employee_id == request.user.id and not doc.viewed_at:
            doc.viewed_at = timezone.now()
            doc.save(update_fields=['viewed_at'])
        return file_download(doc.file)

    @action(detail=False, methods=['get'])
    def categories(self, request):
        return Response([{'value': v, 'label': l} for v, l in Document.Category.choices])


# ---------------------------------------------------------------- leaves

class LeaveRequestViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                          viewsets.GenericViewSet):
    serializer_class = LeaveRequestSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    payroll_warnings = ()

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data['payroll_warnings'] = list(self.payroll_warnings)
        return response

    def get_queryset(self):
        qs = LeaveRequest.objects.select_related('employee', 'reviewer')
        if self.action == 'list':
            qs = scoped_queryset(self.request, qs)
            if self.request.query_params.get('status'):
                qs = qs.filter(status=self.request.query_params['status'])
            if self.request.query_params.get('year'):
                qs = qs.filter(start_date__year=year_param(self.request.query_params['year']))
            return qs
        return visible_to(self.request, qs)

    def _checked_days(self, employee, d):
        days = payroll.count_leave_days(d['start_date'], d['end_date'], weekend_of(employee),
                                        d.get('start_half', False), d.get('end_half', False))
        if days <= 0:
            raise ValidationError('La période choisie ne contient aucun jour ouvré.')
        overlap = LeaveRequest.objects.filter(
            employee=employee, status__in=[RequestStatus.PENDING, RequestStatus.APPROVED],
            start_date__lte=d['end_date'], end_date__gte=d['start_date'])
        if overlap.exists():
            raise ValidationError('Une demande existe déjà sur cette période.')
        if d['leave_type'] in BALANCED_LEAVE_TYPES:
            bal = next(b for b in balance_summary(employee, d['start_date'].year) if b['leave_type'] == d['leave_type'])
            if bal['remaining'] - bal['pending'] < days:
                raise ValidationError(
                    f"Solde insuffisant : {bal['remaining'] - bal['pending']} jour(s) disponible(s), {days} demandé(s).")
        return days

    def perform_create(self, serializer):
        user = self.request.user
        if not user.company_id:
            raise ValidationError("Votre compte n'est rattaché à aucune entreprise.")
        days = self._checked_days(user, serializer.validated_data)
        reviewers = reviewers_for(user)
        if decides_alone(user, reviewers):
            lr = serializer.save(employee=user, days=days, status=RequestStatus.APPROVED, reviewer=user,
                                 reviewed_at=timezone.now(), review_comment=SOLE_REVIEWER_NOTE)
            audit(self.request, 'leave.approve', f'{user} : {lr.get_leave_type_display()} (aucun autre valideur)',
                  user.company)
            self.payroll_warnings = warn_payroll(lr, 'enregistrée')
            return
        lr = serializer.save(employee=user, days=days)
        for r in reviewers:
            notify(r, f"Demande d'absence de {user}",
                   f'{lr.get_leave_type_display()} du {lr.start_date:%d/%m/%Y} au {lr.end_date:%d/%m/%Y} ({days} j)',
                   '/equipe', email=True, company=user.company)

    @action(detail=False, methods=['post'])
    def for_employee(self, request):
        """A manager or HR records an absence for someone else: it is approved straight away."""
        emp = User.objects.filter(is_active=True, id=int_param(request.data.get('employee'), 'employee')).first()
        if emp is None or not can_review(request, emp):
            raise PermissionDenied("Vous ne pouvez pas saisir d'absence pour cette personne.")
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        days = self._checked_days(emp, s.validated_data)
        lr = s.save(employee=emp, days=days, status=RequestStatus.APPROVED, reviewer=request.user,
                    reviewed_at=timezone.now())
        notify(emp, 'Une absence a été enregistrée pour vous',
               f'{lr.get_leave_type_display()} du {lr.start_date:%d/%m/%Y} au {lr.end_date:%d/%m/%Y}', '/absences', email=True)
        audit(request, 'leave.create_for', f'{emp} : {lr.get_leave_type_display()}', emp.company)
        return Response({**LeaveRequestSerializer(lr).data, 'payroll_warnings': warn_payroll(lr, 'enregistrée')},
                        status=status.HTTP_201_CREATED)

    def _review(self, request, new_status):
        lr = self.get_object()
        if not can_review(request, lr.employee):
            raise PermissionDenied('Vous ne pouvez pas valider cette demande.')
        if lr.status != RequestStatus.PENDING:
            raise ValidationError('Cette demande a déjà été traitée.')
        s = ReviewSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        mark_reviewed(lr, request.user, new_status, s.validated_data['comment'])
        verb = 'validée' if new_status == RequestStatus.APPROVED else 'refusée'
        notify(lr.employee, f"Votre demande d'absence a été {verb}",
               f'{lr.get_leave_type_display()} du {lr.start_date:%d/%m/%Y} au {lr.end_date:%d/%m/%Y}'
               + (f' — {lr.review_comment}' if lr.review_comment else ''), '/absences', email=True)
        audit(request, f"leave.{'approve' if new_status == RequestStatus.APPROVED else 'reject'}",
              f'{lr.employee} : {lr.get_leave_type_display()}', lr.employee.company)
        warnings = warn_payroll(lr, 'validée') if new_status == RequestStatus.APPROVED else []
        return Response({**LeaveRequestSerializer(lr).data, 'payroll_warnings': warnings})

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        return self._review(request, RequestStatus.APPROVED)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        return self._review(request, RequestStatus.REJECTED)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        lr = self.get_object()
        user = request.user
        own = lr.employee_id == user.id
        if own:
            if lr.status == RequestStatus.APPROVED and lr.start_date <= date.today():
                raise ValidationError('Une absence déjà commencée ne peut plus être annulée.')
        elif not is_company_admin(request) or lr.employee.company_id != active_company(request).id:
            raise PermissionDenied()
        if lr.status not in [RequestStatus.PENDING, RequestStatus.APPROVED]:
            raise ValidationError('Cette demande ne peut plus être annulée.')
        was_approved = lr.status == RequestStatus.APPROVED
        lr.status = RequestStatus.CANCELLED
        lr.save(update_fields=['status'])
        period = f'{lr.get_leave_type_display()} du {lr.start_date:%d/%m/%Y} au {lr.end_date:%d/%m/%Y}'
        if not own:
            notify(lr.employee, 'Votre absence a été annulée', f'{period}, par {user}', '/absences', email=True)
            audit(request, 'leave.cancel', f'{lr.employee} : {lr.get_leave_type_display()}', lr.employee.company)
        elif was_approved and lr.reviewer and lr.reviewer_id != user.id:
            # The planning changes: whoever approved it is told.
            notify(lr.reviewer, f'Absence annulée par {user}', period, '/equipe', company=lr.employee.company)
        warnings = warn_payroll(lr, 'annulée') if was_approved else []
        return Response({**LeaveRequestSerializer(lr).data, 'payroll_warnings': warnings})

    @action(detail=True, methods=['get'])
    def attachment(self, request, pk=None):
        return file_download(self.get_object().attachment)

    @action(detail=False, methods=['get'])
    def balances(self, request):
        year = year_param(request.query_params.get('year') or date.today().year)
        return Response(balance_summary(request.user, year) if request.user.company_id else [])

    @action(detail=False, methods=['get'])
    def types(self, request):
        return Response(LEAVE_TYPE_CHOICES)

    @action(detail=False, methods=['get'])
    def preview(self, request):
        """Live day count for the request form."""
        try:
            start = date.fromisoformat(request.query_params['start'])
            end = date.fromisoformat(request.query_params['end'])
        except (KeyError, ValueError):
            raise ValidationError('Dates invalides.')
        days = payroll.count_leave_days(start, end, weekend_of(request.user),
                                        request.query_params.get('start_half') == '1',
                                        request.query_params.get('end_half') == '1')
        return Response({'days': days})

    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """Absences of the people around the user for one month.
        The reason of a colleague's absence is private: only company admins, the manager
        and the employee themself see the leave type."""
        user = request.user
        today = date.today()
        year = year_param(request.query_params.get('year') or today.year)
        month = month_param(request.query_params.get('month') or today.month)
        first, last = date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
        company = active_company(request)
        admin = is_company_admin(request)

        if admin:
            people = User.objects.filter(is_active=True, company=company)
        elif not user.company_id:
            people = User.objects.none()
        else:
            people = User.objects.filter(is_active=True, company_id=user.company_id).filter(
                Q(id=user.id) | Q(manager=user) | (Q(manager_id=user.manager_id) if user.manager_id else Q(pk__in=[]))
                | Q(id=user.manager_id or 0))
        people = people.order_by('last_name', 'first_name')
        leaves = LeaveRequest.objects.filter(
            employee__in=people, status__in=[RequestStatus.PENDING, RequestStatus.APPROVED],
            start_date__lte=last, end_date__gte=first).exclude(leave_type=LeaveType.REMOTE)

        def visible(lr):
            return admin or lr.employee_id == user.id or lr.employee.manager_id == user.id

        return Response({
            'year': year, 'month': month, 'weekend_days': company.weekend_days if company else [4, 5],
            'people': [{'id': p.id, 'full_name': p.get_full_name() or p.username, 'job_title': p.job_title}
                       for p in people],
            'leaves': [{
                'id': lr.id, 'employee': lr.employee_id, 'start_date': lr.start_date, 'end_date': lr.end_date,
                'start_half': lr.start_half, 'end_half': lr.end_half, 'status': lr.status,
                'leave_type': lr.leave_type if visible(lr) else None,
                'label': lr.get_leave_type_display() if visible(lr) else 'Absent',
            } for lr in leaves.select_related('employee')],
        })


# ---------------------------------------------------------------- expenses

class ExpenseViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                     viewsets.GenericViewSet):
    serializer_class = ExpenseSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = ExpenseReport.objects.select_related('employee', 'reviewer')
        if self.action == 'list':
            qs = scoped_queryset(self.request, qs)
            if self.request.query_params.get('status'):
                qs = qs.filter(status=self.request.query_params['status'])
            return qs
        return visible_to(self.request, qs)

    def perform_create(self, serializer):
        user = self.request.user
        if not user.company_id:
            raise ValidationError("Votre compte n'est rattaché à aucune entreprise.")
        reviewers = reviewers_for(user)
        if decides_alone(user, reviewers):
            exp = serializer.save(employee=user, status=ExpenseReport.Status.APPROVED, reviewer=user,
                                  reviewed_at=timezone.now(), review_comment=SOLE_REVIEWER_NOTE)
            audit(self.request, 'expense.approve', f'{user} : {exp.description} (aucun autre valideur)', user.company)
            return
        exp = serializer.save(employee=user)
        for r in reviewers:
            notify(r, f'Note de frais de {user}', f'{exp.description} — {fmt(exp.amount)} DA', '/equipe',
                   company=user.company)

    def _review(self, request, new_status):
        exp = self.get_object()
        if not can_review(request, exp.employee):
            raise PermissionDenied('Vous ne pouvez pas valider cette note de frais.')
        if exp.status != ExpenseReport.Status.PENDING:
            raise ValidationError('Cette note de frais a déjà été traitée.')
        s = ReviewSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        mark_reviewed(exp, request.user, new_status, s.validated_data['comment'])
        verb = 'validée' if new_status == ExpenseReport.Status.APPROVED else 'refusée'
        notify(exp.employee, f'Votre note de frais a été {verb}',
               f'{exp.description} — {fmt(exp.amount)} DA' + (f' — {exp.review_comment}' if exp.review_comment else ''),
               '/notes-de-frais', email=True)
        audit(request, f"expense.{'approve' if new_status == ExpenseReport.Status.APPROVED else 'reject'}",
              f'{exp.employee} : {exp.description}', exp.employee.company)
        return Response(ExpenseSerializer(exp).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        return self._review(request, ExpenseReport.Status.APPROVED)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        return self._review(request, ExpenseReport.Status.REJECTED)

    @action(detail=True, methods=['post'], permission_classes=[IsCompanyAdmin])
    def mark_paid(self, request, pk=None):
        exp = self.get_object()
        if exp.employee.company_id != active_company(request).id:
            raise PermissionDenied()
        if exp.status != ExpenseReport.Status.APPROVED:
            raise ValidationError('Seule une note validée peut être marquée remboursée.')
        if exp.payslip_id:
            raise ValidationError('Cette note est déjà incluse dans un bulletin : elle sera remboursée à sa publication.')
        exp.status = ExpenseReport.Status.PAID
        exp.save(update_fields=['status'])
        audit(request, 'expense.paid', f'{exp.employee} : {exp.description}')
        notify(exp.employee, 'Note de frais remboursée', f'{exp.description} — {fmt(exp.amount)} DA', '/notes-de-frais')
        return Response(ExpenseSerializer(exp).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        exp = self.get_object()
        if exp.employee_id != request.user.id:
            raise PermissionDenied()
        if exp.status != ExpenseReport.Status.PENDING:
            raise ValidationError('Seule une note en attente peut être annulée.')
        exp.status = ExpenseReport.Status.CANCELLED
        exp.save(update_fields=['status'])
        return Response(ExpenseSerializer(exp).data)

    @action(detail=True, methods=['get'])
    def receipt(self, request, pk=None):
        return file_download(self.get_object().receipt)

    @action(detail=False, methods=['get'])
    def categories(self, request):
        return Response([{'value': v, 'label': l} for v, l in ExpenseReport.Category.choices])


# ---------------------------------------------------------------- profile change requests

class ProfileChangeRequestViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ProfileChangeRequestSerializer

    def get_queryset(self):
        qs = ProfileChangeRequest.objects.select_related('employee')
        if self.action == 'list':
            # The values asked for (bank details, address...) are private: never shown to the manager.
            qs = scoped_queryset(self.request, qs, hr_only=True)
            if self.request.query_params.get('status'):
                qs = qs.filter(status=self.request.query_params['status'])
            return qs
        cond = Q(employee=self.request.user)
        if is_company_admin(self.request):
            cond |= Q(employee__company=active_company(self.request))
        return qs.filter(cond)

    def perform_create(self, serializer):
        user = self.request.user
        if not user.company_id:
            raise ValidationError("Votre compte n'est rattaché à aucune entreprise.")
        if ProfileChangeRequest.objects.filter(employee=user, status=RequestStatus.PENDING).exists():
            raise ValidationError('Une demande de modification est déjà en cours de traitement.')
        reviewers = hr_reviewers_for(user)
        if decides_alone(user, reviewers):
            with transaction.atomic():
                req = serializer.save(employee=user, status=RequestStatus.APPROVED, reviewer=user,
                                      reviewed_at=timezone.now(), review_comment=SOLE_REVIEWER_NOTE)
                apply_profile_changes(user, req.changes)
            audit(self.request, 'profile.approve', f"{user} : {', '.join(sorted(req.changes))} (aucun autre valideur)",
                  user.company)
            return
        serializer.save(employee=user)
        for hr in reviewers:
            notify(hr, f'Modification de dossier demandée par {user}', '', '/admin/demandes', company=user.company)

    def _check_admin(self, request, req):
        if not is_company_admin(request) or req.employee.company_id != active_company(request).id:
            raise PermissionDenied('Réservé à la gestion RH.')
        if req.employee_id == request.user.id:
            raise PermissionDenied('Vous ne pouvez pas valider votre propre demande.')
        if req.status != RequestStatus.PENDING:
            raise ValidationError('Cette demande a déjà été traitée.')

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        req = self.get_object()
        self._check_admin(request, req)
        comment = review_comment(request)
        emp = req.employee
        with transaction.atomic():
            apply_profile_changes(emp, req.changes)
            mark_reviewed(req, request.user, RequestStatus.APPROVED, comment)
        notify(emp, 'Votre dossier a été mis à jour', 'Les modifications demandées ont été appliquées.', '/profil')
        audit(request, 'profile.approve', f"{emp} : {', '.join(sorted(req.changes))}")
        return Response(ProfileChangeRequestSerializer(req).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        req = self.get_object()
        self._check_admin(request, req)
        mark_reviewed(req, request.user, RequestStatus.REJECTED, review_comment(request))
        notify(req.employee, 'Demande de modification refusée', req.review_comment, '/profil')
        audit(request, 'profile.reject', str(req.employee))
        return Response(ProfileChangeRequestSerializer(req).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        req = self.get_object()
        if req.employee_id != request.user.id or req.status != RequestStatus.PENDING:
            raise ValidationError('Cette demande ne peut pas être annulée.')
        req.status = RequestStatus.CANCELLED
        req.save(update_fields=['status'])
        return Response(ProfileChangeRequestSerializer(req).data)


# ---------------------------------------------------------------- certificates

class CertificateRequestViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = CertificateRequestSerializer

    def get_queryset(self):
        qs = CertificateRequest.objects.select_related('employee', 'employee__company')
        if self.action == 'list':
            qs = scoped_queryset(self.request, qs, hr_only=True)
            if self.request.query_params.get('status'):
                qs = qs.filter(status=self.request.query_params['status'])
            return qs
        cond = Q(employee=self.request.user)
        if is_company_admin(self.request):
            cond |= Q(employee__company=active_company(self.request))
        return qs.filter(cond)

    def perform_create(self, serializer):
        user = self.request.user
        if not user.company_id:
            raise ValidationError("Votre compte n'est rattaché à aucune entreprise.")
        kind = serializer.validated_data['kind']
        if CertificateRequest.objects.filter(employee=user, kind=kind, status=RequestStatus.PENDING).exists():
            raise ValidationError('Une demande de ce type est déjà en cours de traitement.')
        reviewers = hr_reviewers_for(user)
        if decides_alone(user, reviewers):
            with transaction.atomic():
                req = serializer.save(employee=user)
                issue_certificate(req, user, SOLE_REVIEWER_NOTE)
            audit(self.request, 'certificate.approve', f'{user} : {req.get_kind_display()} (aucun autre valideur)',
                  user.company)
            return
        req = serializer.save(employee=user)
        for hr in reviewers:
            notify(hr, f'{req.get_kind_display()} demandée par {user}', req.comment, '/admin/demandes',
                   company=user.company)

    def _check_admin(self, request, req):
        if not is_company_admin(request) or req.employee.company_id != active_company(request).id:
            raise PermissionDenied('Réservé à la gestion RH.')
        if req.employee_id == request.user.id:
            raise PermissionDenied('Vous ne pouvez pas traiter votre propre demande.')
        if req.status != RequestStatus.PENDING:
            raise ValidationError('Cette demande a déjà été traitée.')

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        req = self.get_object()
        self._check_admin(request, req)
        with transaction.atomic():
            issue_certificate(req, request.user, review_comment(request))
        audit(request, 'certificate.approve', f'{req.employee} : {req.get_kind_display()}')
        return Response(CertificateRequestSerializer(req).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        req = self.get_object()
        self._check_admin(request, req)
        mark_reviewed(req, request.user, RequestStatus.REJECTED, review_comment(request))
        notify(req.employee, "Demande d'attestation refusée", req.review_comment, '/documents')
        audit(request, 'certificate.reject', f'{req.employee} : {req.get_kind_display()}')
        return Response(CertificateRequestSerializer(req).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        req = self.get_object()
        if req.employee_id != request.user.id or req.status != RequestStatus.PENDING:
            raise ValidationError('Cette demande ne peut pas être annulée.')
        req.status = RequestStatus.CANCELLED
        req.save(update_fields=['status'])
        return Response(CertificateRequestSerializer(req).data)


# ---------------------------------------------------------------- notifications

class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)[:100]

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        n = get_object_or_404(Notification, pk=pk, user=request.user)
        n.read = True
        n.save(update_fields=['read'])
        return Response(NotificationSerializer(n).data)

    @action(detail=False, methods=['post'])
    def read_all(self, request):
        Notification.objects.filter(user=request.user, read=False).update(read=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        return Response({'count': Notification.objects.filter(user=request.user, read=False).count()})
