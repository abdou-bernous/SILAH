import type { MetadataRoute } from 'next'

/** Makes the site installable on a phone, and gives the future native app its identity. */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'SILAH — Portail paie & RH',
    short_name: 'SILAH',
    description: 'Bulletins de paie, documents, congés et notes de frais.',
    start_url: '/',
    display: 'standalone',
    orientation: 'portrait',
    background_color: '#f7f4f0',
    theme_color: '#8a6e5a',
    icons: [{ src: '/icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' }],
  }
}
