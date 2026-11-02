'use client'
import { useState } from 'react'
import { KeyIcon, PencilSquareIcon } from '@heroicons/react/24/outline'
import api, { errorMessage } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { useFetch } from '@/lib/useFetch'
import { useI18n, type TKey } from '@/lib/i18n'
import { date, initials, PROFILE_FIELDS } from '@/lib/format'
import type { ProfileRequest, User } from '@/lib/types'
import Card, { Alert, PageHeader, Spinner } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { StatusBadge } from '@/components/ui/Badge'
import Modal from '@/components/ui/Modal'
import Field from '@/components/ui/Field'

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  const { t } = useI18n()
  return (
    <div className="grid grid-cols-[minmax(0,10rem)_1fr] gap-3 px-5 py-2.5 text-sm">
      <dt className="text-muted">{label}</dt>
      <dd className="min-w-0 break-words">{value || <span className="text-muted/60">{t('common.notProvided')}</span>}</dd>
    </div>
  )
}

function ChangeRequestModal({ open, onClose, user, onDone }: { open: boolean; onClose: () => void; user: User; onDone: () => void }) {
  const { t } = useI18n()
  const fields: readonly string[] = PROFILE_FIELDS
  const initial = Object.fromEntries(fields.map((f) => [f, String((user as unknown as Record<string, unknown>)[f] ?? '')]))
  const [values, setValues] = useState<Record<string, string>>(initial)
  const [comment, setComment] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const changes = Object.fromEntries(Object.entries(values).filter(([k, v]) => v.trim() !== initial[k].trim()))
    if (!Object.keys(changes).length) { setError(t('profile.noChange')); return }
    setSaving(true)
    try {
      await api.post('/profile-requests/', { changes, comment })
      onDone()
      onClose()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={t('profile.requestTitle')} wide>
      <form onSubmit={submit} className="space-y-4">
        <p className="text-sm text-muted">{t('profile.requestIntro')}</p>
        {error && <Alert>{error}</Alert>}
        <div className="grid gap-4 sm:grid-cols-2">
          {fields.map((f) => (
            <Field key={f} label={t(`field.${f}` as TKey)} className={f === 'address' || f === 'iban' ? 'sm:col-span-2' : ''}>
              {f === 'marital_status' ? (
                <select className="input" value={values[f]} onChange={(e) => setValues({ ...values, [f]: e.target.value })}>
                  {(['single', 'married', 'divorced', 'widowed'] as const).map((m) => <option key={m} value={m}>{t(`marital.${m}`)}</option>)}
                </select>
              ) : (
                <input className="input" type={f === 'birth_date' ? 'date' : f === 'children_count' ? 'number' : 'text'}
                  min={f === 'children_count' ? 0 : undefined} value={values[f]}
                  dir={['iban', 'nin', 'social_security_number'].includes(f) ? 'ltr' : undefined}
                  onChange={(e) => setValues({ ...values, [f]: e.target.value })} />
              )}
            </Field>
          ))}
        </div>
        <Field label={t('profile.messageHr')}>
          <textarea className="input" rows={2} value={comment} onChange={(e) => setComment(e.target.value)} />
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>{t('common.cancel')}</Button>
          <Button type="submit" disabled={saving}>{saving ? t('common.sending') : t('leave.submit')}</Button>
        </div>
      </form>
    </Modal>
  )
}

function PasswordModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useI18n()
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm: '' })
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (form.new_password !== form.confirm) { setError(t('pwd.mismatch')); return }
    try {
      await api.post('/auth/change-password/', { current_password: form.current_password, new_password: form.new_password })
      setDone(true)
      setForm({ current_password: '', new_password: '', confirm: '' })
    } catch (err) {
      setError(errorMessage(err))
    }
  }
  return (
    <Modal open={open} onClose={() => { setDone(false); onClose() }} title={t('pwd.title')}>
      {done ? (
        <div className="space-y-4">
          <Alert tone="sage">{t('pwd.done')}</Alert>
          <div className="flex justify-end"><Button onClick={() => { setDone(false); onClose() }}>{t('common.close')}</Button></div>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          {error && <Alert>{error}</Alert>}
          <Field label={t('pwd.current')}>
            <input type="password" required autoComplete="current-password" className="input" value={form.current_password}
              onChange={(e) => setForm({ ...form, current_password: e.target.value })} />
          </Field>
          <Field label={t('pwd.new')} hint={t('pwd.hint')}>
            <input type="password" required minLength={8} autoComplete="new-password" className="input" value={form.new_password}
              onChange={(e) => setForm({ ...form, new_password: e.target.value })} />
          </Field>
          <Field label={t('pwd.confirm')}>
            <input type="password" required autoComplete="new-password" className="input" value={form.confirm}
              onChange={(e) => setForm({ ...form, confirm: e.target.value })} />
          </Field>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={onClose}>{t('common.cancel')}</Button>
            <Button type="submit">{t('common.save')}</Button>
          </div>
        </form>
      )}
    </Modal>
  )
}

