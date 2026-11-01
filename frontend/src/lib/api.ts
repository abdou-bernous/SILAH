import axios from 'axios'
import Cookies from 'js-cookie'

export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8100/api'

const api = axios.create({ baseURL: API_URL })

export const COMPANY_KEY = 'silah_company'

export function getActiveCompany(): string | null {
  try { return typeof window !== 'undefined' ? localStorage.getItem(COMPANY_KEY) : null } catch { return null }
}

export function setActiveCompany(id: number | string | null) {
  try {
    if (id === null) localStorage.removeItem(COMPANY_KEY)
    else localStorage.setItem(COMPANY_KEY, String(id))
  } catch { /* storage unavailable */ }
}

api.interceptors.request.use((config) => {
  const token = Cookies.get('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  // Accountants work on one company at a time; the API ignores
  // this header for everyone else and never lets it reach a company they don't manage.
  const company = getActiveCompany()
  if (company) config.headers['X-Company'] = company
  if (typeof document !== 'undefined') config.headers['Accept-Language'] = document.documentElement.lang || 'fr'
  return config
})

let refreshing: Promise<string> | null = null

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      const refresh = Cookies.get('refresh_token')
      if (refresh) {
        original._retry = true
        try {
          // One refresh shared by every request that failed at the same time.
          refreshing ??= axios.post(`${API_URL}/auth/refresh/`, { refresh }).then((r) => r.data.access)
          const access = await refreshing
          Cookies.set('access_token', access, { expires: 1, sameSite: 'lax' })
          original.headers.Authorization = `Bearer ${access}`
          return api(original)
        } catch {
          Cookies.remove('access_token')
          Cookies.remove('refresh_token')
          if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/connexion')) {
            window.location.href = '/connexion'
          }
        } finally {
          refreshing = null
        }
      }
    }
    return Promise.reject(error)
  }
)

/** Turn a DRF error payload into one readable French sentence. */
export function errorMessage(err: unknown, fallback = ''): string {
  fallback = fallback || (typeof document !== 'undefined' && document.documentElement.lang === 'ar'
    ? 'حدث خطأ.' : 'Une erreur est survenue.')
  const data = (err as { response?: { data?: unknown } })?.response?.data
  if (!data) return fallback
  if (typeof data === 'string') return data.length < 300 ? data : fallback
  if (Array.isArray(data)) return data.map(String).join(' ')
  if (typeof data === 'object') {
    const d = data as Record<string, unknown>
    if (typeof d.detail === 'string') return d.detail
    return Object.values(d)
      .flat()
      .map((v) => (typeof v === 'object' ? Object.values(v as object).flat().join(' ') : String(v)))
      .join(' ')
  }
  return fallback
}

/** Download a protected file (the API needs the bearer token, so a plain link won't do).
 *  Every download goes through here: blob links do not work in a mobile WebView, so this is
 *  the one place to plug Capacitor Filesystem and Share (see docs/mobile.md). */
export async function downloadFile(url: string, fallbackName = 'document') {
  const res = await api.get(url, { responseType: 'blob' })
  const disposition: string = res.headers['content-disposition'] || ''
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition)
  const name = match ? decodeURIComponent(match[1]) : fallbackName
  const href = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = href
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(href), 1000)
}

/** Open a protected PDF in a new tab. */
export async function openFile(url: string) {
  const win = window.open('', '_blank')
  const res = await api.get(url, { responseType: 'blob' })
  const href = URL.createObjectURL(res.data)
  if (win) win.location.href = href
  else window.location.href = href
}

export default api
