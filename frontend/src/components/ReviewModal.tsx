'use client'
import { useEffect, useState } from 'react'
import Modal from './ui/Modal'
import Button from './ui/Button'
import Field from './ui/Field'
import { Alert } from './ui/Card'

/** Approve / reject with an optional comment. */
export default function ReviewModal({ open, decision, summary, onClose, onConfirm }: {
  open: boolean
  decision: 'approve' | 'reject'
  summary: React.ReactNode
  onClose: () => void
  onConfirm: (comment: string) => Promise<void>
}) {
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
      setError((e as Error).message || 'Une erreur est survenue.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={decision === 'approve' ? 'Valider la demande' : 'Refuser la demande'}>
      <div className="space-y-4">
        <div className="rounded-lg bg-sand/70 p-3 text-sm">{summary}</div>
        {error && <Alert>{error}</Alert>}
        <Field label={decision === 'approve' ? 'Commentaire (facultatif)' : 'Motif du refus'}>
          <textarea className="input" rows={3} value={comment} onChange={(e) => setComment(e.target.value)} />
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>Annuler</Button>
          <Button variant={decision === 'approve' ? 'success' : 'danger'} disabled={saving} onClick={confirm}>
            {decision === 'approve' ? 'Valider' : 'Refuser'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
