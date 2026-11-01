'use client'
import { useState } from 'react'
import { ArrowDownTrayIcon, CloudArrowUpIcon, FolderIcon, TrashIcon } from '@heroicons/react/24/outline'
import api, { downloadFile, errorMessage } from '@/lib/api'
import { useFetch } from '@/lib/useFetch'
import { date, fileSize } from '@/lib/format'
import type { Choice, DocumentItem } from '@/lib/types'
import Card, { Alert, EmptyState, PageHeader, Spinner } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import Field from '@/components/ui/Field'
import { HrOnly } from '@/components/AppShell'

export default function AdminDocumentsPage() {
  const { data: directory } = useFetch<{ id: number; full_name: string }[]>('/employees/directory/')
  const { data: categories } = useFetch<Choice[]>('/documents/categories/')
  const [filter, setFilter] = useState('')
  const { data, loading, reload } = useFetch<DocumentItem[]>(`/documents/?scope=all${filter ? `&employee=${filter}` : ''}`)
  const [form, setForm] = useState({ employee: '', category: 'certificate', title: '', description: '' })
  const [file, setFile] = useState<File | null>(null)
  const [msg, setMsg] = useState<{ tone: 'sage' | 'rose'; text: string } | null>(null)
  const [saving, setSaving] = useState(false)
  const [inputKey, setInputKey] = useState(0)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return
    setSaving(true); setMsg(null)
    try {
      const fd = new FormData()
      if (form.employee) fd.append('employee', form.employee)
      fd.append('category', form.category)
      fd.append('title', form.title || file.name)
      fd.append('description', form.description)
      fd.append('file', file)
      await api.post('/documents/', fd)
      setMsg({ tone: 'sage', text: 'Document déposé, le salarié a été notifié.' })
      setForm({ ...form, title: '', description: '' }); setFile(null); setInputKey((k) => k + 1)
      reload()
    } catch (err) { setMsg({ tone: 'rose', text: errorMessage(err) }) } finally { setSaving(false) }
  }

  const remove = async (d: DocumentItem) => {
    if (!confirm(`Supprimer « ${d.title} » ?`)) return
    await api.delete(`/documents/${d.id}/`); reload()
  }

  return (
    <HrOnly>
      <PageHeader title="Dépôt de documents" subtitle="Déposez un document dans le coffre-fort d'un salarié, ou pour toute l'entreprise." />
      <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
        <Card title="Nouveau document">
          <form onSubmit={submit} className="space-y-4 p-5">
            {msg && <Alert tone={msg.tone}>{msg.text}</Alert>}
            <Field label="Destinataire">
              <select className="input" value={form.employee} onChange={(e) => setForm({ ...form, employee: e.target.value })}>
                <option value="">Toute l&apos;entreprise</option>
                {directory?.map((d) => <option key={d.id} value={d.id}>{d.full_name}</option>)}
              </select>
            </Field>
            <Field label="Catégorie">
              <select className="input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                {categories?.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </Field>
            <Field label="Titre">
              <input className="input" placeholder="Ex. : Attestation de travail" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            </Field>
            <Field label="Description (facultatif)">
              <input className="input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </Field>
            <Field label="Fichier" hint="10 Mo maximum.">
              <input key={inputKey} type="file" required className="input file:mr-3 file:rounded file:border-0 file:bg-sand file:px-2 file:py-1 file:text-xs"
                onChange={(e) => setFile(e.target.files?.[0] || null)} />
            </Field>
            <Button type="submit" className="w-full" disabled={saving || !file}><CloudArrowUpIcon className="h-4 w-4" /> {saving ? 'Envoi…' : 'Déposer'}</Button>
          </form>
        </Card>

        <Card title="Documents déposés" action={
          <select className="input w-auto py-1 text-xs" value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="">Tous les salariés</option>
            {directory?.map((d) => <option key={d.id} value={d.id}>{d.full_name}</option>)}
          </select>}>
          {loading ? <Spinner /> : !data?.length ? <EmptyState icon={<FolderIcon />} title="Aucun document" /> : (
            <ul className="divide-y divide-stone">
              {data.map((d) => (
                <li key={d.id} className="flex items-center gap-3 px-5 py-3 text-sm">
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{d.title}</p>
                    <p className="truncate text-xs text-muted">{d.employee_name || 'Toute l\'entreprise'} · {d.category_label} · {date(d.created_at)} {d.file_size ? `· ${fileSize(d.file_size)}` : ''}
                      {d.employee && ` · ${d.viewed_at ? 'consulté' : 'non consulté'}`}</p>
                  </div>
                  <button onClick={() => downloadFile(`/documents/${d.id}/download/`, d.file_name || 'document')} className="rounded-lg p-1.5 text-muted hover:bg-sand" aria-label="Télécharger"><ArrowDownTrayIcon className="h-4 w-4" /></button>
                  <button onClick={() => remove(d)} className="rounded-lg p-1.5 text-muted hover:bg-rose hover:text-rose-ink" aria-label="Supprimer"><TrashIcon className="h-4 w-4" /></button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </HrOnly>
  )
}
