'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import api, { errorMessage } from '@/lib/api'
import { useI18n } from '@/lib/i18n'
import Logo from '@/components/Logo'
import Button from '@/components/ui/Button'
import { Alert } from '@/components/ui/Card'
import Field from '@/components/ui/Field'
import LanguageSwitcher from '@/components/LanguageSwitcher'

export default function ResetPasswordPage() {
  const { t } = useI18n()
  const [link, setLink] = useState<{ uid: string; token: string } | null>(null)
  const [form, setForm] = useState({ password: '', confirm: '' })
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const q = new URLSearchParams(window.location.search)
    setLink({ uid: q.get('uid') || '', token: q.get('token') || '' })
  }, [])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (form.password !== form.confirm) { setError(t('pwd.mismatch')); return }
    setSaving(true)
    try {
      await api.post('/auth/password-reset/confirm/', { ...link, new_password: form.password })
      setDone(true)
    } catch (err) { setError(errorMessage(err)) } finally { setSaving(false) }
  }

  const broken = link && (!link.uid || !link.token)

  return (
    <div className="relative flex min-h-screen items-center justify-center px-6 py-12">
      <div className="absolute end-4 top-4"><LanguageSwitcher /></div>
      <div className="w-full max-w-sm">
        <div className="mb-8"><Logo /></div>
        <h1 className="text-2xl font-semibold">{t('reset.title')}</h1>
        {done ? <div className="mt-6"><Alert tone="sage">{t('reset.done')}</Alert></div>
          : broken ? <div className="mt-6"><Alert>{t('reset.invalidLink')}</Alert></div> : (
            <form onSubmit={submit} className="mt-6 space-y-4">
              {error && <Alert>{error}</Alert>}
              <Field label={t('pwd.new')} hint={t('pwd.hint')}>
                <input className="input" type="password" required minLength={8} autoComplete="new-password" value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })} />
              </Field>
              <Field label={t('pwd.confirm')}>
                <input className="input" type="password" required autoComplete="new-password" value={form.confirm}
                  onChange={(e) => setForm({ ...form, confirm: e.target.value })} />
              </Field>
              <Button type="submit" disabled={saving} className="w-full py-2.5">{saving ? t('common.saving') : t('common.save')}</Button>
            </form>
          )}
        <Link href="/connexion" className="mt-4 inline-block text-xs font-medium text-coffee hover:underline">{t('forgot.back')}</Link>
      </div>
    </div>
  )
}
