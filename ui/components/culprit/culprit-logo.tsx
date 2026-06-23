import { cn } from '@/lib/utils'

interface CulpritLogoProps {
  className?: string
}

export function CulpritLogo({ className }: CulpritLogoProps) {
  return (
    <svg
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn('size-7', className)}
    >
      <defs>
        <linearGradient id="culprit-fill" x1="18" y1="10" x2="84" y2="90" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#b16cf3" />
          <stop offset="48%" stopColor="#7b6ef2" />
          <stop offset="100%" stopColor="#46baf3" />
        </linearGradient>
        <linearGradient id="culprit-dot" x1="40" y1="42" x2="58" y2="58" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#c7d6fd" />
          <stop offset="100%" stopColor="#8ba6f6" />
        </linearGradient>
      </defs>
      {/* Thick rounded C body, open on the right */}
      <path
        d="M 66.96 22.86 A 32 32 0 1 0 66.96 77.14"
        stroke="url(#culprit-fill)"
        strokeWidth="21"
        strokeLinecap="round"
        fill="none"
      />
      {/* Center dot — the eye of the C */}
      <circle cx="49" cy="50" r="8.5" fill="url(#culprit-dot)" />
    </svg>
  )
}
