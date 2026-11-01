'use client'
import Link from 'next/link'
import { BuildingOffice2Icon, ChartBarIcon } from '@heroicons/react/24/outline'
import { useFetch } from '@/lib/useFetch'
import { useI18n, type TKey } from '@/lib/i18n'
import { date, money, months, num } from '@/lib/format'
import type { PayrollTotals, Role } from '@/lib/types'
import Card, { EmptyState, PageHeader, Spinner, Stat } from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'
import { PlatformOnly } from '@/components/AppShell'

interface Stats {
  totals: {
    companies: number; companies_inactive: number; employees: number; accountants: number; admins: number
    payslips_total: number; pending_leaves: number; pending_expenses: number; documents: number
  }
  roles: Partial<Record<Role, number>>
  trend: (PayrollTotals & { year: number; month: number })[]
  companies: {
    id: number; name: string; city: string; is_active: boolean; employee_count: number; managers: string[]
    last_payroll: string | null; last_net: string | null; pending: number
  }[]
  recent_users: { id: number; full_name: string; role: Role; company: string | null; date_joined: string }[]
}

/** Net payroll per month: one series, so the card title names it and no legend is needed. */
function TrendChart({ trend }: { trend: Stats['trend'] }) {
  const { t } = useI18n()
  const max = Math.max(...trend.map((m) => Number(m.net || 0)), 1)
  const names = months()
  return (
    <div className="p-5">
      <div className="flex h-48 items-end gap-3 border-b border-stone" role="img" aria-label={t('platform.trend')}>
        {trend.map((m, i) => {
          const v = Number(m.net || 0)
          const last = i === trend.length - 1
          return (
            <div key={`${m.year}-${m.month}`} className="group relative flex h-full flex-1 flex-col justify-end">
              {(last || v === max) && v > 0 && (
                <span className="mb-1 text-center text-[11px] tabular-nums text-muted">{num(Math.round(v / 1000))}k</span>
              )}
              <div className="w-full rounded-t bg-coffee/80 transition-colors group-hover:bg-coffee" style={{ height: `${(v / max) * 100}%`, minHeight: v ? 2 : 0 }} />
              <div className="pointer-events-none absolute bottom-full start-1/2 z-10 mb-2 hidden w-44 -translate-x-1/2 rounded-lg border border-stone bg-white p-2.5 text-xs shadow-md group-hover:block rtl:translate-x-1/2">
                <p className="font-semibold">{names[m.month - 1]} {m.year}</p>
                <p className="mt-1 flex justify-between gap-2"><span className="text-muted">{t('payroll.net')}</span><span className="tabular-nums">{money(m.net)}</span></p>
                <p className="flex justify-between gap-2"><span className="text-muted">{t('payroll.gross')}</span><span className="tabular-nums">{money(m.gross)}</span></p>
                <p className="flex justify-between gap-2"><span className="text-muted">{t('platform.payslips')}</span><span className="tabular-nums">{m.count}</span></p>
              </div>
            </div>
          )
        })}
      </div>
      <div className="mt-2 flex gap-3">
        {trend.map((m) => <span key={`${m.year}-${m.month}`} className="flex-1 truncate text-center text-[11px] text-muted">{names[m.month - 1]}</span>)}
      </div>
    </div>
  )
}

export default function PlatformPage() {
  const { t } = useI18n()
  const { data, loading } = useFetch<Stats>('/platform/stats/')
  const lastPaid = data && [...data.trend].reverse().find((m) => m.count > 0)

  return (
    <PlatformOnly>
      <PageHeader title={t('nav.platformDashboard')} subtitle={t('platform.subtitle')} />
      {loading || !data ? <Spinner /> : (
        <div className="space-y-6">
          <div className="card grid grid-cols-2 gap-6 p-5 lg:grid-cols-4">
            <Stat label={t('platform.companies')} value={data.totals.companies}
              hint={data.totals.companies_inactive ? t('platform.inactive', { n: data.totals.companies_inactive }) : undefined} />
            <Stat label={t('platform.employees')} value={data.totals.employees} />
            <Stat label={t('platform.accountants')} value={data.totals.accountants} hint={t('platform.admins', { n: data.totals.admins })} />
            <Stat label={t('platform.payslipsTotal')} value={data.totals.payslips_total} />
            <Stat label={t('platform.pendingLeaves')} value={data.totals.pending_leaves} />
            <Stat label={t('platform.pendingExpenses')} value={data.totals.pending_expenses} />
            <Stat label={t('platform.documents')} value={data.totals.documents} />
            <Stat label={t('platform.lastNet')} value={money(lastPaid?.net)}
              hint={lastPaid ? `${months()[lastPaid.month - 1]} ${lastPaid.year}` : undefined} />
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2" title={t('platform.trend')}>
              {data.trend.some((m) => m.count) ? <TrendChart trend={data.trend} /> : <EmptyState icon={<ChartBarIcon />} title={t('payroll.empty')} />}
            </Card>
            <Card title={t('platform.recentUsers')}>
              <ul className="divide-y divide-stone">
                {data.recent_users.map((u) => (
                  <li key={u.id} className="flex items-center justify-between gap-3 px-5 py-2.5 text-sm">
                    <span className="min-w-0">
                      <span className="block truncate font-medium">{u.full_name}</span>
                      <span className="block truncate text-xs text-muted">{t(`role.${u.role}` as TKey)}{u.company ? ` · ${u.company}` : ''}</span>
                    </span>
                    <span className="shrink-0 text-xs text-muted">{date(u.date_joined)}</span>
                  </li>
                ))}
              </ul>
            </Card>
          </div>

          <Card title={t('nav.companies')} action={<Link href="/entreprises" className="text-xs font-medium text-coffee hover:underline">{t('platform.manage')}</Link>}>
            {!data.companies.length ? <EmptyState icon={<BuildingOffice2Icon />} title={t('firms.empty')} /> : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[720px] text-sm">
                  <thead className="table-head">
                    <tr>
                      <th className="px-5 py-2.5">{t('company.name')}</th>
                      <th className="px-3 py-2.5">{t('firms.managedBy')}</th>
                      <th className="px-3 py-2.5 text-end">{t('nav.employees')}</th>
                      <th className="px-3 py-2.5">{t('firms.lastPayroll')}</th>
                      <th className="px-3 py-2.5 text-end">{t('payroll.netTotal')}</th>
                      <th className="px-3 py-2.5 text-end">{t('firms.toProcess')}</th>
                      <th className="px-5 py-2.5">{t('common.status')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone">
                    {data.companies.map((c) => (
                      <tr key={c.id}>
                        <td className="px-5 py-3"><p className="font-medium">{c.name}</p><p className="text-xs text-muted">{c.city}</p></td>
                        <td className="px-3 py-3 text-muted">{c.managers.join(t('common.listSep')) || '—'}</td>
                        <td className="px-3 py-3 text-end tabular-nums">{c.employee_count}</td>
                        <td className="px-3 py-3" dir="ltr">{c.last_payroll || '—'}</td>
                        <td className="px-3 py-3 text-end tabular-nums">{money(c.last_net)}</td>
                        <td className="px-3 py-3 text-end tabular-nums">{c.pending}</td>
                        <td className="px-5 py-3">{c.is_active ? <Badge tone="sage">{t('firms.active')}</Badge> : <Badge tone="rose">{t('firms.inactive')}</Badge>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      )}
    </PlatformOnly>
  )
}
