"""Bilingual (French / Arabic) payslip PDF rendering with ReportLab.

Arabic text is reshaped (contextual letter forms) and reordered for right-to-left display
before drawing, since ReportLab has no shaping engine. DejaVu Sans covers both scripts.
"""
import io
import textwrap
from decimal import Decimal
from pathlib import Path
from xml.sax.saxutils import escape

import arabic_reshaper
from bidi.algorithm import get_display
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

FONT_DIR = Path(__file__).resolve().parent / 'fonts'
FONT, FONT_BOLD = 'SilahSans', 'SilahSans-Bold'
if FONT not in pdfmetrics.getRegisteredFontNames():
    pdfmetrics.registerFont(TTFont(FONT, str(FONT_DIR / 'DejaVuSans.ttf')))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(FONT_DIR / 'DejaVuSans-Bold.ttf')))

MONTHS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août',
          'septembre', 'octobre', 'novembre', 'décembre']
# Months as used in Algeria (Syriac-derived names).
MONTHS_AR = ['جانفي', 'فيفري', 'مارس', 'أفريل', 'ماي', 'جوان', 'جويلية', 'أوت',
             'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
CONTRACTS = {'cdi': ('CDI', 'عقد غير محدد المدة'), 'cdd': ('CDD', 'عقد محدد المدة'),
             'intern': ('Stage', 'تربص'), 'other': ('Autre', 'آخر')}
# How a certificate states the employment relationship. 'other' says nothing rather than something vague.
CERTIFICATE_CONTRACTS = {
    'cdi': ('sous contrat à durée indéterminée (CDI)', 'بموجب عقد عمل غير محدد المدة'),
    'cdd': ('sous contrat à durée déterminée (CDD)', 'بموجب عقد عمل محدد المدة'),
    'intern': ("dans le cadre d'un stage", 'في إطار تربص'),
    'other': ('', ''),
}
MARITAL = {'single': ('Célibataire', 'أعزب'), 'married': ('Marié(e)', 'متزوج'),
           'divorced': ('Divorcé(e)', 'مطلق'), 'widowed': ('Veuf / veuve', 'أرمل')}
PAYMENT = {'transfer': ('Virement', 'تحويل'), 'cheque': ('Chèque', 'صك'), 'cash': ('Espèces', 'نقدا')}

COFFEE = colors.HexColor('#8a6e5a')
COFFEE_PALE = colors.HexColor('#f3ede7')
GREY = colors.HexColor('#6b6560')
LINE = colors.HexColor('#e2dcd5')


def esc(value):
    """Paragraphs read ReportLab's mini-markup: user text is escaped, so that a '<' in a company name
    or a pay item label can neither break the PDF nor restyle it."""
    return escape(str(value)) if value not in (None, '') else ''


def ar(text):
    """Arabic shaped and put in display order, escaped like esc()."""
    return escape(get_display(arabic_reshaper.reshape(str(text)))) if text else ''


def fmt(value):
    if value is None or value == '':
        return ''
    v = Decimal(value)
    s = f'{abs(v):,.2f}'.replace(',', ' ').replace('.', ',')
    return f'-{s}' if v < 0 else s


def month_label(year, month):
    return f'{MONTHS[month - 1].capitalize()} {year}'


def certificate_text(request) -> tuple[str, str]:
    """The body of a work or salary certificate, in French and in Arabic (logical order, not shaped)."""
    e, c = request.employee, request.employee.company
    salary = request.kind == 'salary'
    name = e.get_full_name() or e.username
    contract_fr, contract_ar = CERTIFICATE_CONTRACTS.get(e.contract_type, CERTIFICATE_CONTRACTS['other'])
    hired = e.hire_date.strftime('%d/%m/%Y') if e.hire_date else '—'

    text_fr = (f'Nous soussignés, {c.name}, attestons que {name}, matricule {e.employee_number or "—"}, '
               f'fait partie de notre personnel depuis le {hired}, en qualité de {e.job_title or "—"}'
               f'{", " + contract_fr if contract_fr else ""}.')
    text_ar = (f'نحن الموقعين أدناه، {c.name_ar or c.name}، نشهد أن {name}، الرقم {e.employee_number or "—"}، '
               f'يعمل لدينا منذ {hired}، بصفة {e.job_title or "—"}{"، " + contract_ar if contract_ar else ""}.')
    if salary:
        # Non-breaking spaces: the amount must not be cut at the end of a line, and in Arabic a plain
        # space would let the bidi algorithm swap the groups of digits.
        amount = fmt(e.base_salary).replace(' ', '\u00a0')
        text_fr += f' Son salaire de base mensuel brut est de {amount}\u00a0DA.'
        text_ar += f' ويبلغ أجره القاعدي الشهري الخام {amount} دج.'
    text_fr += " Cette attestation est délivrée à l'intéressé(e) pour servir et valoir ce que de droit."
    text_ar += ' سُلمت هذه الشهادة للمعني بالأمر للإدلاء بها عند الحاجة.'
    return text_fr, text_ar


def render_certificate(request, issued_on) -> bytes:
    """Work or salary certificate, French first, then Arabic. ReportLab cannot wrap
    reordered Arabic text, so its lines are cut before being shaped."""
    c = request.employee.company
    salary = request.kind == 'salary'
    title_fr, title_ar = ('Attestation de salaire', 'شهادة أجر') if salary else ('Attestation de travail', 'شهادة عمل')
    today = issued_on.strftime('%d/%m/%Y')
    text_fr, text_ar = certificate_text(request)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=22 * mm, rightMargin=22 * mm,
                            topMargin=22 * mm, bottomMargin=22 * mm, title=title_fr)
    normal = ParagraphStyle('normal', fontName=FONT, fontSize=10.5, leading=16)
    normal_r = ParagraphStyle('normal_r', parent=normal, alignment=TA_RIGHT)
    title = ParagraphStyle('title', fontName=FONT_BOLD, fontSize=16, leading=22, alignment=TA_CENTER, textColor=COFFEE)

    ids = ' · '.join(f'{k} {v}' for k, v in [('NIF', c.nif), ('NIS', c.nis), ('RC', c.rc)] if v)
    story = [Paragraph(esc(c.name), ParagraphStyle('company', parent=normal, fontName=FONT_BOLD))]
    story += [Paragraph(esc(x), normal) for x in [' '.join(filter(None, [c.address, c.city])), ids] if x]
    story += [Spacer(1, 14 * mm), Paragraph(title_fr, title), Paragraph(ar(title_ar), title), Spacer(1, 12 * mm),
              Paragraph(esc(text_fr), normal), Spacer(1, 4 * mm),
              Paragraph(esc(f'Fait à {c.city or "—"}, le {today}.'), normal), Spacer(1, 10 * mm)]
    story += [Paragraph(ar(line), normal_r) for line in textwrap.wrap(text_ar, 84)]
    story += [Spacer(1, 4 * mm), Paragraph(ar(f'حرر في {c.city or "—"}، بتاريخ {today}.'), normal_r),
              Spacer(1, 22 * mm), Paragraph('Signature et cachet de l\'employeur', normal),
              Paragraph(ar('إمضاء وختم المستخدم'), normal_r)]
    doc.build(story)
    return buf.getvalue()


