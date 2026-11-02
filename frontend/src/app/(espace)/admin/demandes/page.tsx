'use client'
import { useState } from 'react'
import { ClipboardDocumentCheckIcon } from '@heroicons/react/24/outline'
import api, { errorMessage } from '@/lib/api'
import { useFetch } from '@/lib/useFetch'
import { useI18n } from '@/lib/i18n'
import { date } from '@/lib/format'
import type { CertificateRequest, ProfileRequest } from '@/lib/types'
import Card, { EmptyState, PageHeader, Spinner } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { StatusBadge } from '@/components/ui/Badge'
import ReviewModal from '@/components/ReviewModal'
import { HrOnly } from '@/components/AppShell'

export default function ProfileRequestsPage() {
  const { t, tx } = useI18n()
  const [showAll, setShowAll] = useState(false)
  // scope=team: one's own requests are decided by another HR user or the accountant.
  const { data, loading, reload } = useFetch<ProfileRequest[]>(`/profile-requests/?scope=team${showAll ? '' : '&status=pending'}`)
  const [review, setReview] = useState<{ r: ProfileRequest; decision: 'approve' | 'reject' } | null>(null)
  const certificates = useFetch<CertificateRequest[]>('/certificates/?scope=team&status=pending')
  const [certReview, setCertReview] = useState<{ c: CertificateRequest; decision: 'approve' | 'reject' } | null>(null)

  const confirmCert = async (comment: string) => {
    if (!certReview) return
    try { await api.post(`/certificates/${certReview.c.id}/${certReview.decision}/`, { comment }) }
    catch (e) { throw new Error(errorMessage(e)) }
    certificates.reload()
  }

  const confirm = async (comment: string) => {
    if (!review) return
    try { await api.post(`/profile-requests/${review.r.id}/${review.decision}/`, { comment }) }
    catch (e) { throw new Error(errorMessage(e)) }
    reload()
  }

  return (
    <HrOnly>
      <PageHeader title={t('nav.profileRequests')} subtitle={t('preq.subtitle')}
        actions={<label className="flex items-center gap-2 text-sm text-muted"><input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} /> {t('preq.showHistory')}</label>} />
      {!!certificates.data?.length && (
        <Card className="mb-4" title={t('cert.requests')}>
          <ul className="divide-y divide-stone">
            {certificates.data.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 text-sm">
                <span><strong className="font-medium">{c.employee.full_name}</strong> · {tx(`certKind.${c.kind}`, c.kind_label)} <span className="text-xs text-muted">· {date(c.created_at)}</span></span>
                <div className="flex gap-2">
                  <Button size="sm" variant="danger" onClick={() => setCertReview({ c, decision: 'reject' })}>{t('common.reject')}</Button>
                  <Button size="sm" variant="success" onClick={() => setCertReview({ c, decision: 'approve' })}>{t('cert.issue')}</Button>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}
      {loading ? <Spinner /> : !data?.length ? (
        <Card><EmptyState icon={<ClipboardDocumentCheckIcon />} title={t('preq.empty')} /></Card>
      ) : (
        <div className="space-y-4">
          {data.map((r) => (
            <Card key={r.id} title={<>{r.employee.full_name} <span className="ms-2 font-normal text-muted">{date(r.created_at)}</span></>}
              action={r.status === 'pending' ? (
                <div className="flex gap-2">
                  <Button size="sm" variant="danger" onClick={() => setReview({ r, decision: 'reject' })}>{t('common.reject')}</Button>
                  <Button size="sm" variant="success" onClick={() => setReview({ r, decision: 'approve' })}>{t('preq.apply')}</Button>
                </div>
              ) : <StatusBadge status={r.status} />}>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="table-head"><tr><th className="px-5 py-2">{t('preq.field')}</th><th className="px-3 py-2">{t('preq.current')}</th><th className="px-5 py-2">{t('preq.new')}</th></tr></thead>
                  <tbody className="divide-y divide-stone">
                    {Object.entries(r.changes).map(([k, v]) => (
                      <tr key={k}>
                        <td className="px-5 py-2.5 text-muted">{tx(`field.${k}`, k)}</td>
                        <td className="px-3 py-2.5 text-muted line-through decoration-latte">{r.current_values[k] || '—'}</td>
                        <td className="px-5 py-2.5 font-medium">{v || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {r.comment && <p className="border-t border-stone px-5 py-3 text-sm text-muted">« {r.comment} »</p>}
            </Card>
          ))}
        </div>
      )}
      {review && <ReviewModal open decision={review.decision} onClose={() => setReview(null)} onConfirm={confirm}
        summary={<>{t('preq.requestOf')} <strong>{review.r.employee.full_name}</strong> : {Object.keys(review.r.changes).map((k) => tx(`field.${k}`, k)).join(t('common.listSep'))}</>} />}
      {certReview && <ReviewModal open decision={certReview.decision} onClose={() => setCertReview(null)} onConfirm={confirmCert}
        summary={<><strong>{certReview.c.employee.full_name}</strong> : {tx(`certKind.${certReview.c.kind}`, certReview.c.kind_label)}</>} />}
    </HrOnly>
  )
}
