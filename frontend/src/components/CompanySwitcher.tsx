'use client'
import { useEffect, useState } from 'react'
import { BuildingOffice2Icon } from '@heroicons/react/24/outline'
import { useAuth } from '@/context/AuthContext'
import { getActiveCompany, setActiveCompany } from '@/lib/api'
import { useI18n } from '@/lib/i18n'

type Client = { id: number; name: string }

function savedClient(companies?: Client[]): Client | null {
  const saved = getActiveCompany()
  return companies?.find((c) => String(c.id) === saved) || null
}

/** The client an accountant is working on, or null: he belongs to none of them, so none is implied. */
export function useActiveCompany() {
  const { user } = useAuth()
  const companies = user?.companies
  // Read at once, so a page about the chosen client never flashes the "pick a client first" message.
  const [active, setActive] = useState<Client | null>(() => savedClient(companies))

  useEffect(() => {
    const found = savedClient(companies)
    // A client that was removed or deactivated must not stay selected.
    if (getActiveCompany() && companies && !found) setActiveCompany(null)
    setActive(found)
  }, [companies])

  return active
}

/** Lets accountants pick the client they are working on. */
export default function CompanySwitcher() {
  const { user } = useAuth()
  const { t } = useI18n()
  const active = useActiveCompany()
  const companies = user?.companies || []

  if (!companies.length) return null

  const pick = (value: string) => {
    if (!value) {
      setActiveCompany(null)
      window.location.href = '/entreprises'
      return
    }
    setActiveCompany(value)
    window.location.reload()
  }

  return (
    <label className="flex min-w-0 items-center gap-2 rounded-lg border border-stone bg-white px-2 py-1">
      <BuildingOffice2Icon className="h-4 w-4 shrink-0 text-coffee" />
      <span className="sr-only">{t('switcher.label')}</span>
      <select value={active ? String(active.id) : ''} className="min-w-0 max-w-44 truncate bg-transparent py-0.5 text-sm outline-none sm:max-w-64"
        onChange={(e) => pick(e.target.value)}>
        <option value="">{t('switcher.pick')}</option>
        {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
      </select>
    </label>
  )
}
