'use client'
import { useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  ArrowDownTrayIcon, ArrowRightIcon, CalendarDaysIcon, DocumentTextIcon, PlusIcon, ReceiptPercentIcon,
} from '@heroicons/react/24/outline'
import { useAuth } from '@/context/AuthContext'
import { useI18n } from '@/lib/i18n'
import { useFetch } from '@/lib/useFetch'
import { downloadFile } from '@/lib/api'
import { date, longDate, money, monthLabel, num } from '@/lib/format'
import type { Balance, DocumentItem, LeaveRequest, PayslipSummary } from '@/lib/types'
import Card, { EmptyState, Spinner } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { StatusBadge } from '@/components/ui/Badge'
import BalanceCard from '@/components/BalanceCard'

interface Dashboard {
  has_employee_space: boolean
  last_payslip: PayslipSummary | null
  balances: Balance[]
  upcoming_leaves: LeaveRequest[]
  recent_documents: DocumentItem[]
  pending_requests: { leaves: number; expenses: number; profile: number }
  unread_notifications: number
  to_review: { leaves?: number; expenses?: number; profile_requests?: number }
}

export default function DashboardPage() {
  const { user } = useAuth()
  const { t, tx } = useI18n()
  const router = useRouter()
  // Accountants and the platform admin have no personal employee space.
  const redirect = user && !user.company ? (user.is_platform_admin ? '/plateforme' : '/entreprises') : null
  const { data, loading } = useFetch<Dashboard>(redirect ? null : '/dashboard/')

  useEffect(() => { if (redirect) router.replace(redirect) }, [redirect, router])

  if (redirect || loading || !data) return <Spinner />
  const p = data.last_payslip
  const review = data.to_review
  const reviewTotal = (review.leaves || 0) + (review.expenses || 0) + (review.profile_requests || 0)
  const h = new Date().getHours()

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm text-muted first-letter:uppercase">{longDate(new Date().toISOString())}</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">
          {t(h < 5 || h >= 18 ? 'home.evening' : 'home.morning', { name: user?.first_name || user?.full_name || '' })}
        </h1>
      </div>

      {reviewTotal > 0 && (
        <Link href={review.profile_requests && !review.leaves && !review.expenses ? '/admin/demandes' : '/equipe'}
          className="flex items-center justify-between gap-4 rounded-2xl border border-latte bg-honey/60 px-5 py-4 text-sm hover:bg-honey">
          <span>
            <strong className="font-semibold">{t('home.toReview', { n: reviewTotal })}</strong>
            <span className="text-muted"> — {[
              review.leaves ? t('home.toReview.leaves', { n: review.leaves }) : '',
              review.expenses ? t('home.toReview.expenses', { n: review.expenses }) : '',
              review.profile_requests ? t('home.toReview.profile', { n: review.profile_requests }) : '',
            ].filter(Boolean).join(t('common.listSep'))}</span>
          </span>
          <ArrowRightIcon className="h-4 w-4 shrink-0 rtl:rotate-180" />
        </Link>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2" title={t('home.lastPayslip')}
          action={<Link href="/bulletins" className="text-xs font-medium text-coffee hover:underline">{t('home.allPayslips')}</Link>}>
          {p ? (
            <div className="flex flex-wrap items-center justify-between gap-6 p-5">
              <div>
                <p className="text-sm text-muted">{monthLabel(p.year, p.month)}</p>
                <p className="mt-1 text-3xl font-semibold tracking-tight">{money(p.net_salary)}</p>
                <p className="mt-1 text-xs text-muted">{t('home.netGross', { gross: money(p.gross_salary) })}</p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" href={`/bulletins/${p.id}`}>{t('common.view')}</Button>
                <Button onClick={() => downloadFile(`/payslips/${p.id}/pdf/`, 'bulletin.pdf')}>
                  <ArrowDownTrayIcon className="h-4 w-4" /> PDF
                </Button>
              </div>
            </div>
          ) : (
            <EmptyState icon={<DocumentTextIcon />} title={t('home.noPayslip')}>{t('home.noPayslipHint')}</EmptyState>
          )}
        </Card>

        <Card title={t('home.shortcuts')}>
          <div className="grid gap-2 p-4">
            <Button variant="outline" href="/absences?nouvelle=1" className="justify-start">
              <CalendarDaysIcon className="h-4 w-4" /> {t('home.newLeave')}
            </Button>
            <Button variant="outline" href="/notes-de-frais?nouvelle=1" className="justify-start">
              <ReceiptPercentIcon className="h-4 w-4" /> {t('home.newExpense')}
            </Button>
            <Button variant="outline" href="/profil" className="justify-start">
              <PlusIcon className="h-4 w-4" /> {t('home.updateProfile')}
            </Button>
          </div>
          <div className="border-t border-stone px-5 py-3 text-xs text-muted">
            {t('home.pending', { leaves: data.pending_requests.leaves, expenses: data.pending_requests.expenses })}
            {data.pending_requests.profile ? t('home.pendingProfile') : ''}
          </div>
        </Card>
      </div>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold">{t('home.balances')}</h2>
          <Link href="/absences" className="text-xs font-medium text-coffee hover:underline">{t('home.manageLeaves')}</Link>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {data.balances.map((b) => <BalanceCard key={b.leave_type} balance={b} />)}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title={t('home.upcoming')}>
          {data.upcoming_leaves.length === 0 ? (
            <EmptyState icon={<CalendarDaysIcon />} title={t('home.noUpcoming')} />
          ) : (
            <ul className="divide-y divide-stone">
              {data.upcoming_leaves.map((l) => (
                <li key={l.id} className="flex items-center justify-between gap-3 px-5 py-3 text-sm">
                  <div>
                    <p className="font-medium">{tx(`leaveType.${l.leave_type}`, l.leave_type_label)}</p>
                    <p className="text-xs text-muted">{t('leave.range', { start: date(l.start_date), end: date(l.end_date) })} · {num(l.days)} {t('unit.days')}</p>
                  </div>
                  <StatusBadge status={l.status} />
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title={t('home.recentDocs')}
          action={<Link href="/documents" className="text-xs font-medium text-coffee hover:underline">{t('nav.documents')}</Link>}>
          {data.recent_documents.length === 0 ? (
            <EmptyState icon={<DocumentTextIcon />} title={t('docs.empty')} />
          ) : (
            <ul className="divide-y divide-stone">
              {data.recent_documents.map((d) => (
                <li key={d.id} className="flex items-center justify-between gap-3 px-5 py-3 text-sm">
                  <div className="min-w-0">
                    <p className="truncate font-medium">
                      {d.title}
                      {!d.viewed_at && d.employee && <span className="ms-2 inline-block h-2 w-2 rounded-full bg-coffee align-middle" title={t('common.new')} />}
                    </p>
                    <p className="text-xs text-muted">{tx(`docCat.${d.category}`, d.category_label)} · {date(d.created_at)}</p>
                  </div>
                  <button onClick={() => downloadFile(`/documents/${d.id}/download/`, d.file_name || 'document')}
                    className="rounded-lg p-2 text-muted hover:bg-sand hover:text-coffee" aria-label={t('common.download')}>
                    <ArrowDownTrayIcon className="h-4 w-4" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  )
}
