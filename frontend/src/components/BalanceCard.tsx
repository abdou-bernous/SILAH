'use client'
import type { Balance } from '@/lib/types'
import { num } from '@/lib/format'
import { useI18n } from '@/lib/i18n'

export default function BalanceCard({ balance }: { balance: Balance }) {
  const { t, tx } = useI18n()
  const total = Number(balance.allotted) || 0
  const taken = Number(balance.taken)
  const pending = Number(balance.pending)
  const pct = (v: number) => (total ? Math.min(100, (v / total) * 100) : 0)
  return (
    <div className="rounded-xl border border-stone bg-white p-4">
      <div className="flex items-baseline justify-between">
        <p className="text-sm font-medium">{tx(`leaveType.${balance.leave_type}`, balance.label)}</p>
        <p className="text-xs text-muted">{balance.year}</p>
      </div>
      <p className="mt-2 text-2xl font-semibold">
        {num(balance.remaining)} <span className="text-sm font-normal text-muted">{t('balance.daysLeft')}</span>
      </p>
      <div className="mt-3 flex h-1.5 overflow-hidden rounded-full bg-sand" aria-hidden>
        <div className="bg-coffee" style={{ width: `${pct(taken)}%` }} />
        <div className="bg-latte" style={{ width: `${pct(pending)}%` }} />
      </div>
      <p className="mt-2 text-xs text-muted">
        {t('balance.detail', { taken: num(balance.taken), pending: num(balance.pending), allotted: num(balance.allotted) })}
      </p>
    </div>
  )
}
