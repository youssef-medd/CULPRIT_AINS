'use client'

import { useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Search,
  Clock,
  ChevronRight,
  Wrench,
  ChevronDown,
  CheckCircle2,
  CircleDashed,
  Crosshair,
} from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { STEP_TYPE_META, STEP_TYPES, VERDICT_META } from '@/lib/constants'
import { formatCategory } from '@/lib/data'
import type { Run, StepType } from '@/lib/types'
import { StepTypeBadge, VerdictBadge, MetricBadge } from './badges'
import { TraceTimeline } from './trace-timeline'

export function RunsView({ runs }: { runs: Run[] }) {
  const [query, setQuery] = useState('')
  const [verdictFilter, setVerdictFilter] = useState<'all' | 'pass' | 'fail' | 'unknown'>('all')
  const [componentFilter, setComponentFilter] = useState<'all' | StepType>('all')
  const [selectedId, setSelectedId] = useState<string>(runs[0]?.run_id ?? '')

  const filtered = useMemo(() => {
    return runs.filter((r) => {
      const q = query.trim().toLowerCase()
      const matchesQuery =
        !q ||
        r.ticket.id.toLowerCase().includes(q) ||
        r.ticket.title.toLowerCase().includes(q) ||
        r.run_id.toLowerCase().includes(q) ||
        r.ticket.product_area.toLowerCase().includes(q)
      const matchesVerdict =
        verdictFilter === 'all' || r.attribution.end_to_end_verdict === verdictFilter
      const matchesComponent =
        componentFilter === 'all' || r.attribution.decisive_step_type === componentFilter
      return matchesQuery && matchesVerdict && matchesComponent
    })
  }, [runs, query, verdictFilter, componentFilter])

  const selected = runs.find((r) => r.run_id === selectedId) ?? filtered[0] ?? null

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,400px)_1fr]">
      {/* List */}
      <div className="flex flex-col gap-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search tickets, runs, areas..."
            className="pl-9"
          />
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <FilterChip active={verdictFilter === 'all'} onClick={() => setVerdictFilter('all')}>
            All
          </FilterChip>
          <FilterChip
            active={verdictFilter === 'fail'}
            onClick={() => setVerdictFilter('fail')}
            color="var(--fail)"
          >
            Fail
          </FilterChip>
          <FilterChip
            active={verdictFilter === 'pass'}
            onClick={() => setVerdictFilter('pass')}
            color="var(--pass)"
          >
            Pass
          </FilterChip>
          <FilterChip
            active={verdictFilter === 'unknown'}
            onClick={() => setVerdictFilter('unknown')}
            color="var(--skipped)"
          >
            Unknown
          </FilterChip>
          <span className="mx-1 h-4 w-px bg-border" />
          <FilterChip active={componentFilter === 'all'} onClick={() => setComponentFilter('all')}>
            Any step
          </FilterChip>
          {STEP_TYPES.map((t) => (
            <FilterChip
              key={t}
              active={componentFilter === t}
              onClick={() => setComponentFilter(t)}
              color={STEP_TYPE_META[t].color}
            >
              {STEP_TYPE_META[t].label}
            </FilterChip>
          ))}
        </div>

        <div className="flex max-h-[640px] flex-col gap-2 overflow-y-auto pr-1">
          {filtered.map((run) => {
            const active = selected?.run_id === run.run_id
            const verdict = run.attribution.end_to_end_verdict
            const comp = run.attribution.decisive_step_type
            return (
              <button
                key={run.run_id}
                onClick={() => setSelectedId(run.run_id)}
                className={cn(
                  'group flex flex-col gap-2 rounded-xl border p-3 text-left transition-all',
                  active
                    ? 'border-primary/50 bg-primary/5'
                    : 'border-border bg-card hover:border-border hover:bg-secondary/40',
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs text-muted-foreground">{run.ticket.id}</span>
                  <VerdictBadge verdict={verdict} size="sm" />
                </div>
                <p className="line-clamp-1 text-sm font-medium">{run.ticket.title}</p>
                <div className="flex items-center justify-between gap-2">
                  {comp ? (
                    <StepTypeBadge type={comp} size="sm" />
                  ) : (
                    <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                      <CheckCircle2 className="size-3" style={{ color: 'var(--pass)' }} />
                      resolved
                    </span>
                  )}
                  <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
                    <Clock className="size-3" />
                    {(run.total_ms / 1000).toFixed(2)}s
                  </span>
                </div>
              </button>
            )
          })}
          {filtered.length === 0 && (
            <Card className="p-6 text-center text-sm text-muted-foreground">
              No runs match your filters.
            </Card>
          )}
        </div>
      </div>

      {/* Detail */}
      <div>
        <AnimatePresence mode="wait">
          {selected && (
            <motion.div
              key={selected.run_id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25 }}
              className="space-y-4"
            >
              <RunDetail run={selected} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

function RunDetail({ run }: { run: Run }) {
  const a = run.attribution
  const verdictColor = VERDICT_META[a.end_to_end_verdict].color
  const accent = a.decisive_step_type ? STEP_TYPE_META[a.decisive_step_type].color : verdictColor

  return (
    <>
      {/* Verdict hero */}
      <Card
        className="relative overflow-hidden p-5"
        style={{
          backgroundColor: `color-mix(in oklch, ${verdictColor} 7%, var(--card))`,
        }}
      >
        <span
          className="absolute inset-y-0 left-0 w-1"
          style={{ backgroundColor: verdictColor }}
        />
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-muted-foreground">{run.ticket.id}</span>
              <span className="text-xs text-muted-foreground">· {run.ticket.product_area}</span>
            </div>
            <h2 className="text-lg font-semibold">{run.ticket.title}</h2>
          </div>
          <VerdictBadge verdict={a.end_to_end_verdict} />
        </div>

        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">{run.ticket.description}</p>

        {a.decisive_step_type && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="text-xs text-muted-foreground">Decisive component</span>
            <StepTypeBadge type={a.decisive_step_type} />
            {a.failure_category && (
              <span
                className="rounded-full border px-2.5 py-1 text-xs font-medium"
                style={{
                  color: accent,
                  borderColor: `color-mix(in oklch, ${accent} 35%, transparent)`,
                }}
              >
                {formatCategory(a.failure_category)}
              </span>
            )}
          </div>
        )}
      </Card>

      {/* Metric badges */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MetricBadge label="Confidence" value={`${Math.round(a.confidence * 100)}%`} accent="var(--primary)" />
        <MetricBadge label="CRS" value={a.crs !== null ? a.crs.toFixed(2) : '—'} accent="var(--retrieval)" />
        <MetricBadge
          label="Confirmed"
          value={a.confirmed ? 'Yes' : 'No'}
          accent={a.confirmed ? 'var(--ok)' : 'var(--skipped)'}
        />
        <MetricBadge label="Total time" value={`${(run.total_ms / 1000).toFixed(2)}s`} />
      </div>

      {/* Explanation + recommended fix */}
      <Card className="p-5">
        <h3 className="text-sm font-semibold">Attribution</h3>
        <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{a.why}</p>

        <div className="mt-4 rounded-lg border border-border bg-secondary/30 p-3">
          <div className="flex items-center justify-between gap-2">
            <span className="flex items-center gap-2 text-sm font-medium">
              <Wrench className="size-4 text-primary" />
              Recommended Fix
            </span>
            {a.counterfactual.performed && a.counterfactual.confirms_attribution && (
              <span
                className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium"
                style={{ color: 'var(--ok)', backgroundColor: 'color-mix(in oklch, var(--ok) 14%, transparent)' }}
              >
                <CheckCircle2 className="size-3" />
                Counterfactually confirmed
              </span>
            )}
          </div>
          <p className="mt-1.5 text-sm text-foreground/90">{a.recommended_fix}</p>
          {a.counterfactual.performed && (
            <div className="mt-3 flex items-start gap-2 border-t border-border pt-3 text-xs text-muted-foreground">
              <Crosshair className="mt-0.5 size-3.5 shrink-0" style={{ color: accent }} />
              <div className="space-y-1">
                <p>{a.counterfactual.result}</p>
                <div className="flex flex-wrap gap-3">
                  <span className="inline-flex items-center gap-1">
                    {a.counterfactual.minimal ? (
                      <CheckCircle2 className="size-3" style={{ color: 'var(--ok)' }} />
                    ) : (
                      <CircleDashed className="size-3" />
                    )}
                    Minimal repair
                  </span>
                  {a.counterfactual.repair && (
                    <span>
                      Repair:                     <span className="font-mono text-foreground/80">{a.counterfactual.repair.description}</span>
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {a.evidence.length > 0 && <EvidenceList run={run} />}
      </Card>

      {/* Trace */}
      <Card className="p-5">
        <h3 className="mb-4 text-sm font-semibold">Execution Trace</h3>
        <TraceTimeline run={run} />
      </Card>
    </>
  )
}

function EvidenceList({ run }: { run: Run }) {
  const [open, setOpen] = useState(true)
  const evidence = run.attribution.evidence
  return (
    <div className="mt-4">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between rounded-lg px-1 py-1 text-sm font-medium hover:text-foreground"
      >
        <span>Evidence ({evidence.length})</span>
        <ChevronDown className={cn('size-4 transition-transform', open && 'rotate-180')} />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-2 space-y-2">
              {evidence.map((e, i) => (
                <div key={i} className="rounded-lg border border-border bg-background/50 p-3">
                  <p className="mb-2 font-mono text-xs text-muted-foreground">{e.field}</p>
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                    <div
                      className="rounded-md border px-2.5 py-1.5"
                      style={{
                        borderColor: 'color-mix(in oklch, var(--ok) 30%, transparent)',
                        backgroundColor: 'color-mix(in oklch, var(--ok) 8%, transparent)',
                      }}
                    >
                      <p className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--ok)' }}>
                        Expected
                      </p>
                      <p className="font-mono text-xs text-foreground/90">{e.expected}</p>
                    </div>
                    <div
                      className="rounded-md border px-2.5 py-1.5"
                      style={{
                        borderColor: 'color-mix(in oklch, var(--fail) 30%, transparent)',
                        backgroundColor: 'color-mix(in oklch, var(--fail) 8%, transparent)',
                      }}
                    >
                      <p className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--fail)' }}>
                        Actual
                      </p>
                      <p className="font-mono text-xs text-foreground/90">{e.actual}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function FilterChip({
  active,
  onClick,
  children,
  color,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
  color?: string
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors',
        active
          ? 'border-transparent text-background'
          : 'border-border bg-card text-muted-foreground hover:text-foreground',
      )}
      style={
        active
          ? { backgroundColor: color ?? 'var(--primary)' }
          : undefined
      }
    >
      {color && !active && <span className="size-2 rounded-full" style={{ backgroundColor: color }} />}
      {children}
    </button>
  )
}
