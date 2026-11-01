'use client'
import { useState } from 'react'
import {
  ArrowRightIcon, BuildingOffice2Icon, CalculatorIcon, MagnifyingGlassIcon, PlusIcon, UsersIcon,
} from '@heroicons/react/24/outline'
import api, { errorMessage, setActiveCompany } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { useFetch } from '@/lib/useFetch'
import { useI18n, type TKey } from '@/lib/i18n'
import { money, monthLabel } from '@/lib/format'
import type { Company, CompanyOverview } from '@/lib/types'
import Card, { Alert, EmptyState, PageHeader, Spinner } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import Badge from '@/components/ui/Badge'
import Modal from '@/components/ui/Modal'
import Field from '@/components/ui/Field'
import CompanyFields from '@/components/CompanyFields'

const BLANK: Partial<Company> = {
  name: '', name_ar: '', legal_form: 'SARL', sector: '', phone: '', email: '', address: '', city: '',
  nif: '', nis: '', rc: '', cnas_number: '',
}

function NewCompanyModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: (c: Company) => void }) {
  const { t } = useI18n()
  const [form, setForm] = useState<Partial<Company>>(BLANK)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const text = (k: keyof Company, label: TKey, ltr = false) => (
    <Field label={t(label)}>
      <input className={`input ${ltr ? 'text-start' : ''}`} dir={ltr ? 'ltr' : undefined} required={k === 'name'}
        value={(form[k] as string) ?? ''} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
    </Field>
  )

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true); setError('')
    try {
      const r = await api.post('/companies/', form)
      setForm(BLANK)
      onCreated(r.data)
    } catch (err) { setError(errorMessage(err)) } finally { setSaving(false) }
  }

  return (
    <Modal open={open} onClose={onClose} title={t('firms.newTitle')} wide>
      <form onSubmit={submit} className="space-y-4">
        {error && <Alert>{error}</Alert>}
        <p className="text-sm text-muted">{t('firms.newIntro')}</p>
        <CompanyFields text={text} />
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>{t('common.cancel')}</Button>
          <Button type="submit" disabled={saving}>{saving ? t('common.saving') : t('firms.create')}</Button>
        </div>
      </form>
    </Modal>
  )
}

