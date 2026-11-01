'use client'
import { useState } from 'react'
import { CheckIcon, PaperClipIcon, PlusIcon, XMarkIcon, InboxIcon } from '@heroicons/react/24/outline'
import api, { downloadFile, errorMessage } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { useFetch } from '@/lib/useFetch'
import { useI18n } from '@/lib/i18n'
import { date, money, num } from '@/lib/format'
import type { Expense, LeaveRequest } from '@/lib/types'
import Card, { EmptyState, PageHeader, Spinner } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { StatusBadge } from '@/components/ui/Badge'
import TeamCalendar from '@/components/TeamCalendar'
import TeamLeaveModal from '@/components/TeamLeaveModal'
import ReviewModal from '@/components/ReviewModal'

type Pending = { kind: 'leave'; item: LeaveRequest } | { kind: 'expense'; item: Expense }

function Actions({ onApprove, onReject }: { onApprove: () => void; onReject: () => void }) {
  const { t } = useI18n()
  return (
    <div className="flex gap-1">
      <button onClick={onReject} className="rounded-lg border border-stone p-1.5 text-rose-ink hover:bg-rose" aria-label={t('common.reject')}><XMarkIcon className="h-4 w-4" /></button>
      <button onClick={onApprove} className="rounded-lg bg-sage-ink p-1.5 text-white hover:opacity-90" aria-label={t('common.approve')}><CheckIcon className="h-4 w-4" /></button>
    </div>
  )
}

