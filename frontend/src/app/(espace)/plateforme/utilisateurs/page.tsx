'use client'
import { useState } from 'react'
import { PencilSquareIcon, ShieldCheckIcon, UserPlusIcon } from '@heroicons/react/24/outline'
import api, { errorMessage } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { useFetch } from '@/lib/useFetch'
import { useI18n } from '@/lib/i18n'
import { date, relative } from '@/lib/format'
import type { CompanyAdmin, PlatformUser } from '@/lib/types'
import Card, { Alert, EmptyState, PageHeader, Spinner } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import Badge from '@/components/ui/Badge'
import Modal from '@/components/ui/Modal'
import Field from '@/components/ui/Field'
import { PlatformOnly } from '@/components/AppShell'

const BLANK: Partial<PlatformUser> = {
  username: '', email: '', first_name: '', last_name: '', role: 'accountant', phone: '', is_active: true, companies: [], password: '',
}

function UserModal({ initial, companies, onClose, onSaved }: {
  initial: PlatformUser | null; companies: CompanyAdmin[]; onClose: () => void; onSaved: () => void
}) {
  const { t } = useI18n()
  const [form, setForm] = useState<Partial<PlatformUser>>(initial ? { ...initial, password: '' } : BLANK)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const set = (k: keyof PlatformUser) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm({ ...form, [k]: e.target.value })
  const selected = form.companies || []

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true); setError('')
    const payload: Record<string, unknown> = { ...form }
    if (initial && !payload.password) delete payload.password
    for (const k of ['full_name', 'last_login', 'date_joined', 'id']) delete payload[k]
    try {
      if (initial) await api.patch(`/platform/users/${initial.id}/`, payload)
      else await api.post('/platform/users/', payload)
      onSaved(); onClose()
    } catch (err) { setError(errorMessage(err)) } finally { setSaving(false) }
  }

  return (
    <Modal open onClose={onClose} title={initial ? initial.full_name : t('pusers.new')} wide>
      <form onSubmit={submit} className="space-y-4">
        {error && <Alert>{error}</Alert>}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t('field.last_name')}><input className="input" required value={form.last_name} onChange={set('last_name')} /></Field>
          <Field label={t('field.first_name')}><input className="input" required value={form.first_name} onChange={set('first_name')} /></Field>
          <Field label={t('field.email')}><input className="input text-start" dir="ltr" type="email" value={form.email} onChange={set('email')} /></Field>
          <Field label={t('field.phone')}><input className="input text-start" dir="ltr" value={form.phone} onChange={set('phone')} /></Field>
          <Field label={t('field.username')}><input className="input text-start" dir="ltr" required value={form.username} onChange={set('username')} /></Field>
          <Field label={initial ? t('emp.form.newPassword') : t('emp.form.initialPassword')}>
            <input className="input" type="password" autoComplete="new-password" required={!initial} value={form.password}
              placeholder={initial ? t('emp.form.keepPassword') : ''} onChange={set('password')} />
          </Field>
          <Field label={t('field.role')}>
            <select className="input" value={form.role} onChange={set('role')}>
              <option value="accountant">{t('role.accountant')}</option>
              <option value="admin">{t('role.admin')}</option>
            </select>
          </Field>
          <label className="flex items-center gap-2 self-end pb-2 text-sm">
            <input type="checkbox" checked={!!form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /> {t('pusers.active')}
          </label>
        </div>
        {form.role === 'accountant' && (
          <div>
            <p className="label">{t('pusers.companies')}</p>
            <div className="grid max-h-56 gap-1 overflow-y-auto rounded-lg border border-stone p-2 sm:grid-cols-2">
              {companies.map((c) => (
                <label key={c.id} className="flex items-center gap-2 rounded px-2 py-1 text-sm hover:bg-sand">
                  <input type="checkbox" checked={selected.includes(c.id)}
                    onChange={(e) => setForm({ ...form, companies: e.target.checked ? [...selected, c.id] : selected.filter((x) => x !== c.id) })} />
                  {c.name}{!c.is_active && <span className="text-xs text-muted"> ({t('firms.inactive')})</span>}
                </label>
              ))}
            </div>
          </div>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>{t('common.cancel')}</Button>
          <Button type="submit" disabled={saving}>{saving ? t('common.saving') : t('common.save')}</Button>
        </div>
      </form>
    </Modal>
  )
}

export default function PlatformUsersPage() {
  const { user } = useAuth()
  const { t } = useI18n()
  const { data, loading, reload } = useFetch<PlatformUser[]>(user?.is_platform_admin ? '/platform/users/' : null)
  const { data: companies } = useFetch<CompanyAdmin[]>(user?.is_platform_admin ? '/companies/' : null)
  const [editing, setEditing] = useState<PlatformUser | null | 'new'>(null)
  const names = new Map((companies || []).map((c) => [c.id, c.name]))

  return (
    <PlatformOnly>
      <PageHeader title={t('nav.platformUsers')} subtitle={t('pusers.subtitle')}
        actions={<Button onClick={() => setEditing('new')}><UserPlusIcon className="h-4 w-4" /> {t('pusers.new')}</Button>} />
      <Card>
        {loading ? <Spinner /> : !data?.length ? <EmptyState icon={<ShieldCheckIcon />} title={t('pusers.empty')} /> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-sm">
              <thead className="table-head">
                <tr>
                  <th className="px-5 py-2.5">{t('pusers.user')}</th>
                  <th className="px-3 py-2.5">{t('field.role')}</th>
                  <th className="px-3 py-2.5">{t('pusers.companies')}</th>
                  <th className="px-3 py-2.5">{t('pusers.lastLogin')}</th>
                  <th className="px-5 py-2.5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-stone">
                {data.map((u) => (
                  <tr key={u.id} className={u.is_active ? '' : 'opacity-60'}>
                    <td className="px-5 py-3"><p className="font-medium">{u.full_name}</p><p className="text-xs text-muted" dir="ltr">{u.email || u.username}</p></td>
                    <td className="px-3 py-3">
                      <Badge tone={u.role === 'admin' ? 'coffee' : 'mist'}>{t(`role.${u.role}`)}</Badge>
                      {!u.is_active && <span className="ms-1"><Badge tone="rose">{t('firms.inactive')}</Badge></span>}
                    </td>
                    <td className="px-3 py-3 text-muted">
                      {u.role === 'admin' ? t('pusers.notApplicable') : u.companies.map((id) => names.get(id)).filter(Boolean).join(t('common.listSep')) || '—'}
                    </td>
                    <td className="px-3 py-3 text-muted">{u.last_login ? relative(u.last_login) : t('pusers.never')}<p className="text-[11px]">{t('pusers.since', { date: date(u.date_joined) })}</p></td>
                    <td className="px-5 py-3 text-end">
                      <button onClick={() => setEditing(u)} className="rounded-lg p-1.5 text-muted hover:bg-sand hover:text-coffee" aria-label={t('common.edit')}>
                        <PencilSquareIcon className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      {editing && <UserModal initial={editing === 'new' ? null : editing} companies={companies || []} onClose={() => setEditing(null)} onSaved={reload} />}
    </PlatformOnly>
  )
}
