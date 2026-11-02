'use client'
import { PlusIcon, TrashIcon } from '@heroicons/react/24/outline'
import { useFetch } from '@/lib/useFetch'
import { useI18n } from '@/lib/i18n'
import type { Preset } from '@/lib/types'
import Button from './ui/Button'

export type Tax = 'scale' | 'flat' | 'exempt'
export type Bonus = { preset: string; label: string; label_ar: string; amount: string; contributory: boolean; tax: Tax }
export type BonusPayload = Omit<Bonus, 'preset'>

/** What the API expects: complete lines only. */
export function bonusPayload(bonuses: Bonus[]): BonusPayload[] {
  return bonuses.filter((b) => b.label && Number(b.amount) > 0)
    .map(({ label, label_ar, amount, contributory, tax }) => ({ label, label_ar, amount, contributory, tax }))
}

export function bonusesFrom(items: BonusPayload[]): Bonus[] {
  return items.map((i) => ({ ...i, preset: '', amount: String(Number(i.amount)) }))
}

/** Bonuses applied to a payroll run (or to a correction): presets or free lines, with their CNAS and IRG rules. */
export default function BonusEditor({ value, onChange }: { value: Bonus[]; onChange: (b: Bonus[]) => void }) {
  const { t, locale } = useI18n()
  const { data: presets } = useFetch<Preset[]>('/payslips/presets/')
  const update = (i: number, patch: Partial<Bonus>) => onChange(value.map((x, j) => (j === i ? { ...x, ...patch } : x)))

  const addPreset = (key: string) => {
    const p = presets?.find((x) => x.key === key)
    if (!p) return
    onChange([...value, { preset: p.key, label: p.label, label_ar: p.label_ar, amount: '', contributory: p.contributory, tax: p.tax }])
  }

  return (
    <div className="space-y-3">
      {value.map((b, i) => (
        <div key={i} className="rounded-lg border border-stone p-3">
          <div className="flex gap-2">
            <input className="input" placeholder={t('payroll.labelPlaceholder')}
              value={locale === 'ar' && b.label_ar ? b.label_ar : b.label}
              onChange={(e) => update(i, locale === 'ar' ? { label_ar: e.target.value, label: b.label || e.target.value } : { label: e.target.value })} />
            <button type="button" onClick={() => onChange(value.filter((_, j) => j !== i))} className="rounded-lg p-2 text-muted hover:bg-sand" aria-label={t('common.remove')}><TrashIcon className="h-4 w-4" /></button>
          </div>
          <input type="number" min="0" className="input mt-2" placeholder={t('exp.amount')} value={b.amount}
            onChange={(e) => update(i, { amount: e.target.value })} />
          <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-muted">
            <label className="flex items-center gap-1.5"><input type="checkbox" checked={b.contributory}
              onChange={(e) => update(i, { contributory: e.target.checked })} /> {t('payroll.contributory')}</label>
            <select className="input py-1 text-xs" value={b.tax} onChange={(e) => update(i, { tax: e.target.value as Tax })} aria-label={t('payroll.taxMode')}>
              <option value="scale">{t('payroll.tax.scale')}</option>
              <option value="flat">{t('payroll.tax.flat')}</option>
              <option value="exempt">{t('payroll.tax.exempt')}</option>
            </select>
          </div>
        </div>
      ))}
      <div className="flex gap-2">
        <select className="input text-sm" value="" onChange={(e) => addPreset(e.target.value)} aria-label={t('payroll.addPreset')}>
          <option value="">{t('payroll.addPreset')}</option>
          {presets?.map((p) => <option key={p.key} value={p.key}>{locale === 'ar' ? p.label_ar : p.label}</option>)}
        </select>
        <Button type="button" size="sm" variant="outline" title={t('payroll.addCustom')}
          onClick={() => onChange([...value, { preset: '', label: '', label_ar: '', amount: '', contributory: true, tax: 'scale' }])}>
          <PlusIcon className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