def day(dt):
    return timezone.localtime(dt).strftime('%d/%m/%Y') if dt else '—'


def correction_note(payslip, style, style_r):
    """The banner of a corrective payslip, or of the payslip it replaced."""
    if payslip.replaces_id:
        when = day(payslip.replaces.published_at)
        fr = f'<b>Bulletin rectificatif</b> : annule et remplace le bulletin publié le {when}.'
        if payslip.correction_reason:
            fr += f' Motif : {esc(payslip.correction_reason)}'
        ar_text = f'كشف تصحيحي: يلغي ويعوض الكشف المنشور بتاريخ {when}.'
    elif payslip.status == 'replaced':
        correction = getattr(payslip, 'replaced_by', None)
        when = day(correction.published_at if correction else None)
        fr = f"<b>Bulletin remplacé</b> le {when} par un bulletin rectificatif : il n'est plus en vigueur."
        ar_text = f'عُوّض هذا الكشف بكشف تصحيحي بتاريخ {when}، ولم يعد ساري المفعول.'
    else:
        return None
    box = Table([[[Paragraph(fr, style), Paragraph(ar(ar_text), style_r)]]], colWidths=[186 * mm])
    box.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), COFFEE_PALE), ('BOX', (0, 0), (-1, -1), 0.6, COFFEE),
                             ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                             ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]))
    return box


