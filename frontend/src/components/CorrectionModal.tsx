'use client'
import { useEffect, useState } from 'react'
import api, { errorMessage } from '@/lib/api'
import { useFetch } from '@/lib/useFetch'
import { useI18n } from '@/lib/i18n'
import { monthLabel } from '@/lib/format'
import { Alert, Spinner } from './ui/Card'
import Button from './ui/Button'
import Field from './ui/Field'
import Modal from './ui/Modal'
import BonusEditor, { bonusesFrom, bonusPayload, type Bonus, type BonusPayload } from './BonusEditor'

type Defaults = { draft: number | null; reason: string; items: BonusPayload[] }

/** Prepares (or redoes) the corrective payslip of a published one. `payslipId` is the published payslip. */
export default function CorrectionModal({ payslipId, year, month, onClose, onDone }: {
  payslipId: number
  year: number
  month: number
  onClose: () => void
  onDone: (draftId: number) => void
}) {
  const { t } = useI18n()
  const { data, loading, error: loadError } = useFetch<Defaults>(`/payslips/${payslipId}/correct/`)
  const [reason, setReason] = useState('')
  const [items, setItems] = useState<Bonus[]>([])
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!data) return
    setReason(data.reason)
    setItems(bonusesFrom(data.items))
  }, [data])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true); setError('')
    try {
      const r = await api.post(`/payslips/${payslipId}/correct/`, { reason, items: bonusPayload(items) })
      onDone(r.data.id)
    } catch (err) { setError(errorMessage(err)) } finally { setSaving(false) }
  }

  return (
    <Modal open onClose={onClose} title={t('correct.title', { month: monthLabel(year, month) })}>
      {loading ? <Spinner /> : loadError ? <Alert>{loadError}</Alert> : (
        <form onSubmit={submit} className="space-y-4">
          <p className="text-sm text-muted">{t('correct.intro')}</p>
          {error && <Alert>{error}</Alert>}
          <Field label={t('correct.reason')}>
            <textarea className="input min-h-20" required maxLength={500} value={reason}
              placeholder={t('correct.reasonPlaceholder')} onChange={(e) => setReason(e.target.value)} />
          </Field>
          <div>
            <p className="label">{t('correct.items')}</p>
            <BonusEditor value={items} onChange={setItems} />
          </div>
          <p className="rounded-lg bg-sand/70 p-3 text-xs text-muted">{t('correct.note')}</p>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={onClose}>{t('common.cancel')}</Button>
            <Button type="submit" disabled={saving || !reason.trim()}>{t('correct.submit')}</Button>
          </div>
        </form>
      )}
    </Modal>
  )
}
