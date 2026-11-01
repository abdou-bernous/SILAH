'use client'
import { useEffect, useMemo, useState } from 'react'
import { PaperClipIcon, PlusIcon, ReceiptPercentIcon } from '@heroicons/react/24/outline'
import api, { downloadFile, errorMessage } from '@/lib/api'
import { useFetch } from '@/lib/useFetch'
import { useI18n } from '@/lib/i18n'
import { date, isoDate, money } from '@/lib/format'
import type { Choice, Expense } from '@/lib/types'
import Card, { Alert, EmptyState, PageHeader, Spinner, Stat } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { StatusBadge } from '@/components/ui/Badge'
import Modal from '@/components/ui/Modal'
import Field from '@/components/ui/Field'

function NewExpenseModal({ open, onClose, onCreated, categories }: {
  open: boolean; onClose: () => void; onCreated: () => void; categories: Choice[]
}) {
  const { t, tx } = useI18n()
  const empty = { date: isoDate(new Date()), category: 'transport', amount: '', description: '' }
  const [form, setForm] = useState(empty)
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  useEffect(() => { if (open) { setForm(empty); setFile(null); setError('') } }, [open])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const fd = new FormData()
      Object.entries(form).forEach(([k, v]) => fd.append(k, v))
      if (file) fd.append('receipt', file)
      await api.post('/expenses/', fd)
      onCreated()
      onClose()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={t('exp.newTitle')}>
      <form onSubmit={submit} className="space-y-4">
        {error && <Alert>{error}</Alert>}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t('exp.date')}>
            <input type="date" required max={isoDate(new Date())} className="input" value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })} />
          </Field>
          <Field label={t('common.category')}>
            <select className="input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              {categories.map((c) => <option key={c.value} value={c.value}>{tx(`expCat.${c.value}`, c.label)}</option>)}
            </select>
          </Field>
        </div>
        <Field label={t('exp.amount')}>
          <input type="number" min="0.01" step="0.01" required className="input" value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })} />
        </Field>
        <Field label={t('common.description')}>
          <input required maxLength={255} className="input" placeholder={t('exp.placeholder')} value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>
        <Field label={t('exp.receipt')} hint={t('exp.receiptHint')}>
          <input type="file" accept="image/*,application/pdf" className="input file:me-3 file:rounded file:border-0 file:bg-sand file:px-2 file:py-1 file:text-xs"
            onChange={(e) => setFile(e.target.files?.[0] || null)} />
        </Field>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose}>{t('common.cancel')}</Button>
          <Button type="submit" disabled={saving}>{saving ? t('common.sending') : t('common.submit')}</Button>
        </div>
      </form>
    </Modal>
  )
}

export default function ExpensesPage() {
  const { t, tx } = useI18n()
  const [open, setOpen] = useState(false)
  const [error, setError] = useState('')
  const { data, loading, reload } = useFetch<Expense[]>('/expenses/')
  const { data: categories } = useFetch<Choice[]>('/expenses/categories/')

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get('nouvelle')) setOpen(true)
  }, [])

  const totals = useMemo(() => {
    const sum = { pending: 0, approved: 0, paid: 0 }
    for (const e of data || []) if (e.status in sum) sum[e.status as keyof typeof sum] += Number(e.amount)
    return sum
  }, [data])

  const cancel = async (e: Expense) => {
    if (!confirm(t('exp.confirmCancel'))) return
    try { await api.post(`/expenses/${e.id}/cancel/`); reload() } catch (err) { setError(errorMessage(err)) }
  }

  return (
    <div className="space-y-6">
      <PageHeader title={t('exp.title')} subtitle={t('exp.subtitle')}
        actions={<Button onClick={() => setOpen(true)}><PlusIcon className="h-4 w-4" /> {t('exp.new')}</Button>} />

      <div className="card grid gap-6 p-5 sm:grid-cols-3">
        <Stat label={t('exp.pending')} value={money(totals.pending)} />
        <Stat label={t('exp.approved')} value={money(totals.approved)} />
        <Stat label={t('exp.paid')} value={money(totals.paid)} />
      </div>

      {error && <Alert>{error}</Alert>}

      <Card>
        {loading ? <Spinner /> : !data || data.length === 0 ? (
          <EmptyState icon={<ReceiptPercentIcon />} title={t('exp.empty')}>{t('exp.emptyHint')}</EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead className="table-head">
                <tr>
                  <th className="px-5 py-2.5">{t('common.date')}</th>
                  <th className="px-3 py-2.5">{t('exp.expense')}</th>
                  <th className="px-3 py-2.5 text-end">{t('common.amount')}</th>
                  <th className="px-3 py-2.5">{t('common.status')}</th>
                  <th className="px-5 py-2.5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-stone">
                {data.map((e) => (
                  <tr key={e.id}>
                    <td className="px-5 py-3 text-muted">{date(e.date)}</td>
                    <td className="px-3 py-3">
                      <p className="font-medium">{e.description}</p>
                      <p className="text-xs text-muted">{tx(`expCat.${e.category}`, e.category_label)}</p>
                    </td>
                    <td className="px-3 py-3 text-end font-medium tabular-nums">{money(e.amount)}</td>
                    <td className="px-3 py-3">
                      <StatusBadge status={e.status} />
                      {e.review_comment && <p className="mt-1 max-w-48 text-xs text-muted">« {e.review_comment} »</p>}
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex justify-end gap-1">
                        {e.has_receipt && (
                          <button onClick={() => downloadFile(`/expenses/${e.id}/receipt/`)} className="rounded-lg p-1.5 text-muted hover:bg-sand" aria-label={t('leave.attachmentShort')}>
                            <PaperClipIcon className="h-4 w-4" />
                          </button>
                        )}
                        {e.status === 'pending' && <Button size="sm" variant="ghost" onClick={() => cancel(e)}>{t('common.cancel')}</Button>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <NewExpenseModal open={open} onClose={() => setOpen(false)} onCreated={reload} categories={categories || []} />
    </div>
  )
}
