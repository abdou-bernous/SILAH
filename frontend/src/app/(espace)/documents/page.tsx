'use client'
import { useMemo, useState } from 'react'
import { ArrowDownTrayIcon, BuildingOfficeIcon, DocumentTextIcon, FolderIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline'
import { useFetch } from '@/lib/useFetch'
import { useI18n } from '@/lib/i18n'
import { downloadFile } from '@/lib/api'
import { date, fileSize } from '@/lib/format'
import type { Choice, DocumentItem } from '@/lib/types'
import Card, { EmptyState, PageHeader, Spinner } from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'
import CertificatesCard from '@/components/CertificatesCard'

export default function DocumentsPage() {
  const { t, tx } = useI18n()
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
      <PageHeader title={t('docs.title')} subtitle={t('docs.subtitle')} />
      <CertificatesCard />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[220px_minmax(0,1fr)]">
        <nav className="flex min-w-0 gap-2 overflow-x-auto lg:flex-col lg:gap-1">
          <button onClick={() => setCategory('')}
            className={`flex shrink-0 items-center justify-between gap-3 rounded-lg px-3 py-2 text-sm ${!category ? 'bg-white font-medium shadow-sm' : 'text-muted hover:bg-white/60'}`}>
            {t('docs.all')} <span className="text-xs text-muted">{data?.length ?? ''}</span>
          </button>
          {categories?.filter((c) => counts[c.value]).map((c) => (
            <button key={c.value} onClick={() => setCategory(c.value)}
              className={`flex shrink-0 items-center justify-between gap-3 rounded-lg px-3 py-2 text-sm ${category === c.value ? 'bg-white font-medium shadow-sm' : 'text-muted hover:bg-white/60'}`}>
              {tx(`docCat.${c.value}`, c.label)} <span className="text-xs text-muted">{counts[c.value]}</span>
            </button>
          ))}
        </nav>

        <Card>
          <div className="border-b border-stone p-3">
            <div className="relative">
              <MagnifyingGlassIcon className="pointer-events-none absolute start-3 top-2.5 h-4 w-4 text-muted" />
              <input className="input ps-9" placeholder={t('docs.search')} value={q} onChange={(e) => setQ(e.target.value)} />
            </div>
          </div>
          {loading ? <Spinner /> : filtered.length === 0 ? (
            <EmptyState icon={<FolderIcon />} title={t('docs.empty')}>{t('docs.emptyHint')}</EmptyState>
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
                      {d.employee && !d.viewed_at && <span className="ms-2"><Badge tone="coffee">{t('common.new')}</Badge></span>}
                    </p>
                    <p className="truncate text-xs text-muted">
                      {tx(`docCat.${d.category}`, d.category_label)} · {date(d.created_at)}{d.file_size ? ` · ${fileSize(d.file_size)}` : ''}
                      {!d.employee && ` · ${t('docs.companyDoc')}`}
                    </p>
                    {d.description && <p className="mt-0.5 truncate text-xs text-muted">{d.description}</p>}
                  </div>
                  <button onClick={() => download(d)}
                    className="rounded-lg p-2 text-muted hover:bg-sand hover:text-coffee" aria-label={`${t('common.download')} ${d.title}`}>
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
