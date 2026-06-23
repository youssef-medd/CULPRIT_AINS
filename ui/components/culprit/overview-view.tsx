'use client'

import {
  Area,
  AreaChart,
  CartesianGrid,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Activity, AlertTriangle, GitBranch, ShieldCheck, TrendingDown } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { SpotlightCard } from '@/components/ui/spotlight-card'
import { KpiCard } from './kpi-card'
import { ChartTooltip } from './chart-tooltip'
import { STEP_TYPE_META } from '@/lib/constants'
import { formatCategory } from '@/lib/data'
import type { Overview } from '@/lib/data'
import type { StepType } from '@/lib/types'

export function OverviewView({ overview }: { overview: Overview }) {

  const {
    totalRuns,
    failures,
    failureRate,
    attributionAccuracy,
    meanConfidence,
    confidenceSeries,
    lowestConfidence,
    failuresByComponent,
    topCategories,
    passSeries,
    failSeries,
    confidenceTrend,
  } = overview

  const radarData = failuresByComponent.map((c) => ({
    component: STEP_TYPE_META[c.component].label,
    count: c.count,
    type: c.component,
  }))

  return (
    <div className="space-y-6">
      {/* KPI cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="Total Runs"
          value={String(totalRuns)}
          sub="Evaluated traces"
          trend={passSeries}
          color="var(--retrieval)"
          icon={<GitBranch className="size-4.5" />}
        />
        <KpiCard
          label="Failures"
          value={String(failures)}
          sub={`${failureRate}% failure rate`}
          trend={failSeries}
          color="var(--fail)"
          icon={<AlertTriangle className="size-4.5" />}
        />
        <KpiCard
          label="Attribution Accuracy"
          value={attributionAccuracy !== null ? `${Math.round(attributionAccuracy * 100)}%` : '—'}
          sub="vs. ground-truth labels"
          trend={confidenceTrend}
          color="var(--ok)"
          icon={<ShieldCheck className="size-4.5" />}
        />
        <KpiCard
          label="Mean Confidence"
          value={`${meanConfidence}%`}
          sub="Across all attributions"
          trend={confidenceTrend}
          color="var(--primary)"
          icon={<Activity className="size-4.5" />}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Confidence across runs */}
        <Card className="lg:col-span-2 p-5">
          <div className="mb-4 flex items-start justify-between">
            <div>
              <h2 className="text-base font-semibold">Attribution Confidence</h2>
              <p className="text-xs text-muted-foreground">Per-run confidence with lowest point flagged</p>
            </div>
            {lowestConfidence && (
              <div className="flex items-center gap-1.5 rounded-full border border-border bg-secondary/40 px-2.5 py-1 text-xs">
                <TrendingDown className="size-3.5 text-fail" />
                <span className="text-muted-foreground">Low:</span>
                <span className="font-mono font-medium" style={{ color: 'var(--fail)' }}>
                  {lowestConfidence.confidence}%
                </span>
                <span className="text-muted-foreground">({lowestConfidence.run_id})</span>
              </div>
            )}
          </div>
          <div className="h-[260px] w-full">
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={confidenceSeries} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <defs>
                  <linearGradient id="confGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--primary)" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="var(--primary)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(1 0 0 / 7%)" vertical={false} />
                <XAxis
                  dataKey="index"
                  tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  width={42}
                  unit="%"
                />
                <Tooltip
                  cursor={{ stroke: 'oklch(1 0 0 / 20%)' }}
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null
                    const p = payload[0].payload
                    return (
                      <ChartTooltip
                        title={`${p.run_id} · run ${p.index}`}
                        rows={[
                          { label: 'Confidence', value: `${p.confidence}%`, color: 'var(--primary)' },
                          { label: 'Verdict', value: p.verdict },
                        ]}
                      />
                    )
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="confidence"
                  stroke="var(--primary)"
                  strokeWidth={2}
                  fill="url(#confGrad)"
                  dot={{ r: 3, fill: 'var(--background)', stroke: 'var(--primary)', strokeWidth: 1.5 }}
                  activeDot={{ r: 5 }}
                />
                {lowestConfidence && (
                  <ReferenceDot
                    x={lowestConfidence.index}
                    y={lowestConfidence.confidence}
                    r={6}
                    fill="var(--fail)"
                    stroke="var(--background)"
                    strokeWidth={2}
                  />
                )}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Failures by component (radar) */}
        <Card className="p-5">
          <div className="mb-2">
            <h2 className="text-base font-semibold">Failures by Component</h2>
            <p className="text-xs text-muted-foreground">Where faults are attributed</p>
          </div>
          <div className="h-[260px] w-full">
            <ResponsiveContainer width="100%" height={260}>
              <RadarChart data={radarData} outerRadius="72%">
                <PolarGrid stroke="oklch(1 0 0 / 10%)" />
                <PolarAngleAxis
                  dataKey="component"
                  tick={{ fill: 'var(--muted-foreground)', fontSize: 10 }}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null
                    const p = payload[0].payload
                    return (
                      <ChartTooltip
                        rows={[
                          {
                            label: p.component,
                            value: `${p.count} fault${p.count === 1 ? '' : 's'}`,
                            color: STEP_TYPE_META[p.type as StepType].color,
                          },
                        ]}
                      />
                    )
                  }}
                />
                <Radar
                  dataKey="count"
                  stroke="var(--primary)"
                  fill="var(--primary)"
                  fillOpacity={0.25}
                  strokeWidth={2}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 flex flex-wrap items-center justify-center gap-x-3 gap-y-1">
            {failuresByComponent.map((c) => (
              <span key={c.component} className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                <span
                  className="size-2 rounded-full"
                  style={{ backgroundColor: STEP_TYPE_META[c.component].color }}
                />
                {STEP_TYPE_META[c.component].label} · {c.count}
              </span>
            ))}
          </div>
        </Card>
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Top Failure Categories
        </h2>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
          {topCategories.map((cat, i) => {
            const color = `var(--${cat.component})`
            return (
              <SpotlightCard
                key={cat.category}
                className="p-6 flex flex-col gap-4"
                spotlightColor={spotlightRGBA(cat.component)}
              >
                <div className="flex items-start justify-between">
                  <span className="font-mono text-2xl font-semibold text-muted-foreground/40">
                    #{i + 1}
                  </span>
                  <span
                    className="rounded-full px-2 py-0.5 text-[11px] font-medium"
                    style={{
                      color,
                      backgroundColor: `color-mix(in oklch, ${color} 14%, transparent)`,
                    }}
                  >
                    {STEP_TYPE_META[cat.component].label}
                  </span>
                </div>
                <div>
                  <p className="text-base font-semibold">{formatCategory(cat.category)}</p>
                  <p className="text-sm text-neutral-400">
                    {cat.count} attributed failure{cat.count === 1 ? '' : 's'}
                  </p>
                </div>
              </SpotlightCard>
            )
          })}
          {topCategories.length === 0 && (
            <SpotlightCard className="col-span-full p-5 text-sm text-muted-foreground">
              No failures attributed.
            </SpotlightCard>
          )}
        </div>
      </div>
    </div>
  )
}

function spotlightRGBA(component: string): string {
  const map: Record<string, string> = {
    retrieval: 'rgba(59, 130, 246, 0.2)',
    planning: 'rgba(139, 92, 246, 0.2)',
    tool: 'rgba(16, 185, 129, 0.2)',
    synthesis: 'rgba(245, 158, 11, 0.2)',
  }
  return map[component] ?? 'rgba(255, 255, 255, 0.15)'
}
