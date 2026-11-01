'use client'
import { useState } from 'react'
import { CheckIcon, PaperClipIcon, XMarkIcon, InboxIcon } from '@heroicons/react/24/outline'
import api, { downloadFile, errorMessage } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { useFetch } from '@/lib/useFetch'
import { date, money, num } from '@/lib/format'
import type { Expense, LeaveRequest } from '@/lib/types'
import Card, { EmptyState, PageHeader, Spinner } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/Badge'
import TeamCalendar from '@/components/TeamCalendar'
import ReviewModal from '@/components/ReviewModal'

type Pending = { kind: 'leave'; item: LeaveRequest } | { kind: 'expense'; item: Expense }

function Actions({ onApprove, onReject }: { onApprove: () => void; onReject: () => void }) {
  return (
    <div className="flex gap-1">
      <button onClick={onReject} className="rounded-lg border border-stone p-1.5 text-rose-ink hover:bg-rose" aria-label="Refuser"><XMarkIcon className="h-4 w-4" /></button>
      <button onClick={onApprove} className="rounded-lg bg-sage-ink p-1.5 text-white hover:opacity-90" aria-label="Valider"><CheckIcon className="h-4 w-4" /></button>
    </div>
  )
}

export default function TeamPage() {
  const { user, refreshUnread } = useAuth()
  const [tab, setTab] = useState<'todo' | 'history' | 'calendar'>('todo')
  const leaves = useFetch<LeaveRequest[]>('/leaves/?scope=team')
  const expenses = useFetch<Expense[]>('/expenses/?scope=team')
  const [review, setReview] = useState<{ p: Pending; decision: 'approve' | 'reject' } | null>(null)

  if (!user || (user.role !== 'manager' && !user.is_hr)) {
    return <p className="card p-8 text-center text-sm text-muted">Cette page est réservée aux managers.</p>
  }

  const pendingLeaves = leaves.data?.filter((l) => l.status === 'pending') || []
  const pendingExpenses = expenses.data?.filter((e) => e.status === 'pending') || []
  const approvedExpenses = expenses.data?.filter((e) => e.status === 'approved') || []

  const confirm = async (comment: string) => {
    if (!review) return
    const { p, decision } = review
    const url = p.kind === 'leave' ? `/leaves/${p.item.id}/${decision}/` : `/expenses/${p.item.id}/${decision}/`
    try {
      await api.post(url, { comment })
    } catch (e) {
      throw new Error(errorMessage(e))
    }
    leaves.reload(); expenses.reload(); refreshUnread()
  }

  const markPaid = async (e: Expense) => {
    await api.post(`/expenses/${e.id}/mark_paid/`)
    expenses.reload()
  }

  const summary = review && (review.p.kind === 'leave' ? (
    <><strong>{review.p.item.employee.full_name}</strong> — {review.p.item.leave_type_label}, du {date(review.p.item.start_date)} au {date(review.p.item.end_date)} ({num(review.p.item.days)} j)</>
  ) : (
    <><strong>{review.p.item.employee.full_name}</strong> — {review.p.item.description}, {money(review.p.item.amount)}</>
  ))

  const tabs = [
    ['todo', `À valider${pendingLeaves.length + pendingExpenses.length ? ` (${pendingLeaves.length + pendingExpenses.length})` : ''}`],
    ['history', 'Historique'],
    ['calendar', 'Planning'],
  ] as const

  return (
    <div className="space-y-6">
      <PageHeader title="Validations équipe" subtitle={user.is_hr ? 'Toutes les demandes des salariés.' : `Les demandes de vos ${user.team_size} collaborateur(s) direct(s).`} />
      <div className="flex gap-1 border-b border-stone">
        {tabs.map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm ${tab === k ? 'border-coffee font-medium text-espresso' : 'border-transparent text-muted hover:text-espresso'}`}>{l}</button>
        ))}
      </div>

      {tab === 'calendar' && <TeamCalendar />}

      {tab === 'todo' && (leaves.loading || expenses.loading ? <Spinner /> : (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="Absences à valider">
            {pendingLeaves.length === 0 ? <EmptyState icon={<InboxIcon />} title="Rien à valider" /> : (
              <ul className="divide-y divide-stone">
                {pendingLeaves.map((l) => (
                  <li key={l.id} className="flex items-center gap-3 px-5 py-3.5">
                    <div className="min-w-0 flex-1 text-sm">
                      <p className="font-medium">{l.employee.full_name}</p>
                      <p className="text-xs text-muted">{l.leave_type_label} · {date(l.start_date)} → {date(l.end_date)} · {num(l.days)} j</p>
                      {l.reason && <p className="mt-0.5 truncate text-xs text-muted">« {l.reason} »</p>}
                    </div>
                    {l.has_attachment && (
                      <button onClick={() => downloadFile(`/leaves/${l.id}/attachment/`)} className="rounded-lg p-1.5 text-muted hover:bg-sand" aria-label="Justificatif"><PaperClipIcon className="h-4 w-4" /></button>
                    )}
                    <Actions onApprove={() => setReview({ p: { kind: 'leave', item: l }, decision: 'approve' })}
                      onReject={() => setReview({ p: { kind: 'leave', item: l }, decision: 'reject' })} />
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card title="Notes de frais à valider">
            {pendingExpenses.length === 0 ? <EmptyState icon={<InboxIcon />} title="Rien à valider" /> : (
              <ul className="divide-y divide-stone">
                {pendingExpenses.map((e) => (
                  <li key={e.id} className="flex items-center gap-3 px-5 py-3.5">
                    <div className="min-w-0 flex-1 text-sm">
                      <p className="font-medium">{e.employee.full_name} · {money(e.amount)}</p>
                      <p className="truncate text-xs text-muted">{e.category_label} · {date(e.date)} · {e.description}</p>
                    </div>
                    {e.has_receipt && (
                      <button onClick={() => downloadFile(`/expenses/${e.id}/receipt/`)} className="rounded-lg p-1.5 text-muted hover:bg-sand" aria-label="Justificatif"><PaperClipIcon className="h-4 w-4" /></button>
                    )}
                    <Actions onApprove={() => setReview({ p: { kind: 'expense', item: e }, decision: 'approve' })}
                      onReject={() => setReview({ p: { kind: 'expense', item: e }, decision: 'reject' })} />
                  </li>
                ))}
              </ul>
            )}
          </Card>
          {user.is_hr && approvedExpenses.length > 0 && (
            <Card className="lg:col-span-2" title="Notes validées à rembourser">
              <ul className="divide-y divide-stone">
                {approvedExpenses.map((e) => (
                  <li key={e.id} className="flex items-center gap-3 px-5 py-3 text-sm">
                    <span className="flex-1">{e.employee.full_name} — {e.description}</span>
                    <span className="font-medium tabular-nums">{money(e.amount)}</span>
                    <button onClick={() => markPaid(e)} className="rounded-lg border border-stone px-2.5 py-1 text-xs hover:bg-sand">Marquer remboursée</button>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      ))}

      {tab === 'history' && (
        <Card>
          {leaves.loading ? <Spinner /> : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-sm">
                <thead className="table-head">
                  <tr><th className="px-5 py-2.5">Collaborateur</th><th className="px-3 py-2.5">Demande</th><th className="px-3 py-2.5">Détail</th><th className="px-5 py-2.5">Statut</th></tr>
                </thead>
                <tbody className="divide-y divide-stone">
                  {[
                    ...(leaves.data || []).map((l) => ({ key: `l${l.id}`, who: l.employee.full_name, what: l.leave_type_label, detail: `${date(l.start_date)} → ${date(l.end_date)} (${num(l.days)} j)`, status: l.status, created: l.created_at })),
                    ...(expenses.data || []).map((e) => ({ key: `e${e.id}`, who: e.employee.full_name, what: `Frais · ${e.category_label}`, detail: `${money(e.amount)} — ${e.description}`, status: e.status, created: e.created_at })),
                  ].filter((r) => r.status !== 'pending').sort((a, b) => b.created.localeCompare(a.created)).map((r) => (
                    <tr key={r.key}>
                      <td className="px-5 py-3 font-medium">{r.who}</td>
                      <td className="px-3 py-3">{r.what}</td>
                      <td className="px-3 py-3 text-muted">{r.detail}</td>
                      <td className="px-5 py-3"><StatusBadge status={r.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {review && <ReviewModal open decision={review.decision} summary={summary} onClose={() => setReview(null)} onConfirm={confirm} />}
    </div>
  )
}
