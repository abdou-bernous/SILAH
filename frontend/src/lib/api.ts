import axios from 'axios'
import Cookies from 'js-cookie'

export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8100/api'

const api = axios.create({ baseURL: API_URL })

api.interceptors.request.use((config) => {
  const token = Cookies.get('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
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
export function errorMessage(err: unknown, fallback = 'Une erreur est survenue.'): string {
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

/** Download a protected file (the API needs the bearer token, so a plain link won't do). */
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
