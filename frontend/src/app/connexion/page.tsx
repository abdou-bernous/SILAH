'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { BanknotesIcon, CalendarDaysIcon, FolderIcon, LockClosedIcon } from '@heroicons/react/24/outline'
import { login } from '@/lib/auth'
import { useAuth } from '@/context/AuthContext'
import Logo from '@/components/Logo'
import Button from '@/components/ui/Button'
import { Alert } from '@/components/ui/Card'

const SHOW_DEMO = process.env.NEXT_PUBLIC_SHOW_DEMO !== '0'
const DEMO = [
  { username: 'salarie', label: 'Salarié' },
  { username: 'manager', label: 'Manager' },
  { username: 'rh', label: 'RH' },
]

export default function LoginPage() {
  const router = useRouter()
  const { user, refresh } = useAuth()
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => { if (user) router.replace('/') }, [user, router])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await login(form.username.trim(), form.password)
      await refresh()
      router.replace('/')
    } catch (err) {
      const status = (err as { response?: { status?: number } }).response?.status
      setError(status === 429 ? 'Trop de tentatives, réessayez dans une minute.' : 'Identifiant ou mot de passe incorrect.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden overflow-hidden bg-sand lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div className="absolute -right-24 -top-24 h-80 w-80 rounded-full bg-latte/50" />
        <div className="absolute -bottom-32 -left-16 h-96 w-96 rounded-full bg-white/60" />
        <div className="relative"><Logo /></div>
        <div className="relative max-w-md">
          <h1 className="text-3xl font-semibold leading-tight text-espresso">
            Votre paie et vos démarches RH, au même endroit.
          </h1>
          <p className="mt-3 text-muted">Consultez vos bulletins, posez vos congés et retrouvez vos documents à tout moment.</p>
          <ul className="mt-8 space-y-4 text-sm text-espresso">
            {[
              [BanknotesIcon, 'Bulletins de paie en ligne, téléchargeables en PDF'],
              [CalendarDaysIcon, 'Demandes de congés et soldes en temps réel'],
              [FolderIcon, 'Coffre-fort personnel pour vos documents RH'],
            ].map(([Icon, text], i) => {
              const I = Icon as typeof BanknotesIcon
              return (
                <li key={i} className="flex items-center gap-3">
                  <span className="rounded-lg bg-white p-2 text-coffee"><I className="h-5 w-5" /></span>
                  {text as string}
                </li>
              )
            })}
          </ul>
        </div>
        <p className="relative text-xs text-muted">© {new Date().getFullYear()} SILAH</p>
      </div>

      <div className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden"><Logo /></div>
          <h2 className="text-2xl font-semibold">Connexion</h2>
          <p className="mt-1 text-sm text-muted">Accédez à votre espace salarié.</p>

          <form onSubmit={submit} className="mt-8 space-y-4">
            {error && <Alert>{error}</Alert>}
            <label className="block">
              <span className="label">Identifiant ou e-mail</span>
              <input className="input" autoComplete="username" required value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })} />
            </label>
            <label className="block">
              <span className="label">Mot de passe</span>
              <input className="input" type="password" autoComplete="current-password" required value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })} />
            </label>
            <Button type="submit" disabled={loading} className="w-full py-2.5">
              <LockClosedIcon className="h-4 w-4" />
              {loading ? 'Connexion…' : 'Se connecter'}
            </Button>
          </form>
          <p className="mt-4 text-xs text-muted">Mot de passe oublié ? Contactez votre service RH, qui peut le réinitialiser.</p>

          {SHOW_DEMO && (
            <div className="mt-10 rounded-xl border border-dashed border-latte bg-white/60 p-4">
              <p className="text-xs font-medium text-muted">Comptes de démonstration (mot de passe : Silah2026!)</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {DEMO.map((d) => (
                  <button key={d.username} type="button"
                    onClick={() => setForm({ username: d.username, password: 'Silah2026!' })}
                    className="rounded-full border border-stone bg-white px-3 py-1 text-xs text-espresso hover:border-coffee">
                    {d.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
