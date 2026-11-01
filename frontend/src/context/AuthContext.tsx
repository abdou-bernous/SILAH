'use client'
import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from 'react'
import api from '@/lib/api'
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
      const { data } = await api.get('/auth/me/')
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
