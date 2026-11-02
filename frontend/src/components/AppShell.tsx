'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  HomeIcon, BanknotesIcon, FolderIcon, CalendarDaysIcon, ReceiptPercentIcon, UserCircleIcon,
  UserGroupIcon, UsersIcon, CalculatorIcon, DocumentArrowUpIcon, ClipboardDocumentCheckIcon,
  BuildingOfficeIcon, BellIcon, Bars3Icon, XMarkIcon, ArrowRightStartOnRectangleIcon, ChartBarIcon,
  BuildingOffice2Icon, ClockIcon, ShieldCheckIcon,
} from '@heroicons/react/24/outline'
import { useAuth } from '@/context/AuthContext'
import { useI18n, type TKey } from '@/lib/i18n'
import { initials } from '@/lib/format'
import Logo from './Logo'
import { Spinner } from './ui/Card'
import CompanySwitcher, { useActiveCompany } from './CompanySwitcher'
import LanguageSwitcher from './LanguageSwitcher'

// `tab` is a shorter label for the phone tab bar, where each entry gets a fifth of the width.
type Item = { href: string; label: TKey; tab?: TKey; icon: React.ComponentType<{ className?: string }> }

const MAIN: Item[] = [
  { href: '/', label: 'nav.home', icon: HomeIcon },
  { href: '/bulletins', label: 'nav.payslips', tab: 'nav.payslipsTab', icon: BanknotesIcon },
  { href: '/documents', label: 'nav.documents', icon: FolderIcon },
  { href: '/absences', label: 'nav.leaves', icon: CalendarDaysIcon },
  { href: '/notes-de-frais', label: 'nav.expenses', tab: 'nav.expensesTab', icon: ReceiptPercentIcon },
  { href: '/profil', label: 'nav.profile', icon: UserCircleIcon },
]
const TEAM: Item[] = [{ href: '/equipe', label: 'nav.team', icon: UserGroupIcon }]
const HR: Item[] = [
  { href: '/admin/salaries', label: 'nav.employees', icon: UsersIcon },
  { href: '/admin/paie', label: 'nav.payroll', icon: CalculatorIcon },
  { href: '/admin/documents', label: 'nav.uploadDocs', icon: DocumentArrowUpIcon },
  { href: '/admin/demandes', label: 'nav.profileRequests', icon: ClipboardDocumentCheckIcon },
  { href: '/admin/entreprise', label: 'nav.company', icon: BuildingOfficeIcon },
  { href: '/admin/journal', label: 'nav.journal', icon: ClockIcon },
]
const PLATFORM: Item[] = [
  { href: '/plateforme', label: 'nav.platformDashboard', icon: ChartBarIcon },
  { href: '/entreprises', label: 'nav.companies', icon: BuildingOffice2Icon },
  { href: '/plateforme/utilisateurs', label: 'nav.platformUsers', icon: ShieldCheckIcon },
]
const ACCOUNTANT: Item[] = [{ href: '/entreprises', label: 'nav.myCompanies', icon: BuildingOffice2Icon }]
// Accountants and admins have no employee space: they still need their own account page.
const ACCOUNT: Item = { href: '/profil', label: 'nav.account', icon: UserCircleIcon }

// Thumb-reachable shortcuts on phones. Everything else stays in the side menu.
const TABS = MAIN.filter((i) => i.href !== '/documents')

function TabBar() {
  const pathname = usePathname()
  const { t } = useI18n()
  return (
    <nav className="no-print fixed inset-x-0 bottom-0 z-30 flex border-t border-stone bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden">
      {TABS.map((item) => {
        const active = item.href === '/' ? pathname === '/' : pathname.startsWith(item.href)
        const Icon = item.icon
        return (
          <Link key={item.href} href={item.href} aria-current={active ? 'page' : undefined}
            className={`flex min-h-14 min-w-0 flex-1 flex-col items-center justify-center gap-0.5 px-1 text-[10px] ${active ? 'font-medium text-coffee' : 'text-muted'}`}>
            <Icon className="h-5 w-5 shrink-0" />
            <span className="max-w-full truncate">{t(item.tab ?? item.label)}</span>
          </Link>
        )
      })}
    </nav>
  )
}

