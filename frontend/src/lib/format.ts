import { currentLocale } from './i18n'

export const MONTHS_FR = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août',
  'septembre', 'octobre', 'novembre', 'décembre']
// Month names as used in Algeria.
export const MONTHS_AR = ['جانفي', 'فيفري', 'مارس', 'أفريل', 'ماي', 'جوان', 'جويلية', 'أوت',
  'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
const WEEKDAYS_FR = ['dimanche', 'lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi']
const WEEKDAYS_AR = ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت']
export const WEEKDAY_INITIALS = { fr: 'DLMMJVS', ar: ['ح', 'ن', 'ث', 'ر', 'خ', 'ج', 'س'] }

// Algeria writes amounts with Latin digits in both languages.
const moneyFmt = new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const numFmt = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 })

export function months(): string[] {
  return currentLocale() === 'ar' ? MONTHS_AR : MONTHS_FR
}

export function money(value: string | number | null | undefined, currency = true): string {
  if (value === null || value === undefined || value === '') return '—'
  const s = moneyFmt.format(Number(value))
  if (!currency) return s
  return currentLocale() === 'ar' ? `${s} د.ج` : `${s} DA`
}

export function num(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—'
  return numFmt.format(Number(value))
}

export function monthLabel(year: number, month: number): string {
  const m = months()[month - 1]
  return `${m.charAt(0).toUpperCase()}${m.slice(1)} ${year}`
}

/** Parse YYYY-MM-DD as a local date (new Date('2026-01-01') would be UTC midnight). */
export function parseDate(value: string): Date {
  const [y, m, d] = value.slice(0, 10).split('-').map(Number)
  return new Date(y, m - 1, d)
}

export function isoDate(d: Date): string {
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function toDate(value: string) {
  return value.length <= 10 ? parseDate(value) : new Date(value)
}

export function date(value: string | null | undefined): string {
  if (!value) return '—'
  const d = toDate(value)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()}`
}

export function longDate(value: string | null | undefined): string {
  if (!value) return '—'
  const d = toDate(value)
  const ar = currentLocale() === 'ar'
  const wd = (ar ? WEEKDAYS_AR : WEEKDAYS_FR)[d.getDay()]
  const m = months()[d.getMonth()]
  return `${wd} ${d.getDate()} ${m}`
}

export function relative(value: string): string {
  const ar = currentLocale() === 'ar'
  const diff = (Date.now() - new Date(value).getTime()) / 1000
  if (diff < 60) return ar ? 'الآن' : "à l'instant"
  if (diff < 3600) return ar ? `منذ ${Math.floor(diff / 60)} د` : `il y a ${Math.floor(diff / 60)} min`
  if (diff < 86400) return ar ? `منذ ${Math.floor(diff / 3600)} سا` : `il y a ${Math.floor(diff / 3600)} h`
  if (diff < 86400 * 7) return ar ? `منذ ${Math.floor(diff / 86400)} ي` : `il y a ${Math.floor(diff / 86400)} j`
  return date(value)
}

export function fileSize(bytes: number | null): string {
  if (!bytes) return ''
  const ar = currentLocale() === 'ar'
  if (bytes < 1024) return `${bytes} ${ar ? 'بايت' : 'o'}`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} ${ar ? 'ك.ب' : 'Ko'}`
  return `${(bytes / 1024 / 1024).toFixed(1)} ${ar ? 'م.ب' : 'Mo'}`
}

export function initials(name: string): string {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase()).join('')
}

/** Profile fields an employee can ask HR to change (keys of the `field.*` messages). */
export const PROFILE_FIELDS = ['last_name', 'first_name', 'birth_date', 'marital_status', 'children_count',
  'social_security_number', 'nin', 'address', 'city', 'postal_code', 'bank_name', 'iban'] as const
