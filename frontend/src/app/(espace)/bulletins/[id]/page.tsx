'use client'
import { useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { ArrowDownTrayIcon, ArrowLeftIcon, PencilSquareIcon, PrinterIcon } from '@heroicons/react/24/outline'
import { useFetch } from '@/lib/useFetch'
import { useI18n } from '@/lib/i18n'
import api, { downloadFile, errorMessage } from '@/lib/api'
import { date, money } from '@/lib/format'
import type { PayslipDetail } from '@/lib/types'
import { Alert, Spinner } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import Badge, { StatusBadge } from '@/components/ui/Badge'
import PayslipView from '@/components/PayslipView'
import CorrectionModal from '@/components/CorrectionModal'
import { useAuth } from '@/context/AuthContext'

/** Signed difference of net pay, e.g. "+4 646,40 DA". */
function signed(diff: number) {
  return `${diff >= 0 ? '+' : '−'}${money(Math.abs(diff))}`
}

export default function PayslipPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const { user } = useAuth()
  const { t } = useI18n()
  const { data, loading, error, reload } = useFetch<PayslipDetail>(`/payslips/${id}/`)
  const [correcting, setCorrecting] = useState<number | null>(null)
  const [actionError, setActionError] = useState('')

  if (loading && !data) return <Spinner />
  if (error || !data) return <Alert>{error || t('payslips.notFound')}</Alert>
  const own = data.employee.id === user?.id
  const hr = !!user?.is_hr
  const corrective = data.replaces !== null
  const diff = corrective && data.previous_net !== null ? Number(data.net_salary) - Number(data.previous_net) : 0
  const pendingCorrection = data.replaced_by?.status === 'draft' ? data.replaced_by.id : null

  const publish = async () => {
    if (!confirm(t('correct.confirmPublish'))) return
    try { await api.post(`/payslips/${data.id}/publish/`); setActionError(''); reload() } catch (err) { setActionError(errorMessage(err)) }
  }
  const cancel = async () => {
    if (!confirm(t('correct.confirmCancel'))) return
    try { await api.delete(`/payslips/${data.id}/`); router.push(`/bulletins/${data.replaces}`) } catch (err) { setActionError(errorMessage(err)) }
  }
  const done = (draftId: number) => {
    setCorrecting(null)
    if (String(draftId) === id) reload()
    else router.push(`/bulletins/${draftId}`)
  }

  return (
    <div className="space-y-4">
      <div className="no-print flex flex-wrap items-center justify-between gap-3">
        <Button variant="ghost" href={own ? '/bulletins' : '/admin/paie'}>
          <ArrowLeftIcon className="h-4 w-4 rtl:rotate-180" /> {t('common.back')}
        </Button>
        <div className="flex flex-wrap items-center gap-2">
          {corrective && <Badge tone="mist">{t('correct.badge')}</Badge>}
          {data.status !== 'published' && <StatusBadge status={data.status} />}
          {hr && data.status === 'published' && !pendingCorrection && (
            <Button variant="outline" onClick={() => setCorrecting(data.id)}><PencilSquareIcon className="h-4 w-4" /> {t('correct.action')}</Button>
          )}
          <Button variant="outline" onClick={() => window.print()}><PrinterIcon className="h-4 w-4" /> {t('common.print')}</Button>
          <Button onClick={() => downloadFile(`/payslips/${data.id}/pdf/`, 'bulletin.pdf')}>
            <ArrowDownTrayIcon className="h-4 w-4" /> {t('common.downloadPdf')}
          </Button>
        </div>
      </div>

      {actionError && <Alert>{actionError}</Alert>}
      {corrective && (
        <Alert tone={data.status === 'draft' ? 'honey' : 'sage'}>
          <p>{t('correct.banner', { date: date(data.previous_published_at) })}</p>
          {data.correction_reason && <p className="mt-0.5">{t('correct.bannerReason', { reason: data.correction_reason })}</p>}
          <p className="mt-0.5 font-medium">
            {t('correct.difference')} <span dir="ltr">{signed(diff)}</span>
            {hr && diff !== 0 && <> · {diff > 0 ? t('correct.toPay') : t('correct.toRecover')}</>}
          </p>
          {hr && data.status === 'draft' && (
            <div className="no-print mt-3 flex flex-wrap gap-2">
              <Button size="sm" onClick={publish}>{t('correct.publish')}</Button>
              <Button size="sm" variant="outline" onClick={() => setCorrecting(data.replaces)}>{t('correct.redo')}</Button>
              <Button size="sm" variant="danger" onClick={cancel}>{t('correct.cancel')}</Button>
            </div>
          )}
        </Alert>
      )}
      {data.status === 'replaced' && (
        <Alert tone="mist">
          {t('correct.replaced')}
          {data.replaced_by && <> <Link href={`/bulletins/${data.replaced_by.id}`} className="font-medium underline">{t('correct.seeCurrent')}</Link></>}
        </Alert>
      )}
      {hr && pendingCorrection && (
        <Alert tone="honey">
          {t('correct.inProgress')} <Link href={`/bulletins/${pendingCorrection}`} className="font-medium underline">{t('correct.seeDraft')}</Link>
        </Alert>
      )}

      <PayslipView p={data} />
      {correcting !== null && (
        <CorrectionModal payslipId={correcting} year={data.year} month={data.month}
          onClose={() => setCorrecting(null)} onDone={done} />
      )}
    </div>
  )
}
