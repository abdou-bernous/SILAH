'use client'
import { useRouter } from 'next/navigation'
import { BellIcon } from '@heroicons/react/24/outline'
import api from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { useFetch } from '@/lib/useFetch'
import { useI18n } from '@/lib/i18n'
import { relative } from '@/lib/format'
import type { Notification } from '@/lib/types'
import Card, { EmptyState, PageHeader, Spinner } from '@/components/ui/Card'
import Button from '@/components/ui/Button'

export default function NotificationsPage() {
  const router = useRouter()
  const { refreshUnread } = useAuth()
  const { t } = useI18n()
  const { data, loading, reload } = useFetch<Notification[]>('/notifications/')

  const open = async (n: Notification) => {
    if (!n.read) { await api.post(`/notifications/${n.id}/read/`); refreshUnread() }
    if (n.link) router.push(n.link)
    else reload()
  }
  const readAll = async () => { await api.post('/notifications/read_all/'); refreshUnread(); reload() }

  return (
    <div>
      <PageHeader title={t('nav.notifications')}
        actions={data?.some((n) => !n.read) && <Button variant="outline" onClick={readAll}>{t('notif.readAll')}</Button>} />
      <Card>
        {loading ? <Spinner /> : !data?.length ? (
          <EmptyState icon={<BellIcon />} title={t('notif.empty')} />
        ) : (
          <ul className="divide-y divide-stone">
            {data.map((n) => (
              <li key={n.id}>
                <button onClick={() => open(n)} className="flex w-full items-start gap-3 px-5 py-4 text-start hover:bg-cream">
                  <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.read ? 'bg-transparent' : 'bg-coffee'}`} />
                  <span className="min-w-0 flex-1">
                    <span className={`block text-sm ${n.read ? 'text-muted' : 'font-medium'}`}>{n.title}</span>
                    {n.message && <span className="block truncate text-xs text-muted">{n.message}</span>}
                  </span>
                  <span className="shrink-0 text-xs text-muted">{relative(n.created_at)}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
