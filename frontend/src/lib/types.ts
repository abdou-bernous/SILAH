export type Role = 'employee' | 'manager' | 'hr' | 'accountant' | 'admin'
export type RequestStatus = 'pending' | 'approved' | 'rejected' | 'cancelled' | 'paid'

export interface Company {
  id: number
  name: string
  name_ar: string
  legal_form: string
  sector: string
  phone: string
  email: string
  is_active: boolean
  address: string
  city: string
  nif: string
  nis: string
  rc: string
  cnas_number: string
  weekend_days: number[]
  annual_leave_days: string
}

export interface UserLite {
  id: number
  username: string
  full_name: string
  first_name: string
  last_name: string
  job_title: string
  department: string
}

export interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  role: Role
  is_hr: boolean
  is_platform_admin: boolean
  employee_number: string
  job_title: string
  department: string
  qualification: string
  contract_type: string
  hire_date: string | null
  birth_date: string | null
  social_security_number: string
  nin: string
  marital_status: string
  children_count: number
  phone: string
  address: string
  city: string
  postal_code: string
  emergency_contact: string
  bank_name: string
  iban: string
  payment_method: string
  manager: UserLite | null
  company: Company | null
  team_size: number
  companies: { id: number; name: string }[]
}

export interface Employee extends Omit<User, 'manager' | 'company' | 'is_hr' | 'is_platform_admin' | 'team_size' | 'companies'> {
  is_active: boolean
  is_disabled: boolean
  base_salary: string
  manager: number | null
  manager_name: string | null
  password?: string
}

export interface PayslipSummary {
  id: number
  employee: UserLite
  year: number
  month: number
  status: 'draft' | 'published' | 'replaced'
  gross_salary: string
  net_salary: string
  employer_cost: string
  published_at: string | null
  viewed_at: string | null
  // Corrections ("annule et remplace"): `replaces` is set on a corrective payslip,
  // `replaced_by` on the payslip it corrects (a draft while the correction is prepared).
  replaces: number | null
  replaced_by: { id: number; status: PayslipSummary['status'] } | null
  previous_net: string | null
  previous_published_at: string | null
  correction_reason: string
}

export interface PayslipLine {
  code: string
  label: string
  label_ar: string
  kind: 'earning' | 'deduction' | 'contribution' | 'tax' | 'non_taxable'
  base: string | null
  rate: string | null
  employee_amount: string
  employer_amount: string
}

export interface PayslipDetail extends Omit<PayslipSummary, 'employee'> {
  employee: {
    id: number
    full_name: string
    employee_number: string
    social_security_number: string
    nin: string
    hire_date: string | null
    contract_type: string
    address: string
    city: string
    iban: string
    bank_name: string
    marital_status: string
    children_count: number
    payment_method: string
  }
  company: Company | null
  job_title: string
  department: string
  qualification: string
  worked_days: string
  worked_hours: string
  unpaid_days: string
  social_contributions: string
  taxable_salary: string
  income_tax: string
  flat_tax: string
  non_taxable: string
  employer_contributions: string
  lines: PayslipLine[]
}

export interface DocumentItem {
  id: number
  employee: number | null
  employee_name: string | null
  category: string
  category_label: string
  title: string
  description: string
  file_name: string | null
  file_size: number | null
  created_at: string
  viewed_at: string | null
}

export interface Balance {
  leave_type: string
  label: string
  year: number
  allotted: string
  taken: string
  pending: string
  remaining: string
}

export interface LeaveRequest {
  id: number
  employee: UserLite
  leave_type: string
  leave_type_label: string
  start_date: string
  end_date: string
  start_half: boolean
  end_half: boolean
  days: string
  reason: string
  has_attachment: boolean
  status: RequestStatus
  status_label: string
  reviewer_name: string | null
  review_comment: string
  reviewed_at: string | null
  created_at: string
}

export interface Expense {
  id: number
  employee: UserLite
  date: string
  category: string
  category_label: string
  amount: string
  description: string
  has_receipt: boolean
  status: RequestStatus
  status_label: string
  payslip: number | null
  reviewer_name: string | null
  review_comment: string
  reviewed_at: string | null
  created_at: string
}

export interface ProfileRequest {
  id: number
  employee: UserLite
  changes: Record<string, string>
  current_values: Record<string, string>
  comment: string
  status: RequestStatus
  status_label: string
  review_comment: string
  reviewed_at: string | null
  created_at: string
}

export interface Notification {
  id: number
  title: string
  message: string
  link: string
  read: boolean
  created_at: string
}

export interface Choice {
  value: string
  label: string
}

export interface PayrollTotals {
  gross: string | null
  net: string | null
  cost: string | null
  irg: string | null
  irg_flat: string | null
  cnas: string | null
  cnas_employer: string | null
  count: number
  /** Drafts included in the figures (only on the month summary): they stay provisional until published. */
  drafts?: number
}

export interface CompanyAdmin extends Company {
  employee_count: number
  managers: { id: number; full_name: string }[]
  created_at: string
}

export interface CompanyOverview extends CompanyAdmin {
  last_payroll: (PayrollTotals & { year: number; month: number }) | null
  drafts: number
  pending_leaves: number
  pending_expenses: number
  pending_profile: number
  pending_certificates: number
  absent_today: number
}

export interface PlatformUser {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  role: 'accountant' | 'admin'
  phone: string
  is_active: boolean
  companies: number[]
  last_login: string | null
  date_joined: string
  password?: string
}

export interface PayItem {
  id: number
  employee: number
  label: string
  label_ar: string
  amount: string
  contributory: boolean
  tax: 'scale' | 'flat' | 'exempt'
  is_active: boolean
}

export interface MonthlyVariableRow {
  employee: number
  full_name: string
  overtime_hours: string
  overtime_rate: string
  bonus_label: string
  bonus_amount: string
}

export interface CertificateRequest {
  id: number
  employee: UserLite
  kind: 'work' | 'salary'
  kind_label: string
  comment: string
  status: RequestStatus
  status_label: string
  document: number | null
  review_comment: string
  reviewed_at: string | null
  created_at: string
}

export interface AuditEntry {
  id: number
  actor_name: string
  action: string
  summary: string
  created_at: string
}

export interface Preset {
  key: string
  label: string
  label_ar: string
  contributory: boolean
  tax: 'scale' | 'flat' | 'exempt'
}
