export default function Field({ label, children, hint, className = '' }: {
  label: string
  children: React.ReactNode
  hint?: React.ReactNode
  className?: string
}) {
  return (
    <label className={`block ${className}`}>
      <span className="label">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-muted">{hint}</span>}
    </label>
  )
}
