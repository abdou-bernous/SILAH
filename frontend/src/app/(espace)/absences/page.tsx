'use client'
import { useEffect, useState } from 'react'
import { CalendarDaysIcon, PaperClipIcon, PlusIcon } from '@heroicons/react/24/outline'
import api, { downloadFile, errorMessage } from '@/lib/api'
import { useFetch } from '@/lib/useFetch'
import { useI18n } from '@/lib/i18n'
import { date, isoDate, num } from '@/lib/format'
import type { Balance, Choice, LeaveRequest } from '@/lib/types'
import Card, { Alert, EmptyState, PageHeader, Spinner } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { StatusBadge } from '@/components/ui/Badge'
import Modal from '@/components/ui/Modal'
import Field from '@/components/ui/Field'
import BalanceCard from '@/components/BalanceCard'
import TeamCalendar from '@/components/TeamCalendar'

const EMPTY = { leave_type: 'annual', start_date: '', end_date: '', start_half: false, end_half: false, reason: '' }

function NewLeaveModal({ open, onClose, onCreated, types }: {
  open: boolean; onClose: () => void; onCreated: () => void; types: Choice[]
}) {
  const { t, tx } = useI18n()
  const [form, setForm] = useState(EMPTY)
  const [file, setFile] = useState<File | null>(null)
  const [days, setDays] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => { if (open) { setForm(EMPTY); setFile(null); setError(''); setDays(null) } }, [open])

  useEffect(() => {
    if (!form.start_date || !form.end_date || form.end_date < form.start_date) { setDays(null); return }
    const params = new URLSearchParams({
      start: form.start_date, end: form.end_date,
      start_half: form.start_half ? '1' : '0', end_half: form.end_half ? '1' : '0',
    })
    api.get(`/leaves/preview/?${params}`).then((r) => setDays(r.data.days)).catch(() => setDays(null))
  }, [form.start_date, form.end_date, form.start_half, form.end_half])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const fd = new FormData()
      Object.entries(form).forEach(([k, v]) => fd.append(k, String(v)))
      if (file) fd.append('attachment', file)
      await api.post('/leaves/', fd)
      onCreated()
      onClose()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const sameDay = form.start_date && form.start_date === form.end_date

  return (
    <Modal open={open} onClose={onClose} title={t('leave.newTitle')}>
      <form onSubmit={submit} className="space-y-4">
        {error && <Alert>{error}</Alert>}
        <Field label={t('leave.type')}>
          <select className="input" value={form.leave_type} onChange={(e) => setForm({ ...form, leave_type: e.target.value })}>
            {types.map((ty) => <option key={ty.value} value={ty.value}>{tx(`leaveType.${ty.value}`, ty.label)}</option>)}
          </select>
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Field label={t('leave.from')}>
              <input type="date" required className="input" value={form.start_date}
                onChange={(e) => setForm({ ...form, start_date: e.target.value, end_date: form.end_date && form.end_date >= e.target.value ? form.end_date : e.target.value })} />
            </Field>
            <label className="mt-2 flex items-center gap-2 text-xs text-muted">
              <input type="checkbox" checked={form.start_half} onChange={(e) => setForm({ ...form, start_half: e.target.checked })} />
              {t('leave.startHalf')}
            </label>
          </div>
          <div>
            <Field label={t('leave.to')}>
              <input type="date" required min={form.start_date} className="input" value={form.end_date}
                onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
            </Field>
            {!sameDay && (
              <label className="mt-2 flex items-center gap-2 text-xs text-muted">
                <input type="checkbox" checked={form.end_half} onChange={(e) => setForm({ ...form, end_half: e.target.checked })} />
                {t('leave.endHalf')}
              </label>
            )}
          </div>
        </div>
        {days !== null && (
          <p className="rounded-lg bg-sand px-3 py-2 text-sm">
            {t('leave.duration')} <strong>{t('leave.workingDays', { n: num(days) })}</strong>
          </p>
        )}
        <Field label={t('leave.comment')}>
          <textarea className="input" rows={2} value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
        </Field>
        <Field label={t('leave.attachment')} hint={t('leave.attachmentHint')}>
          <input type="file" className="input file:me-3 file:rounded file:border-0 file:bg-sand file:px-2 file:py-1 file:text-xs"
            onChange={(e) => setFile(e.target.files?.[0] || null)} />
        </Field>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose}>{t('common.cancel')}</Button>
          <Button type="submit" disabled={saving || days === null || Number(days) === 0}>
            {saving ? t('common.sending') : t('leave.submit')}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export default function LeavesPage() {
  const { t, tx } = useI18n()
  const [tab, setTab] = useState<'requests' | 'calendar'>('requests')
  const [open, setOpen] = useState(false)
  const { data: balances, reload: reloadBalances } = useFetch<Balance[]>('/leaves/balances/')
  const { data: types } = useFetch<Choice[]>('/leaves/types/')
  const { data, loading, reload } = useFetch<LeaveRequest[]>('/leaves/')
  const [error, setError] = useState('')

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get('nouvelle')) setOpen(true)
  }, [])

  const refresh = () => { reload(); reloadBalances() }

  const cancel = async (l: LeaveRequest) => {
    if (!confirm(t('leave.confirmCancel'))) return
    try {
      await api.post(`/leaves/${l.id}/cancel/`)
      refresh()
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const today = isoDate(new Date())

  return (
    <div className="space-y-6">
      <PageHeader title={t('leave.title')} subtitle={t('leave.subtitle')}
        actions={<Button onClick={() => setOpen(true)}><PlusIcon className="h-4 w-4" /> {t('common.newRequest')}</Button>} />

      <div className="grid gap-4 sm:grid-cols-2">
        {balances?.map((b) => <BalanceCard key={b.leave_type} balance={b} />)}
      </div>

      <div className="flex gap-1 border-b border-stone">
        {([['requests', t('leave.myRequests')], ['calendar', t('leave.teamCalendar')]] as const).map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm ${tab === k ? 'border-coffee font-medium text-espresso' : 'border-transparent text-muted hover:text-espresso'}`}>
            {l}
          </button>
        ))}
      </div>

      {error && <Alert>{error}</Alert>}

      {tab === 'calendar' ? <TeamCalendar /> : (
        <Card>
          {loading ? <Spinner /> : !data || data.length === 0 ? (
            <EmptyState icon={<CalendarDaysIcon />} title={t('leave.empty')}>{t('common.requestsAppearHere')}</EmptyState>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-sm">
                <thead className="table-head">
                  <tr>
                    <th className="px-5 py-2.5">{t('common.type')}</th>
                    <th className="px-3 py-2.5">{t('common.period')}</th>
                    <th className="px-3 py-2.5 text-end">{t('common.days')}</th>
                    <th className="px-3 py-2.5">{t('common.status')}</th>
                    <th className="px-5 py-2.5" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone">
                  {data.map((l) => (
                    <tr key={l.id}>
                      <td className="px-5 py-3">
                        <p className="font-medium">{tx(`leaveType.${l.leave_type}`, l.leave_type_label)}</p>
                        {l.reason && <p className="max-w-56 truncate text-xs text-muted">{l.reason}</p>}
                      </td>
                      <td className="px-3 py-3">
                        {date(l.start_date)}{l.start_half && ` (${t('leave.afternoon')})`} <span className="inline-block rtl:rotate-180">→</span> {date(l.end_date)}{l.end_half && ` (${t('leave.morning')})`}
                      </td>
                      <td className="px-3 py-3 text-end tabular-nums">{num(l.days)}</td>
                      <td className="px-3 py-3">
                        <StatusBadge status={l.status} />
                        {l.review_comment && <p className="mt-1 max-w-48 text-xs text-muted">« {l.review_comment} »</p>}
                        {l.reviewer_name && l.status !== 'pending' && <p className="text-[11px] text-muted">{t('common.by', { name: l.reviewer_name })}</p>}
                      </td>
                      <td className="px-5 py-3 text-end">
                        <div className="flex justify-end gap-1">
                          {l.has_attachment && (
                            <button onClick={() => downloadFile(`/leaves/${l.id}/attachment/`)} className="rounded-lg p-1.5 text-muted hover:bg-sand" aria-label={t('leave.attachmentShort')}>
                              <PaperClipIcon className="h-4 w-4" />
                            </button>
                          )}
                          {(l.status === 'pending' || (l.status === 'approved' && l.start_date > today)) && (
                            <Button size="sm" variant="ghost" onClick={() => cancel(l)}>{t('common.cancel')}</Button>
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
      )}

      <NewLeaveModal open={open} onClose={() => setOpen(false)} onCreated={refresh} types={types || []} />
    </div>
  )
}