export default function ProfilePage() {
  const { user, refresh } = useAuth()
  const { t, tx } = useI18n()
  // Accountants and the system admin belong to no company: no employee file to show or change.
  const hasEmployeeSpace = !!user?.company
  const { data: requests, reload } = useFetch<ProfileRequest[]>(hasEmployeeSpace ? '/profile-requests/' : null)
  const [contact, setContact] = useState<{ phone: string; emergency_contact: string } | null>(null)
  const [msg, setMsg] = useState('')
  const [requestOpen, setRequestOpen] = useState(false)
  const [pwdOpen, setPwdOpen] = useState(false)

  if (!user) return <Spinner />
  const pending = requests?.find((r) => r.status === 'pending')
  const lastClosed = requests?.find((r) => r.status === 'approved' || r.status === 'rejected')

  const saveContact = async () => {
    if (!contact) return
    try {
      await api.patch('/auth/me/', contact)
      await refresh()
      setContact(null)
      setMsg(t('profile.contactSaved'))
    } catch (err) {
      setMsg(errorMessage(err))
    }
  }

  const cancelRequest = async (r: ProfileRequest) => {
    await api.post(`/profile-requests/${r.id}/cancel/`)
    reload()
  }

  return (
    <div className="space-y-6">
      <PageHeader title={t('profile.title')} actions={<Button variant="outline" onClick={() => setPwdOpen(true)}><KeyIcon className="h-4 w-4" /> {t('login.password')}</Button>} />

      <div className="card flex flex-wrap items-center gap-5 p-5">
        <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-latte text-xl font-semibold text-coffee-dark">{initials(user.full_name)}</span>
        <div>
          <p className="text-lg font-semibold">{user.full_name}</p>
          <p className="text-sm text-muted">{user.job_title || t(`role.${user.role}` as TKey)}{!user.company && user.job_title ? ` · ${t(`role.${user.role}` as TKey)}` : ''}{user.department ? ` · ${user.department}` : ''}</p>
          <p className="text-xs text-muted">{user.email}</p>
        </div>
      </div>

      {pending && (
        <Alert tone="honey">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span>{t('profile.pending', { fields: Object.keys(pending.changes).map((k) => tx(`field.${k}`, k)).join(t('common.listSep')) })}</span>
            <button onClick={() => cancelRequest(pending)} className="text-xs font-medium underline">{t('profile.cancelRequest')}</button>
          </div>
        </Alert>
      )}
      {!pending && lastClosed && lastClosed.status === 'rejected' && (
        <Alert>{t('profile.rejected')}{lastClosed.review_comment ? ` « ${lastClosed.review_comment} »` : ''}</Alert>
      )}
      {msg && <Alert tone="sage">{msg}</Alert>}

      <div className={`grid gap-6 ${user.company ? 'lg:grid-cols-2' : 'max-w-2xl'}`}>
        {user.company && (
        <Card title={t('profile.work')}>
          <dl className="divide-y divide-stone py-1">
            <Row label={t('field.employee_number')} value={user.employee_number} />
            <Row label={t('field.job_title')} value={user.job_title} />
            <Row label={t('field.qualification')} value={user.qualification} />
            <Row label={t('field.department')} value={user.department} />
            <Row label={t('field.contract_type')} value={user.contract_type && tx(`contract.${user.contract_type}`, user.contract_type)} />
            <Row label={t('field.hire_date')} value={user.hire_date && date(user.hire_date)} />
            <Row label={t('field.manager')} value={user.manager?.full_name} />
            <Row label={t('field.company')} value={user.company?.name} />
            <Row label={t('field.payment_method')} value={user.payment_method && tx(`payment.${user.payment_method}`, user.payment_method)} />
          </dl>
        </Card>
        )}

        <Card title={t('profile.contact')}
          action={contact ? (
            <div className="flex gap-1">
              <Button size="sm" variant="ghost" onClick={() => setContact(null)}>{t('common.cancel')}</Button>
              <Button size="sm" onClick={saveContact}>{t('common.save')}</Button>
            </div>
          ) : (
            <Button size="sm" variant="ghost" onClick={() => { setMsg(''); setContact({ phone: user.phone, emergency_contact: user.emergency_contact }) }}>
              <PencilSquareIcon className="h-4 w-4" /> {t('common.edit')}
            </Button>
          )}>
          {contact ? (
            <div className="space-y-4 p-5">
              <Field label={t('field.phone')}>
                <input className="input text-start" dir="ltr" value={contact.phone} onChange={(e) => setContact({ ...contact, phone: e.target.value })} />
              </Field>
              <Field label={t('field.emergency_contact')} hint={t('profile.emergencyHint')}>
                <input className="input" value={contact.emergency_contact} onChange={(e) => setContact({ ...contact, emergency_contact: e.target.value })} />
              </Field>
            </div>
          ) : (
            <dl className="divide-y divide-stone py-1">
              <Row label={t('field.email')} value={user.email} />
              <Row label={t('field.phone')} value={user.phone && <span dir="ltr">{user.phone}</span>} />
              <Row label={t('field.emergency_contact')} value={user.emergency_contact} />
            </dl>
          )}
        </Card>

        {user.company && (
        <Card className="lg:col-span-2" title={t('profile.civil')}
          action={!pending && (
            <Button size="sm" variant="ghost" onClick={() => setRequestOpen(true)}>
              <PencilSquareIcon className="h-4 w-4" /> {t('profile.requestChange')}
            </Button>
          )}>
          <dl className="grid divide-y divide-stone py-1 md:grid-cols-2 md:divide-y-0">
            <div className="divide-y divide-stone">
              <Row label={t('field.last_name')} value={user.last_name} />
              <Row label={t('field.first_name')} value={user.first_name} />
              <Row label={t('field.birth_date')} value={user.birth_date && date(user.birth_date)} />
              <Row label={t('field.marital_status')} value={user.marital_status && `${tx(`marital.${user.marital_status}`, user.marital_status)} · ${t('payslip.children', { n: user.children_count })}`} />
              <Row label={t('field.social_security_number')} value={user.social_security_number && <span dir="ltr">{user.social_security_number}</span>} />
              <Row label={t('field.nin')} value={user.nin && <span dir="ltr">{user.nin}</span>} />
            </div>
            <div className="divide-y divide-stone">
              <Row label={t('field.address')} value={user.address} />
              <Row label={t('field.city')} value={[user.postal_code, user.city].filter(Boolean).join(' ')} />
              <Row label={t('field.bank_name')} value={user.bank_name} />
              <Row label={t('field.iban')} value={user.iban && <span dir="ltr">{user.iban}</span>} />
            </div>
          </dl>
        </Card>
        )}

        {requests && requests.length > 0 && (
          <Card className="lg:col-span-2" title={t('profile.history')}>
            <ul className="divide-y divide-stone">
              {requests.map((r) => (
                <li key={r.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 text-sm">
                  <span>{Object.keys(r.changes).map((k) => tx(`field.${k}`, k)).join(t('common.listSep'))}
                    <span className="ms-2 text-xs text-muted">{date(r.created_at)}</span></span>
                  <StatusBadge status={r.status} />
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>

      {requestOpen && <ChangeRequestModal open onClose={() => setRequestOpen(false)} user={user}
        onDone={() => { reload(); refresh() }} />}
      <PasswordModal open={pwdOpen} onClose={() => setPwdOpen(false)} />
    </div>
  )
}
