'use client'
import { useState } from 'react'
import Link from 'next/link'
import { ArrowDownTrayIcon, CalculatorIcon, PaperAirplaneIcon, PlusIcon, TrashIcon } from '@heroicons/react/24/outline'
import api, { downloadFile, errorMessage } from '@/lib/api'
import { useFetch } from '@/lib/useFetch'
import { MONTHS, money, monthLabel } from '@/lib/format'
import type { PayslipSummary } from '@/lib/types'
import Card, { Alert, EmptyState, PageHeader, Spinner, Stat } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { StatusBadge } from '@/components/ui/Badge'
import Field from '@/components/ui/Field'
import { HrOnly } from '@/components/AppShell'

type Bonus = { label: string; amount: string; contributory: boolean; taxable: boolean }

export default function PayrollPage() {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [bonuses, setBonuses] = useState<Bonus[]>([])
  const [msg, setMsg] = useState<{ tone: 'sage' | 'rose' | 'honey'; text: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const { data, loading, reload } = useFetch<PayslipSummary[]>(`/payslips/?scope=all&year=${year}&month=${month}`)

  const drafts = data?.filter((p) => p.status === 'draft') || []
  const total = (k: keyof PayslipSummary) => (data || []).reduce((s, p) => s + Number(p[k]), 0)

  const run = async () => {
    setBusy(true); setMsg(null)
    try {
      const r = await api.post('/payslips/run/', {
        year, month, bonuses: bonuses.filter((b) => b.label && Number(b.amount) > 0),
      })
      const skipped = r.data.skipped as { employee: string; reason: string }[]
      setMsg({
        tone: skipped.length ? 'honey' : 'sage',
        text: `${r.data.created.length} bulletin(s) calculé(s) en brouillon.` +
          (skipped.length ? ` Ignorés : ${skipped.map((s) => `${s.employee} (${s.reason})`).join(', ')}.` : ''),
      })
      reload()
    } catch (err) { setMsg({ tone: 'rose', text: errorMessage(err) }) } finally { setBusy(false) }
  }

  const publishAll = async () => {
    if (!confirm(`Publier ${drafts.length} bulletin(s) ? Les salariés seront notifiés et le bulletin ne pourra plus être recalculé.`)) return
    setBusy(true)
    try {
      const r = await api.post('/payslips/publish_month/', { year, month })
      setMsg({ tone: 'sage', text: `${r.data.published} bulletin(s) publié(s).` })
      reload()
    } catch (err) { setMsg({ tone: 'rose', text: errorMessage(err) }) } finally { setBusy(false) }
  }

  const publish = async (p: PayslipSummary) => { await api.post(`/payslips/${p.id}/publish/`); reload() }
  const remove = async (p: PayslipSummary) => {
    if (!confirm('Supprimer ce brouillon ?')) return
    await api.delete(`/payslips/${p.id}/`); reload()
  }

  return (
    <HrOnly>
      <PageHeader title="Paie" subtitle="Calculez les bulletins du mois, vérifiez-les puis publiez-les dans l'espace des salariés." />
      <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
        <Card title="Préparer la paie">
          <div className="space-y-4 p-5">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Mois">
                <select className="input" value={month} onChange={(e) => setMonth(Number(e.target.value))}>
                  {MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
                </select>
              </Field>
              <Field label="Année">
                <input type="number" className="input" value={year} onChange={(e) => setYear(Number(e.target.value))} />
              </Field>
            </div>
            <div>
              <p className="label">Éléments variables (appliqués à tous)</p>
              <div className="space-y-3">
                {bonuses.map((b, i) => (
                  <div key={i} className="rounded-lg border border-stone p-3">
                    <div className="flex gap-2">
                      <input className="input" placeholder="Libellé (ex. prime de rendement)" value={b.label}
                        onChange={(e) => setBonuses(bonuses.map((x, j) => j === i ? { ...x, label: e.target.value } : x))} />
                      <button onClick={() => setBonuses(bonuses.filter((_, j) => j !== i))} className="rounded-lg p-2 text-muted hover:bg-sand" aria-label="Retirer"><TrashIcon className="h-4 w-4" /></button>
                    </div>
                    <input type="number" min="0" className="input mt-2" placeholder="Montant (DA)" value={b.amount}
                      onChange={(e) => setBonuses(bonuses.map((x, j) => j === i ? { ...x, amount: e.target.value } : x))} />
                    <div className="mt-2 flex gap-4 text-xs text-muted">
                      <label className="flex items-center gap-1.5"><input type="checkbox" checked={b.contributory}
                        onChange={(e) => setBonuses(bonuses.map((x, j) => j === i ? { ...x, contributory: e.target.checked } : x))} /> Soumis CNAS</label>
                      <label className="flex items-center gap-1.5"><input type="checkbox" checked={b.taxable}
                        onChange={(e) => setBonuses(bonuses.map((x, j) => j === i ? { ...x, taxable: e.target.checked } : x))} /> Imposable IRG</label>
                    </div>
                  </div>
                ))}
                <Button size="sm" variant="outline" onClick={() => setBonuses([...bonuses, { label: '', amount: '', contributory: true, taxable: true }])}>
                  <PlusIcon className="h-4 w-4" /> Ajouter une prime ou indemnité
                </Button>
              </div>
            </div>
            <p className="text-xs text-muted">Les congés sans solde validés du mois sont déduits automatiquement. Les brouillons existants sont recalculés, les bulletins publiés ne sont jamais modifiés.</p>
            <Button className="w-full" onClick={run} disabled={busy}><CalculatorIcon className="h-4 w-4" /> Calculer {monthLabel(year, month).toLowerCase()}</Button>
          </div>
        </Card>

        <div className="space-y-4">
          {msg && <Alert tone={msg.tone}>{msg.text}</Alert>}
          {data && data.length > 0 && (
            <div className="card grid gap-6 p-5 sm:grid-cols-3">
              <Stat label="Masse salariale brute" value={money(total('gross_salary'))} />
              <Stat label="Total net à payer" value={money(total('net_salary'))} />
              <Stat label="Coût employeur" value={money(total('employer_cost'))} />
            </div>
          )}
          <Card title={`Bulletins — ${monthLabel(year, month)}`}
            action={drafts.length > 0 && <Button size="sm" onClick={publishAll} disabled={busy}><PaperAirplaneIcon className="h-4 w-4" /> Publier les {drafts.length} brouillon(s)</Button>}>
            {loading ? <Spinner /> : !data?.length ? (
              <EmptyState icon={<CalculatorIcon />} title="Aucun bulletin pour ce mois">Lancez le calcul pour générer les brouillons.</EmptyState>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-sm">
                  <thead className="table-head">
                    <tr><th className="px-5 py-2.5">Salarié</th><th className="px-3 py-2.5 text-right">Brut</th><th className="px-3 py-2.5 text-right">Net</th><th className="px-3 py-2.5">Statut</th><th className="px-5 py-2.5" /></tr>
                  </thead>
                  <tbody className="divide-y divide-stone">
                    {data.map((p) => (
                      <tr key={p.id}>
                        <td className="px-5 py-3"><Link href={`/bulletins/${p.id}`} className="font-medium hover:text-coffee">{p.employee.full_name}</Link>
                          <p className="text-xs text-muted">{p.employee.job_title}</p></td>
                        <td className="px-3 py-3 text-right tabular-nums">{money(p.gross_salary)}</td>
                        <td className="px-3 py-3 text-right font-medium tabular-nums">{money(p.net_salary)}</td>
                        <td className="px-3 py-3"><StatusBadge status={p.status} />{p.status === 'published' && <p className="mt-0.5 text-[11px] text-muted">{p.viewed_at ? 'Consulté' : 'Non consulté'}</p>}</td>
                        <td className="px-5 py-3">
                          <div className="flex justify-end gap-1">
                            <button onClick={() => downloadFile(`/payslips/${p.id}/pdf/`, 'bulletin.pdf')} className="rounded-lg p-1.5 text-muted hover:bg-sand" aria-label="PDF"><ArrowDownTrayIcon className="h-4 w-4" /></button>
                            {p.status === 'draft' && <>
                              <button onClick={() => remove(p)} className="rounded-lg p-1.5 text-muted hover:bg-rose hover:text-rose-ink" aria-label="Supprimer"><TrashIcon className="h-4 w-4" /></button>
                              <Button size="sm" variant="outline" onClick={() => publish(p)}>Publier</Button>
                            </>}
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
    </HrOnly>
  )
}
