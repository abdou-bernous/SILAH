import Link from 'next/link'

interface ButtonProps {
  children: React.ReactNode
  variant?: 'primary' | 'outline' | 'ghost' | 'danger' | 'success'
  size?: 'sm' | 'md'
  href?: string
  onClick?: () => void
  type?: 'button' | 'submit'
  disabled?: boolean
  className?: string
  title?: string
}

const styles = {
  primary: 'bg-coffee text-white hover:bg-coffee-dark',
  outline: 'border border-latte bg-white text-coffee-dark hover:bg-sand',
  ghost: 'text-coffee-dark hover:bg-sand',
  danger: 'border border-rose bg-white text-rose-ink hover:bg-rose',
  success: 'bg-sage-ink text-white hover:opacity-90',
}
const sizes = {
  sm: 'text-xs px-3 py-1.5',
  md: 'text-sm px-4 py-2',
}

export default function Button({ children, variant = 'primary', size = 'md', href, onClick, type = 'button', disabled, className = '', title }: ButtonProps) {
  const cls = `inline-flex items-center justify-center gap-1.5 font-medium rounded-lg transition-colors whitespace-nowrap ${styles[variant]} ${sizes[size]} ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`
  if (href) return <Link href={href} className={cls}>{children}</Link>
  return <button type={type} onClick={onClick} disabled={disabled} className={cls} title={title}>{children}</button>
}
