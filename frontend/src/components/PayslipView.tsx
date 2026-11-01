import type { PayslipDetail } from '@/lib/types'
import { date, money, monthLabel, num } from '@/lib/format'

function amount(v: string | null | undefined) {
  if (v === null || v === undefined || Number(v) === 0) return ''
  return money(v, false)
}

export default function PayslipView({ p }: { p: PayslipDetail }) {
  const c = p.company
  return (
    <article className="card overflow-hidden">
      <div className="flex flex-wrap justify-between gap-6 border-b border-stone p-6">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-coffee">Bulletin de paie</p>
          <h2 className="mt-1 text-xl font-semibold">{monthLabel(p.year, p.month)}</h2>
          {c && (
            <div className="mt-4 text-sm text-muted">
              <p className="font-medium text-espresso">{c.name} {c.legal_form}</p>
              {c.address && <p>{c.address}{c.city ? `, ${c.city}` : ''}</p>}
              <p className="text-xs">{[c.nif && `NIF ${c.nif}`, c.nis && `NIS ${c.nis}`, c.cnas_number && `CNAS ${c.cnas_number}`].filter(Boolean).join(' · ')}</p>
            </div>
          )}
        </div>
        <div className="min-w-64 rounded-xl bg-sand/70 p-4 text-sm">
          <p className="font-semibold">{p.employee.full_name}</p>
          {p.employee.address && <p className="text-muted">{p.employee.address}{p.employee.city ? `, ${p.employee.city}` : ''}</p>}
          <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-xs">
            <dt className="text-muted">Matricule</dt><dd>{p.employee.employee_number || '—'}</dd>
            <dt className="text-muted">Poste</dt><dd>{p.job_title || '—'}</dd>
            {p.department && <><dt className="text-muted">Service</dt><dd>{p.department}</dd></>}
            <dt className="text-muted">Contrat</dt><dd>{p.employee.contract_type}</dd>
            <dt className="text-muted">Entrée</dt><dd>{date(p.employee.hire_date)}</dd>
            <dt className="text-muted">N° SS</dt><dd>{p.employee.social_security_number || '—'}</dd>
          </dl>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead className="table-head">
            <tr>
              <th className="px-6 py-2.5">Rubrique</th>
              <th className="px-3 py-2.5 text-right">Base</th>
              <th className="px-3 py-2.5 text-right">Taux</th>
              <th className="px-3 py-2.5 text-right">Gain / Retenue</th>
              <th className="px-6 py-2.5 text-right">Part employeur</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone">
            {p.lines.map((l, i) => (
              <tr key={i}>
                <td className="px-6 py-2.5">
                  <span className="mr-2 text-xs text-muted">{l.code}</span>{l.label}
                </td>
                <td className="px-3 py-2.5 text-right tabular-nums">{l.kind === 'deduction' ? `${num(l.base)} j` : amount(l.base)}</td>
                <td className="px-3 py-2.5 text-right tabular-nums">
                  {l.rate ? (l.kind === 'contribution' ? `${num(l.rate)} %` : money(l.rate, false)) : ''}
                </td>
                <td className={`px-3 py-2.5 text-right tabular-nums ${Number(l.employee_amount) < 0 ? 'text-rose-ink' : ''}`}>
                  {amount(l.employee_amount)}
                </td>
                <td className="px-6 py-2.5 text-right tabular-nums text-muted">{amount(l.employer_amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid gap-6 border-t border-stone p-6 md:grid-cols-2">
        <dl className="grid grid-cols-[1fr_auto] gap-y-1.5 text-sm">
          <dt className="text-muted">Salaire brut</dt><dd className="text-right tabular-nums">{money(p.gross_salary)}</dd>
          <dt className="text-muted">Cotisations salariales</dt><dd className="text-right tabular-nums">- {money(p.social_contributions)}</dd>
          <dt className="text-muted">Salaire imposable</dt><dd className="text-right tabular-nums">{money(p.taxable_salary)}</dd>
          <dt className="text-muted">IRG retenu</dt><dd className="text-right tabular-nums">- {money(p.income_tax)}</dd>
          <dt className="text-muted">Jours travaillés</dt><dd className="text-right">{num(p.worked_days)}</dd>
          {Number(p.unpaid_days) > 0 && <><dt className="text-muted">Absences non rémunérées</dt><dd className="text-right">{num(p.unpaid_days)} j</dd></>}
        </dl>
        <div className="flex flex-col justify-between gap-4">
          <div className="rounded-xl bg-coffee p-5 text-white">
            <p className="text-xs uppercase tracking-wider text-white/70">Net à payer</p>
            <p className="mt-1 text-3xl font-semibold tabular-nums">{money(p.net_salary)}</p>
            {p.employee.iban && <p className="mt-2 text-xs text-white/70">Virement · {p.employee.bank_name} {p.employee.iban}</p>}
          </div>
          <p className="text-xs text-muted">
            Coût total employeur : {money(p.employer_cost)} (dont {money(p.employer_contributions)} de cotisations patronales)
          </p>
        </div>
      </div>
    </article>
  )
}
