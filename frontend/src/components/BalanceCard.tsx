import type { Balance } from '@/lib/types'
import { num } from '@/lib/format'

export default function BalanceCard({ balance }: { balance: Balance }) {
  const total = Number(balance.allotted) || 0
  const taken = Number(balance.taken)
  const pending = Number(balance.pending)
  const pct = (v: number) => (total ? Math.min(100, (v / total) * 100) : 0)
  return (
    <div className="rounded-xl border border-stone bg-white p-4">
      <div className="flex items-baseline justify-between">
        <p className="text-sm font-medium">{balance.label}</p>
        <p className="text-xs text-muted">{balance.year}</p>
      </div>
      <p className="mt-2 text-2xl font-semibold">
        {num(balance.remaining)} <span className="text-sm font-normal text-muted">j restants</span>
      </p>
      <div className="mt-3 flex h-1.5 overflow-hidden rounded-full bg-sand" aria-hidden>
        <div className="bg-coffee" style={{ width: `${pct(taken)}%` }} />
        <div className="bg-latte" style={{ width: `${pct(pending)}%` }} />
      </div>
      <p className="mt-2 text-xs text-muted">
        {num(balance.taken)} pris · {num(balance.pending)} en attente · {num(balance.allotted)} acquis
      </p>
    </div>
  )
}
