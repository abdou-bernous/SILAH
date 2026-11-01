'use client'
import { useState } from 'react'
import { ArrowDownTrayIcon, CloudArrowUpIcon, FolderIcon, TrashIcon } from '@heroicons/react/24/outline'
import api, { downloadFile, errorMessage } from '@/lib/api'
import { useFetch } from '@/lib/useFetch'
import { useI18n } from '@/lib/i18n'
import { date, fileSize } from '@/lib/format'
import type { Choice, DocumentItem } from '@/lib/types'
import Card, { Alert, EmptyState, PageHeader, Spinner } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import Field from '@/components/ui/Field'
import { HrOnly } from '@/components/AppShell'

export default function AdminDocumentsPage() {
  const { t, tx } = useI18n()
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
      setMsg({ tone: 'sage', text: t('adoc.uploaded') })
      setForm({ ...form, title: '', description: '' }); setFile(null); setInputKey((k) => k + 1)
      reload()
    } catch (err) { setMsg({ tone: 'rose', text: errorMessage(err) }) } finally { setSaving(false) }
  }

  const remove = async (d: DocumentItem) => {
    if (!confirm(t('adoc.confirmDelete', { title: d.title }))) return
    await api.delete(`/documents/${d.id}/`); reload()
  }

  return (
    <HrOnly>
      <PageHeader title={t('nav.uploadDocs')} subtitle={t('adoc.subtitle')} />
      <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
        <Card title={t('adoc.new')}>
          <form onSubmit={submit} className="space-y-4 p-5">
            {msg && <Alert tone={msg.tone}>{msg.text}</Alert>}
            <Field label={t('adoc.recipient')}>
              <select className="input" value={form.employee} onChange={(e) => setForm({ ...form, employee: e.target.value })}>
                <option value="">{t('adoc.wholeCompany')}</option>
                {directory?.map((d) => <option key={d.id} value={d.id}>{d.full_name}</option>)}
              </select>
            </Field>
            <Field label={t('common.category')}>
              <select className="input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                {categories?.map((c) => <option key={c.value} value={c.value}>{tx(`docCat.${c.value}`, c.label)}</option>)}
              </select>
            </Field>
            <Field label={t('common.title')}>
              <input className="input" placeholder={t('adoc.titlePlaceholder')} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            </Field>
            <Field label={t('common.descriptionOptional')}>
              <input className="input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </Field>
            <Field label={t('common.file')} hint={t('common.maxSize')}>
              <input key={inputKey} type="file" required className="input file:me-3 file:rounded file:border-0 file:bg-sand file:px-2 file:py-1 file:text-xs"
                onChange={(e) => setFile(e.target.files?.[0] || null)} />
            </Field>
            <Button type="submit" className="w-full" disabled={saving || !file}><CloudArrowUpIcon className="h-4 w-4" /> {saving ? t('common.sending') : t('adoc.upload')}</Button>
          </form>
        </Card>

        <Card title={t('adoc.list')} action={
          <select className="input w-auto py-1 text-xs" value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="">{t('adoc.allEmployees')}</option>
            {directory?.map((d) => <option key={d.id} value={d.id}>{d.full_name}</option>)}
          </select>}>
          {loading ? <Spinner /> : !data?.length ? <EmptyState icon={<FolderIcon />} title={t('docs.empty')} /> : (
            <ul className="divide-y divide-stone">
              {data.map((d) => (
                <li key={d.id} className="flex items-center gap-3 px-5 py-3 text-sm">
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{d.title}</p>
                    <p className="truncate text-xs text-muted">{d.employee_name || t('adoc.wholeCompany')} · {tx(`docCat.${d.category}`, d.category_label)} · {date(d.created_at)} {d.file_size ? `· ${fileSize(d.file_size)}` : ''}
                      {d.employee && ` · ${d.viewed_at ? t('docs.viewed') : t('docs.notViewed')}`}</p>
                  </div>
                  <button onClick={() => downloadFile(`/documents/${d.id}/download/`, d.file_name || 'document')} className="rounded-lg p-1.5 text-muted hover:bg-sand" aria-label={t('common.download')}><ArrowDownTrayIcon className="h-4 w-4" /></button>
                  <button onClick={() => remove(d)} className="rounded-lg p-1.5 text-muted hover:bg-rose hover:text-rose-ink" aria-label={t('common.delete')}><TrashIcon className="h-4 w-4" /></button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </HrOnly>
  )
}