export default function CompaniesPage() {
  const { user, refresh } = useAuth()
  const { t, locale } = useI18n()
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const { data, loading, reload } = useFetch<CompanyOverview[]>(`/companies/overview/?q=${encodeURIComponent(q)}`)

  if (!user || !(user.is_platform_admin || user.role === 'accountant')) {
    return <p className="card p-8 text-center text-sm text-muted">{t('common.hrOnly')}</p>
  }
  // The platform admin manages companies as a whole; only accountants work inside them.
  const canEnter = user.role === 'accountant'

  const enter = (c: { id: number }, path = '/admin/paie') => {
    setActiveCompany(c.id)
    window.location.href = path
  }

  const toggle = async (c: CompanyOverview) => {
    if (c.is_active) {
      if (!confirm(t('firms.confirmDeactivate', { name: c.name }))) return
      await api.delete(`/companies/${c.id}/`)
    } else {
      await api.post(`/companies/${c.id}/reactivate/`)
    }
    reload(); refresh()
  }

  return (
    <div>
      <PageHeader title={user.is_platform_admin ? t('nav.companies') : t('nav.myCompanies')}
        subtitle={data ? t('firms.count', { n: data.length }) : undefined}
        actions={<Button onClick={() => setOpen(true)}><PlusIcon className="h-4 w-4" /> {t('firms.new')}</Button>} />

      <div className="relative mb-4 max-w-md">
        <MagnifyingGlassIcon className="pointer-events-none absolute start-3 top-2.5 h-4 w-4 text-muted" />
        <input className="input ps-9" placeholder={t('firms.search')} value={q} onChange={(e) => setQ(e.target.value)} />
      </div>

      {loading && !data ? <Spinner /> : !data?.length ? (
        <Card><EmptyState icon={<BuildingOffice2Icon />} title={t('firms.empty')}>{t('firms.emptyHint')}</EmptyState></Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {data.map((c) => {
            const pending = c.pending_leaves + c.pending_expenses + c.pending_profile
            return (
              <Card key={c.id} className={c.is_active ? '' : 'opacity-70'}>
                <div className="flex items-start justify-between gap-3 border-b border-stone p-5">
                  <div className="min-w-0">
                    <p className="truncate font-semibold">{locale === 'ar' && c.name_ar ? c.name_ar : c.name} <span className="text-xs font-normal text-muted">{c.legal_form}</span></p>
                    <p className="truncate text-xs text-muted">{[c.sector, c.city].filter(Boolean).join(' · ') || '—'}</p>
                    {c.nif && <p className="text-[11px] text-muted" dir="ltr">NIF {c.nif}</p>}
                  </div>
                  {c.is_active ? <Badge tone="sage">{t('firms.active')}</Badge> : <Badge tone="rose">{t('firms.inactive')}</Badge>}
                </div>
                <dl className="grid grid-cols-3 gap-3 p-5 text-sm">
                  <div>
                    <dt className="text-xs text-muted">{t('nav.employees')}</dt>
                    <dd className="mt-0.5 flex items-center gap-1 font-semibold"><UsersIcon className="h-4 w-4 text-coffee" />{c.employee_count}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted">{c.last_payroll ? monthLabel(c.last_payroll.year, c.last_payroll.month) : t('firms.lastPayroll')}</dt>
                    <dd className="mt-0.5 font-semibold tabular-nums">{c.last_payroll ? money(c.last_payroll.net) : '—'}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted">{t('firms.toProcess')}</dt>
                    <dd className="mt-0.5 font-semibold">{pending + c.drafts}</dd>
                  </div>
                </dl>
                <div className="flex flex-wrap gap-2 px-5 pb-2 text-[11px]">
                  {c.drafts > 0 && <Badge tone="honey">{t('firms.drafts', { n: c.drafts })}</Badge>}
                  {c.pending_leaves > 0 && <Badge tone="mist">{t('home.toReview.leaves', { n: c.pending_leaves })}</Badge>}
                  {c.pending_expenses > 0 && <Badge tone="mist">{t('home.toReview.expenses', { n: c.pending_expenses })}</Badge>}
                  {c.pending_profile > 0 && <Badge tone="mist">{t('home.toReview.profile', { n: c.pending_profile })}</Badge>}
                  {c.absent_today > 0 && <Badge tone="neutral">{t('firms.absentToday', { n: c.absent_today })}</Badge>}
                </div>
                {c.managers.length > 0 && (
                  <p className="px-5 pb-3 text-xs text-muted">{t('firms.managedBy')} {c.managers.map((m) => m.full_name).join(t('common.listSep'))}</p>
                )}
                <div className="flex flex-wrap items-center justify-end gap-2 border-t border-stone px-5 py-3">
                  {user.is_platform_admin && (
                    <Button size="sm" variant={c.is_active ? 'ghost' : 'outline'} onClick={() => toggle(c)}>
                      {c.is_active ? t('firms.deactivate') : t('firms.reactivate')}
                    </Button>
                  )}
                  {c.is_active && canEnter && <>
                    <Button size="sm" variant="outline" onClick={() => enter(c, '/admin/salaries')}><UsersIcon className="h-4 w-4" /> {t('nav.employees')}</Button>
                    <Button size="sm" onClick={() => enter(c)}><CalculatorIcon className="h-4 w-4" /> {t('nav.payroll')} <ArrowRightIcon className="h-3.5 w-3.5 rtl:rotate-180" /></Button>
                  </>}
                </div>
              </Card>
            )
          })}
        </div>
      )}

      <NewCompanyModal open={open} onClose={() => setOpen(false)}
        onCreated={async (c) => { setOpen(false); await refresh(); reload(); if (canEnter) enter(c, '/admin/salaries') }} />
    </div>
  )
}
