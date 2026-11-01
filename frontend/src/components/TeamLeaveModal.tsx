'use client'
import { useState } from 'react'
import api, { errorMessage } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { useFetch } from '@/lib/useFetch'
import { useI18n } from '@/lib/i18n'
import type { Choice } from '@/lib/types'
import { Alert } from './ui/Card'
import Button from './ui/Button'
import Field from './ui/Field'
import Modal from './ui/Modal'

type Person = { id: number; full_name: string; manager: number | null }

/** A manager or HR records an absence for a colleague; it is approved at once. */
export default function TeamLeaveModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const { user } = useAuth()
  const { t, tx } = useI18n()
  const { data: directory } = useFetch<Person[]>('/employees/directory/')
  const { data: types } = useFetch<Choice[]>('/leaves/types/')
  const [form, setForm] = useState({ employee: '', leave_type: 'sick', start_date: '', end_date: '', reason: '' })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const people = directory?.filter((p) => p.id !== user?.id && (user?.is_hr || p.manager === user?.id)) || []

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true); setError('')
    try {
      await api.post('/leaves/for_employee/', { ...form, employee: Number(form.employee) })
      onCreated()
      onClose()
    } catch (err) { setError(errorMessage(err)) } finally { setSaving(false) }
  }

  return (
    <Modal open onClose={onClose} title={t('team.addAbsence')}>
      <form onSubmit={submit} className="space-y-4">
        <p className="text-sm text-muted">{t('team.addAbsenceIntro')}</p>
        {error && <Alert>{error}</Alert>}
        <Field label={t('team.colleague')}>
          <select className="input" required value={form.employee} onChange={(e) => setForm({ ...form, employee: e.target.value })}>
            <option value="" />
            {people.map((p) => <option key={p.id} value={p.id}>{p.full_name}</option>)}
          </select>
        </Field>
        <Field label={t('leave.type')}>
          <select className="input" value={form.leave_type} onChange={(e) => setForm({ ...form, leave_type: e.target.value })}>
            {types?.map((ty) => <option key={ty.value} value={ty.value}>{tx(`leaveType.${ty.value}`, ty.label)}</option>)}
          </select>
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t('leave.from')}>
            <input type="date" required className="input" value={form.start_date}
              onChange={(e) => setForm({ ...form, start_date: e.target.value, end_date: form.end_date >= e.target.value ? form.end_date : e.target.value })} />
          </Field>
          <Field label={t('leave.to')}>
            <input type="date" required min={form.start_date} className="input" value={form.end_date}
              onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
          </Field>
        </div>
        <Field label={t('leave.comment')}>
          <textarea className="input" rows={2} value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>{t('common.cancel')}</Button>
          <Button type="submit" disabled={saving}>{saving ? t('common.saving') : t('common.save')}</Button>
        </div>
      </form>
    </Modal>
  )
}
