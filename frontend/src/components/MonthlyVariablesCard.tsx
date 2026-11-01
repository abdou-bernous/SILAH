'use client'
import { useEffect, useState } from 'react'
import api, { errorMessage } from '@/lib/api'
import { useFetch } from '@/lib/useFetch'
import { useI18n } from '@/lib/i18n'
import { monthLabel } from '@/lib/format'
import type { MonthlyVariableRow } from '@/lib/types'
import Card, { Alert } from './ui/Card'
import Button from './ui/Button'

/** One row per employee: what changes this month only. Saved before the payroll run. */
export default function MonthlyVariablesCard({ year, month }: { year: number; month: number }) {
  const { t } = useI18n()
  const { data } = useFetch<MonthlyVariableRow[]>(`/payslips/variables/?year=${year}&month=${month}`)
  const [rows, setRows] = useState<MonthlyVariableRow[]>([])
  const [msg, setMsg] = useState<{ tone: 'sage' | 'rose'; text: string } | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => { setRows(data || []); setMsg(null) }, [data])

  const update = (id: number, patch: Partial<MonthlyVariableRow>) =>
    setRows(rows.map((r) => (r.employee === id ? { ...r, ...patch } : r)))

  const save = async () => {
    setSaving(true); setMsg(null)
    try {
      await api.post('/payslips/variables/', { year, month, rows: rows.map(({ full_name: _, ...r }) => r) })
      setMsg({ tone: 'sage', text: t('payroll.varsSaved') })
    } catch (err) { setMsg({ tone: 'rose', text: errorMessage(err) }) } finally { setSaving(false) }
  }

  return (
    <Card title={t('payroll.monthlyVars', { month: monthLabel(year, month) })}
      action={<Button size="sm" variant="outline" onClick={save} disabled={saving || !rows.length}>{t('common.save')}</Button>}>
      <p className="border-b border-stone px-5 py-2.5 text-xs text-muted">{t('payroll.monthlyVarsHint')}</p>
      {msg && <div className="p-3"><Alert tone={msg.tone}>{msg.text}</Alert></div>}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead className="table-head">
            <tr>
              <th className="px-5 py-2.5">{t('role.employee')}</th>
              <th className="px-2 py-2.5">{t('payroll.overtimeHours')}</th>
              <th className="px-2 py-2.5">{t('payroll.overtimeRate')}</th>
              <th className="px-2 py-2.5">{t('payroll.bonusLabel')}</th>
              <th className="px-5 py-2.5">{t('exp.amount')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone">
            {rows.map((r) => (
              <tr key={r.employee}>
                <td className="px-5 py-2 font-medium">{r.full_name}</td>
                <td className="px-2 py-2"><input type="number" min="0" step="0.5" className="input w-20" aria-label={t('payroll.overtimeHours')}
                  value={Number(r.overtime_hours) || ''} onChange={(e) => update(r.employee, { overtime_hours: e.target.value || '0' })} /></td>
                <td className="px-2 py-2"><input type="number" min="50" step="25" className="input w-20" aria-label={t('payroll.overtimeRate')}
                  value={Number(r.overtime_rate)} onChange={(e) => update(r.employee, { overtime_rate: e.target.value })} /></td>
                <td className="px-2 py-2"><input className="input" aria-label={t('payroll.bonusLabel')} value={r.bonus_label}
                  onChange={(e) => update(r.employee, { bonus_label: e.target.value })} /></td>
                <td className="px-5 py-2"><input type="number" min="0" className="input w-28" aria-label={t('exp.amount')}
                  value={Number(r.bonus_amount) || ''} onChange={(e) => update(r.employee, { bonus_amount: e.target.value || '0' })} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
