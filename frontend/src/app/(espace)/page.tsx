'use client'
import Link from 'next/link'
import {
  ArrowDownTrayIcon, ArrowRightIcon, CalendarDaysIcon, DocumentTextIcon, PlusIcon, ReceiptPercentIcon,
} from '@heroicons/react/24/outline'
import { useAuth } from '@/context/AuthContext'
import { useFetch } from '@/lib/useFetch'
import { downloadFile } from '@/lib/api'
import { date, longDate, money, monthLabel, num } from '@/lib/format'
import type { Balance, DocumentItem, LeaveRequest, PayslipSummary } from '@/lib/types'
import Card, { EmptyState, Spinner } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { StatusBadge } from '@/components/ui/Badge'
import BalanceCard from '@/components/BalanceCard'

interface Dashboard {
  last_payslip: PayslipSummary | null
  balances: Balance[]
  upcoming_leaves: LeaveRequest[]
  recent_documents: DocumentItem[]
  pending_requests: { leaves: number; expenses: number; profile: number }
  unread_notifications: number
  to_review: { leaves?: number; expenses?: number; profile_requests?: number }
}

function greeting() {
  const h = new Date().getHours()
  return h < 5 || h >= 18 ? 'Bonsoir' : 'Bonjour'
}

export default function DashboardPage() {
  const { user } = useAuth()
  const { data, loading } = useFetch<Dashboard>('/dashboard/')

  if (loading || !data) return <Spinner />
  const p = data.last_payslip
  const review = data.to_review
  const reviewTotal = (review.leaves || 0) + (review.expenses || 0) + (review.profile_requests || 0)

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm text-muted first-letter:uppercase">{longDate(new Date().toISOString())}</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">{greeting()}, {user?.first_name || user?.full_name}</h1>
      </div>

      {reviewTotal > 0 && (
        <Link href={review.profile_requests && !review.leaves && !review.expenses ? '/admin/demandes' : '/equipe'}
          className="flex items-center justify-between gap-4 rounded-2xl border border-latte bg-honey/60 px-5 py-4 text-sm hover:bg-honey">
          <span>
            <strong className="font-semibold">{reviewTotal} demande{reviewTotal > 1 ? 's' : ''} à traiter</strong>
            <span className="text-muted"> — {[
              review.leaves ? `${review.leaves} absence${review.leaves > 1 ? 's' : ''}` : '',
              review.expenses ? `${review.expenses} note${review.expenses > 1 ? 's' : ''} de frais` : '',
              review.profile_requests ? `${review.profile_requests} modification${review.profile_requests > 1 ? 's' : ''} de dossier` : '',
            ].filter(Boolean).join(', ')}</span>
          </span>
          <ArrowRightIcon className="h-4 w-4 shrink-0" />
        </Link>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2" title="Dernier bulletin de paie"
          action={<Link href="/bulletins" className="text-xs font-medium text-coffee hover:underline">Tous mes bulletins</Link>}>
          {p ? (
            <div className="flex flex-wrap items-center justify-between gap-6 p-5">
              <div>
                <p className="text-sm text-muted">{monthLabel(p.year, p.month)}</p>
                <p className="mt-1 text-3xl font-semibold tracking-tight">{money(p.net_salary)}</p>
                <p className="mt-1 text-xs text-muted">Net à payer · brut {money(p.gross_salary)}</p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" href={`/bulletins/${p.id}`}>Consulter</Button>
                <Button onClick={() => downloadFile(`/payslips/${p.id}/pdf/`, 'bulletin.pdf')}>
                  <ArrowDownTrayIcon className="h-4 w-4" /> PDF
                </Button>
              </div>
            </div>
          ) : (
            <EmptyState icon={<DocumentTextIcon />} title="Aucun bulletin pour le moment">
              Vos bulletins apparaîtront ici dès leur publication.
            </EmptyState>
          )}
        </Card>

        <Card title="Raccourcis">
          <div className="grid gap-2 p-4">
            <Button variant="outline" href="/absences?nouvelle=1" className="justify-start">
              <CalendarDaysIcon className="h-4 w-4" /> Poser une absence
            </Button>
            <Button variant="outline" href="/notes-de-frais?nouvelle=1" className="justify-start">
              <ReceiptPercentIcon className="h-4 w-4" /> Déclarer une note de frais
            </Button>
            <Button variant="outline" href="/profil" className="justify-start">
              <PlusIcon className="h-4 w-4" /> Mettre à jour mon dossier
            </Button>
          </div>
          <div className="border-t border-stone px-5 py-3 text-xs text-muted">
            En attente : {data.pending_requests.leaves} absence(s), {data.pending_requests.expenses} note(s) de frais
            {data.pending_requests.profile ? ', 1 modification de dossier' : ''}
          </div>
        </Card>
      </div>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold">Mes compteurs</h2>
          <Link href="/absences" className="text-xs font-medium text-coffee hover:underline">Gérer mes absences</Link>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {data.balances.map((b) => <BalanceCard key={b.leave_type} balance={b} />)}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Mes prochaines absences">
          {data.upcoming_leaves.length === 0 ? (
            <EmptyState icon={<CalendarDaysIcon />} title="Aucune absence prévue" />
          ) : (
            <ul className="divide-y divide-stone">
              {data.upcoming_leaves.map((l) => (
                <li key={l.id} className="flex items-center justify-between gap-3 px-5 py-3 text-sm">
                  <div>
                    <p className="font-medium">{l.leave_type_label}</p>
                    <p className="text-xs text-muted">Du {date(l.start_date)} au {date(l.end_date)} · {num(l.days)} j</p>
                  </div>
                  <StatusBadge status={l.status} />
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Documents récents"
          action={<Link href="/documents" className="text-xs font-medium text-coffee hover:underline">Coffre-fort</Link>}>
          {data.recent_documents.length === 0 ? (
            <EmptyState icon={<DocumentTextIcon />} title="Aucun document" />
          ) : (
            <ul className="divide-y divide-stone">
              {data.recent_documents.map((d) => (
                <li key={d.id} className="flex items-center justify-between gap-3 px-5 py-3 text-sm">
                  <div className="min-w-0">
                    <p className="truncate font-medium">
                      {d.title}
                      {!d.viewed_at && d.employee && <span className="ml-2 inline-block h-2 w-2 rounded-full bg-coffee align-middle" title="Nouveau" />}
                    </p>
                    <p className="text-xs text-muted">{d.category_label} · {date(d.created_at)}</p>
                  </div>
                  <button onClick={() => downloadFile(`/documents/${d.id}/download/`, d.file_name || 'document')}
                    className="rounded-lg p-2 text-muted hover:bg-sand hover:text-coffee" aria-label="Télécharger">
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
