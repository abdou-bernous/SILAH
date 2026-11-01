'use client'
import { ClockIcon } from '@heroicons/react/24/outline'
import { useFetch } from '@/lib/useFetch'
import { useI18n } from '@/lib/i18n'
import { date } from '@/lib/format'
import type { AuditEntry } from '@/lib/types'
import Card, { EmptyState, PageHeader, Spinner } from '@/components/ui/Card'
import { HrOnly } from '@/components/AppShell'

export default function AuditPage() {
  const { t, tx } = useI18n()
  const { data, loading } = useFetch<AuditEntry[]>('/audit/')

  return (
    <HrOnly>
      <PageHeader title={t('nav.journal')} subtitle={t('journal.subtitle')} />
      <Card>
        {loading ? <Spinner /> : !data?.length ? <EmptyState icon={<ClockIcon />} title={t('journal.empty')} /> : (
          <ul className="divide-y divide-stone">
            {data.map((e) => (
              <li key={e.id} className="px-5 py-3 text-sm">
                <p className="font-medium">{tx(`audit.${e.action}`, e.action)}</p>
                {e.summary && <p className="break-words text-xs text-muted">{e.summary}</p>}
                <p className="mt-0.5 text-[11px] text-muted">
                  {e.actor_name} · {date(e.created_at)} <span dir="ltr">{new Date(e.created_at).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</span>
                </p>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </HrOnly>
  )
}
