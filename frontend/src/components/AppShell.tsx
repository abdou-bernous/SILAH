'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  HomeIcon, BanknotesIcon, FolderIcon, CalendarDaysIcon, ReceiptPercentIcon, UserCircleIcon,
  UserGroupIcon, UsersIcon, CalculatorIcon, DocumentArrowUpIcon, ClipboardDocumentCheckIcon,
  BuildingOfficeIcon, BellIcon, Bars3Icon, XMarkIcon, ArrowRightStartOnRectangleIcon,
} from '@heroicons/react/24/outline'
import { useAuth } from '@/context/AuthContext'
import { initials, ROLE_LABELS } from '@/lib/format'
import Logo from './Logo'
import { Spinner } from './ui/Card'

type Item = { href: string; label: string; icon: React.ComponentType<{ className?: string }> }

const MAIN: Item[] = [
  { href: '/', label: 'Accueil', icon: HomeIcon },
  { href: '/bulletins', label: 'Mes bulletins', icon: BanknotesIcon },
  { href: '/documents', label: 'Mes documents', icon: FolderIcon },
  { href: '/absences', label: 'Absences & congés', icon: CalendarDaysIcon },
  { href: '/notes-de-frais', label: 'Notes de frais', icon: ReceiptPercentIcon },
  { href: '/profil', label: 'Mon profil', icon: UserCircleIcon },
]
const TEAM: Item[] = [{ href: '/equipe', label: 'Validations équipe', icon: UserGroupIcon }]
const HR: Item[] = [
  { href: '/admin/salaries', label: 'Salariés', icon: UsersIcon },
  { href: '/admin/paie', label: 'Paie', icon: CalculatorIcon },
  { href: '/admin/documents', label: 'Dépôt de documents', icon: DocumentArrowUpIcon },
  { href: '/admin/demandes', label: 'Modifications de dossier', icon: ClipboardDocumentCheckIcon },
  { href: '/admin/entreprise', label: 'Entreprise', icon: BuildingOfficeIcon },
]

function NavLink({ item, onNavigate }: { item: Item; onNavigate: () => void }) {
  const pathname = usePathname()
  const active = item.href === '/' ? pathname === '/' : pathname.startsWith(item.href)
  const Icon = item.icon
  return (
    <Link href={item.href} onClick={onNavigate}
      className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
        active ? 'bg-white font-medium text-espresso shadow-sm' : 'text-muted hover:bg-white/60 hover:text-espresso'}`}>
      <Icon className={`h-5 w-5 ${active ? 'text-coffee' : ''}`} />
      {item.label}
    </Link>
  )
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout, unread } = useAuth()
  const router = useRouter()
  const pathname = usePathname()
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!loading && !user) router.replace('/connexion')
  }, [loading, user, router])

  useEffect(() => { setOpen(false) }, [pathname])

  if (loading || !user) return <div className="min-h-screen"><Spinner /></div>

  const close = () => setOpen(false)
  const sidebar = (
    <nav className="flex h-full flex-col gap-6 overflow-y-auto px-4 py-5">
      <Link href="/" className="px-2"><Logo /></Link>
      <div className="space-y-1">
        <p className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-muted/80">Mon espace</p>
        {MAIN.map((i) => <NavLink key={i.href} item={i} onNavigate={close} />)}
      </div>
      {(user.role === 'manager' || user.is_hr) && (
        <div className="space-y-1">
          <p className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-muted/80">Management</p>
          {TEAM.map((i) => <NavLink key={i.href} item={i} onNavigate={close} />)}
        </div>
      )}
      {user.is_hr && (
        <div className="space-y-1">
          <p className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-muted/80">Gestion RH</p>
          {HR.map((i) => <NavLink key={i.href} item={i} onNavigate={close} />)}
        </div>
      )}
      <div className="mt-auto rounded-xl bg-white/70 p-3 text-xs text-muted">
        {user.company?.name || 'SILAH'}
        <span className="block text-[11px]">Portail paie & RH</span>
      </div>
    </nav>
  )

  return (
    <div className="flex min-h-screen">
      <aside className="no-print sticky top-0 hidden h-screen w-64 shrink-0 border-r border-stone bg-sand/70 lg:block">
        {sidebar}
      </aside>

      {open && (
        <div className="no-print fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-espresso/30" onClick={close} />
          <aside className="absolute inset-y-0 left-0 w-72 bg-sand shadow-xl">
            <button onClick={close} className="absolute right-3 top-4 rounded-lg p-1 text-muted hover:bg-white" aria-label="Fermer le menu">
              <XMarkIcon className="h-5 w-5" />
            </button>
            {sidebar}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="no-print sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-stone bg-cream/90 px-4 backdrop-blur sm:px-6">
          <button onClick={() => setOpen(true)} className="rounded-lg p-2 text-muted hover:bg-sand lg:hidden" aria-label="Ouvrir le menu">
            <Bars3Icon className="h-5 w-5" />
          </button>
          <div className="lg:hidden"><Logo /></div>
          <div className="ml-auto flex items-center gap-2">
            <Link href="/notifications" className="relative rounded-lg p-2 text-muted hover:bg-sand" aria-label="Notifications">
              <BellIcon className="h-5 w-5" />
              {unread > 0 && (
                <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-coffee px-1 text-[10px] font-semibold text-white">
                  {unread > 9 ? '9+' : unread}
                </span>
              )}
            </Link>
            <Link href="/profil" className="flex items-center gap-2 rounded-lg px-2 py-1 hover:bg-sand">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-latte text-xs font-semibold text-coffee-dark">
                {initials(user.full_name)}
              </span>
              <span className="hidden text-left sm:block">
                <span className="block text-sm font-medium leading-tight">{user.full_name}</span>
                <span className="block text-xs leading-tight text-muted">{ROLE_LABELS[user.role]}</span>
              </span>
            </Link>
            <button onClick={() => { logout(); router.replace('/connexion') }}
              className="rounded-lg p-2 text-muted hover:bg-sand" title="Se déconnecter" aria-label="Se déconnecter">
              <ArrowRightStartOnRectangleIcon className="h-5 w-5" />
            </button>
          </div>
        </header>
        <main className="print-full mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 lg:py-8">{children}</main>
      </div>
    </div>
  )
}

export function HrOnly({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  if (!user?.is_hr) {
    return <p className="card p-8 text-center text-sm text-muted">Cette page est réservée aux gestionnaires RH.</p>
  }
  return <>{children}</>
}
