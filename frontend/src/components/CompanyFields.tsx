'use client'
import { useI18n, type TKey } from '@/lib/i18n'
import type { Company } from '@/lib/types'
import Card from './ui/Card'

/** Employer identity fields, shared with the company creation form. */
export default function CompanyFields({ text }: { text: (k: keyof Company, label: TKey, ltr?: boolean) => React.ReactNode }) {
  const { t } = useI18n()
  return (
    <Card title={t('company.identity')}>
      <div className="grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-3">
        {text('name', 'company.name')}
        {text('name_ar', 'company.nameAr')}
        {text('legal_form', 'company.legalForm')}
        {text('sector', 'company.sector')}
        {text('city', 'field.city')}
        {text('phone', 'field.phone', true)}
        <div className="sm:col-span-2">{text('address', 'field.address')}</div>
        {text('email', 'field.email', true)}
        {text('nif', 'company.nif', true)}
        {text('nis', 'company.nis', true)}
        {text('rc', 'company.rc', true)}
        {text('cnas_number', 'company.cnas', true)}
      </div>
    </Card>
  )
}
