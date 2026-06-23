'use client'

import { useState, Suspense, type CSSProperties } from 'react'
import Spline from '@splinetool/react-spline'

interface SplineSceneProps {
  scene: string
  className?: string
  style?: CSSProperties
}

export function SplineScene({ scene, className, style }: SplineSceneProps) {
  const [loaded, setLoaded] = useState(false)

  return (
    <div className={cn('relative', className)} style={style}>
      <div
        className="absolute inset-0 flex items-center justify-center transition-opacity duration-500"
        style={{ opacity: loaded ? 0 : 1, pointerEvents: 'none' }}
      >
        <PosterSVG />
      </div>

      <Suspense fallback={null}>
        <div
          className="absolute inset-0 transition-opacity duration-600"
          style={{ opacity: loaded ? 1 : 0 }}
        >
          <Spline
            scene={scene}
            className="h-full w-full"
            renderOnDemand
            onLoad={() => setLoaded(true)}
          />
        </div>
      </Suspense>
    </div>
  )
}

function PosterSVG() {
  return (
    <svg
      width="120"
      height="120"
      viewBox="0 0 120 120"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="animate-pulse"
    >
      <circle cx="60" cy="50" r="24" stroke="var(--primary)" strokeWidth="2" fill="var(--primary)" fillOpacity="0.08" />
      <rect x="36" y="78" width="48" height="8" rx="4" fill="var(--primary)" fillOpacity="0.12" />
      <rect x="42" y="90" width="36" height="6" rx="3" fill="var(--primary)" fillOpacity="0.08" />
      <circle cx="52" cy="46" r="3" fill="var(--primary)" fillOpacity="0.5" />
      <circle cx="68" cy="46" r="3" fill="var(--primary)" fillOpacity="0.5" />
      <path d="M52 54 Q60 58 68 54" stroke="var(--primary)" strokeWidth="1.5" fill="none" opacity="0.4" />
    </svg>
  )
}

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(' ')
}
