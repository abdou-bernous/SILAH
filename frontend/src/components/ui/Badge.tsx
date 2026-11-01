type Tone = 'sage' | 'honey' | 'rose' | 'mist' | 'neutral' | 'coffee'

const tones: Record<Tone, string> = {
  sage: 'bg-sage text-sage-ink',
  honey: 'bg-honey text-honey-ink',
  rose: 'bg-rose text-rose-ink',
  mist: 'bg-mist text-mist-ink',
  neutral: 'bg-sand text-muted',
  coffee: 'bg-coffee text-white',
}

export default function Badge({ children, tone = 'neutral' }: { children: React.ReactNode; tone?: Tone }) {
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  )
}

const STATUS: Record<string, { tone: Tone; label: string }> = {
  pending: { tone: 'honey', label: 'En attente' },
  approved: { tone: 'sage', label: 'Validée' },
  rejected: { tone: 'rose', label: 'Refusée' },
  cancelled: { tone: 'neutral', label: 'Annulée' },
  paid: { tone: 'mist', label: 'Remboursée' },
  draft: { tone: 'honey', label: 'Brouillon' },
  published: { tone: 'sage', label: 'Publié' },
}

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  const s = STATUS[status] || { tone: 'neutral' as Tone, label: status }
  return <Badge tone={s.tone}>{label || s.label}</Badge>
}
