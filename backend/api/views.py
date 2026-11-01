import calendar
import logging
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q, Sum
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from . import payroll
from .models import (
    BALANCED_LEAVE_TYPES, Company, Document, ExpenseReport, LeaveBalance, LeaveRequest, LeaveType,
    Notification, Payslip, PayslipLine, ProfileChangeRequest, RequestStatus,
)
from .pdf import fmt, month_label, render_payslip
from .permissions import IsHR, can_review
from .serializers import (
    LEAVE_TYPE_CHOICES, REQUESTABLE_FIELDS, ChangePasswordSerializer, CompanySerializer,
    DocumentSerializer, EmployeeSerializer, ExpenseSerializer, LeaveBalanceSerializer,
    LeaveRequestSerializer, NotificationSerializer, PayrollRunSerializer, PayslipDetailSerializer,
    PayslipListSerializer, ProfileChangeRequestSerializer, ProfileSerializer, ReviewSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------- helpers

def notify(user, title, message='', link='', email=False):
    if not user or not user.is_active:
        return
    Notification.objects.create(user=user, title=title, message=message, link=link)
    if email and user.email:
        try:
            send_mail(f'[SILAH] {title}', message or title, settings.DEFAULT_FROM_EMAIL, [user.email])
        except Exception:  # an email outage must never block the HR action itself
            logger.exception('Notification email failed')


def reviewers_for(employee):
    """Who gets told about a new request: the manager, or HR when there is none."""
    if employee.manager and employee.manager.is_active:
        return [employee.manager]
    return list(User.objects.filter(Q(role=User.Role.HR) | Q(is_superuser=True), is_active=True)
                .exclude(id=employee.id))


def company_of(user):
    return user.company or Company.objects.first()


def weekend_of(user):
    c = company_of(user)
    return c.weekend_days if c else [4, 5]


def balance_summary(employee, year):
    company = company_of(employee)
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


def scoped_queryset(request, qs):
    """?scope=mine (default) | team (manager: direct reports, HR: everyone but self) | all (HR)."""
    user = request.user
    scope = request.query_params.get('scope', 'mine')
    if scope == 'team':
        if user.is_hr:
            return qs.exclude(employee=user)
        return qs.filter(employee__manager=user)
    if scope == 'all':
        if not user.is_hr:
            raise PermissionDenied('Réservé aux gestionnaires RH.')
        return qs
    return qs.filter(employee=user)


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
        return super().validate(attrs)


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


class CompanyView(APIView):
    def get(self, request):
        c = company_of(request.user)
        return Response(CompanySerializer(c).data if c else None)

    def patch(self, request):
        if not request.user.is_hr:
            raise PermissionDenied('Réservé aux gestionnaires RH.')
        c = company_of(request.user) or Company.objects.create(name='Mon entreprise')
        s = CompanySerializer(c, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({'status': 'ok'})


# ---------------------------------------------------------------- dashboard

class DashboardView(APIView):
    def get(self, request):
        user = request.user
        today = date.today()
        last = Payslip.objects.filter(employee=user, status=Payslip.Status.PUBLISHED).first()
        docs = Document.objects.filter(Q(employee=user) | Q(employee__isnull=True))[:4]
        upcoming = LeaveRequest.objects.filter(
            employee=user, end_date__gte=today,
            status__in=[RequestStatus.PENDING, RequestStatus.APPROVED]).order_by('start_date')[:3]

        to_review = {}
        if user.is_hr or user.is_manager:
            team_leaves = LeaveRequest.objects.filter(status=RequestStatus.PENDING)
            team_expenses = ExpenseReport.objects.filter(status=ExpenseReport.Status.PENDING)
            if user.is_hr:
                team_leaves, team_expenses = team_leaves.exclude(employee=user), team_expenses.exclude(employee=user)
            else:
                team_leaves = team_leaves.filter(employee__manager=user)
                team_expenses = team_expenses.filter(employee__manager=user)
            to_review = {'leaves': team_leaves.count(), 'expenses': team_expenses.count()}
            if user.is_hr:
                to_review['profile_requests'] = ProfileChangeRequest.objects.filter(
                    status=RequestStatus.PENDING).count()

        return Response({
            'last_payslip': PayslipListSerializer(last).data if last else None,
            'balances': balance_summary(user, today.year),
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


# ---------------------------------------------------------------- employees (HR)

class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = [IsHR]

    def get_queryset(self):
        qs = User.objects.select_related('manager').order_by('last_name', 'first_name', 'username')
        q = self.request.query_params.get('q')
        if q:
            qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(username__icontains=q)
                           | Q(employee_number__icontains=q) | Q(department__icontains=q))
        if self.request.query_params.get('active') == '1':
            qs = qs.filter(is_active=True)
        return qs

    def get_permissions(self):
        # Managers need the directory to read names (team calendar, filters).
        if self.action == 'directory':
            return [IsAuthenticated()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(company=company_of(self.request.user))

    def destroy(self, request, *args, **kwargs):
        # Payroll records must be kept: deactivate instead of deleting.
        emp = self.get_object()
        if emp == request.user:
            raise ValidationError('Vous ne pouvez pas désactiver votre propre compte.')
        emp.is_active = False
        emp.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get', 'post'])
    def balances(self, request, pk=None):
        emp = self.get_object()
        year = int(request.query_params.get('year') or request.data.get('year') or date.today().year)
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
        qs = User.objects.filter(is_active=True).order_by('last_name', 'first_name')
        return Response([{'id': u.id, 'full_name': u.get_full_name() or u.username, 'job_title': u.job_title,
                          'department': u.department, 'manager': u.manager_id} for u in qs])


# ---------------------------------------------------------------- payslips

class PayslipViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin,
                     viewsets.GenericViewSet):

    def get_serializer_class(self):
        return PayslipDetailSerializer if self.action == 'retrieve' else PayslipListSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Payslip.objects.select_related('employee', 'employee__company').prefetch_related('lines')
        params = self.request.query_params
        if user.is_hr and params.get('scope') == 'all':
            if params.get('employee'):
                qs = qs.filter(employee_id=params['employee'])
            if params.get('month'):
                qs = qs.filter(month=params['month'])
        elif user.is_hr and self.action not in ('list', 'years'):
            pass  # HR can open any payslip by id
        else:
            qs = qs.filter(employee=user, status=Payslip.Status.PUBLISHED)
        if params.get('year'):
            qs = qs.filter(year=params['year'])
        return qs

    def retrieve(self, request, *args, **kwargs):
        p = self.get_object()
        if p.employee_id == request.user.id and not p.viewed_at:
            p.viewed_at = timezone.now()
            p.save(update_fields=['viewed_at'])
        return Response(PayslipDetailSerializer(p).data)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_hr:
            raise PermissionDenied('Réservé aux gestionnaires RH.')
        p = self.get_object()
        if p.status != Payslip.Status.DRAFT:
            raise ValidationError('Un bulletin publié ne peut pas être supprimé.')
        p.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        p = self.get_object()
        if p.employee_id == request.user.id and not p.viewed_at:
            p.viewed_at = timezone.now()
            p.save(update_fields=['viewed_at'])
        response = HttpResponse(render_payslip(p), content_type='application/pdf')
        name = (p.employee.get_full_name() or p.employee.username).replace(' ', '_')
        response['Content-Disposition'] = f'attachment; filename="bulletin_{p.year}_{p.month:02d}_{name}.pdf"'
        return response

    @action(detail=False, methods=['get'])
    def years(self, request):
        qs = self.get_queryset().values_list('year', flat=True).distinct()
        return Response(sorted(set(qs), reverse=True))

    @action(detail=True, methods=['post'], permission_classes=[IsHR])
    def publish(self, request, pk=None):
        p = self.get_object()
        self._publish(p)
        return Response(PayslipListSerializer(p).data)

    @staticmethod
    def _publish(p):
        if p.status == Payslip.Status.PUBLISHED:
            return
        p.status = Payslip.Status.PUBLISHED
        p.published_at = timezone.now()
        p.save(update_fields=['status', 'published_at'])
        notify(p.employee, f'Votre bulletin de {month_label(p.year, p.month).lower()} est disponible',
               f'Net à payer : {fmt(p.net_salary)} DA', f'/bulletins/{p.id}', email=True)

    @action(detail=False, methods=['post'], permission_classes=[IsHR])
    def run(self, request):
        """Generate (or regenerate drafts of) the payslips of a month."""
        s = PayrollRunSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        year, month = s.validated_data['year'], s.validated_data['month']
        employees = s.validated_data.get('employees') or list(
            User.objects.filter(is_active=True, base_salary__gt=0))
        bonuses = [payroll.Bonus(**b) for b in s.validated_data.get('bonuses', [])]
        first, last = date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])

        created, skipped = [], []
        with transaction.atomic():
            for emp in employees:
                existing = Payslip.objects.filter(employee=emp, year=year, month=month).first()
                if existing and existing.status == Payslip.Status.PUBLISHED:
                    skipped.append({'employee': str(emp), 'reason': 'Bulletin déjà publié'})
                    continue
                if emp.base_salary <= 0:
                    skipped.append({'employee': str(emp), 'reason': 'Salaire de base non renseigné'})
                    continue
                weekend = weekend_of(emp)
                unpaid = Decimal('0')
                for lr in LeaveRequest.objects.filter(employee=emp, leave_type=LeaveType.UNPAID,
                                                      status=RequestStatus.APPROVED,
                                                      start_date__lte=last, end_date__gte=first):
                    unpaid += payroll.overlap_days(lr.start_date, lr.end_date, year, month, weekend,
                                                   lr.start_half, lr.end_half)
                result = payroll.compute_payslip(emp.base_salary, bonuses, unpaid)
                p = existing or Payslip(employee=emp, year=year, month=month)
                p.job_title, p.department = emp.job_title, emp.department
                p.unpaid_days = unpaid
                p.worked_days = max(payroll.working_days_in_month(year, month, weekend) - unpaid, Decimal('0'))
                for f in ['gross_salary', 'social_contributions', 'taxable_salary', 'income_tax',
                          'net_salary', 'employer_contributions', 'employer_cost']:
                    setattr(p, f, getattr(result, f))
                p.save()
                p.lines.all().delete()
                PayslipLine.objects.bulk_create([
                    PayslipLine(payslip=p, order=i, code=l.code, label=l.label, kind=l.kind, base=l.base,
                                rate=l.rate, employee_amount=l.employee_amount, employer_amount=l.employer_amount)
                    for i, l in enumerate(result.lines)])
                if s.validated_data['publish']:
                    self._publish(p)
                created.append(p)

        return Response({'created': PayslipListSerializer(created, many=True).data, 'skipped': skipped},
                        status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], permission_classes=[IsHR])
    def publish_month(self, request):
        year, month = request.data.get('year'), request.data.get('month')
        drafts = Payslip.objects.filter(year=year, month=month, status=Payslip.Status.DRAFT)
        count = 0
        for p in drafts.select_related('employee'):
            self._publish(p)
            count += 1
        return Response({'published': count})