def render_payslip(payslip) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm,
                            title=f'Bulletin de paie {month_label(payslip.year, payslip.month)}')
    small = ParagraphStyle('small', fontName=FONT, fontSize=7.5, leading=10, textColor=GREY)
    normal = ParagraphStyle('normal', fontName=FONT, fontSize=8.5, leading=11.5)
    normal_r = ParagraphStyle('normal_r', parent=normal, alignment=TA_RIGHT)
    title = ParagraphStyle('title', fontName=FONT_BOLD, fontSize=14, leading=18, textColor=COFFEE)
    title_r = ParagraphStyle('title_r', parent=title, alignment=TA_RIGHT)

    e = payslip.employee
    c = payslip.company or e.company
    period_fr = month_label(payslip.year, payslip.month)
    period_ar = f'{MONTHS_AR[payslip.month - 1]} {payslip.year}'

    head = Table([[Paragraph(f'Bulletin de paie<br/><font size="9" color="#6b6560">{period_fr}</font>', title),
                   Paragraph(f'{ar("كشف الراتب")}<br/><font size="9" color="#6b6560">{ar(period_ar)}</font>', title_r)]],
                 colWidths=[93 * mm, 93 * mm])
    head.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
                              ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
    story = [head, Spacer(1, 5 * mm)]
    note = correction_note(payslip, normal, normal_r)
    if note:
        story += [note, Spacer(1, 4 * mm)]

    company_lines = [f'<b>{esc(c.name)} {esc(c.legal_form)}</b>' if c else '<b>Employeur</b>']
    if c and c.name_ar:
        company_lines.append(ar(c.name_ar))
    if c:
        company_lines += [esc(x) for x in [c.address, c.city] if x]
        for k, v in [('NIF', c.nif), ('NIS', c.nis), ('RC', c.rc), ('N° employeur CNAS', c.cnas_number)]:
            if v:
                company_lines.append(f'{k} : {esc(v)}')

    def pair(fr, ar_label, value):
        return f'{fr} / {ar(ar_label)} : <b>{esc(value) or "—"}</b>'

    contract = CONTRACTS.get(e.contract_type, ('', ''))
    marital = MARITAL.get(e.marital_status, ('', ''))
    employee_lines = [f'<b>{esc(e.get_full_name() or e.username)}</b>']
    employee_lines += [esc(x) for x in [e.address, e.city] if x]
    employee_lines += [
        pair('Matricule', 'الرقم', e.employee_number),
        pair('N° SS', 'رقم الضمان الاجتماعي', e.social_security_number),
        pair('NIN', 'رقم التعريف الوطني', e.nin),
        pair('Poste', 'المنصب', payslip.job_title),
        pair('Catégorie', 'الصنف', payslip.qualification),
        pair('Entrée', 'تاريخ التوظيف', e.hire_date.strftime('%d/%m/%Y') if e.hire_date else ''),
        pair('Contrat', 'العقد', contract[0]),
        pair('Situation', 'الحالة العائلية', f'{marital[0]}, {e.children_count} enf.'),
    ]

    header = Table([[Paragraph('<br/>'.join(company_lines), normal),
                     Paragraph('<br/>'.join(employee_lines), normal)]], colWidths=[86 * mm, 100 * mm])
    header.setStyle(TableStyle([
        ('BOX', (1, 0), (1, 0), 0.6, LINE),
        ('BACKGROUND', (1, 0), (1, 0), COFFEE_PALE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6), ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story += [header, Spacer(1, 5 * mm)]

    th = ParagraphStyle('th', fontName=FONT_BOLD, fontSize=7.5, leading=9.5, textColor=colors.white)
    th_r = ParagraphStyle('th_r', parent=th, alignment=TA_RIGHT)

    def head_cell(fr, ar_label, right=False):
        return Paragraph(f'{fr}<br/>{ar(ar_label)}', th_r if right else th)

    rows = [[head_cell('Code', 'الرمز'), head_cell('Rubrique', 'البيان'), head_cell('Base', 'الأساس', True),
             head_cell('Taux', 'النسبة', True), head_cell('Gain / Retenue', 'المبلغ', True),
             head_cell('Part employeur', 'حصة المستخدم', True)]]
    for line in payslip.lines.all():
        label = esc(line.label) + (f'<br/><font color="#6b6560">{ar(line.label_ar)}</font>' if line.label_ar else '')
        if line.code == 'R100':
            base, rate = f'{fmt(line.base)} h', fmt(line.rate)
        elif line.kind == 'deduction':
            base, rate = f'{fmt(line.base)} j', fmt(line.rate)
        else:
            base = fmt(line.base)
            rate = f'{fmt(line.rate)} %' if line.rate is not None else ''
        rows.append([line.code, Paragraph(label, normal), base, rate, fmt(line.employee_amount),
                     fmt(line.employer_amount) if line.employer_amount else ''])
    table = Table(rows, colWidths=[13 * mm, 73 * mm, 26 * mm, 18 * mm, 28 * mm, 28 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT),
        ('FONTSIZE', (0, 1), (-1, -1), 8.5),
        ('BACKGROUND', (0, 0), (-1, 0), COFFEE),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
        ('LINEBELOW', (0, 1), (-1, -1), 0.4, LINE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story += [table, Spacer(1, 5 * mm)]

    def total_row(fr, ar_label, value):
        return [Paragraph(f'{fr} <font color="#6b6560">/ {ar(ar_label)}</font>', normal), fmt(value)]

    totals = [
        total_row('Salaire brut', 'الأجر الخام', payslip.gross_salary),
        total_row('Cotisations CNAS', 'اشتراكات الضمان الاجتماعي', -payslip.social_contributions),
        total_row('Salaire imposable', 'الأجر الخاضع للضريبة', payslip.taxable_salary),
        total_row('IRG retenu', 'الضريبة المقتطعة', -(payslip.income_tax + payslip.flat_tax)),
    ]
    if payslip.non_taxable:
        totals.append(total_row('Indemnités non soumises', 'تعويضات غير خاضعة', payslip.non_taxable))
    totals.append([Paragraph(f'<b>Net à payer (DA)</b> / <b>{ar("الصافي للدفع")}</b>', normal),
                   fmt(payslip.net_salary)])
    tt = Table(totals, colWidths=[78 * mm, 32 * mm], hAlign='RIGHT')
    tt.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, 0), (-1, -2), 0.4, LINE),
        ('FONTNAME', (1, -1), (1, -1), FONT_BOLD),
        ('FONTSIZE', (1, -1), (1, -1), 11),
        ('BACKGROUND', (0, -1), (-1, -1), COFFEE_PALE),
        ('TOPPADDING', (0, -1), (-1, -1), 6), ('BOTTOMPADDING', (0, -1), (-1, -1), 6),
    ]))
    story += [tt, Spacer(1, 4 * mm)]

    pay = PAYMENT.get(e.payment_method, ('', ''))
    absences = f'Absences non rémunérées : {payslip.unpaid_days.normalize()} j · ' if payslip.unpaid_days else ''
    story.append(Paragraph(
        f'Jours travaillés / {ar("أيام العمل")} : {payslip.worked_days.normalize()} · '
        f'Heures / {ar("الساعات")} : {fmt(payslip.worked_hours)} · {absences}'
        f'Coût employeur / {ar("تكلفة المستخدم")} : {fmt(payslip.employer_cost)}&nbsp;DA', small))
    payment = f'Mode de paiement / {ar("طريقة الدفع")} : {pay[0]}'
    if e.payment_method == 'transfer' and e.iban:
        payment += f' — {esc(e.bank_name) or "Banque"} {esc(e.iban)}'
    story.append(Paragraph(payment, small))
    story += [Spacer(1, 6 * mm), Paragraph(
        'Document généré par SILAH. Conservez ce bulletin sans limitation de durée. / '
        + ar('احتفظ بكشف الراتب هذا دون تحديد المدة.'), small)]

    doc.build(story)
    return buf.getvalue()
