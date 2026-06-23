'use client'

import { useState, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Crosshair, LayoutDashboard, ListTree, GaugeCircle, Activity } from 'lucide-react'
import { cn } from '@/lib/utils'
import { computeOverview, getData } from '@/lib/data'
import { Hero } from './hero'
import { OverviewView } from './overview-view'
import { RunsView } from './runs-view'
import { MetaView } from './meta-view'
import { DriftView } from './drift-view'
import { ThemeToggleWrapper } from './theme-toggle-wrapper'

type TabId = 'overview' | 'runs' | 'meta' | 'drift'

const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: 'overview', label: 'Overview', icon: <LayoutDashboard className="size-4" /> },
  { id: 'runs', label: 'Runs & Attribution', icon: <ListTree className="size-4" /> },
  { id: 'meta', label: 'Meta-Evaluation', icon: <GaugeCircle className="size-4" /> },
  { id: 'drift', label: 'Drift', icon: <Activity className="size-4" /> },
]

export function Dashboard() {
  const [tab, setTab] = useState<TabId>('overview')
  const [generatedAt, setGeneratedAt] = useState('')
  const data = getData()
  const overview = computeOverview()

  useEffect(() => {
    const formatted = new Date(data.generated_at).toLocaleString('en-US', {
      dateStyle: 'medium',
      timeStyle: 'short',
    })
    setGeneratedAt(formatted)
  }, [data.generated_at])

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 md:px-6">
          <div className="flex items-center gap-3">
            <span className="flex size-7 items-center justify-center rounded border border-primary/30 bg-primary/10 text-primary">
              <Crosshair className="size-4" strokeWidth={1.5} />
            </span>
            <div className="leading-none">
              <p className="text-xs font-semibold uppercase tracking-wide text-foreground">CULPRIT</p>
              <p className="hidden text-xs text-muted-foreground sm:block">
                Fault Attribution
              </p>
            </div>
          </div>

          <nav className="hidden items-center gap-px rounded-md border border-border bg-muted/30 p-px lg:flex">
            {TABS.map((t) => (
              <TabButton key={t.id} active={tab === t.id} onClick={() => setTab(t.id)} {...t} />
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <div className="hidden text-right md:block">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Generated</p>
              <p className="font-mono text-[11px] text-foreground/60">{generatedAt}</p>
            </div>
            <ThemeToggleWrapper />
          </div>
        </div>

        {/* Mobile nav */}
        <nav className="flex items-center gap-px overflow-x-auto border-t border-border/40 px-3 py-2 lg:hidden">
          {TABS.map((t) => (
            <TabButton key={t.id} active={tab === t.id} onClick={() => setTab(t.id)} {...t} />
          ))}
        </nav>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 md:px-6 md:py-8">
        <div className={cn('mb-6', tab !== 'overview' && 'hidden')}>
          <Hero
            totalRuns={overview.totalRuns}
            failures={overview.failures}
            attributionAccuracy={overview.attributionAccuracy}
          />
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
          >
            {tab === 'overview' && <OverviewView overview={overview} />}
            {tab === 'runs' && <RunsView runs={data.runs} />}
            {tab === 'meta' && <MetaView meta={data.meta_eval} />}
            {tab === 'drift' && <DriftView runs={data.runs} />}
          </motion.div>
        </AnimatePresence>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-2 px-4 py-5 text-xs text-muted-foreground sm:flex-row md:px-6">
          <p>CULPRIT — counterfactual fault attribution for AI agents.</p>
          <p className="font-mono">{overview.totalRuns} runs · {overview.failures} attributed faults</p>
        </div>
      </footer>
    </div>
  )
}

function TabButton({
  active,
  onClick,
  label,
  icon,
}: {
  active: boolean
  onClick: () => void
  label: string
  icon: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'relative flex shrink-0 items-center gap-2 rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors',
        active ? 'text-primary-foreground' : 'text-muted-foreground hover:text-foreground',
      )}
    >
      {active && (
        <motion.span
          layoutId="tab-pill"
          className="absolute inset-0 rounded-full bg-primary"
          transition={{ type: 'spring', stiffness: 400, damping: 32 }}
        />
      )}
      <span className="relative z-10 flex items-center gap-2">
        {icon}
        {label}
      </span>
    </button>
  )
}