# ---------------------------------------------------------------- documents

class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        user = self.request.user
        qs = Document.objects.select_related('employee')
        params = self.request.query_params
        if user.is_hr and params.get('scope') == 'all':
            if params.get('employee'):
                qs = qs.filter(employee_id=params['employee'])
        elif user.is_hr and self.action not in ['list']:
            pass
        else:
            qs = qs.filter(Q(employee=user) | Q(employee__isnull=True))
        if params.get('category'):
            qs = qs.filter(category=params['category'])
        return qs

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsHR()]
        return super().get_permissions()

    def perform_create(self, serializer):
        doc = serializer.save(uploaded_by=self.request.user)
        if doc.employee:
            notify(doc.employee, 'Nouveau document dans votre coffre-fort', doc.title, '/documents', email=True)
        else:
            for u in User.objects.filter(is_active=True).exclude(id=self.request.user.id):
                notify(u, 'Nouveau document de l\'entreprise', doc.title, '/documents')

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

    def get_queryset(self):
        qs = LeaveRequest.objects.select_related('employee', 'reviewer')
        if self.action == 'list':
            qs = scoped_queryset(self.request, qs)
            if self.request.query_params.get('status'):
                qs = qs.filter(status=self.request.query_params['status'])
            if self.request.query_params.get('year'):
                qs = qs.filter(start_date__year=self.request.query_params['year'])
            return qs
        user = self.request.user
        if user.is_hr:
            return qs
        return qs.filter(Q(employee=user) | Q(employee__manager=user))

    def perform_create(self, serializer):
        user = self.request.user
        d = serializer.validated_data
        days = payroll.count_leave_days(d['start_date'], d['end_date'], weekend_of(user),
                                        d.get('start_half', False), d.get('end_half', False))
        if days <= 0:
            raise ValidationError('La période choisie ne contient aucun jour ouvré.')
        overlap = LeaveRequest.objects.filter(
            employee=user, status__in=[RequestStatus.PENDING, RequestStatus.APPROVED],
            start_date__lte=d['end_date'], end_date__gte=d['start_date'])
        if overlap.exists():
            raise ValidationError('Une demande existe déjà sur cette période.')
        if d['leave_type'] in BALANCED_LEAVE_TYPES:
            bal = next(b for b in balance_summary(user, d['start_date'].year) if b['leave_type'] == d['leave_type'])
            if bal['remaining'] - bal['pending'] < days:
                raise ValidationError(
                    f"Solde insuffisant : {bal['remaining'] - bal['pending']} jour(s) disponible(s), {days} demandé(s).")
        lr = serializer.save(employee=user, days=days)
        for r in reviewers_for(user):
            notify(r, f'Demande d\'absence de {user}',
                   f'{lr.get_leave_type_display()} du {lr.start_date:%d/%m/%Y} au {lr.end_date:%d/%m/%Y} ({days} j)',
                   '/equipe', email=True)

    def _review(self, request, new_status):
        lr = self.get_object()
        if not can_review(request.user, lr.employee):
            raise PermissionDenied("Vous ne pouvez pas valider cette demande.")
        if lr.status != RequestStatus.PENDING:
            raise ValidationError('Cette demande a déjà été traitée.')
        s = ReviewSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        mark_reviewed(lr, request.user, new_status, s.validated_data['comment'])
        verb = 'validée' if new_status == RequestStatus.APPROVED else 'refusée'
        notify(lr.employee, f'Votre demande d\'absence a été {verb}',
               f'{lr.get_leave_type_display()} du {lr.start_date:%d/%m/%Y} au {lr.end_date:%d/%m/%Y}'
               + (f' — {lr.review_comment}' if lr.review_comment else ''), '/absences', email=True)
        return Response(LeaveRequestSerializer(lr).data)

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
        if lr.employee_id == user.id:
            if lr.status == RequestStatus.APPROVED and lr.start_date <= date.today():
                raise ValidationError('Une absence déjà commencée ne peut plus être annulée.')
        elif not user.is_hr:
            raise PermissionDenied()
        if lr.status not in [RequestStatus.PENDING, RequestStatus.APPROVED]:
            raise ValidationError('Cette demande ne peut plus être annulée.')
        lr.status = RequestStatus.CANCELLED
        lr.save(update_fields=['status'])
        return Response(LeaveRequestSerializer(lr).data)

    @action(detail=True, methods=['get'])
    def attachment(self, request, pk=None):
        return file_download(self.get_object().attachment)

    @action(detail=False, methods=['get'])
    def balances(self, request):
        year = int(request.query_params.get('year') or date.today().year)
        return Response(balance_summary(request.user, year))

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
        The reason of a colleague's absence is private: only HR, the manager
        and the employee themself see the leave type."""
        user = request.user
        today = date.today()
        year = int(request.query_params.get('year') or today.year)
        month = int(request.query_params.get('month') or today.month)
        first, last = date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])

        if user.is_hr:
            people = User.objects.filter(is_active=True)
        else:
            people = User.objects.filter(is_active=True).filter(
                Q(id=user.id) | Q(manager=user) | (Q(manager_id=user.manager_id) if user.manager_id else Q(pk__in=[]))
                | Q(id=user.manager_id or 0))
        people = people.order_by('last_name', 'first_name')
        leaves = LeaveRequest.objects.filter(
            employee__in=people, status__in=[RequestStatus.PENDING, RequestStatus.APPROVED],
            start_date__lte=last, end_date__gte=first).exclude(leave_type=LeaveType.REMOTE)

        def visible(lr):
            return user.is_hr or lr.employee_id == user.id or lr.employee.manager_id == user.id

        return Response({
            'year': year, 'month': month, 'weekend_days': weekend_of(user),
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
        user = self.request.user
        if user.is_hr:
            return qs
        return qs.filter(Q(employee=user) | Q(employee__manager=user))

    def perform_create(self, serializer):
        user = self.request.user
        exp = serializer.save(employee=user)
        for r in reviewers_for(user):
            notify(r, f'Note de frais de {user}', f'{exp.description} — {fmt(exp.amount)} DA', '/equipe')

    def _review(self, request, new_status):
        exp = self.get_object()
        if not can_review(request.user, exp.employee):
            raise PermissionDenied("Vous ne pouvez pas valider cette note de frais.")
        if exp.status != ExpenseReport.Status.PENDING:
            raise ValidationError('Cette note de frais a déjà été traitée.')
        s = ReviewSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        mark_reviewed(exp, request.user, new_status, s.validated_data['comment'])
        verb = 'validée' if new_status == ExpenseReport.Status.APPROVED else 'refusée'
        notify(exp.employee, f'Votre note de frais a été {verb}',
               f'{exp.description} — {fmt(exp.amount)} DA' + (f' — {exp.review_comment}' if exp.review_comment else ''),
               '/notes-de-frais', email=True)
        return Response(ExpenseSerializer(exp).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        return self._review(request, ExpenseReport.Status.APPROVED)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        return self._review(request, ExpenseReport.Status.REJECTED)

    @action(detail=True, methods=['post'], permission_classes=[IsHR])
    def mark_paid(self, request, pk=None):
        exp = self.get_object()
        if exp.status != ExpenseReport.Status.APPROVED:
            raise ValidationError('Seule une note validée peut être marquée remboursée.')
        exp.status = ExpenseReport.Status.PAID
        exp.save(update_fields=['status'])
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
            qs = scoped_queryset(self.request, qs)
            if self.request.query_params.get('status'):
                qs = qs.filter(status=self.request.query_params['status'])
            return qs
        return qs if self.request.user.is_hr else qs.filter(employee=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        if ProfileChangeRequest.objects.filter(employee=user, status=RequestStatus.PENDING).exists():
            raise ValidationError('Une demande de modification est déjà en cours de traitement.')
        serializer.save(employee=user)
        for hr in User.objects.filter(Q(role=User.Role.HR) | Q(is_superuser=True), is_active=True).exclude(id=user.id):
            notify(hr, f'Modification de dossier demandée par {user}', '', '/admin/demandes')

    @action(detail=True, methods=['post'], permission_classes=[IsHR])
    def approve(self, request, pk=None):
        req = self.get_object()
        if req.status != RequestStatus.PENDING:
            raise ValidationError('Cette demande a déjà été traitée.')
        emp = req.employee
        for field, value in req.changes.items():
            if field not in REQUESTABLE_FIELDS:
                continue
            if field == 'birth_date':
                value = date.fromisoformat(value) if value else None
            setattr(emp, field, value)
        emp.save()
        mark_reviewed(req, request.user, RequestStatus.APPROVED, request.data.get('comment', ''))
        notify(emp, 'Votre dossier a été mis à jour', 'Les modifications demandées ont été appliquées.', '/profil')
        return Response(ProfileChangeRequestSerializer(req).data)

    @action(detail=True, methods=['post'], permission_classes=[IsHR])
    def reject(self, request, pk=None):
        req = self.get_object()
        if req.status != RequestStatus.PENDING:
            raise ValidationError('Cette demande a déjà été traitée.')
        mark_reviewed(req, request.user, RequestStatus.REJECTED, request.data.get('comment', ''))
        notify(req.employee, 'Demande de modification refusée', req.review_comment, '/profil')
        return Response(ProfileChangeRequestSerializer(req).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        req = self.get_object()
        if req.employee_id != request.user.id or req.status != RequestStatus.PENDING:
            raise ValidationError('Cette demande ne peut pas être annulée.')
        req.status = RequestStatus.CANCELLED
        req.save(update_fields=['status'])
        return Response(ProfileChangeRequestSerializer(req).data)


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
