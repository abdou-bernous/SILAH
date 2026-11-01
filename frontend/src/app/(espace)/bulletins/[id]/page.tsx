'use client'
import { useParams } from 'next/navigation'
import { ArrowDownTrayIcon, ArrowLeftIcon, PrinterIcon } from '@heroicons/react/24/outline'
import { useFetch } from '@/lib/useFetch'
import { downloadFile } from '@/lib/api'
import type { PayslipDetail } from '@/lib/types'
import { Alert, Spinner } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { StatusBadge } from '@/components/ui/Badge'
import PayslipView from '@/components/PayslipView'
import { useAuth } from '@/context/AuthContext'

export default function PayslipPage() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const { data, loading, error } = useFetch<PayslipDetail>(`/payslips/${id}/`)

  if (loading) return <Spinner />
  if (error || !data) return <Alert>{error || 'Bulletin introuvable.'}</Alert>
  const own = data.employee.id === user?.id

  return (
    <div className="space-y-4">
      <div className="no-print flex flex-wrap items-center justify-between gap-3">
        <Button variant="ghost" href={own ? '/bulletins' : '/admin/paie'}>
          <ArrowLeftIcon className="h-4 w-4" /> Retour
        </Button>
        <div className="flex items-center gap-2">
          {data.status === 'draft' && <StatusBadge status="draft" />}
          <Button variant="outline" onClick={() => window.print()}><PrinterIcon className="h-4 w-4" /> Imprimer</Button>
          <Button onClick={() => downloadFile(`/payslips/${data.id}/pdf/`, 'bulletin.pdf')}>
            <ArrowDownTrayIcon className="h-4 w-4" /> Télécharger le PDF
          </Button>
        </div>
      </div>
      <PayslipView p={data} />
    </div>
  )
}
