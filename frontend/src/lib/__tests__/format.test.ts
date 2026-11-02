import { afterEach, describe, expect, it } from 'vitest'
import { date, fileSize, initials, isoDate, money, monthLabel, months, num, parseDate } from '../format'

// The formatters read the language from <html lang>; simulate it without a browser.
function setLang(lang: 'fr' | 'ar' | null) {
  const g = globalThis as { document?: unknown }
  if (lang === null) delete g.document
  else g.document = { documentElement: { lang } }
}
afterEach(() => setLang(null))

const nbsp = (s: string) => s.replace(/[  ]/g, ' ')

describe('money', () => {
  it('formats dinars in French', () => {
    setLang('fr')
    expect(nbsp(money('59705.2'))).toBe('59 705,20 DA')
    expect(nbsp(money(0, false))).toBe('0,00')
  })

  it('uses the Arabic currency symbol and keeps Latin digits', () => {
    setLang('ar')
    expect(nbsp(money(1500))).toBe('1 500,00 د.ج')
  })

  it('shows a dash for missing values', () => {
    expect(money(null)).toBe('—')
    expect(money('')).toBe('—')
    expect(num(undefined)).toBe('—')
  })
})

describe('months', () => {
  it('uses the month names written in Algeria', () => {
    setLang('ar')
    expect(months()[0]).toBe('جانفي')
    expect(monthLabel(2026, 8)).toBe('أوت 2026')
    setLang('fr')
    expect(monthLabel(2026, 8)).toBe('Août 2026')
  })
})

describe('dates', () => {
  it('parses ISO dates as local dates, without a timezone shift', () => {
    const d = parseDate('2026-03-01')
    expect([d.getFullYear(), d.getMonth(), d.getDate()]).toEqual([2026, 2, 1])
    expect(isoDate(d)).toBe('2026-03-01')
  })

  it('formats as dd/mm/yyyy', () => {
    expect(date('2026-11-01')).toBe('01/11/2026')
    expect(date(null)).toBe('—')
  })
})

describe('misc', () => {
  it('builds initials from the first two words', () => {
    expect(initials('Amine  Mansouri Ben')).toBe('AM')
    expect(initials('')).toBe('')
  })

  it('formats file sizes', () => {
    setLang('fr')
    expect(fileSize(2048)).toBe('2 Ko')
    expect(fileSize(null)).toBe('')
  })
})
