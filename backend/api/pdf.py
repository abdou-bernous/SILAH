"""Payslip PDF rendering (reportlab)."""
import io
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

MONTHS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août',
          'septembre', 'octobre', 'novembre', 'décembre']

COFFEE = colors.HexColor('#8a6e5a')
COFFEE_PALE = colors.HexColor('#f3ede7')
GREY = colors.HexColor('#6b6560')
LINE = colors.HexColor('#e2dcd5')


def fmt(value):
    if value is None or value == '':
        return ''
    v = Decimal(value)
    s = f'{abs(v):,.2f}'.replace(',', ' ').replace('.', ',')
    return f'-{s}' if v < 0 else s


def month_label(year, month):
    return f'{MONTHS[month - 1].capitalize()} {year}'


def render_payslip(payslip) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm,
                            title=f'Bulletin de paie {month_label(payslip.year, payslip.month)}')
    small = ParagraphStyle('small', fontName='Helvetica', fontSize=8.5, leading=11, textColor=GREY)
    normal = ParagraphStyle('normal', fontName='Helvetica', fontSize=9.5, leading=13)
    title = ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=15, leading=19, textColor=COFFEE)

    e = payslip.employee
    c = e.company
    story = [Paragraph('Bulletin de paie', title),
             Paragraph(f'Période : {month_label(payslip.year, payslip.month)}', normal),
             Spacer(1, 6 * mm)]

    company_lines = [f'<b>{c.name}</b>' if c else '<b>Employeur</b>']
    if c:
        company_lines += [x for x in [c.address, c.city] if x]
        ids = [f'{k} {v}' for k, v in [('NIF', c.nif), ('NIS', c.nis), ('CNAS', c.cnas_number)] if v]
        if ids:
            company_lines.append(' · '.join(ids))
    employee_lines = [f'<b>{e.get_full_name() or e.username}</b>']
    employee_lines += [x for x in [e.address, e.city] if x]
    employee_lines.append(f'Matricule : {e.employee_number or "—"}')
    employee_lines.append(f'N° SS : {e.social_security_number or "—"}')
    employee_lines.append(f'Poste : {payslip.job_title or "—"}')
    if payslip.department:
        employee_lines.append(f'Service : {payslip.department}')

    header = Table([[Paragraph('<br/>'.join(company_lines), normal),
                     Paragraph('<br/>'.join(employee_lines), normal)]],
                   colWidths=[90 * mm, 90 * mm])
    header.setStyle(TableStyle([
        ('BOX', (1, 0), (1, 0), 0.6, LINE),
        ('BACKGROUND', (1, 0), (1, 0), COFFEE_PALE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6), ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story += [header, Spacer(1, 6 * mm)]

    rows = [['Code', 'Libellé', 'Base', 'Taux', 'Part salarié', 'Part employeur']]
    for line in payslip.lines.all():
        rows.append([line.code, Paragraph(line.label, normal), fmt(line.base),
                     f'{fmt(line.rate)} %' if line.rate is not None and line.kind == 'contribution' else fmt(line.rate),
                     fmt(line.employee_amount), fmt(line.employer_amount) if line.employer_amount else ''])
    table = Table(rows, colWidths=[14 * mm, 66 * mm, 26 * mm, 20 * mm, 27 * mm, 27 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), COFFEE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('LINEBELOW', (0, 1), (-1, -1), 0.4, LINE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story += [table, Spacer(1, 6 * mm)]

    totals = [
        ['Salaire brut', fmt(payslip.gross_salary)],
        ['Cotisations salariales', fmt(-payslip.social_contributions)],
        ['Salaire imposable', fmt(payslip.taxable_salary)],
        ['IRG retenu', fmt(-payslip.income_tax)],
        ['Net à payer (DZD)', fmt(payslip.net_salary)],
    ]
    tt = Table(totals, colWidths=[60 * mm, 35 * mm], hAlign='RIGHT')
    tt.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('LINEBELOW', (0, 0), (-1, -2), 0.4, LINE),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 11),
        ('BACKGROUND', (0, -1), (-1, -1), COFFEE_PALE),
        ('TOPPADDING', (0, -1), (-1, -1), 6), ('BOTTOMPADDING', (0, -1), (-1, -1), 6),
    ]))
    story += [tt, Spacer(1, 4 * mm)]
    story.append(Paragraph(
        f'Coût total employeur : {fmt(payslip.employer_cost)} DZD · '
        f'Jours travaillés : {fmt(payslip.worked_days)} · Absences non rémunérées : {fmt(payslip.unpaid_days)} j', small))
    if e.iban:
        story.append(Paragraph(f'Paiement par virement — {e.bank_name or "Banque"} · {e.iban}', small))
    story += [Spacer(1, 8 * mm), Paragraph(
        'Document généré par SILAH. Conservez ce bulletin sans limitation de durée.', small)]

    doc.build(story)
    return buf.getvalue()
