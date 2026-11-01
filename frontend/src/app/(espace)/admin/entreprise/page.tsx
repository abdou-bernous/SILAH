'use client'
import { useEffect, useState } from 'react'
import api, { errorMessage } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { useFetch } from '@/lib/useFetch'
import { useI18n, type TKey } from '@/lib/i18n'
import type { Company } from '@/lib/types'
import Card, { Alert, PageHeader, Spinner } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import Field from '@/components/ui/Field'
import { HrOnly } from '@/components/AppShell'
import CompanyFields from '@/components/CompanyFields'

// Python weekday numbers (0 = Monday); Algeria's weekend is Friday + Saturday.
const DAYS: TKey[] = ['day.mon', 'day.tue', 'day.wed', 'day.thu', 'day.fri', 'day.sat', 'day.sun']

export default function CompanyPage() {
  const { refresh } = useAuth()
  const { t } = useI18n()
  const { data, loading } = useFetch<Company | null>('/company/')
  const [form, setForm] = useState<Partial<Company>>({})
  const [msg, setMsg] = useState<{ tone: 'sage' | 'rose'; text: string } | null>(null)
  useEffect(() => { if (data) setForm(data) }, [data])

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const r = await api.patch('/company/', form)
      setForm(r.data); refresh()
      setMsg({ tone: 'sage', text: t('company.saved') })
    } catch (err) { setMsg({ tone: 'rose', text: errorMessage(err) }) }
  }

  if (loading) return <Spinner />
  const text = (k: keyof Company, label: TKey, ltr = false) => (
    <Field label={t(label)}>
      <input className={`input ${ltr ? 'text-start' : ''}`} dir={ltr ? 'ltr' : undefined} value={(form[k] as string) ?? ''}
        onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
    </Field>
  )
  const weekend = form.weekend_days || []

  return (
    <HrOnly>
      <PageHeader title={t('nav.company')} subtitle={t('company.subtitle')} />
      <form onSubmit={save} className="space-y-6">
        {msg && <Alert tone={msg.tone}>{msg.text}</Alert>}
        <CompanyFields text={text} />
        <Card title={t('company.time')}>
          <div className="grid gap-6 p-5 sm:grid-cols-2">
            <div>
              <p className="label">{t('company.weekend')}</p>
              <div className="flex flex-wrap gap-2">
                {DAYS.map((d, i) => (
                  <button type="button" key={d}
                    onClick={() => setForm({ ...form, weekend_days: weekend.includes(i) ? weekend.filter((x) => x !== i) : [...weekend, i].sort() })}
                    className={`rounded-full border px-3 py-1 text-xs ${weekend.includes(i) ? 'border-coffee bg-coffee text-white' : 'border-stone bg-white text-muted'}`}>
                    {t(d)}
                  </button>
                ))}
              </div>
              <p className="mt-2 text-xs text-muted">{t('company.weekendHint')}</p>
            </div>
            <Field label={t('company.annualLeave')} hint={t('company.annualLeaveHint')}>
              <input type="number" step="0.5" min="0" className="input" value={form.annual_leave_days ?? ''} onChange={(e) => setForm({ ...form, annual_leave_days: e.target.value })} />
            </Field>
          </div>
        </Card>
        <div className="flex justify-end"><Button type="submit">{t('common.save')}</Button></div>
      </form>
    </HrOnly>
  )
}
