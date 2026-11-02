import type { Metadata, Viewport } from 'next'
import './globals.css'
import { AuthProvider } from '@/context/AuthContext'
import { I18nProvider } from '@/lib/i18n'

export const metadata: Metadata = {
  title: { default: 'SILAH — Portail paie & RH', template: '%s | SILAH' },
  description: 'Bulletins de paie, documents, congés et notes de frais : votre espace salarié en ligne.',
  robots: { index: false, follow: false },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
  themeColor: '#8a6e5a',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="min-h-screen">
        <I18nProvider><AuthProvider>{children}</AuthProvider></I18nProvider>
      </body>
    </html>
  )
}
