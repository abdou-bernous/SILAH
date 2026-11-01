'use client'
import { useState } from 'react'
import { KeyIcon, PencilSquareIcon } from '@heroicons/react/24/outline'
import api, { errorMessage } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { useFetch } from '@/lib/useFetch'
import { CONTRACT_LABELS, date, PROFILE_FIELD_LABELS, ROLE_LABELS, initials } from '@/lib/format'
import type { ProfileRequest, User } from '@/lib/types'
import Card, { Alert, PageHeader, Spinner } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { StatusBadge } from '@/components/ui/Badge'
import Modal from '@/components/ui/Modal'
import Field from '@/components/ui/Field'

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[minmax(0,10rem)_1fr] gap-3 px-5 py-2.5 text-sm">
      <dt className="text-muted">{label}</dt>
      <dd className="min-w-0 break-words">{value || <span className="text-muted/60">Non renseigné</span>}</dd>
    </div>
  )
}

function ChangeRequestModal({ open, onClose, user, onDone }: { open: boolean; onClose: () => void; user: User; onDone: () => void }) {
  const fields = Object.keys(PROFILE_FIELD_LABELS)
  const initial = Object.fromEntries(fields.map((f) => [f, String((user as unknown as Record<string, unknown>)[f] ?? '')]))
  const [values, setValues] = useState<Record<string, string>>(initial)
  const [comment, setComment] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const changes = Object.fromEntries(Object.entries(values).filter(([k, v]) => v.trim() !== initial[k].trim()))
    if (!Object.keys(changes).length) { setError('Aucune modification à envoyer.'); return }
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
    <Modal open={open} onClose={onClose} title="Demander une modification de mon dossier" wide>
      <form onSubmit={submit} className="space-y-4">
        <p className="text-sm text-muted">Ces informations figurent sur vos bulletins et servent au versement de votre salaire. Elles seront mises à jour après vérification par le service RH.</p>
        {error && <Alert>{error}</Alert>}
        <div className="grid gap-4 sm:grid-cols-2">
          {fields.map((f) => (
            <Field key={f} label={PROFILE_FIELD_LABELS[f]} className={f === 'address' || f === 'iban' ? 'sm:col-span-2' : ''}>
              <input className="input" type={f === 'birth_date' ? 'date' : 'text'} value={values[f]}
                onChange={(e) => setValues({ ...values, [f]: e.target.value })} />
            </Field>
          ))}
        </div>
        <Field label="Message pour le service RH (facultatif)">
          <textarea className="input" rows={2} value={comment} onChange={(e) => setComment(e.target.value)} />
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>Annuler</Button>
          <Button type="submit" disabled={saving}>{saving ? 'Envoi…' : 'Envoyer la demande'}</Button>
        </div>
      </form>
    </Modal>
  )
}

function PasswordModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm: '' })
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (form.new_password !== form.confirm) { setError('Les deux mots de passe ne correspondent pas.'); return }
    try {
      await api.post('/auth/change-password/', { current_password: form.current_password, new_password: form.new_password })
      setDone(true)
      setForm({ current_password: '', new_password: '', confirm: '' })
    } catch (err) {
      setError(errorMessage(err))
    }
  }
  return (
    <Modal open={open} onClose={() => { setDone(false); onClose() }} title="Changer mon mot de passe">
      {done ? (
        <div className="space-y-4">
          <Alert tone="sage">Votre mot de passe a été modifié.</Alert>
          <div className="flex justify-end"><Button onClick={() => { setDone(false); onClose() }}>Fermer</Button></div>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          {error && <Alert>{error}</Alert>}
          <Field label="Mot de passe actuel">
            <input type="password" required autoComplete="current-password" className="input" value={form.current_password}
              onChange={(e) => setForm({ ...form, current_password: e.target.value })} />
          </Field>
          <Field label="Nouveau mot de passe" hint="8 caractères minimum, évitez les mots trop courants.">
            <input type="password" required minLength={8} autoComplete="new-password" className="input" value={form.new_password}
              onChange={(e) => setForm({ ...form, new_password: e.target.value })} />
          </Field>
          <Field label="Confirmation">
            <input type="password" required autoComplete="new-password" className="input" value={form.confirm}
              onChange={(e) => setForm({ ...form, confirm: e.target.value })} />
          </Field>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={onClose}>Annuler</Button>
            <Button type="submit">Enregistrer</Button>
          </div>
        </form>
      )}
    </Modal>
  )
}

