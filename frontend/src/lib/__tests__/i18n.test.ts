import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { messages } from '../i18n/messages'
import { translate } from '../i18n'

const entries = Object.entries(messages) as [string, readonly [string, string]][]
const ARABIC = /[؀-ۿ]/
const placeholders = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((f) => {
    const p = join(dir, f)
    if (statSync(p).isDirectory()) return f === '__tests__' ? [] : sourceFiles(p)
    return p.endsWith('.tsx') || p.endsWith('.ts') ? [p] : []
  })
}
const SOURCE = sourceFiles(join(__dirname, '..', '..')).map((f) => readFileSync(f, 'utf8')).join('\n')

describe('dictionary', () => {
  it('has a French and an Arabic text for every key', () => {
    for (const [key, [fr, ar]] of entries) {
      expect(fr.trim(), key).not.toBe('')
      expect(ar.trim(), key).not.toBe('')
    }
  })

  it('writes the Arabic column in Arabic', () => {
    // Separators and symbols are the only entries allowed to be identical in both languages.
    const exceptions = new Set(['common.listSep'])
    for (const [key, [, ar]] of entries) {
      if (!exceptions.has(key)) expect(ar, key).toMatch(ARABIC)
    }
  })

  it('uses the same placeholders in both languages', () => {
    for (const [key, [fr, ar]] of entries) expect(placeholders(ar), key).toEqual(placeholders(fr))
  })

  it('covers every value the API can send for translated enums', () => {
    const families: Record<string, string[]> = {
      status: ['pending', 'approved', 'rejected', 'cancelled', 'paid', 'draft', 'published'],
      leaveType: ['annual', 'recovery', 'sick', 'exceptional', 'unpaid', 'remote'],
      docCat: ['contract', 'certificate', 'payroll', 'medical', 'company', 'other'],
      expCat: ['transport', 'meals', 'lodging', 'mileage', 'supplies', 'other'],
      contract: ['cdi', 'cdd', 'intern', 'other'],
      marital: ['single', 'married', 'divorced', 'widowed'],
      payment: ['transfer', 'cheque', 'cash'],
      role: ['employee', 'manager', 'hr', 'accountant', 'admin'],
    }
    for (const [family, values] of Object.entries(families)) {
      for (const v of values) expect(messages, `${family}.${v}`).toHaveProperty([`${family}.${v}`])
    }
  })

  it('defines every key the screens use', () => {
    const used = new Set([...SOURCE.matchAll(/\bt\(\s*'([a-zA-Z0-9_.]+)'/g)].map((m) => m[1]))
    expect(used.size).toBeGreaterThan(100)
    for (const key of used) expect(messages, key).toHaveProperty([key])
  })

  it('has no key that no screen uses', () => {
    // Keys reached dynamically (`t(\`role.${...}\`)`, `tx(\`status.${...}\`)`…) are matched by prefix.
    const dynamic = [...SOURCE.matchAll(/\b(?:t|tx)\(\s*`([a-zA-Z.]+)\$\{/g)].map((m) => m[1])
    const unused = entries.map(([k]) => k).filter((k) => !SOURCE.includes(`'${k}'`) && !dynamic.some((p) => k.startsWith(p)))
    expect(unused).toEqual([])
  })
})

describe('translate', () => {
  it('picks the language and fills placeholders', () => {
    expect(translate('fr', 'payslips.publishedOn', { date: '01/11/2026' })).toBe('Publié le 01/11/2026')
    expect(translate('ar', 'payslips.publishedOn', { date: '01/11/2026' })).toBe('نُشر في 01/11/2026')
  })

  it('replaces every occurrence and returns undefined for unknown keys', () => {
    expect(translate('fr', 'home.pending', { leaves: 2, expenses: 0 })).toBe('En attente : 2 absence(s), 0 note(s) de frais')
    expect(translate('fr', 'does.not.exist')).toBeUndefined()
  })
})
