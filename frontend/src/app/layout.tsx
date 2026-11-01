import type { Metadata } from 'next'
import './globals.css'
import { AuthProvider } from '@/context/AuthContext'

export const metadata: Metadata = {
  title: { default: 'SILAH — Portail paie & RH', template: '%s | SILAH' },
  description: 'Bulletins de paie, documents, congés et notes de frais : votre espace salarié en ligne.',
  robots: { index: false, follow: false },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="min-h-screen">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  )
}
