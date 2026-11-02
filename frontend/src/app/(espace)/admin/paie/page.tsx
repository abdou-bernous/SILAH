'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ArrowDownTrayIcon, CalculatorIcon, PaperAirplaneIcon, PencilSquareIcon, TrashIcon } from '@heroicons/react/24/outline'
import api, { downloadFile, errorMessage } from '@/lib/api'
import { useFetch } from '@/lib/useFetch'
import { useI18n } from '@/lib/i18n'
import { months, money, monthLabel } from '@/lib/format'
import type { PayrollTotals, PayslipSummary } from '@/lib/types'
import Card, { Alert, EmptyState, PageHeader, Spinner, Stat } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import Badge, { StatusBadge } from '@/components/ui/Badge'
import Field from '@/components/ui/Field'
import { HrOnly } from '@/components/AppShell'
import MonthlyVariablesCard from '@/components/MonthlyVariablesCard'
import BonusEditor, { bonusPayload, type Bonus } from '@/components/BonusEditor'
import CorrectionModal from '@/components/CorrectionModal'

type Issue = { employee: string; reason?: string; message?: string }

export default function PayrollPage() {
  const { t } = useI18n()
  const router = useRouter()
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [bonuses, setBonuses] = useState<Bonus[]>([])
  const [includeExpenses, setIncludeExpenses] = useState(true)
  const [msg, setMsg] = useState<{ tone: 'sage' | 'rose' | 'honey'; text: string; details?: string[] } | null>(null)
  const [busy, setBusy] = useState(false)
  const [correcting, setCorrecting] = useState<PayslipSummary | null>(null)
  const { data, loading, reload } = useFetch<PayslipSummary[]>(`/payslips/?scope=all&year=${year}&month=${month}`)
  const { data: summary, reload: reloadSummary } = useFetch<PayrollTotals>(`/payslips/summary/?year=${year}&month=${month}`)

  // The result of a run belongs to its month: it must not stay on screen once another month is shown.
  useEffect(() => { setMsg(null) }, [year, month])

  // Corrections are published one by one, from their own page.
  const drafts = data?.filter((p) => p.status === 'draft' && p.replaces === null) || []
  const refresh = () => { reload(); reloadSummary() }

  const run = async () => {
    setBusy(true); setMsg(null)
    try {
      const r = await api.post('/payslips/run/', {
        year, month, include_expenses: includeExpenses, bonuses: bonusPayload(bonuses),
      })
      const skipped = r.data.skipped as Issue[]
      const warnings = r.data.warnings as Issue[]
      setMsg({
        tone: skipped.length || warnings.length ? 'honey' : 'sage',
        text: t('payroll.computed', { n: r.data.created.length }),
        details: [
          ...skipped.map((s) => `${t('payroll.skipped')} ${s.employee} : ${s.reason}`),
          ...warnings.map((w) => `${w.employee} : ${w.message}`),
        ],
      })
      refresh()
    } catch (err) { setMsg({ tone: 'rose', text: errorMessage(err) }) } finally { setBusy(false) }
  }

  const publishAll = async () => {
    if (!confirm(t('payroll.confirmPublish', { n: drafts.length }))) return
    setBusy(true)
    try {
      const r = await api.post('/payslips/publish_month/', { year, month })
      setMsg({ tone: 'sage', text: t('payroll.published', { n: r.data.published }) })
      refresh()
    } catch (err) { setMsg({ tone: 'rose', text: errorMessage(err) }) } finally { setBusy(false) }
  }

  const publish = async (p: PayslipSummary) => {
    try { await api.post(`/payslips/${p.id}/publish/`) } catch (err) { setMsg({ tone: 'rose', text: errorMessage(err) }) }
    refresh()
  }
  const remove = async (p: PayslipSummary) => {
    if (!confirm(t('payroll.confirmDelete'))) return
    try { await api.delete(`/payslips/${p.id}/`) } catch (err) { setMsg({ tone: 'rose', text: errorMessage(err) }) }
    refresh()
  }

  const irgTotal = summary ? Number(summary.irg || 0) + Number(summary.irg_flat || 0) : 0
  const cnasTotal = summary ? Number(summary.cnas || 0) + Number(summary.cnas_employer || 0) : 0

  return (
    <HrOnly>
      <PageHeader title={t('nav.payroll')} subtitle={t('payroll.subtitle')} />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
        <Card title={t('payroll.prepare')}>
          <div className="space-y-4 p-5">
            <div className="grid grid-cols-2 gap-3">
              <Field label={t('common.month')}>
                <select className="input" value={month} onChange={(e) => setMonth(Number(e.target.value))}>
                  {months().map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
                </select>
              </Field>
              <Field label={t('common.year')}>
                <input type="number" className="input" value={year} onChange={(e) => setYear(Number(e.target.value))} />
              </Field>
            </div>
            <div>
              <p className="label">{t('payroll.variables')}</p>
              <BonusEditor value={bonuses} onChange={setBonuses} />
            </div>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={includeExpenses}
              onChange={(e) => setIncludeExpenses(e.target.checked)} /> {t('payroll.includeExpenses')}</label>
            <p className="text-xs text-muted">{t('payroll.help')}</p>
            <Button className="w-full" onClick={run} disabled={busy}><CalculatorIcon className="h-4 w-4" /> {t('payroll.compute', { month: monthLabel(year, month) })}</Button>
          </div>
        </Card>

        <div className="min-w-0 space-y-4">
          <MonthlyVariablesCard year={year} month={month} />
          {msg && (
            <Alert tone={msg.tone}>
              {msg.text}
              {!!msg.details?.length && <ul className="mt-1 list-disc ps-5 text-xs">{msg.details.map((d, i) => <li key={i}>{d}</li>)}</ul>}
            </Alert>
          )}
          {summary && summary.count > 0 && (
            <>
              <div className="card grid gap-6 p-5 sm:grid-cols-3">
                <Stat label={t('payroll.grossTotal')} value={money(summary.gross)} />
                <Stat label={t('payroll.netTotal')} value={money(summary.net)} />
                <Stat label={t('payroll.costTotal')} value={money(summary.cost)} />
              </div>
              <Card title={t('payroll.declarations')}>
                {!!summary.drafts && (
                  <p className="border-b border-stone bg-honey/50 px-5 py-2.5 text-xs">{t('payroll.provisional', { n: summary.drafts })}</p>
                )}
                <div className="grid gap-4 p-5 text-sm sm:grid-cols-2">
                  <div className="rounded-xl bg-sand/70 p-4">
                    <p className="font-semibold">{t('payroll.g50')}</p>
                    <dl className="mt-2 grid grid-cols-[1fr_auto] gap-y-1 text-xs">
                      <dt className="text-muted">{t('payroll.irgScale')}</dt><dd className="text-end tabular-nums">{money(summary.irg)}</dd>
                      <dt className="text-muted">{t('payroll.irgFlat')}</dt><dd className="text-end tabular-nums">{money(summary.irg_flat)}</dd>
                      <dt className="font-medium">{t('common.total')}</dt><dd className="text-end font-semibold tabular-nums">{money(irgTotal)}</dd>
                    </dl>
                    <p className="mt-2 text-[11px] text-muted">{t('payroll.g50Hint')}</p>
                  </div>
                  <div className="rounded-xl bg-sand/70 p-4">
                    <p className="font-semibold">{t('payroll.cnas')}</p>
                    <dl className="mt-2 grid grid-cols-[1fr_auto] gap-y-1 text-xs">
                      <dt className="text-muted">{t('payroll.cnasEmployee')}</dt><dd className="text-end tabular-nums">{money(summary.cnas)}</dd>
                      <dt className="text-muted">{t('payroll.cnasEmployer')}</dt><dd className="text-end tabular-nums">{money(summary.cnas_employer)}</dd>
                      <dt className="font-medium">{t('common.total')}</dt><dd className="text-end font-semibold tabular-nums">{money(cnasTotal)}</dd>
                    </dl>
                    <p className="mt-2 text-[11px] text-muted">{t('payroll.cnasHint')}</p>
                  </div>
                </div>
              </Card>
            </>
          )}
          <Card title={t('payroll.listTitle', { month: monthLabel(year, month) })}
            action={drafts.length > 0 && <Button size="sm" onClick={publishAll} disabled={busy}><PaperAirplaneIcon className="h-4 w-4 rtl:-scale-x-100" /> {t('payroll.publishAll', { n: drafts.length })}</Button>}>
            {loading ? <Spinner /> : !data?.length ? (
              <EmptyState icon={<CalculatorIcon />} title={t('payroll.empty')}>{t('payroll.emptyHint')}</EmptyState>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[560px] text-sm">
                  <thead className="table-head">
                    <tr>
                      <th className="px-5 py-2.5">{t('role.employee')}</th>
                      <th className="px-3 py-2.5 text-end">{t('payroll.gross')}</th>
                      <th className="px-3 py-2.5 text-end">{t('payroll.net')}</th>
                      <th className="px-3 py-2.5">{t('common.status')}</th>
                      <th className="px-5 py-2.5" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone">
                    {data.map((p) => (
                      <tr key={p.id} className={p.status === 'replaced' ? 'text-muted' : ''}>
                        <td className="px-5 py-3"><Link href={`/bulletins/${p.id}`} className="font-medium hover:text-coffee">{p.employee.full_name}</Link>
                          <p className="text-xs text-muted">{p.employee.job_title}</p></td>
                        <td className="px-3 py-3 text-end tabular-nums">{money(p.gross_salary)}</td>
                        <td className="px-3 py-3 text-end font-medium tabular-nums">
                          {money(p.net_salary)}
                          {p.previous_net !== null && <p className="text-[11px] font-normal text-muted">{t('correct.before', { net: money(p.previous_net) })}</p>}
                        </td>
                        <td className="px-3 py-3">
                          <div className="flex flex-wrap gap-1">
                            <StatusBadge status={p.status} />
                            {p.replaces !== null && <Badge tone="mist">{t('correct.badge')}</Badge>}
                          </div>
                          {p.status === 'published' && <p className="mt-0.5 text-[11px] text-muted">{p.viewed_at ? t('docs.viewed') : t('docs.notViewed')}</p>}
                        </td>
                        <td className="px-5 py-3">
                          <div className="flex justify-end gap-1">
                            <button onClick={() => downloadFile(`/payslips/${p.id}/pdf/`, 'bulletin.pdf')} className="rounded-lg p-1.5 text-muted hover:bg-sand" aria-label="PDF"><ArrowDownTrayIcon className="h-4 w-4" /></button>
                            {p.status === 'draft' && p.replaces === null && <>
                              <button onClick={() => remove(p)} className="rounded-lg p-1.5 text-muted hover:bg-rose hover:text-rose-ink" aria-label={t('common.delete')}><TrashIcon className="h-4 w-4" /></button>
                              <Button size="sm" variant="outline" onClick={() => publish(p)}>{t('payroll.publish')}</Button>
                            </>}
                            {p.status === 'draft' && p.replaces !== null && (
                              <Button size="sm" variant="outline" href={`/bulletins/${p.id}`}>{t('correct.review')}</Button>
                            )}
                            {p.status === 'published' && !p.replaced_by && (
                              <button onClick={() => setCorrecting(p)} className="rounded-lg p-1.5 text-muted hover:bg-sand hover:text-coffee"
                                aria-label={t('correct.action')} title={t('correct.action')}><PencilSquareIcon className="h-4 w-4" /></button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      </div>
      {correcting && (
        <CorrectionModal payslipId={correcting.id} year={correcting.year} month={correcting.month}
          onClose={() => setCorrecting(null)} onDone={(draftId) => router.push(`/bulletins/${draftId}`)} />
      )}
    </HrOnly>
  )
}
