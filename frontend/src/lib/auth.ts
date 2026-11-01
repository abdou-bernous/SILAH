import Cookies from 'js-cookie'
import api from './api'
import type { User } from './types'

export async function login(username: string, password: string): Promise<User> {
  const { data } = await api.post('/auth/login/', { username, password })
  Cookies.set('access_token', data.access, { expires: 1, sameSite: 'lax' })
  Cookies.set('refresh_token', data.refresh, { expires: 7, sameSite: 'lax' })
  const profile = await api.get('/auth/me/')
  return profile.data
}

export function logout() {
  Cookies.remove('access_token')
  Cookies.remove('refresh_token')
}

export function isLoggedIn(): boolean {
  return !!Cookies.get('access_token') || !!Cookies.get('refresh_token')
}
