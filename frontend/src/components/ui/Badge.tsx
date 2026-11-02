'use client'
import { useI18n } from '@/lib/i18n'

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

const STATUS_TONES: Record<string, Tone> = {
  pending: 'honey', approved: 'sage', rejected: 'rose', cancelled: 'neutral', paid: 'mist',
  draft: 'honey', published: 'sage', replaced: 'neutral',
}

export function StatusBadge({ status }: { status: string }) {
  const { tx } = useI18n()
  return <Badge tone={STATUS_TONES[status] || 'neutral'}>{tx(`status.${status}`, status)}</Badge>
}
