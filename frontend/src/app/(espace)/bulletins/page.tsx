'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { ArrowDownTrayIcon, BanknotesIcon, EyeIcon } from '@heroicons/react/24/outline'
import { useFetch } from '@/lib/useFetch'
import { downloadFile } from '@/lib/api'
import { date, money, monthLabel } from '@/lib/format'
import type { PayslipSummary } from '@/lib/types'
import Card, { EmptyState, PageHeader, Spinner, Stat } from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'

export default function PayslipsPage() {
  const { data: years } = useFetch<number[]>('/payslips/years/')
  const [year, setYear] = useState<number | null>(null)
  useEffect(() => { if (years && years.length && year === null) setYear(years[0]) }, [years, year])
  const { data, loading } = useFetch<PayslipSummary[]>(year ? `/payslips/?year=${year}` : years && !years.length ? '/payslips/' : null)

  const totalNet = (data || []).reduce((s, p) => s + Number(p.net_salary), 0)
  const totalGross = (data || []).reduce((s, p) => s + Number(p.gross_salary), 0)

  return (
    <div>
      <PageHeader title="Mes bulletins de paie" subtitle="Vos bulletins sont conservés sans limite de durée et restent accessibles à tout moment."
        actions={years && years.length > 0 && (
          <div className="flex rounded-lg border border-stone bg-white p-1">
            {years.map((y) => (
              <button key={y} onClick={() => setYear(y)}
                className={`rounded-md px-3 py-1 text-sm ${y === year ? 'bg-coffee text-white' : 'text-muted hover:text-espresso'}`}>
                {y}
              </button>
            ))}
          </div>
        )} />

      {data && data.length > 0 && (
        <div className="card mb-6 grid gap-6 p-5 sm:grid-cols-3">
          <Stat label={`Net cumulé ${year ?? ''}`} value={money(totalNet)} />
          <Stat label="Brut cumulé" value={money(totalGross)} />
          <Stat label="Bulletins" value={data.length} />
        </div>
      )}

      <Card>
        {loading || (!data && years === null) ? <Spinner /> : !data || data.length === 0 ? (
          <EmptyState icon={<BanknotesIcon />} title="Aucun bulletin disponible">
            Votre service RH vous préviendra dès la publication de votre premier bulletin.
          </EmptyState>
        ) : (
          <ul className="divide-y divide-stone">
            {data.map((p) => (
              <li key={p.id} className="flex flex-wrap items-center gap-4 px-5 py-4">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-sand text-coffee">
                  <BanknotesIcon className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-medium">
                    {monthLabel(p.year, p.month)}
                    {!p.viewed_at && <span className="ml-2"><Badge tone="coffee">Nouveau</Badge></span>}
                  </p>
                  <p className="text-xs text-muted">Publié le {date(p.published_at)}</p>
                </div>
                <div className="text-right">
                  <p className="font-semibold">{money(p.net_salary)}</p>
                  <p className="text-xs text-muted">Brut {money(p.gross_salary)}</p>
                </div>
                <div className="flex gap-1">
                  <Link href={`/bulletins/${p.id}`} className="rounded-lg p-2 text-muted hover:bg-sand hover:text-coffee" aria-label="Consulter">
                    <EyeIcon className="h-5 w-5" />
                  </Link>
                  <button onClick={() => downloadFile(`/payslips/${p.id}/pdf/`, 'bulletin.pdf')}
                    className="rounded-lg p-2 text-muted hover:bg-sand hover:text-coffee" aria-label="Télécharger en PDF">
                    <ArrowDownTrayIcon className="h-5 w-5" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
