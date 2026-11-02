'use client'
import { useState } from 'react'
import { TrashIcon } from '@heroicons/react/24/outline'
import api, { errorMessage } from '@/lib/api'
import { useFetch } from '@/lib/useFetch'
import { useI18n } from '@/lib/i18n'
import { money } from '@/lib/format'
import type { PayItem, Preset } from '@/lib/types'
import Card, { Alert } from './ui/Card'
import Button from './ui/Button'

/** Pay elements that come back on every payslip of one employee. */
export default function PayItemsCard({ employeeId }: { employeeId: number }) {
  const { t, locale } = useI18n()
  const { data, reload } = useFetch<PayItem[]>(`/pay-items/?employee=${employeeId}`)
  const { data: presets } = useFetch<Preset[]>('/payslips/presets/')
  const [preset, setPreset] = useState('')
  const [amount, setAmount] = useState('')
  const [error, setError] = useState('')

  const add = async () => {
    const p = presets?.find((x) => x.key === preset)
    if (!p || !(Number(amount) > 0)) return
    try {
      await api.post('/pay-items/', {
        employee: employeeId, label: p.label, label_ar: p.label_ar, amount, contributory: p.contributory, tax: p.tax,
      })
      setPreset(''); setAmount(''); setError('')
      reload()
    } catch (err) { setError(errorMessage(err)) }
  }

  const remove = async (item: PayItem) => {
    await api.delete(`/pay-items/${item.id}/`)
    reload()
  }

  return (
    <Card className="lg:col-span-2" title={t('pay.items')}>
      <p className="border-b border-stone px-5 py-2.5 text-xs text-muted">{t('pay.itemsHint')}</p>
      {error && <div className="p-3"><Alert>{error}</Alert></div>}
      <ul className="divide-y divide-stone">
        {data?.length ? data.map((i) => (
          <li key={i.id} className="flex items-center gap-3 px-5 py-2.5 text-sm">
            <span className="min-w-0 flex-1 truncate">{locale === 'ar' && i.label_ar ? i.label_ar : i.label}</span>
            <span className="tabular-nums">{money(i.amount)}</span>
            <button onClick={() => remove(i)} className="rounded-lg p-1.5 text-muted hover:bg-rose hover:text-rose-ink" aria-label={t('common.remove')}>
              <TrashIcon className="h-4 w-4" />
            </button>
          </li>
        )) : <li className="px-5 py-5 text-center text-sm text-muted">{t('pay.none')}</li>}
      </ul>
      <div className="flex flex-wrap gap-2 border-t border-stone p-3">
        <select className="input min-w-0 basis-full sm:basis-auto sm:flex-1" value={preset} onChange={(e) => setPreset(e.target.value)} aria-label={t('payroll.addPreset')}>
          <option value="">{t('payroll.addPreset')}</option>
          {presets?.map((p) => <option key={p.key} value={p.key}>{locale === 'ar' ? p.label_ar : p.label}</option>)}
        </select>
        <input type="number" min="0" className="input min-w-0 flex-1 sm:w-32 sm:flex-none" placeholder={t('exp.amount')} value={amount} onChange={(e) => setAmount(e.target.value)} />
        <Button variant="outline" onClick={add}>{t('pay.add')}</Button>
      </div>
    </Card>
  )
}