export default function TeamPage() {
  const { user, refreshUnread } = useAuth()
  const { t, tx } = useI18n()
  const [tab, setTab] = useState<'todo' | 'history' | 'calendar'>('todo')
  const leaves = useFetch<LeaveRequest[]>('/leaves/?scope=team')
  const expenses = useFetch<Expense[]>('/expenses/?scope=team')
  const [review, setReview] = useState<{ p: Pending; decision: 'approve' | 'reject' } | null>(null)
  const [adding, setAdding] = useState(false)

  if (!user || (user.role !== 'manager' && !user.is_hr)) {
    return <p className="card p-8 text-center text-sm text-muted">{t('team.managersOnly')}</p>
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
    <><strong>{review.p.item.employee.full_name}</strong> — {tx(`leaveType.${review.p.item.leave_type}`, review.p.item.leave_type_label)}, {t('leave.range', { start: date(review.p.item.start_date), end: date(review.p.item.end_date) })} ({num(review.p.item.days)} {t('unit.days')})</>
  ) : (
    <><strong>{review.p.item.employee.full_name}</strong> — {review.p.item.description}, {money(review.p.item.amount)}</>
  ))

  const tabs = [
    ['todo', `${t('team.todo')}${pendingLeaves.length + pendingExpenses.length ? ` (${pendingLeaves.length + pendingExpenses.length})` : ''}`],
    ['history', t('team.history')],
    ['calendar', t('team.planning')],
  ] as const

  return (
    <div className="space-y-6">
      <PageHeader title={t('team.title')} subtitle={user.is_hr ? t('team.subtitleHr') : t('team.subtitleManager', { n: user.team_size })}
        actions={<Button onClick={() => setAdding(true)}><PlusIcon className="h-4 w-4" /> {t('team.addAbsence')}</Button>} />
      <div className="flex gap-1 border-b border-stone">
        {tabs.map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm ${tab === k ? 'border-coffee font-medium text-espresso' : 'border-transparent text-muted hover:text-espresso'}`}>{l}</button>
        ))}
      </div>

      {tab === 'calendar' && <TeamCalendar />}

      {tab === 'todo' && (leaves.loading || expenses.loading ? <Spinner /> : (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card title={t('team.leavesTodo')}>
            {pendingLeaves.length === 0 ? <EmptyState icon={<InboxIcon />} title={t('team.nothing')} /> : (
              <ul className="divide-y divide-stone">
                {pendingLeaves.map((l) => (
                  <li key={l.id} className="flex items-center gap-3 px-5 py-3.5">
                    <div className="min-w-0 flex-1 text-sm">
                      <p className="font-medium">{l.employee.full_name}</p>
                      <p className="text-xs text-muted">{tx(`leaveType.${l.leave_type}`, l.leave_type_label)} · {t('leave.range', { start: date(l.start_date), end: date(l.end_date) })} · {num(l.days)} {t('unit.days')}</p>
                      {l.reason && <p className="mt-0.5 truncate text-xs text-muted">« {l.reason} »</p>}
                    </div>
                    {l.has_attachment && (
                      <button onClick={() => downloadFile(`/leaves/${l.id}/attachment/`)} className="rounded-lg p-1.5 text-muted hover:bg-sand" aria-label={t('leave.attachmentShort')}><PaperClipIcon className="h-4 w-4" /></button>
                    )}
                    <Actions onApprove={() => setReview({ p: { kind: 'leave', item: l }, decision: 'approve' })}
                      onReject={() => setReview({ p: { kind: 'leave', item: l }, decision: 'reject' })} />
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card title={t('team.expensesTodo')}>
            {pendingExpenses.length === 0 ? <EmptyState icon={<InboxIcon />} title={t('team.nothing')} /> : (
              <ul className="divide-y divide-stone">
                {pendingExpenses.map((e) => (
                  <li key={e.id} className="flex items-center gap-3 px-5 py-3.5">
                    <div className="min-w-0 flex-1 text-sm">
                      <p className="font-medium">{e.employee.full_name} · {money(e.amount)}</p>
                      <p className="truncate text-xs text-muted">{tx(`expCat.${e.category}`, e.category_label)} · {date(e.date)} · {e.description}</p>
                    </div>
                    {e.has_receipt && (
                      <button onClick={() => downloadFile(`/expenses/${e.id}/receipt/`)} className="rounded-lg p-1.5 text-muted hover:bg-sand" aria-label={t('leave.attachmentShort')}><PaperClipIcon className="h-4 w-4" /></button>
                    )}
                    <Actions onApprove={() => setReview({ p: { kind: 'expense', item: e }, decision: 'approve' })}
                      onReject={() => setReview({ p: { kind: 'expense', item: e }, decision: 'reject' })} />
                  </li>
                ))}
              </ul>
            )}
          </Card>
          {user.is_hr && approvedExpenses.length > 0 && (
            <Card className="lg:col-span-2" title={t('team.toRefund')}>
              <ul className="divide-y divide-stone">
                {approvedExpenses.map((e) => (
                  <li key={e.id} className="flex items-center gap-3 px-5 py-3 text-sm">
                    <span className="flex-1">{e.employee.full_name} — {e.description}</span>
                    <span className="font-medium tabular-nums">{money(e.amount)}</span>
                    {e.payslip ? <span className="text-xs text-muted">{t('team.inPayslip')}</span> : (
                      <button onClick={() => markPaid(e)} className="rounded-lg border border-stone px-2.5 py-1 text-xs hover:bg-sand">{t('team.markPaid')}</button>
                    )}
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
                  <tr><th className="px-5 py-2.5">{t('team.colleague')}</th><th className="px-3 py-2.5">{t('team.request')}</th><th className="px-3 py-2.5">{t('team.detail')}</th><th className="px-5 py-2.5">{t('common.status')}</th></tr>
                </thead>
                <tbody className="divide-y divide-stone">
                  {[
                    ...(leaves.data || []).map((l) => ({ key: `l${l.id}`, who: l.employee.full_name, what: tx(`leaveType.${l.leave_type}`, l.leave_type_label), detail: `${t('leave.range', { start: date(l.start_date), end: date(l.end_date) })} (${num(l.days)} ${t('unit.days')})`, status: l.status, created: l.created_at })),
                    ...(expenses.data || []).map((e) => ({ key: `e${e.id}`, who: e.employee.full_name, what: `${t('team.expense')} · ${tx(`expCat.${e.category}`, e.category_label)}`, detail: `${money(e.amount)} — ${e.description}`, status: e.status, created: e.created_at })),
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
      {adding && <TeamLeaveModal onClose={() => setAdding(false)} onCreated={leaves.reload} />}
    </div>
  )
}