export default function ProfilePage() {
  const { user, refresh } = useAuth()
  const { data: requests, reload } = useFetch<ProfileRequest[]>('/profile-requests/')
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
      setMsg('Coordonnées mises à jour.')
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
      <PageHeader title="Mon profil" actions={<Button variant="outline" onClick={() => setPwdOpen(true)}><KeyIcon className="h-4 w-4" /> Mot de passe</Button>} />

      <div className="card flex flex-wrap items-center gap-5 p-5">
        <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-latte text-xl font-semibold text-coffee-dark">{initials(user.full_name)}</span>
        <div>
          <p className="text-lg font-semibold">{user.full_name}</p>
          <p className="text-sm text-muted">{user.job_title || ROLE_LABELS[user.role]}{user.department ? ` · ${user.department}` : ''}</p>
          <p className="text-xs text-muted">{user.email}</p>
        </div>
      </div>

      {pending && (
        <Alert tone="honey">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span>Une demande de modification ({Object.keys(pending.changes).map((k) => PROFILE_FIELD_LABELS[k] || k).join(', ')}) est en cours de traitement par le service RH.</span>
            <button onClick={() => cancelRequest(pending)} className="text-xs font-medium underline">Annuler la demande</button>
          </div>
        </Alert>
      )}
      {!pending && lastClosed && lastClosed.status === 'rejected' && (
        <Alert>Votre dernière demande de modification a été refusée{lastClosed.review_comment ? ` : « ${lastClosed.review_comment} »` : '.'}</Alert>
      )}
      {msg && <Alert tone="sage">{msg}</Alert>}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Informations professionnelles">
          <dl className="divide-y divide-stone py-1">
            <Row label="Matricule" value={user.employee_number} />
            <Row label="Poste" value={user.job_title} />
            <Row label="Service" value={user.department} />
            <Row label="Contrat" value={CONTRACT_LABELS[user.contract_type]} />
            <Row label="Date d'entrée" value={user.hire_date && date(user.hire_date)} />
            <Row label="Manager" value={user.manager?.full_name} />
            <Row label="Entreprise" value={user.company?.name} />
          </dl>
        </Card>

        <Card title="Coordonnées"
          action={contact ? (
            <div className="flex gap-1">
              <Button size="sm" variant="ghost" onClick={() => setContact(null)}>Annuler</Button>
              <Button size="sm" onClick={saveContact}>Enregistrer</Button>
            </div>
          ) : (
            <Button size="sm" variant="ghost" onClick={() => { setMsg(''); setContact({ phone: user.phone, emergency_contact: user.emergency_contact }) }}>
              <PencilSquareIcon className="h-4 w-4" /> Modifier
            </Button>
          )}>
          {contact ? (
            <div className="space-y-4 p-5">
              <Field label="Téléphone">
                <input className="input" value={contact.phone} onChange={(e) => setContact({ ...contact, phone: e.target.value })} />
              </Field>
              <Field label="Contact d'urgence" hint="Nom et numéro de la personne à prévenir.">
                <input className="input" value={contact.emergency_contact} onChange={(e) => setContact({ ...contact, emergency_contact: e.target.value })} />
              </Field>
            </div>
          ) : (
            <dl className="divide-y divide-stone py-1">
              <Row label="E-mail" value={user.email} />
              <Row label="Téléphone" value={user.phone} />
              <Row label="Contact d'urgence" value={user.emergency_contact} />
            </dl>
          )}
        </Card>

        <Card className="lg:col-span-2" title="État civil, adresse et coordonnées bancaires"
          action={!pending && (
            <Button size="sm" variant="ghost" onClick={() => setRequestOpen(true)}>
              <PencilSquareIcon className="h-4 w-4" /> Demander une modification
            </Button>
          )}>
          <dl className="grid divide-y divide-stone py-1 md:grid-cols-2 md:divide-y-0">
            <div className="divide-y divide-stone">
              <Row label="Nom" value={user.last_name} />
              <Row label="Prénom" value={user.first_name} />
              <Row label="Date de naissance" value={user.birth_date && date(user.birth_date)} />
              <Row label="N° sécurité sociale" value={user.social_security_number} />
            </div>
            <div className="divide-y divide-stone">
              <Row label="Adresse" value={user.address} />
              <Row label="Ville" value={[user.postal_code, user.city].filter(Boolean).join(' ')} />
              <Row label="Banque" value={user.bank_name} />
              <Row label="RIB / IBAN" value={user.iban} />
            </div>
          </dl>
        </Card>

        {requests && requests.length > 0 && (
          <Card className="lg:col-span-2" title="Historique de mes demandes">
            <ul className="divide-y divide-stone">
              {requests.map((r) => (
                <li key={r.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 text-sm">
                  <span>{Object.keys(r.changes).map((k) => PROFILE_FIELD_LABELS[k] || k).join(', ')}
                    <span className="ml-2 text-xs text-muted">{date(r.created_at)}</span></span>
                  <StatusBadge status={r.status} />
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>

      {requestOpen && <ChangeRequestModal open onClose={() => setRequestOpen(false)} user={user} onDone={reload} />}
      <PasswordModal open={pwdOpen} onClose={() => setPwdOpen(false)} />
    </div>
  )
}
