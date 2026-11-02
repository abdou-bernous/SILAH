'use client'
import { useState } from 'react'
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline'
import { useFetch } from '@/lib/useFetch'
import { isoDate, monthLabel, WEEKDAY_INITIALS } from '@/lib/format'
import { useI18n } from '@/lib/i18n'
import { Spinner } from './ui/Card'

interface CalendarData {
  year: number
  month: number
  weekend_days: number[]
  people: { id: number; full_name: string; job_title: string }[]
  leaves: { id: number; employee: number; start_date: string; end_date: string; status: string; leave_type: string | null; label: string }[]
}

const TYPE_COLORS: Record<string, string> = {
  annual: 'bg-coffee', recovery: 'bg-latte', sick: 'bg-rose-ink/70', exceptional: 'bg-mist-ink/70', unpaid: 'bg-honey-ink/70',
}

export default function TeamCalendar() {
  const { t, tx, locale } = useI18n()
  const now = new Date()
  const [ym, setYm] = useState({ y: now.getFullYear(), m: now.getMonth() + 1 })
  const { data, loading } = useFetch<CalendarData>(`/leaves/calendar/?year=${ym.y}&month=${ym.m}`)
  const move = (d: number) => setYm(({ y, m }) => {
    const n = new Date(y, m - 1 + d, 1)
    return { y: n.getFullYear(), m: n.getMonth() + 1 }
  })

  const daysInMonth = new Date(ym.y, ym.m, 0).getDate()
  const days = Array.from({ length: daysInMonth }, (_, i) => new Date(ym.y, ym.m - 1, i + 1))
  // JS: Sunday=0; backend weekend days use Monday=0.
  const isWeekend = (d: Date) => data?.weekend_days.includes((d.getDay() + 6) % 7)
  const today = isoDate(now)

  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between border-b border-stone px-5 py-3">
        <button onClick={() => move(-1)} className="rounded-lg p-1.5 text-muted hover:bg-sand" aria-label={t('cal.prev')}><ChevronLeftIcon className="h-4 w-4 rtl:rotate-180" /></button>
        <p className="text-sm font-semibold">{monthLabel(ym.y, ym.m)}</p>
        <button onClick={() => move(1)} className="rounded-lg p-1.5 text-muted hover:bg-sand" aria-label={t('cal.next')}><ChevronRightIcon className="h-4 w-4 rtl:rotate-180" /></button>
      </div>
      {loading || !data ? <Spinner /> : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-xs">
            <thead>
              <tr>
                <th className="sticky start-0 z-10 min-w-40 bg-white px-4 py-2 text-start font-medium text-muted">{t('cal.person')}</th>
                {days.map((d) => (
                  <th key={d.getDate()} className={`w-7 min-w-7 py-2 text-center font-normal ${isWeekend(d) ? 'bg-sand/60 text-muted/70' : 'text-muted'} ${isoDate(d) === today ? 'text-coffee font-semibold' : ''}`}>
                    <div>{WEEKDAY_INITIALS[locale][d.getDay()]}</div>
                    <div>{d.getDate()}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.people.map((p) => (
                <tr key={p.id} className="border-t border-stone">
                  <td className="sticky start-0 z-10 bg-white px-4 py-2">
                    <p className="font-medium text-espresso">{p.full_name}</p>
                    <p className="text-[11px] text-muted">{p.job_title}</p>
                  </td>
                  {days.map((d) => {
                    const iso = isoDate(d)
                    const leave = data.leaves.find((l) => l.employee === p.id && l.start_date <= iso && l.end_date >= iso)
                    const weekend = isWeekend(d)
                    return (
                      <td key={iso} className={`h-10 p-0.5 ${weekend ? 'bg-sand/60' : ''}`}>
                        {leave && !weekend && (
                          <div title={`${leave.leave_type ? tx(`leaveType.${leave.leave_type}`, leave.label) : t('cal.absent')}${leave.status === 'pending' ? ` (${t('status.pending')})` : ''}`}
                            className={`h-6 rounded ${leave.leave_type ? TYPE_COLORS[leave.leave_type] || 'bg-coffee' : 'bg-muted/50'} ${leave.status === 'pending' ? 'opacity-40' : ''}`} />
                        )}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex flex-wrap gap-4 border-t border-stone px-5 py-3 text-xs text-muted">
            <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-coffee" /> {t('leaveType.annual')}</span>
            <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-latte" /> {t('leaveType.recovery')}</span>
            <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-rose-ink/70" /> {t('leaveType.sick')}</span>
            <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-muted/50" /> {t('cal.absent')}</span>
            <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-coffee opacity-40" /> {t('status.pending')}</span>
          </div>
        </div>
      )}
    </div>
  )
}

