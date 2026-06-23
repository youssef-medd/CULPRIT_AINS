'use client'

import { SplineScene } from '@/components/ui/splite'
import { Spotlight } from '@/components/ui/spotlight'
import { Card } from '@/components/ui/card'
import { Crosshair, GitBranch, ShieldCheck } from 'lucide-react'
import { CulpritLogo } from './culprit-logo'

interface HeroProps {
  totalRuns: number
  failures: number
  attributionAccuracy: number | null
}

export function Hero({ totalRuns, failures, attributionAccuracy }: HeroProps) {
  return (
    <Card className="relative h-[360px] w-full overflow-hidden border-border bg-secondary p-0 md:h-[420px]">
      <Spotlight className="-top-40 left-0 md:-top-20 md:left-60" fill="var(--primary)" />
      <div className="grid-bg pointer-events-none absolute inset-0 opacity-40" />

      <div className="flex h-full flex-col md:flex-row">
        {/* Left content */}
        <div className="relative z-10 flex flex-1 flex-col justify-center gap-5 p-6 md:p-10">
          <div className="flex items-center gap-2">
            <CulpritLogo className="size-7" />
            <span className="text-xs font-semibold uppercase tracking-[0.25em] text-primary">
              Culprit
            </span>
          </div>

          <div className="space-y-3">
            <h1 className="text-pretty text-3xl font-bold leading-tight tracking-tight md:text-5xl">
              Find the step that
              <br />
              <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                broke the agent.
              </span>
            </h1>
            <p className="max-w-md text-pretty text-sm leading-relaxed text-muted-foreground md:text-base">
              Counterfactual fault attribution for AI agents. CULPRIT replays execution traces,
              isolates the decisive step, and confirms the root cause before you ship a fix.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <HeroStat icon={<GitBranch className="size-3.5" />} label="Runs analyzed" value={String(totalRuns)} />
            <HeroStat icon={<Crosshair className="size-3.5" />} label="Faults found" value={String(failures)} />
            {attributionAccuracy !== null && (
              <HeroStat
                icon={<ShieldCheck className="size-3.5" />}
                label="Attribution acc."
                value={`${Math.round(attributionAccuracy * 100)}%`}
              />
            )}
          </div>
        </div>

        {/* Right content — interactive 3D scene */}
        <div className="relative min-h-[180px] flex-1">
          <SplineScene
            scene="https://prod.spline.design/kZDDjO5HuC9GJUM2/scene.splinecode"
            className="h-full w-full"
          />
          {/* fade the scene into the card on small screens */}
          <div className="pointer-events-none absolute inset-x-0 top-0 h-12 bg-gradient-to-b from-secondary to-transparent md:hidden" />
        </div>
      </div>
    </Card>
  )
}

function HeroStat({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode
  label: string
  value: string
}) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-border bg-background/40 px-3 py-2 backdrop-blur-sm">
      <span className="text-primary">{icon}</span>
      <div className="flex flex-col leading-none">
        <span className="font-mono text-sm font-semibold tabular-nums">{value}</span>
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</span>
      </div>
    </div>
  )
}
