'use client'
import { useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { ArrowLeftIcon } from '@heroicons/react/24/outline'
import api, { errorMessage } from '@/lib/api'
import { useFetch } from '@/lib/useFetch'
import { date, money, monthLabel, num } from '@/lib/format'
import type { Balance, DocumentItem, Employee, PayslipSummary } from '@/lib/types'
import Card, { Alert, PageHeader, Spinner } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { StatusBadge } from '@/components/ui/Badge'
import EmployeeForm from '@/components/EmployeeForm'
import { HrOnly } from '@/components/AppShell'

function BalancesEditor({ employeeId }: { employeeId: number }) {
  const year = new Date().getFullYear()
  const { data, reload } = useFetch<Balance[]>(`/employees/${employeeId}/balances/?year=${year}`)
  const [edit, setEdit] = useState<Record<string, string>>({})
  const [msg, setMsg] = useState('')

  const save = async (lt: string) => {
    try {
      await api.post(`/employees/${employeeId}/balances/`, { year, leave_type: lt, allotted: edit[lt] })
      setEdit((e) => { const n = { ...e }; delete n[lt]; return n })
      reload()
      setMsg('')
    } catch (err) { setMsg(errorMessage(err)) }
  }

  return (
    <Card title={`Compteurs de congés ${year}`}>
      {msg && <div className="p-3"><Alert>{msg}</Alert></div>}
      <ul className="divide-y divide-stone">
        {data?.map((b) => (
          <li key={b.leave_type} className="flex flex-wrap items-center gap-3 px-5 py-3 text-sm">
            <span className="flex-1 font-medium">{b.label}</span>
            <span className="text-xs text-muted">{num(b.taken)} pris · {num(b.pending)} en attente · <strong className="text-espresso">{num(b.remaining)} restants</strong></span>
            {edit[b.leave_type] !== undefined ? (
              <span className="flex items-center gap-1">
                <input type="number" step="0.5" min="0" className="input w-24" value={edit[b.leave_type]}
                  onChange={(e) => setEdit({ ...edit, [b.leave_type]: e.target.value })} />
                <Button size="sm" onClick={() => save(b.leave_type)}>OK</Button>
              </span>
            ) : (
              <Button size="sm" variant="outline" onClick={() => setEdit({ ...edit, [b.leave_type]: String(Number(b.allotted)) })}>
                Acquis : {num(b.allotted)} j
              </Button>
            )}
          </li>
        ))}
      </ul>
    </Card>
  )
}

export default function EmployeeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data, loading, setData } = useFetch<Employee>(`/employees/${id}/`)
  const { data: payslips } = useFetch<PayslipSummary[]>(`/payslips/?scope=all&employee=${id}`)
  const { data: docs } = useFetch<DocumentItem[]>(`/documents/?scope=all&employee=${id}`)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  if (loading) return <Spinner />
  if (!data) return <Alert>Salarié introuvable.</Alert>

  const toggleActive = async () => {
    try {
      if (data.is_active) {
        if (!confirm(`Désactiver le compte de ${data.full_name} ? Il ne pourra plus se connecter, ses bulletins sont conservés.`)) return
        await api.delete(`/employees/${data.id}/`)
        setData({ ...data, is_active: false })
      } else {
        const r = await api.patch(`/employees/${data.id}/`, { is_active: true })
        setData(r.data)
      }
    } catch (err) { setError(errorMessage(err)) }
  }

  return (
    <HrOnly>
      <div className="mb-2"><Button variant="ghost" href="/admin/salaries"><ArrowLeftIcon className="h-4 w-4" /> Salariés</Button></div>
      <PageHeader title={data.full_name} subtitle={`${data.job_title || ''}${data.department ? ` · ${data.department}` : ''}`}
        actions={<Button variant={data.is_active ? 'danger' : 'outline'} onClick={toggleActive}>{data.is_active ? 'Désactiver le compte' : 'Réactiver le compte'}</Button>} />
      <div className="space-y-6">
        {saved && <Alert tone="sage">Dossier enregistré.</Alert>}
        {error && <Alert>{error}</Alert>}
        {!data.is_active && <Alert tone="honey">Ce compte est désactivé.</Alert>}
        <Card title="Dossier salarié">
          <div className="p-5">
            <EmployeeForm key={data.id} initial={data} onSaved={(e) => { setData(e); setSaved(true); window.scrollTo({ top: 0, behavior: 'smooth' }) }} />
          </div>
        </Card>
        <div className="grid gap-6 lg:grid-cols-2">
          <BalancesEditor employeeId={data.id} />
          <Card title="Bulletins">
            <ul className="divide-y divide-stone">
              {payslips?.length ? payslips.map((p) => (
                <li key={p.id} className="flex items-center justify-between gap-3 px-5 py-2.5 text-sm">
                  <Link href={`/bulletins/${p.id}`} className="font-medium hover:text-coffee">{monthLabel(p.year, p.month)}</Link>
                  <span className="flex items-center gap-3"><span className="tabular-nums">{money(p.net_salary)}</span><StatusBadge status={p.status} /></span>
                </li>
              )) : <li className="px-5 py-6 text-center text-sm text-muted">Aucun bulletin</li>}
            </ul>
          </Card>
          <Card className="lg:col-span-2" title="Documents personnels" action={<Link href="/admin/documents" className="text-xs font-medium text-coffee hover:underline">Déposer un document</Link>}>
            <ul className="divide-y divide-stone">
              {docs?.filter((d) => d.employee).length ? docs.filter((d) => d.employee).map((d) => (
                <li key={d.id} className="flex items-center justify-between gap-3 px-5 py-2.5 text-sm">
                  <span>{d.title} <span className="text-xs text-muted">· {d.category_label}</span></span>
                  <span className="text-xs text-muted">{date(d.created_at)} · {d.viewed_at ? 'consulté' : 'non consulté'}</span>
                </li>
              )) : <li className="px-5 py-6 text-center text-sm text-muted">Aucun document</li>}
            </ul>
          </Card>
        </div>
      </div>
    </HrOnly>
  )
}
