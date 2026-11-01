'use client'
import { useState } from 'react'
import { ClipboardDocumentCheckIcon } from '@heroicons/react/24/outline'
import api, { errorMessage } from '@/lib/api'
import { useFetch } from '@/lib/useFetch'
import { date, PROFILE_FIELD_LABELS } from '@/lib/format'
import type { ProfileRequest } from '@/lib/types'
import Card, { EmptyState, PageHeader, Spinner } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { StatusBadge } from '@/components/ui/Badge'
import ReviewModal from '@/components/ReviewModal'
import { HrOnly } from '@/components/AppShell'

export default function ProfileRequestsPage() {
  const [showAll, setShowAll] = useState(false)
  const { data, loading, reload } = useFetch<ProfileRequest[]>(`/profile-requests/?scope=all${showAll ? '' : '&status=pending'}`)
  const [review, setReview] = useState<{ r: ProfileRequest; decision: 'approve' | 'reject' } | null>(null)

  const confirm = async (comment: string) => {
    if (!review) return
    try { await api.post(`/profile-requests/${review.r.id}/${review.decision}/`, { comment }) }
    catch (e) { throw new Error(errorMessage(e)) }
    reload()
  }

  return (
    <HrOnly>
      <PageHeader title="Modifications de dossier" subtitle="Les salariés demandent ici la mise à jour de leur adresse, RIB ou état civil."
        actions={<label className="flex items-center gap-2 text-sm text-muted"><input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} /> Afficher l&apos;historique</label>} />
      {loading ? <Spinner /> : !data?.length ? (
        <Card><EmptyState icon={<ClipboardDocumentCheckIcon />} title="Aucune demande en attente" /></Card>
      ) : (
        <div className="space-y-4">
          {data.map((r) => (
            <Card key={r.id} title={<>{r.employee.full_name} <span className="ml-2 font-normal text-muted">{date(r.created_at)}</span></>}
              action={r.status === 'pending' ? (
                <div className="flex gap-2">
                  <Button size="sm" variant="danger" onClick={() => setReview({ r, decision: 'reject' })}>Refuser</Button>
                  <Button size="sm" variant="success" onClick={() => setReview({ r, decision: 'approve' })}>Appliquer</Button>
                </div>
              ) : <StatusBadge status={r.status} />}>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="table-head"><tr><th className="px-5 py-2">Champ</th><th className="px-3 py-2">Valeur actuelle</th><th className="px-5 py-2">Nouvelle valeur</th></tr></thead>
                  <tbody className="divide-y divide-stone">
                    {Object.entries(r.changes).map(([k, v]) => (
                      <tr key={k}>
                        <td className="px-5 py-2.5 text-muted">{PROFILE_FIELD_LABELS[k] || k}</td>
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
        summary={<>Demande de <strong>{review.r.employee.full_name}</strong> : {Object.keys(review.r.changes).map((k) => PROFILE_FIELD_LABELS[k] || k).join(', ')}</>} />}
    </HrOnly>
  )
}
