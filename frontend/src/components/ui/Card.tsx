export default function Card({ children, className = '', title, action }: {
  children: React.ReactNode
  className?: string
  title?: React.ReactNode
  action?: React.ReactNode
}) {
  return (
    <section className={`card ${className}`}>
      {(title || action) && (
        <header className="flex items-center justify-between gap-3 border-b border-stone px-5 py-3.5">
          <h2 className="text-sm font-semibold text-espresso">{title}</h2>
          {action}
        </header>
      )}
      {children}
    </section>
  )
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-espresso">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  )
}

export function EmptyState({ icon, title, children }: { icon?: React.ReactNode; title: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
      {icon && <div className="mb-3 rounded-full bg-sand p-3 text-coffee [&>svg]:h-6 [&>svg]:w-6">{icon}</div>}
      <p className="text-sm font-medium text-espresso">{title}</p>
      {children && <div className="mt-1 text-sm text-muted">{children}</div>}
    </div>
  )
}

export function Spinner({ label = 'Chargement…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-12 text-sm text-muted">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-latte border-t-coffee" />
      {label}
    </div>
  )
}

export function Alert({ children, tone = 'rose' }: { children: React.ReactNode; tone?: 'rose' | 'sage' | 'honey' }) {
  const t = { rose: 'bg-rose text-rose-ink', sage: 'bg-sage text-sage-ink', honey: 'bg-honey text-honey-ink' }[tone]
  return <div className={`rounded-lg px-4 py-2.5 text-sm ${t}`}>{children}</div>
}

export function Stat({ label, value, hint }: { label: string; value: React.ReactNode; hint?: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 text-xl font-semibold text-espresso">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
    </div>
  )
}
