'use client'
import { useI18n } from '@/lib/i18n'

export default function LanguageSwitcher({ className = '' }: { className?: string }) {
  const { locale, setLocale, t } = useI18n()
  return (
    <div className={`flex rounded-lg border border-stone bg-white p-0.5 text-xs ${className}`} role="group" aria-label={t('common.language')}>
      {(['fr', 'ar'] as const).map((l) => (
        <button key={l} onClick={() => setLocale(l)} lang={l}
          className={`rounded-md px-2 py-1 ${locale === l ? 'bg-coffee text-white' : 'text-muted hover:text-espresso'}`}>
          {l === 'fr' ? 'FR' : 'ع'}
        </button>
      ))}
    </div>
  )
}
