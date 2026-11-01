'use client'
import { useCallback, useEffect, useState } from 'react'
import api, { errorMessage } from './api'

/** Minimal GET hook: data, loading, error and a reload function. */
export function useFetch<T>(url: string | null) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(!!url)
  const [error, setError] = useState('')

  const reload = useCallback(async () => {
    if (!url) return
    setLoading(true)
    try {
      const r = await api.get<T>(url)
      setData(r.data)
      setError('')
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setLoading(false)
    }
  }, [url])

  useEffect(() => { reload() }, [reload])
  return { data, loading, error, reload, setData }
}
