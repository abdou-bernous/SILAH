'use client'
import { useState } from 'react'
import api, { errorMessage } from '@/lib/api'
import { useFetch } from '@/lib/useFetch'
import { useI18n } from '@/lib/i18n'
import { date } from '@/lib/format'
import type { CertificateRequest } from '@/lib/types'
import Card, { Alert } from './ui/Card'
import Button from './ui/Button'
import { StatusBadge } from './ui/Badge'

/** The employee's side: ask for a certificate and follow the request. */
export default function CertificatesCard() {
  const { t, tx } = useI18n()
  const { data, reload } = useFetch<CertificateRequest[]>('/certificates/')
  const [error, setError] = useState('')

  const ask = async (kind: string) => {
    setError('')
    try {
      await api.post('/certificates/', { kind })
      reload()
    } catch (err) { setError(errorMessage(err)) }
  }

  return (
    <Card className="mb-6" title={t('cert.title')}
      action={<div className="flex flex-wrap justify-end gap-2">
        <Button size="sm" variant="outline" onClick={() => ask('work')}>{t('certKind.work')}</Button>
        <Button size="sm" variant="outline" onClick={() => ask('salary')}>{t('certKind.salary')}</Button>
      </div>}>
      {error && <div className="p-3"><Alert>{error}</Alert></div>}
      {data?.length ? (
        <ul className="divide-y divide-stone">
          {data.slice(0, 5).map((c) => (
            <li key={c.id} className="flex items-center justify-between gap-3 px-5 py-2.5 text-sm">
              <span>{tx(`certKind.${c.kind}`, c.kind_label)} <span className="text-xs text-muted">· {date(c.created_at)}</span></span>
              <StatusBadge status={c.status} />
            </li>
          ))}
        </ul>
      ) : <p className="px-5 py-3 text-xs text-muted">{t('cert.hint')}</p>}
    </Card>
  )
}
