'use client'
import type { PayslipDetail } from '@/lib/types'
import { date, money, monthLabel, num } from '@/lib/format'
import { useI18n } from '@/lib/i18n'

function amount(v: string | null | undefined) {
  if (v === null || v === undefined || Number(v) === 0) return ''
  return money(v, false)
}

export default function PayslipView({ p }: { p: PayslipDetail }) {
  const { t, tx, locale } = useI18n()
  const c = p.company
  const e = p.employee
  const irg = Number(p.income_tax) + Number(p.flat_tax)
  return (
    <article className="card overflow-hidden">
      <div className="flex flex-wrap justify-between gap-6 border-b border-stone p-6">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-coffee">{t('payslip.title')}</p>
          <h2 className="mt-1 text-xl font-semibold">{monthLabel(p.year, p.month)}</h2>
          {c && (
            <div className="mt-4 text-sm text-muted">
              <p className="font-medium text-espresso">{locale === 'ar' && c.name_ar ? c.name_ar : `${c.name} ${c.legal_form}`}</p>
              {c.address && <p>{c.address}{c.city ? `, ${c.city}` : ''}</p>}
              <p className="text-xs" dir="ltr">{[c.nif && `NIF ${c.nif}`, c.nis && `NIS ${c.nis}`, c.rc && `RC ${c.rc}`, c.cnas_number && `CNAS ${c.cnas_number}`].filter(Boolean).join(' · ')}</p>
            </div>
          )}
        </div>
        <div className="min-w-64 rounded-xl bg-sand/70 p-4 text-sm">
          <p className="font-semibold">{e.full_name}</p>
          {e.address && <p className="text-muted">{e.address}{e.city ? `, ${e.city}` : ''}</p>}
          <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-xs">
            <dt className="text-muted">{t('field.employee_number')}</dt><dd>{e.employee_number || '—'}</dd>
            <dt className="text-muted">{t('field.job_title')}</dt><dd>{p.job_title || '—'}</dd>
            {p.qualification && <><dt className="text-muted">{t('field.qualification')}</dt><dd>{p.qualification}</dd></>}
            {p.department && <><dt className="text-muted">{t('field.department')}</dt><dd>{p.department}</dd></>}
            <dt className="text-muted">{t('field.contract_type')}</dt><dd>{tx(`contract.${e.contract_type}`, e.contract_type)}</dd>
            <dt className="text-muted">{t('field.hire_date')}</dt><dd>{date(e.hire_date)}</dd>
            <dt className="text-muted">{t('field.social_security_number')}</dt><dd dir="ltr" className="text-start">{e.social_security_number || '—'}</dd>
            <dt className="text-muted">{t('field.nin')}</dt><dd dir="ltr" className="text-start">{e.nin || '—'}</dd>
            <dt className="text-muted">{t('field.marital_status')}</dt>
            <dd>{tx(`marital.${e.marital_status}`, e.marital_status)} · {t('payslip.children', { n: e.children_count })}</dd>
          </dl>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[680px] text-sm">
          <thead className="table-head">
            <tr>
              <th className="px-6 py-2.5">{t('payslip.item')}</th>
              <th className="px-3 py-2.5 text-end">{t('payslip.base')}</th>
              <th className="px-3 py-2.5 text-end">{t('payslip.rate')}</th>
              <th className="px-3 py-2.5 text-end">{t('payslip.amount')}</th>
              <th className="px-6 py-2.5 text-end">{t('payslip.employerShare')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone">
            {p.lines.map((l, i) => (
              <tr key={i}>
                <td className="px-6 py-2.5">
                  <span className="me-2 text-xs text-muted">{l.code}</span>
                  {locale === 'ar' && l.label_ar ? l.label_ar : l.label}
                </td>
                <td className="px-3 py-2.5 text-end tabular-nums">
                  {l.code === 'R100' ? `${num(l.base)} ${t('unit.hours')}` : l.kind === 'deduction' ? `${num(l.base)} ${t('unit.days')}` : amount(l.base)}
                </td>
                <td className="px-3 py-2.5 text-end tabular-nums">
                  {l.rate ? (l.kind === 'contribution' || l.kind === 'tax' ? <span dir="ltr">{num(l.rate)} %</span> : money(l.rate, false)) : ''}
                </td>
                <td className={`px-3 py-2.5 text-end tabular-nums ${Number(l.employee_amount) < 0 ? 'text-rose-ink' : ''}`} dir="ltr">
                  {amount(l.employee_amount)}
                </td>
                <td className="px-6 py-2.5 text-end tabular-nums text-muted">{amount(l.employer_amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid gap-6 border-t border-stone p-6 md:grid-cols-2">
        <dl className="grid grid-cols-[1fr_auto] gap-y-1.5 text-sm">
          <dt className="text-muted">{t('payslip.gross')}</dt><dd className="text-end tabular-nums">{money(p.gross_salary)}</dd>
          <dt className="text-muted">{t('payslip.employeeContrib')}</dt><dd className="text-end tabular-nums">- {money(p.social_contributions)}</dd>
          <dt className="text-muted">{t('payslip.taxable')}</dt><dd className="text-end tabular-nums">{money(p.taxable_salary)}</dd>
          <dt className="text-muted">{t('payslip.irg')}</dt><dd className="text-end tabular-nums">- {money(irg)}</dd>
          {Number(p.non_taxable) > 0 && <><dt className="text-muted">{t('payslip.nonTaxable')}</dt><dd className="text-end tabular-nums">+ {money(p.non_taxable)}</dd></>}
          <dt className="text-muted">{t('payslip.workedDays')}</dt><dd className="text-end">{num(p.worked_days)} · {num(p.worked_hours)} {t('unit.hours')}</dd>
          {Number(p.unpaid_days) > 0 && <><dt className="text-muted">{t('payslip.unpaidDays')}</dt><dd className="text-end">{num(p.unpaid_days)} {t('unit.days')}</dd></>}
        </dl>
        <div className="flex flex-col justify-between gap-4">
          <div className="rounded-xl bg-coffee p-5 text-white">
            <p className="text-xs uppercase tracking-wider text-white/70">{t('payslip.net')}</p>
            <p className="mt-1 text-3xl font-semibold tabular-nums">{money(p.net_salary)}</p>
            <p className="mt-2 text-xs text-white/70">
              {tx(`payment.${e.payment_method}`, e.payment_method)}
              {e.payment_method === 'transfer' && e.iban && <> · {e.bank_name} <span dir="ltr">{e.iban}</span></>}
            </p>
          </div>
          <p className="text-xs text-muted">
            {t('payslip.employerCost', { cost: money(p.employer_cost), contrib: money(p.employer_contributions) })}
          </p>
        </div>
      </div>
    </article>
  )
}
