'use client'
import { useState } from 'react'
import Link from 'next/link'
import api, { errorMessage } from '@/lib/api'
import { useI18n } from '@/lib/i18n'
import Logo from '@/components/Logo'
import Button from '@/components/ui/Button'
import { Alert } from '@/components/ui/Card'
import Field from '@/components/ui/Field'
import LanguageSwitcher from '@/components/LanguageSwitcher'

export default function ForgotPasswordPage() {
  const { t } = useI18n()
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true); setError('')
    try {
      await api.post('/auth/password-reset/', { email: email.trim() })
      setSent(true)
    } catch (err) { setError(errorMessage(err)) } finally { setSaving(false) }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center px-6 py-12">
      <div className="absolute end-4 top-4"><LanguageSwitcher /></div>
      <div className="w-full max-w-sm">
        <div className="mb-8"><Logo /></div>
        <h1 className="text-2xl font-semibold">{t('forgot.title')}</h1>
        {sent ? <div className="mt-6"><Alert tone="sage">{t('forgot.sent')}</Alert></div> : (
          <form onSubmit={submit} className="mt-6 space-y-4">
            <p className="text-sm text-muted">{t('forgot.intro')}</p>
            {error && <Alert>{error}</Alert>}
            <Field label={t('field.email')}>
              <input className="input text-start" dir="ltr" type="email" required autoComplete="email" value={email}
                onChange={(e) => setEmail(e.target.value)} />
            </Field>
            <Button type="submit" disabled={saving} className="w-full py-2.5">{saving ? t('common.sending') : t('forgot.submit')}</Button>
          </form>
        )}
        <Link href="/connexion" className="mt-4 inline-block text-xs font-medium text-coffee hover:underline">{t('forgot.back')}</Link>
      </div>
    </div>
  )
}