function NavLink({ item, onNavigate }: { item: Item; onNavigate: () => void }) {
  const pathname = usePathname()
  const { t } = useI18n()
  const exact = item.href === '/' || item.href === '/plateforme'
  const active = exact ? pathname === item.href : pathname.startsWith(item.href)
  const Icon = item.icon
  return (
    <Link href={item.href} onClick={onNavigate}
      className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
        active ? 'bg-white font-medium text-espresso shadow-sm' : 'text-muted hover:bg-white/60 hover:text-espresso'}`}>
      <Icon className={`h-5 w-5 shrink-0 ${active ? 'text-coffee' : ''}`} />
      {t(item.label)}
    </Link>
  )
}

function Section({ title, label, items, onNavigate }: { title: TKey; label?: string; items: Item[]; onNavigate: () => void }) {
  const { t } = useI18n()
  return (
    <div className="space-y-1">
      <p className="truncate px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-muted/80">{label || t(title)}</p>
      {items.map((i) => <NavLink key={i.href} item={i} onNavigate={onNavigate} />)}
    </div>
  )
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout, unread } = useAuth()
  const { t } = useI18n()
  const router = useRouter()
  const pathname = usePathname()
  const [open, setOpen] = useState(false)
  const client = useActiveCompany()

  useEffect(() => {
    if (!loading && !user) router.replace('/connexion')
  }, [loading, user, router])

  useEffect(() => { setOpen(false) }, [pathname])

  if (loading || !user) return <div className="min-h-screen"><Spinner /></div>

  const close = () => setOpen(false)
  const hasEmployeeSpace = !!user.company
  // An accountant only gets the payroll menu once he has picked the client to work on.
  const accountant = user.role === 'accountant'
  const managesCompany = accountant ? !!client : user.is_hr && user.companies.length > 0
  const sidebar = (
    <nav className="flex h-full flex-col gap-6 overflow-y-auto px-4 py-5">
      <Link href="/" className="px-2"><Logo /></Link>
      {user.is_platform_admin && <Section title="nav.section.platform" items={hasEmployeeSpace ? PLATFORM : [...PLATFORM, ACCOUNT]} onNavigate={close} />}
      {user.role === 'accountant' && <Section title="nav.section.firm" items={hasEmployeeSpace ? ACCOUNTANT : [...ACCOUNTANT, ACCOUNT]} onNavigate={close} />}
      {hasEmployeeSpace && <Section title="nav.section.mine" items={MAIN} onNavigate={close} />}
      {(user.role === 'manager' || managesCompany) && <Section title="nav.section.management" items={TEAM} onNavigate={close} />}
      {managesCompany && <Section title="nav.section.hr" label={accountant && client ? t('nav.section.client', { name: client.name }) : undefined}
        items={HR} onNavigate={close} />}
      <div className="mt-auto rounded-xl bg-white/70 p-3 text-xs text-muted">
        {user.company?.name || t('common.appTagline')}
        <span className="block text-[11px]">{t('common.portal')}</span>
      </div>
    </nav>
  )

  return (
    <div className="flex min-h-screen">
      <aside className="no-print sticky top-0 hidden h-screen w-64 shrink-0 border-e border-stone bg-sand/70 lg:block">
        {sidebar}
      </aside>

      {open && (
        <div className="no-print fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-espresso/30" onClick={close} />
          <aside className="absolute inset-y-0 start-0 w-72 bg-sand shadow-xl">
            <button onClick={close} className="absolute end-3 top-4 rounded-lg p-1 text-muted hover:bg-white" aria-label={t('common.closeMenu')}>
              <XMarkIcon className="h-5 w-5" />
            </button>
            {sidebar}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="no-print sticky top-0 z-30 flex min-h-16 items-center gap-2 border-b border-stone bg-cream/90 px-4 pt-[env(safe-area-inset-top)] backdrop-blur sm:gap-3 sm:px-6">
          <button onClick={() => setOpen(true)} className="rounded-lg p-2 text-muted hover:bg-sand lg:hidden" aria-label={t('common.openMenu')}>
            <Bars3Icon className="h-5 w-5" />
          </button>
          <div className="hidden sm:block lg:hidden"><Logo /></div>
          {user.role === 'accountant' && !user.company && <CompanySwitcher />}
          <div className="ms-auto flex items-center gap-1 sm:gap-2">
            <LanguageSwitcher />
            <Link href="/notifications" className="relative rounded-lg p-2 text-muted hover:bg-sand" aria-label={t('nav.notifications')}>
              <BellIcon className="h-5 w-5" />
              {unread > 0 && (
                <span className="absolute end-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-coffee px-1 text-[10px] font-semibold text-white">
                  {unread > 9 ? '9+' : unread}
                </span>
              )}
            </Link>
            <Link href="/profil" className="flex items-center gap-2 rounded-lg px-2 py-1 hover:bg-sand">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-latte text-xs font-semibold text-coffee-dark">
                {initials(user.full_name)}
              </span>
              <span className="hidden text-start md:block">
                <span className="block text-sm font-medium leading-tight">{user.full_name}</span>
                <span className="block text-xs leading-tight text-muted">{t(`role.${user.role}` as TKey)}</span>
              </span>
            </Link>
            <button onClick={() => { logout(); router.replace('/connexion') }}
              className="rounded-lg p-2 text-muted hover:bg-sand" title={t('common.logout')} aria-label={t('common.logout')}>
              <ArrowRightStartOnRectangleIcon className="h-5 w-5 rtl:rotate-180" />
            </button>
          </div>
        </header>
        <main className={`print-full mx-auto w-full max-w-6xl flex-1 px-4 pt-6 sm:px-6 lg:py-8 ${hasEmployeeSpace ? 'pb-24' : 'pb-6'}`}>{children}</main>
      </div>
      {hasEmployeeSpace && <TabBar />}
    </div>
  )
}

/** An accountant works on one client at a time: a page about a client's staff or payroll asks him to pick it
 * first, rather than showing empty lists. Everyone else always has their company. */
export function ClientRequired({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  const { t } = useI18n()
  const client = useActiveCompany()
  if (user?.role === 'accountant' && !client) {
    return (
      <div className="card p-8 text-center text-sm text-muted">
        <p>{t('switcher.pickFirst')}</p>
        <Link href="/entreprises" className="mt-3 inline-block font-medium text-coffee hover:underline">{t('nav.myCompanies')}</Link>
      </div>
    )
  }
  return <>{children}</>
}

export function HrOnly({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  const { t } = useI18n()
  if (!user?.is_hr || !user.companies.length) {
    return <p className="card p-8 text-center text-sm text-muted">{t('common.hrOnly')}</p>
  }
  return <ClientRequired>{children}</ClientRequired>
}

export function PlatformOnly({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  const { t } = useI18n()
  if (!user?.is_platform_admin) {
    return <p className="card p-8 text-center text-sm text-muted">{t('common.adminOnly')}</p>
  }
  return <>{children}</>
}
