export type Role = 'employee' | 'manager' | 'hr'
export type RequestStatus = 'pending' | 'approved' | 'rejected' | 'cancelled' | 'paid'

export interface Company {
  id: number
  name: string
  legal_form: string
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
  employee_number: string
  job_title: string
  department: string
  contract_type: string
  hire_date: string | null
  birth_date: string | null
  social_security_number: string
  phone: string
  address: string
  city: string
  postal_code: string
  emergency_contact: string
  bank_name: string
  iban: string
  manager: UserLite | null
  company: Company | null
  team_size: number
}

export interface Employee extends Omit<User, 'manager' | 'company' | 'is_hr' | 'team_size'> {
  is_active: boolean
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
  status: 'draft' | 'published'
  gross_salary: string
  net_salary: string
  employer_cost: string
  published_at: string | null
  viewed_at: string | null
}

export interface PayslipLine {
  code: string
  label: string
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
    hire_date: string | null
    contract_type: string
    address: string
    city: string
    iban: string
    bank_name: string
  }
  company: Company | null
  job_title: string
  department: string
  worked_days: string
  unpaid_days: string
  social_contributions: string
  taxable_salary: string
  income_tax: string
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
