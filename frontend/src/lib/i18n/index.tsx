'use client'
import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { messages, type TKey } from './messages'

export type Locale = 'fr' | 'ar'
export type { TKey }

type Vars = Record<string, string | number>

interface I18n {
  locale: Locale
  dir: 'ltr' | 'rtl'
  setLocale: (l: Locale) => void
  t: (key: TKey, vars?: Vars) => string
  /** Look up a dynamic key (e.g. a status value from the API), falling back to `fallback`. */
  tx: (key: string, fallback?: string) => string
}

const STORAGE_KEY = 'silah_locale'

// Formatting helpers read the locale from <html lang>, so it must change *before* the
// re-render that the state update triggers.
function applyToDocument(l: Locale) {
  document.documentElement.lang = l
  document.documentElement.dir = l === 'ar' ? 'rtl' : 'ltr'
}

function translate(locale: Locale, key: string, vars?: Vars): string | undefined {
  const entry = (messages as Record<string, readonly [string, string]>)[key]
  if (!entry) return undefined
  let s: string = entry[locale === 'ar' ? 1 : 0]
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(String(v))
  return s
}

const I18nContext = createContext<I18n>({
  locale: 'fr', dir: 'ltr', setLocale: () => {},
  t: (k, v) => translate('fr', k, v) ?? k,
  tx: (k, f) => translate('fr', k) ?? f ?? k,
})

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>('fr')

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved === 'ar' || saved === 'fr') { applyToDocument(saved); setLocaleState(saved) }
    } catch { /* storage unavailable */ }
  }, [])

  const setLocale = useCallback((l: Locale) => {
    applyToDocument(l)
    setLocaleState(l)
    try { localStorage.setItem(STORAGE_KEY, l) } catch { /* ignore */ }
  }, [])

  const t = useCallback((key: TKey, vars?: Vars) => translate(locale, key, vars) ?? key, [locale])
  const tx = useCallback((key: string, fallback?: string) => translate(locale, key) ?? fallback ?? key, [locale])

  return (
    <I18nContext.Provider value={{ locale, dir: locale === 'ar' ? 'rtl' : 'ltr', setLocale, t, tx }}>
      {children}
    </I18nContext.Provider>
  )
}

export const useI18n = () => useContext(I18nContext)

/** Current locale outside React (formatting helpers). */
export function currentLocale(): Locale {
  if (typeof document !== 'undefined' && document.documentElement.lang === 'ar') return 'ar'
  return 'fr'
}
