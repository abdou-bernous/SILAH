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
    Company, Document, ExpenseReport, LeaveBalance, LeaveRequest, LeaveType, Notification, RequestStatus, User,
)
from api.views import PayslipViewSet

DEMO_PASSWORD = 'Silah2026!'
DEMO_USERNAMES = ['rh', 'manager', 'salarie', 'yasmine']


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
            Company.objects.filter(name='Atlas Distribution').delete()
        elif User.objects.filter(username__in=DEMO_USERNAMES).exists():
            self.stdout.write('Données de démo déjà présentes (utilisez --reset pour recommencer).')
            return

        company = Company.objects.create(
            name='Atlas Distribution', legal_form='SARL', address='12 rue des Oliviers', city='Alger',
            nif='000216001234567', nis='000216123456789', rc='16/00-1234567B', cnas_number='16123456')

        def make(username, **kw):
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
                       address='5 cité des Pins', city='Blida', postal_code='09000',
                       bank_name='CPA', iban='004 00123 0123456789 12')
        yasmine = make('yasmine', first_name='Yasmine', last_name='Cherif', email='yasmine@atlas.example',
                       employee_number='A031', job_title='Assistante commerciale', department='Commercial',
                       hire_date=date(2023, 4, 3), base_salary=Decimal('52000'), manager=manager, city='Alger')

        today = date.today()
        for u in [rh, manager, salarie, yasmine]:
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
        Document.objects.create(employee=None, category='company', title='Règlement intérieur', uploaded_by=rh,
                                file=simple_pdf('reglement_interieur.pdf', 'Reglement interieur', demo + [
                                    'Horaires : dimanche au jeudi, 8h30 - 17h00.']))
        Document.objects.create(employee=salarie, category='contract', title='Contrat de travail CDI',
                                uploaded_by=rh, file=simple_pdf('contrat_cdi.pdf', 'Contrat de travail', demo))
        Document.objects.create(employee=salarie, category='certificate', title='Attestation de travail',
                                uploaded_by=rh, file=simple_pdf('attestation_travail.pdf', 'Attestation de travail', demo))

        # Three published months of payroll, run through the real API action.
        factory = APIRequestFactory()
        view = PayslipViewSet.as_view({'post': 'run'})
        y, m = today.year, today.month
        for _ in range(3):
            m -= 1
            if m == 0:
                y, m = y - 1, 12
            bonuses = [{'label': 'Prime de rendement (PRI)', 'amount': '6000'},
                       {'label': 'Indemnité de panier', 'amount': '3000', 'contributory': False, 'taxable': False}]
            req = factory.post('/api/payslips/run/', {'year': y, 'month': m, 'bonuses': bonuses, 'publish': True},
                               format='json')
            force_authenticate(req, user=rh)
            view(req)

        Notification.objects.filter(user=salarie).update(read=True)
        Notification.objects.create(user=salarie, title='Bienvenue sur SILAH',
                                    message='Retrouvez ici vos bulletins, documents et demandes.', link='/')

        self.stdout.write(self.style.SUCCESS(
            f'Démo prête. Comptes : rh / manager / salarie / yasmine — mot de passe : {DEMO_PASSWORD}'))
