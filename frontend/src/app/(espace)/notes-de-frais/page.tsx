'use client'
import { useEffect, useMemo, useState } from 'react'
import { PaperClipIcon, PlusIcon, ReceiptPercentIcon } from '@heroicons/react/24/outline'
import api, { downloadFile, errorMessage } from '@/lib/api'
import { useFetch } from '@/lib/useFetch'
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
    <Modal open={open} onClose={onClose} title="Nouvelle note de frais">
      <form onSubmit={submit} className="space-y-4">
        {error && <Alert>{error}</Alert>}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Date de la dépense">
            <input type="date" required max={isoDate(new Date())} className="input" value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })} />
          </Field>
          <Field label="Catégorie">
            <select className="input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              {categories.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </Field>
        </div>
        <Field label="Montant (DA)">
          <input type="number" min="0.01" step="0.01" required className="input" value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })} />
        </Field>
        <Field label="Description">
          <input required maxLength={255} className="input" placeholder="Ex. : taxi aéroport — rendez-vous client" value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>
        <Field label="Justificatif" hint="Photo ou PDF du ticket, 10 Mo maximum.">
          <input type="file" accept="image/*,application/pdf" className="input file:mr-3 file:rounded file:border-0 file:bg-sand file:px-2 file:py-1 file:text-xs"
            onChange={(e) => setFile(e.target.files?.[0] || null)} />
        </Field>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose}>Annuler</Button>
          <Button type="submit" disabled={saving}>{saving ? 'Envoi…' : 'Soumettre'}</Button>
        </div>
      </form>
    </Modal>
  )
}

export default function ExpensesPage() {
  const [open, setOpen] = useState(false)
  const [error, setError] = useState('')
  const { data, loading, reload } = useFetch<Expense[]>('/expenses/')
  const { data: categories } = useFetch<Choice[]>('/expenses/categories/')

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get('nouvelle')) setOpen(true)
  }, [])

  const totals = useMemo(() => {
    const t = { pending: 0, approved: 0, paid: 0 }
    for (const e of data || []) if (e.status in t) t[e.status as keyof typeof t] += Number(e.amount)
    return t
  }, [data])

  const cancel = async (e: Expense) => {
    if (!confirm('Annuler cette note de frais ?')) return
    try { await api.post(`/expenses/${e.id}/cancel/`); reload() } catch (err) { setError(errorMessage(err)) }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Notes de frais" subtitle="Déclarez vos dépenses professionnelles et suivez leur remboursement."
        actions={<Button onClick={() => setOpen(true)}><PlusIcon className="h-4 w-4" /> Nouvelle note</Button>} />

      <div className="card grid gap-6 p-5 sm:grid-cols-3">
        <Stat label="En attente de validation" value={money(totals.pending)} />
        <Stat label="Validées, à rembourser" value={money(totals.approved)} />
        <Stat label="Remboursées" value={money(totals.paid)} />
      </div>

      {error && <Alert>{error}</Alert>}

      <Card>
        {loading ? <Spinner /> : !data || data.length === 0 ? (
          <EmptyState icon={<ReceiptPercentIcon />} title="Aucune note de frais">Ajoutez votre première dépense avec le bouton « Nouvelle note ».</EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead className="table-head">
                <tr>
                  <th className="px-5 py-2.5">Date</th>
                  <th className="px-3 py-2.5">Dépense</th>
                  <th className="px-3 py-2.5 text-right">Montant</th>
                  <th className="px-3 py-2.5">Statut</th>
                  <th className="px-5 py-2.5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-stone">
                {data.map((e) => (
                  <tr key={e.id}>
                    <td className="px-5 py-3 text-muted">{date(e.date)}</td>
                    <td className="px-3 py-3">
                      <p className="font-medium">{e.description}</p>
                      <p className="text-xs text-muted">{e.category_label}</p>
                    </td>
                    <td className="px-3 py-3 text-right font-medium tabular-nums">{money(e.amount)}</td>
                    <td className="px-3 py-3">
                      <StatusBadge status={e.status} />
                      {e.review_comment && <p className="mt-1 max-w-48 text-xs text-muted">« {e.review_comment} »</p>}
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex justify-end gap-1">
                        {e.has_receipt && (
                          <button onClick={() => downloadFile(`/expenses/${e.id}/receipt/`)} className="rounded-lg p-1.5 text-muted hover:bg-sand" aria-label="Justificatif">
                            <PaperClipIcon className="h-4 w-4" />
                          </button>
                        )}
                        {e.status === 'pending' && <Button size="sm" variant="ghost" onClick={() => cancel(e)}>Annuler</Button>}
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
