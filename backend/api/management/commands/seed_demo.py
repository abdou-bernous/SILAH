"""Fill an empty database with a fictional company and three demo accounts.

    python manage.py seed_demo            # idempotent: does nothing if data exists
    python manage.py seed_demo --reset    # wipe the demo users first
"""
import io
from datetime import date, timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from rest_framework.test import APIRequestFactory, force_authenticate

from api.models import (
    CertificateRequest, Company, Document, EmployeePayItem, ExpenseReport, LeaveBalance, LeaveRequest, LeaveType,
    Notification, RequestStatus, User,
)
from api.payroll import PRESETS
from api.views import PayslipViewSet

DEMO_PASSWORD = 'Silah2026!'
DEMO_USERNAMES = ['rh', 'manager', 'salarie', 'yasmine', 'comptable', 'admin', 'rh.nour', 'sofiane', 'lina']
DEMO_COMPANIES = ['Atlas Distribution', 'Nour Pharma']


def simple_pdf(name, title, body):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont('Helvetica-Bold', 16)
    c.drawString(60, 780, title)
    c.setFont('Helvetica', 11)
    y = 750
    for line in body:
        c.drawString(60, y, line)
        y -= 18
    c.showPage()
    c.save()
    return ContentFile(buf.getvalue(), name=name)


