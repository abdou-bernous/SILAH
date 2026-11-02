'use client'
import { useEffect, useState } from 'react'
import Modal from './ui/Modal'
import Button from './ui/Button'
import Field from './ui/Field'
import { Alert } from './ui/Card'
import { useI18n } from '@/lib/i18n'

/** Approve / reject with an optional comment. */
export default function ReviewModal({ open, decision, summary, onClose, onConfirm }: {
  open: boolean
  decision: 'approve' | 'reject'
  summary: React.ReactNode
  onClose: () => void
  onConfirm: (comment: string) => Promise<void>
}) {
  const { t } = useI18n()
  const [comment, setComment] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  useEffect(() => { if (open) { setComment(''); setError('') } }, [open])

  const confirm = async () => {
    setSaving(true)
    try {
      await onConfirm(comment)
      onClose()
    } catch (e) {
      setError((e as Error).message || t('common.error'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={decision === 'approve' ? t('review.approveTitle') : t('review.rejectTitle')}>
      <div className="space-y-4">
        <div className="rounded-lg bg-sand/70 p-3 text-sm">{summary}</div>
        {error && <Alert>{error}</Alert>}
        <Field label={decision === 'approve' ? t('review.comment') : t('review.reason')}>
          <textarea className="input" rows={3} value={comment} onChange={(e) => setComment(e.target.value)} />
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>{t('common.cancel')}</Button>
          <Button variant={decision === 'approve' ? 'success' : 'danger'} disabled={saving} onClick={confirm}>
            {decision === 'approve' ? t('common.approve') : t('common.reject')}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
