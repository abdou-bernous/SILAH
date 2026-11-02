'use client'
import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from 'react'
import api, { getActiveCompany, setActiveCompany } from '@/lib/api'
import { logout as authLogout, isLoggedIn } from '@/lib/auth'
import type { User } from '@/lib/types'

interface AuthContextType {
  user: User | null
  loading: boolean
  logout: () => void
  refresh: () => Promise<void>
  unread: number
  refreshUnread: () => void
}

const AuthContext = createContext<AuthContextType>({
  user: null, loading: true, logout: () => {}, refresh: async () => {}, unread: 0, refreshUnread: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [unread, setUnread] = useState(0)

  const refreshUnread = useCallback(() => {
    api.get('/notifications/unread_count/').then((r) => setUnread(r.data.count)).catch(() => {})
  }, [])

  const refresh = useCallback(async () => {
    if (!isLoggedIn()) { setUser(null); setLoading(false); return }
    try {
      const { data } = await api.get<User>('/auth/me/')
      // An accountant belongs to none of his clients: he picks the one to work on, none is implied.
      // Only a client that is no longer his (removed, deactivated) is cleared.
      const saved = getActiveCompany()
      if (saved && !data.companies.some((c) => String(c.id) === saved)) setActiveCompany(null)
      setUser(data)
      refreshUnread()
    } catch {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [refreshUnread])

  useEffect(() => { refresh() }, [refresh])

  // Light polling so the bell updates when a request is reviewed.
  useEffect(() => {
    if (!user) return
    const id = setInterval(refreshUnread, 60_000)
    return () => clearInterval(id)
  }, [user, refreshUnread])

  const logout = () => { authLogout(); setUser(null) }

  return (
    <AuthContext.Provider value={{ user, loading, logout, refresh, unread, refreshUnread }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
