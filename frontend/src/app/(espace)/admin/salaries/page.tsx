'use client'
import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { MagnifyingGlassIcon, UserPlusIcon, UsersIcon } from '@heroicons/react/24/outline'
import { useFetch } from '@/lib/useFetch'
import { useI18n } from '@/lib/i18n'
import { initials, money } from '@/lib/format'
import type { Employee } from '@/lib/types'
import Card, { EmptyState, PageHeader, Spinner } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import Badge from '@/components/ui/Badge'
import Modal from '@/components/ui/Modal'
import EmployeeForm from '@/components/EmployeeForm'
import { HrOnly } from '@/components/AppShell'

export default function EmployeesPage() {
  const router = useRouter()
  const { t } = useI18n()
  const [q, setQ] = useState('')
  const [showInactive, setShowInactive] = useState(false)
  const [open, setOpen] = useState(false)
  const { data, loading } = useFetch<Employee[]>(`/employees/?q=${encodeURIComponent(q)}${showInactive ? '' : '&active=1'}`)

  return (
    <HrOnly>
      <PageHeader title={t('nav.employees')} subtitle={data ? t('emp.count', { n: data.length }) : undefined}
        actions={<Button onClick={() => setOpen(true)}><UserPlusIcon className="h-4 w-4" /> {t('emp.add')}</Button>} />
      <Card>
        <div className="flex flex-wrap items-center gap-3 border-b border-stone p-3">
          <div className="relative min-w-56 flex-1">
            <MagnifyingGlassIcon className="pointer-events-none absolute start-3 top-2.5 h-4 w-4 text-muted" />
            <input className="input ps-9" placeholder={t('emp.search')} value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <label className="flex items-center gap-2 text-sm text-muted">
            <input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} /> {t('emp.includeLeft')}
          </label>
        </div>
        {loading && !data ? <Spinner /> : !data?.length ? <EmptyState icon={<UsersIcon />} title={t('emp.empty')} /> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-sm">
              <thead className="table-head">
                <tr><th className="px-5 py-2.5">{t('role.employee')}</th><th className="px-3 py-2.5">{t('field.employee_number')}</th><th className="px-3 py-2.5">{t('field.department')}</th><th className="px-3 py-2.5">{t('field.manager')}</th><th className="px-3 py-2.5 text-end">{t('emp.baseSalary')}</th><th className="px-5 py-2.5">{t('field.role')}</th></tr>
              </thead>
              <tbody className="divide-y divide-stone">
                {data.map((e) => (
                  <tr key={e.id} className="cursor-pointer hover:bg-cream" onClick={() => router.push(`/admin/salaries/${e.id}`)}>
                    <td className="px-5 py-3">
                      <Link href={`/admin/salaries/${e.id}`} className="flex items-center gap-3" onClick={(ev) => ev.stopPropagation()}>
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-sand text-xs font-semibold text-coffee-dark">{initials(e.full_name)}</span>
                        <span>
                          <span className="block font-medium">{e.full_name}</span>
                          <span className="block text-xs text-muted">{e.job_title}</span>
                        </span>
                      </Link>
                    </td>
                    <td className="px-3 py-3 text-muted">{e.employee_number}</td>
                    <td className="px-3 py-3">{e.department}</td>
                    <td className="px-3 py-3 text-muted">{e.manager_name || '—'}</td>
                    <td className="px-3 py-3 text-end tabular-nums">{money(e.base_salary)}</td>
                    <td className="px-5 py-3">
                      {e.is_active ? <Badge tone={e.role === 'hr' ? 'coffee' : e.role === 'manager' ? 'mist' : 'neutral'}>{t(`role.${e.role}`)}</Badge> : <Badge tone="rose">{t('emp.left')}</Badge>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <Modal open={open} onClose={() => setOpen(false)} title={t('emp.newTitle')} wide>
        <EmployeeForm onCancel={() => setOpen(false)} onSaved={(e) => router.push(`/admin/salaries/${e.id}`)} />
      </Modal>
    </HrOnly>
  )
}
