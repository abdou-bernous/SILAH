'use client'
import { HrOnly } from '@/components/AppShell'

/** Payroll & HR pages: checked before a page mounts, so an accountant who has not picked a client yet (or
 * anyone without HR rights) is told so without the page first loading data it may not read. */
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <HrOnly>{children}</HrOnly>
}
