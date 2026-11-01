'use client'
import { useEffect, useState } from 'react'
import { BuildingOffice2Icon } from '@heroicons/react/24/outline'
import { useAuth } from '@/context/AuthContext'
import { getActiveCompany, setActiveCompany } from '@/lib/api'
import { useI18n } from '@/lib/i18n'

/** Lets accountants pick the company they are working on. */
export default function CompanySwitcher() {
  const { user } = useAuth()
  const { t } = useI18n()
  const [current, setCurrent] = useState<string>('')
  const companies = user?.companies || []

  useEffect(() => {
    const saved = getActiveCompany()
    if (saved && companies.some((c) => String(c.id) === saved)) setCurrent(saved)
    else if (companies.length) {
      setActiveCompany(companies[0].id)
      setCurrent(String(companies[0].id))
    }
  }, [companies])

  if (!companies.length) return null

  return (
    <label className="flex min-w-0 items-center gap-2 rounded-lg border border-stone bg-white px-2 py-1">
      <BuildingOffice2Icon className="h-4 w-4 shrink-0 text-coffee" />
      <span className="sr-only">{t('switcher.label')}</span>
      <select value={current} className="min-w-0 max-w-44 truncate bg-transparent py-0.5 text-sm outline-none sm:max-w-64"
        onChange={(e) => { setActiveCompany(e.target.value); window.location.reload() }}>
        {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
      </select>
    </label>
  )
}
