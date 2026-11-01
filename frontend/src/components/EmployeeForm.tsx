'use client'
import { useState } from 'react'
import api, { errorMessage } from '@/lib/api'
import type { Employee } from '@/lib/types'
import { useFetch } from '@/lib/useFetch'
import { useI18n, type TKey } from '@/lib/i18n'
import { money } from '@/lib/format'
import Button from './ui/Button'
import Field from './ui/Field'
import { Alert } from './ui/Card'

type Dir = { id: number; full_name: string; role: string }[]

// Salaire national minimum garanti (décret présidentiel 2024).
const SNMG = 24000

const BLANK: Partial<Employee> = {
  username: '', email: '', first_name: '', last_name: '', role: 'employee', is_active: true, employee_number: '',
  job_title: '', department: '', qualification: '', contract_type: 'cdi', hire_date: null, birth_date: null,
  social_security_number: '', nin: '', marital_status: 'single', children_count: 0, is_disabled: false,
  payment_method: 'transfer', phone: '', address: '', city: '', postal_code: '', emergency_contact: '',
  bank_name: '', iban: '', base_salary: '0', manager: null, password: '',
}

export default function EmployeeForm({ initial, onSaved, onCancel }: {
  initial?: Employee
  onSaved: (e: Employee) => void
  onCancel?: () => void
}) {
  const { t } = useI18n()
  const [form, setForm] = useState<Partial<Employee>>(initial ? { ...initial, password: '' } : BLANK)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const { data: directory } = useFetch<Dir>('/employees/directory/')

  const set = (k: keyof Employee) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm({ ...form, [k]: e.target.value })

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    const payload: Record<string, unknown> = { ...form }
    for (const k of ['hire_date', 'birth_date']) if (!payload[k]) payload[k] = null
    if (!payload.manager) payload.manager = null
    payload.children_count = Number(payload.children_count) || 0
    if (initial && !payload.password) delete payload.password
    delete payload.full_name
    delete payload.manager_name
    try {
      const r = initial ? await api.patch(`/employees/${initial.id}/`, payload) : await api.post('/employees/', payload)
      onSaved(r.data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const text = (k: keyof Employee, label: TKey, props: React.InputHTMLAttributes<HTMLInputElement> = {}, className = '') => (
    <Field label={t(label)} className={className}>
      <input className="input" value={(form[k] as string | number) ?? ''} onChange={set(k)} {...props} />
    </Field>
  )
  const ltr = { dir: 'ltr' as const, className: 'input text-start' }
  const salary = Number(form.base_salary || 0)

  return (
    <form onSubmit={submit} className="space-y-6">
      {error && <Alert>{error}</Alert>}
      <fieldset className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <legend className="mb-3 text-sm font-semibold">{t('emp.form.identity')}</legend>
        {text('last_name', 'field.last_name', { required: true })}
        {text('first_name', 'field.first_name', { required: true })}
        {text('email', 'field.email', { type: 'email', ...ltr })}
        {text('username', 'field.username', { required: true, ...ltr })}
        {text('password', initial ? 'emp.form.newPassword' : 'emp.form.initialPassword', {
          type: 'password', required: !initial, autoComplete: 'new-password',
          placeholder: initial ? t('emp.form.keepPassword') : '' })}
        <Field label={t('field.role')}>
          <select className="input" value={form.role} onChange={set('role')}>
            <option value="employee">{t('role.employee')}</option>
            <option value="manager">{t('role.manager')}</option>
            <option value="hr">{t('role.hr')}</option>
          </select>
        </Field>
      </fieldset>

      <fieldset className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <legend className="mb-3 text-sm font-semibold">{t('emp.form.contract')}</legend>
        {text('employee_number', 'field.employee_number')}
        {text('job_title', 'field.job_title')}
        {text('department', 'field.department')}
        {text('qualification', 'field.qualification', { placeholder: t('emp.form.qualificationHint') })}
        <Field label={t('field.contract_type')}>
          <select className="input" value={form.contract_type} onChange={set('contract_type')}>
            {(['cdi', 'cdd', 'intern', 'other'] as const).map((c) => <option key={c} value={c}>{t(`contract.${c}`)}</option>)}
          </select>
        </Field>
        {text('hire_date', 'field.hire_date', { type: 'date' })}
        <Field label={t('field.manager')}>
          <select className="input" value={form.manager ?? ''} onChange={(e) => setForm({ ...form, manager: e.target.value ? Number(e.target.value) : null })}>
            <option value="">{t('common.none')}</option>
            {directory?.filter((d) => d.id !== initial?.id && (d.role === 'manager' || d.role === 'hr' || d.id === form.manager))
              .map((d) => <option key={d.id} value={d.id}>{d.full_name}</option>)}
          </select>
        </Field>
        <Field label={t('field.base_salary')}
          hint={salary > 0 && salary < SNMG
            ? <span className="text-rose-ink">{t('emp.form.belowSnmg', { snmg: money(SNMG) })}</span>
            : t('emp.form.snmgHint', { snmg: money(SNMG) })}>
          <input className="input" type="number" min={0} step="0.01" required value={form.base_salary ?? ''} onChange={set('base_salary')} />
        </Field>
        <Field label={t('field.payment_method')}>
          <select className="input" value={form.payment_method} onChange={set('payment_method')}>
            {(['transfer', 'cheque', 'cash'] as const).map((c) => <option key={c} value={c}>{t(`payment.${c}`)}</option>)}
          </select>
        </Field>
      </fieldset>

      <fieldset className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <legend className="mb-3 text-sm font-semibold">{t('emp.form.personal')}</legend>
        {text('birth_date', 'field.birth_date', { type: 'date' })}
        {text('social_security_number', 'field.social_security_number', ltr)}
        {text('nin', 'field.nin', ltr)}
        <Field label={t('field.marital_status')}>
          <select className="input" value={form.marital_status} onChange={set('marital_status')}>
            {(['single', 'married', 'divorced', 'widowed'] as const).map((c) => <option key={c} value={c}>{t(`marital.${c}`)}</option>)}
          </select>
        </Field>
        {text('children_count', 'field.children_count', { type: 'number', min: 0, max: 20 })}
        <label className="flex items-center gap-2 self-end pb-2 text-sm">
          <input type="checkbox" checked={!!form.is_disabled} onChange={(e) => setForm({ ...form, is_disabled: e.target.checked })} />
          {t('field.is_disabled')}
        </label>
        {text('phone', 'field.phone', ltr)}
        {text('address', 'field.address', {}, 'sm:col-span-2')}
        {text('city', 'field.city')}
        {text('postal_code', 'field.postal_code')}
        {text('bank_name', 'field.bank_name')}
        {text('iban', 'field.iban', ltr)}
        {text('emergency_contact', 'field.emergency_contact', {}, 'sm:col-span-2 lg:col-span-3')}
      </fieldset>

      <div className="flex justify-end gap-2 border-t border-stone pt-4">
        {onCancel && <Button variant="ghost" onClick={onCancel}>{t('common.cancel')}</Button>}
        <Button type="submit" disabled={saving}>{saving ? t('common.saving') : initial ? t('common.save') : t('emp.form.create')}</Button>
      </div>
    </form>
  )
}
