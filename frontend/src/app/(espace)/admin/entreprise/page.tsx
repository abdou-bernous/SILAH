'use client'
import { useEffect, useState } from 'react'
import api, { errorMessage } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { useFetch } from '@/lib/useFetch'
import type { Company } from '@/lib/types'
import Card, { Alert, PageHeader, Spinner } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import Field from '@/components/ui/Field'
import { HrOnly } from '@/components/AppShell'

const DAYS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']

export default function CompanyPage() {
  const { refresh } = useAuth()
  const { data, loading } = useFetch<Company | null>('/company/')
  const [form, setForm] = useState<Partial<Company>>({})
  const [msg, setMsg] = useState<{ tone: 'sage' | 'rose'; text: string } | null>(null)
  useEffect(() => { if (data) setForm(data) }, [data])

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const r = await api.patch('/company/', form)
      setForm(r.data); refresh()
      setMsg({ tone: 'sage', text: 'Informations enregistrées.' })
    } catch (err) { setMsg({ tone: 'rose', text: errorMessage(err) }) }
  }

  if (loading) return <Spinner />
  const text = (k: keyof Company, label: string) => (
    <Field label={label}><input className="input" value={(form[k] as string) ?? ''} onChange={(e) => setForm({ ...form, [k]: e.target.value })} /></Field>
  )
  const weekend = form.weekend_days || []

  return (
    <HrOnly>
      <PageHeader title="Entreprise" subtitle="Ces informations apparaissent en en-tête des bulletins de paie." />
      <form onSubmit={save} className="space-y-6">
        {msg && <Alert tone={msg.tone}>{msg.text}</Alert>}
        <Card title="Identité de l'employeur">
          <div className="grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-3">
            {text('name', 'Raison sociale')}
            {text('legal_form', 'Forme juridique')}
            {text('city', 'Ville')}
            <div className="sm:col-span-2 lg:col-span-3">{text('address', 'Adresse')}</div>
            {text('nif', 'NIF')}
            {text('nis', 'NIS')}
            {text('rc', 'Registre du commerce')}
            {text('cnas_number', 'N° employeur CNAS')}
          </div>
        </Card>
        <Card title="Temps de travail et congés">
          <div className="grid gap-6 p-5 sm:grid-cols-2">
            <div>
              <p className="label">Jours de repos hebdomadaire</p>
              <div className="flex flex-wrap gap-2">
                {DAYS.map((d, i) => (
                  <button type="button" key={d}
                    onClick={() => setForm({ ...form, weekend_days: weekend.includes(i) ? weekend.filter((x) => x !== i) : [...weekend, i].sort() })}
                    className={`rounded-full border px-3 py-1 text-xs ${weekend.includes(i) ? 'border-coffee bg-coffee text-white' : 'border-stone bg-white text-muted'}`}>
                    {d}
                  </button>
                ))}
              </div>
              <p className="mt-2 text-xs text-muted">Ces jours ne sont pas décomptés dans les demandes d&apos;absence.</p>
            </div>
            <Field label="Congé annuel acquis par an (jours ouvrés)" hint="Valeur appliquée aux nouveaux compteurs annuels.">
              <input type="number" step="0.5" min="0" className="input" value={form.annual_leave_days ?? ''} onChange={(e) => setForm({ ...form, annual_leave_days: e.target.value })} />
            </Field>
          </div>
        </Card>
        <div className="flex justify-end"><Button type="submit">Enregistrer</Button></div>
      </form>
    </HrOnly>
  )
}