class Command(BaseCommand):
    help = 'Crée une entreprise fictive et des comptes de démonstration.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true')

    def handle(self, *args, **opts):
        if opts['reset']:
            User.objects.filter(username__in=DEMO_USERNAMES).delete()
            Company.objects.filter(name__in=DEMO_COMPANIES).delete()
        elif User.objects.filter(username__in=DEMO_USERNAMES).exists():
            self.stdout.write('Données de démo déjà présentes (utilisez --reset pour recommencer).')
            return

        company = Company.objects.create(
            name='Atlas Distribution', name_ar='أطلس للتوزيع', legal_form='SARL', sector='Distribution',
            address='12 rue des Oliviers', city='Alger',
            nif='000216001234567', nis='000216123456789', rc='16/00-1234567B', cnas_number='16123456')
        nour = Company.objects.create(
            name='Nour Pharma', name_ar='نور فارما', legal_form='EURL', sector='Pharmacie',
            address='3 boulevard de la Soummam', city='Oran',
            nif='000231009876543', nis='000231987654321', rc='31/00-7654321B', cnas_number='31654321')

        def make(username, company=company, **kw):
            u = User(username=username, company=company, **kw)
            u.set_password(DEMO_PASSWORD)
            u.save()
            return u

        rh = make('rh', first_name='Nadia', last_name='Benali', email='rh@atlas.example', role=User.Role.HR,
                  employee_number='A001', job_title='Responsable RH', department='Ressources humaines',
                  hire_date=date(2019, 3, 1), base_salary=Decimal('145000'), is_staff=True,
                  city='Alger', phone='0550 00 00 01')
        manager = make('manager', first_name='Karim', last_name='Haddad', email='manager@atlas.example',
                       role=User.Role.MANAGER, employee_number='A014', job_title='Chef des ventes',
                       department='Commercial', hire_date=date(2020, 9, 15), base_salary=Decimal('120000'),
                       city='Alger', phone='0550 00 00 02')
        salarie = make('salarie', first_name='Amine', last_name='Mansouri', email='salarie@atlas.example',
                       employee_number='A027', job_title='Commercial terrain', department='Commercial',
                       hire_date=date(2022, 1, 10), birth_date=date(1994, 6, 21), base_salary=Decimal('68000'),
                       manager=manager, social_security_number='94 0621 1234 56', phone='0550 00 00 03',
                       nin='109940621001234567', qualification='Cat. 9 / Éch. 2', marital_status='married',
                       children_count=2,
                       address='5 cité des Pins', city='Blida', postal_code='09000',
                       bank_name='CPA', iban='004 00123 0123456789 12')
        yasmine = make('yasmine', first_name='Yasmine', last_name='Cherif', email='yasmine@atlas.example',
                       employee_number='A031', job_title='Assistante commerciale', department='Commercial',
                       hire_date=date(2023, 4, 3), base_salary=Decimal('52000'), manager=manager, city='Alger')

        # Second company, run by the same accountant.
        rh_nour = make('rh.nour', company=nour, first_name='Samira', last_name='Bouzid', email='rh@nour.example',
                       role=User.Role.HR, employee_number='N001', job_title='Gestionnaire RH',
                       department='Administration', hire_date=date(2021, 2, 1), base_salary=Decimal('98000'), city='Oran')
        sofiane = make('sofiane', company=nour, first_name='Sofiane', last_name='Larbi', email='sofiane@nour.example',
                       employee_number='N007', job_title='Pharmacien', department='Officine',
                       hire_date=date(2020, 6, 1), base_salary=Decimal('110000'), city='Oran', marital_status='married',
                       children_count=1)
        lina = make('lina', company=nour, first_name='Lina', last_name='Meziane', email='lina@nour.example',
                    employee_number='N012', job_title='Préparatrice', department='Officine',
                    hire_date=date(2024, 9, 1), base_salary=Decimal('34000'), city='Oran', manager=sofiane,
                    is_disabled=True)

        # Platform roles: an accountant managing both companies, and the global admin.
        comptable = make('comptable', company=None, first_name='Rachid', last_name='Kaci',
                         email='cabinet@kaci-conseil.example', role=User.Role.ACCOUNTANT, phone='0560 00 00 10')
        comptable.managed_companies.set([company, nour])
        make('admin', company=None, first_name='Admin', last_name='SILAH', email='admin@silah.example',
             role=User.Role.ADMIN)

        today = date.today()
        for u in [rh, manager, salarie, yasmine, rh_nour, sofiane, lina]:
            LeaveBalance.objects.create(employee=u, leave_type=LeaveType.ANNUAL, year=today.year,
                                        allotted=Decimal('30'), carried_over=Decimal('4'))
            LeaveBalance.objects.create(employee=u, leave_type=LeaveType.RECOVERY, year=today.year,
                                        allotted=Decimal('3'))

        # Past approved leave + one pending request awaiting the manager.
        LeaveRequest.objects.create(employee=salarie, leave_type=LeaveType.ANNUAL,
                                    start_date=date(today.year, 1, 4), end_date=date(today.year, 1, 8),
                                    days=Decimal('5'), status=RequestStatus.APPROVED, reviewer=manager)
        start = today + timedelta(days=14)
        LeaveRequest.objects.create(employee=salarie, leave_type=LeaveType.ANNUAL, start_date=start,
                                    end_date=start + timedelta(days=4), days=Decimal('3'),
                                    reason='Vacances en famille')
        LeaveRequest.objects.create(employee=yasmine, leave_type=LeaveType.RECOVERY, start_date=today + timedelta(days=3),
                                    end_date=today + timedelta(days=3), days=Decimal('1'))

        ExpenseReport.objects.create(employee=salarie, date=today - timedelta(days=6), category='transport',
                                     amount=Decimal('3200'), description='Déplacement client Tipaza')
        ExpenseReport.objects.create(employee=salarie, date=today - timedelta(days=30), category='meals',
                                     amount=Decimal('1800'), description='Déjeuner client',
                                     status=ExpenseReport.Status.PAID, reviewer=manager)

        demo = ['Atlas Distribution SARL - document de demonstration.']
        Document.objects.create(company=company, employee=None, category='company', title='Règlement intérieur', uploaded_by=rh,
                                file=simple_pdf('reglement_interieur.pdf', 'Reglement interieur', demo + [
                                    'Horaires : dimanche au jeudi, 8h30 - 17h00.']))
        Document.objects.create(company=company, employee=salarie, category='contract', title='Contrat de travail CDI',
                                uploaded_by=rh, file=simple_pdf('contrat_cdi.pdf', 'Contrat de travail', demo))
        Document.objects.create(company=company, employee=salarie, category='certificate', title='Attestation de travail',
                                uploaded_by=rh, file=simple_pdf('attestation_travail.pdf', 'Attestation de travail', demo))

        # Three published months of payroll per company, run through the real API action.
        factory = APIRequestFactory()
        view = PayslipViewSet.as_view({'post': 'run'})
        p = PRESETS
        for runner, months in [(rh, 3), (rh_nour, 2)]:
            y, m = today.year, today.month
            for i in range(months):
                m -= 1
                if m == 0:
                    y, m = y - 1, 12
                bonuses = [
                    {**p['pri'], 'amount': '6000'},
                    {**p['panier'], 'amount': '2400'},
                    {**p['transport'], 'amount': '1500'},
                ]
                if m % 3 == 0:  # quarterly collective bonus
                    bonuses.append({**p['prc'], 'amount': '9000'})
                for b in bonuses:
                    b.pop('key', None)
                req = factory.post('/api/payslips/run/', {'year': y, 'month': m, 'bonuses': bonuses, 'publish': True},
                                   format='json')
                force_authenticate(req, user=runner)
                view(req)

        # Approved after the last payroll run: repaid by the next payslip.
        ExpenseReport.objects.create(employee=salarie, date=today - timedelta(days=2), category='transport',
                                     amount=Decimal('1500'), description='Péage autoroute Est-Ouest',
                                     status=ExpenseReport.Status.APPROVED, reviewer=manager)
        EmployeePayItem.objects.create(employee=salarie, label=PRESETS['panier']['label'], amount=Decimal('2400'),
                                       label_ar=PRESETS['panier']['label_ar'], contributory=False)
        CertificateRequest.objects.create(employee=yasmine, kind=CertificateRequest.Kind.WORK)

        Notification.objects.filter(user=salarie).update(read=True)
        Notification.objects.create(user=salarie, title='Bienvenue sur SILAH',
                                    message='Retrouvez ici vos bulletins, documents et demandes.', link='/')

        self.stdout.write(self.style.SUCCESS(
            'Démo prête. Comptes : salarie / manager / rh / comptable / admin (et rh.nour, sofiane, lina, yasmine)'
            f' — mot de passe : {DEMO_PASSWORD}'))
