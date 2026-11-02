export default function Logo({ className = '' }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden>
        <rect width="32" height="32" rx="9" fill="#8a6e5a" />
        <path d="M9 20.5c1.6 1.3 3.9 2 6.4 2 3.4 0 5.6-1.5 5.6-3.9 0-2.2-1.6-3.1-5-3.8-2.3-.5-3-.9-3-1.7 0-.9.9-1.5 2.5-1.5 1.5 0 2.9.5 4.1 1.3l1.4-2.4c-1.4-1-3.4-1.6-5.5-1.6-3.2 0-5.4 1.7-5.4 4.2 0 2.3 1.6 3.3 4.9 4 2.4.5 3.1.9 3.1 1.6 0 .9-1 1.5-2.7 1.5-1.9 0-3.6-.6-5-1.7L9 20.5Z" fill="#f7f4f0" />
        <circle cx="23.5" cy="9" r="2" fill="#dccbbb" />
      </svg>
      <span className="text-lg font-semibold tracking-[0.18em] text-espresso">SILAH</span>
    </span>
  )
}
