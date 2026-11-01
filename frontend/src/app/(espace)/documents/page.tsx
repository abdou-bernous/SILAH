'use client'
import { useMemo, useState } from 'react'
import { ArrowDownTrayIcon, BuildingOfficeIcon, DocumentTextIcon, FolderIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline'
import { useFetch } from '@/lib/useFetch'
import { downloadFile } from '@/lib/api'
import { date, fileSize } from '@/lib/format'
import type { Choice, DocumentItem } from '@/lib/types'
import Card, { EmptyState, PageHeader, Spinner } from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'

export default function DocumentsPage() {
  const { data, loading, reload } = useFetch<DocumentItem[]>('/documents/')
  const { data: categories } = useFetch<Choice[]>('/documents/categories/')
  const [category, setCategory] = useState('')
  const [q, setQ] = useState('')

  const filtered = useMemo(() => (data || []).filter((d) =>
    (!category || d.category === category) && (!q || d.title.toLowerCase().includes(q.toLowerCase()))), [data, category, q])

  const counts = useMemo(() => {
    const c: Record<string, number> = {}
    for (const d of data || []) c[d.category] = (c[d.category] || 0) + 1
    return c
  }, [data])

  const download = async (d: DocumentItem) => {
    await downloadFile(`/documents/${d.id}/download/`, d.file_name || 'document')
    if (!d.viewed_at) reload()
  }

  return (
    <div>
      <PageHeader title="Mes documents" subtitle="Votre coffre-fort numérique : contrats, attestations et documents de l'entreprise." />
      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        <nav className="flex gap-2 overflow-x-auto lg:flex-col lg:gap-1">
          <button onClick={() => setCategory('')}
            className={`flex shrink-0 items-center justify-between gap-3 rounded-lg px-3 py-2 text-sm ${!category ? 'bg-white font-medium shadow-sm' : 'text-muted hover:bg-white/60'}`}>
            Tous les documents <span className="text-xs text-muted">{data?.length ?? ''}</span>
          </button>
          {categories?.filter((c) => counts[c.value]).map((c) => (
            <button key={c.value} onClick={() => setCategory(c.value)}
              className={`flex shrink-0 items-center justify-between gap-3 rounded-lg px-3 py-2 text-sm ${category === c.value ? 'bg-white font-medium shadow-sm' : 'text-muted hover:bg-white/60'}`}>
              {c.label} <span className="text-xs text-muted">{counts[c.value]}</span>
            </button>
          ))}
        </nav>

        <Card>
          <div className="border-b border-stone p-3">
            <div className="relative">
              <MagnifyingGlassIcon className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted" />
              <input className="input pl-9" placeholder="Rechercher un document" value={q} onChange={(e) => setQ(e.target.value)} />
            </div>
          </div>
          {loading ? <Spinner /> : filtered.length === 0 ? (
            <EmptyState icon={<FolderIcon />} title="Aucun document">Les documents déposés par votre service RH apparaîtront ici.</EmptyState>
          ) : (
            <ul className="divide-y divide-stone">
              {filtered.map((d) => (
                <li key={d.id} className="flex items-center gap-4 px-5 py-3.5">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-sand text-coffee">
                    {d.employee ? <DocumentTextIcon className="h-5 w-5" /> : <BuildingOfficeIcon className="h-5 w-5" />}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">
                      {d.title}
                      {d.employee && !d.viewed_at && <span className="ml-2"><Badge tone="coffee">Nouveau</Badge></span>}
                    </p>
                    <p className="truncate text-xs text-muted">
                      {d.category_label} · {date(d.created_at)}{d.file_size ? ` · ${fileSize(d.file_size)}` : ''}
                      {!d.employee && ' · Document entreprise'}
                    </p>
                    {d.description && <p className="mt-0.5 truncate text-xs text-muted">{d.description}</p>}
                  </div>
                  <button onClick={() => download(d)}
                    className="rounded-lg p-2 text-muted hover:bg-sand hover:text-coffee" aria-label={`Télécharger ${d.title}`}>
                    <ArrowDownTrayIcon className="h-5 w-5" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  )
}
