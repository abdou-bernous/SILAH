'use client'
import { useState } from 'react'
import api, { errorMessage } from '@/lib/api'
import type { Employee } from '@/lib/types'
import { useFetch } from '@/lib/useFetch'
import Button from './ui/Button'
import Field from './ui/Field'
import { Alert } from './ui/Card'

type Dir = { id: number; full_name: string }[]

const BLANK: Partial<Employee> = {
  username: '', email: '', first_name: '', last_name: '', role: 'employee', is_active: true, employee_number: '',
  job_title: '', department: '', contract_type: 'cdi', hire_date: null, birth_date: null, social_security_number: '',
  phone: '', address: '', city: '', postal_code: '', emergency_contact: '', bank_name: '', iban: '', base_salary: '0',
  manager: null, password: '',
}

export default function EmployeeForm({ initial, onSaved, onCancel }: {
  initial?: Employee
  onSaved: (e: Employee) => void
  onCancel?: () => void
}) {
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

  const text = (k: keyof Employee, label: string, props: React.InputHTMLAttributes<HTMLInputElement> = {}, className = '') => (
    <Field label={label} className={className}>
      <input className="input" value={(form[k] as string) ?? ''} onChange={set(k)} {...props} />
    </Field>
  )

  return (
    <form onSubmit={submit} className="space-y-6">
      {error && <Alert>{error}</Alert>}
      <fieldset className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <legend className="mb-3 text-sm font-semibold">Identité & accès</legend>
        {text('last_name', 'Nom', { required: true })}
        {text('first_name', 'Prénom', { required: true })}
        {text('email', 'E-mail', { type: 'email' })}
        {text('username', 'Identifiant de connexion', { required: true })}
        {text('password', initial ? 'Nouveau mot de passe' : 'Mot de passe initial', { type: 'password', required: !initial, autoComplete: 'new-password', placeholder: initial ? 'Laisser vide pour ne pas changer' : '' })}
        <Field label="Rôle">
          <select className="input" value={form.role} onChange={set('role')}>
            <option value="employee">Salarié</option>
            <option value="manager">Manager</option>
            <option value="hr">Gestionnaire RH</option>
          </select>
        </Field>
      </fieldset>

      <fieldset className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <legend className="mb-3 text-sm font-semibold">Contrat</legend>
        {text('employee_number', 'Matricule')}
        {text('job_title', 'Poste')}
        {text('department', 'Service')}
        <Field label="Type de contrat">
          <select className="input" value={form.contract_type} onChange={set('contract_type')}>
            <option value="cdi">CDI</option><option value="cdd">CDD</option><option value="intern">Stage</option><option value="other">Autre</option>
          </select>
        </Field>
        {text('hire_date', "Date d'entrée", { type: 'date' })}
        <Field label="Manager">
          <select className="input" value={form.manager ?? ''} onChange={(e) => setForm({ ...form, manager: e.target.value ? Number(e.target.value) : null })}>
            <option value="">— Aucun —</option>
            {directory?.filter((d) => d.id !== initial?.id).map((d) => <option key={d.id} value={d.id}>{d.full_name}</option>)}
          </select>
        </Field>
        {text('base_salary', 'Salaire de base mensuel (DA)', { type: 'number', min: 0, step: '0.01', required: true })}
      </fieldset>

      <fieldset className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <legend className="mb-3 text-sm font-semibold">Données personnelles</legend>
        {text('birth_date', 'Date de naissance', { type: 'date' })}
        {text('social_security_number', 'N° sécurité sociale')}
        {text('phone', 'Téléphone')}
        {text('address', 'Adresse', {}, 'sm:col-span-2')}
        {text('city', 'Ville')}
        {text('postal_code', 'Code postal')}
        {text('bank_name', 'Banque')}
        {text('iban', 'RIB / IBAN')}
        {text('emergency_contact', "Contact d'urgence", {}, 'sm:col-span-2 lg:col-span-3')}
      </fieldset>

      <div className="flex justify-end gap-2 border-t border-stone pt-4">
        {onCancel && <Button variant="ghost" onClick={onCancel}>Annuler</Button>}
        <Button type="submit" disabled={saving}>{saving ? 'Enregistrement…' : initial ? 'Enregistrer' : 'Créer le salarié'}</Button>
      </div>
    </form>
  )
}
