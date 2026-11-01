export const MONTHS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août',
  'septembre', 'octobre', 'novembre', 'décembre']
export const WEEKDAYS_SHORT = ['L', 'M', 'M', 'J', 'V', 'S', 'D']

const moneyFmt = new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const numFmt = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 1 })

export function money(value: string | number | null | undefined, currency = true): string {
  if (value === null || value === undefined || value === '') return '—'
  const s = moneyFmt.format(Number(value))
  return currency ? `${s} DA` : s
}

export function num(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—'
  return numFmt.format(Number(value))
}

export function monthLabel(year: number, month: number): string {
  const m = MONTHS[month - 1]
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

export function date(value: string | null | undefined): string {
  if (!value) return '—'
  const d = value.length <= 10 ? parseDate(value) : new Date(value)
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

export function longDate(value: string | null | undefined): string {
  if (!value) return '—'
  const d = value.length <= 10 ? parseDate(value) : new Date(value)
  return d.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })
}

export function relative(value: string): string {
  const diff = (Date.now() - new Date(value).getTime()) / 1000
  if (diff < 60) return "à l'instant"
  if (diff < 3600) return `il y a ${Math.floor(diff / 60)} min`
  if (diff < 86400) return `il y a ${Math.floor(diff / 3600)} h`
  if (diff < 86400 * 7) return `il y a ${Math.floor(diff / 86400)} j`
  return date(value)
}

export function fileSize(bytes: number | null): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} o`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} Ko`
  return `${(bytes / 1024 / 1024).toFixed(1)} Mo`
}

export function initials(name: string): string {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase()).join('')
}

export const ROLE_LABELS: Record<string, string> = {
  employee: 'Salarié',
  manager: 'Manager',
  hr: 'Gestionnaire RH',
}

export const CONTRACT_LABELS: Record<string, string> = {
  cdi: 'CDI', cdd: 'CDD', intern: 'Stage', other: 'Autre',
}

export const PROFILE_FIELD_LABELS: Record<string, string> = {
  first_name: 'Prénom',
  last_name: 'Nom',
  address: 'Adresse',
  city: 'Ville',
  postal_code: 'Code postal',
  bank_name: 'Banque',
  iban: 'RIB / IBAN',
  social_security_number: 'N° de sécurité sociale',
  birth_date: 'Date de naissance',
}
