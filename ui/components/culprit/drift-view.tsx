'use client'

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts'
import { Info, TrendingUp } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { ChartTooltip } from './chart-tooltip'
import { STEP_TYPE_META, STEP_TYPES } from '@/lib/constants'
import type { Run, StepType } from '@/lib/types'

export function DriftView({ runs }: { runs: Run[] }) {
  const failing = runs.filter((r) => r.attribution.end_to_end_verdict === 'fail')
  const totalFailures = failing.length

  const counts = STEP_TYPES.map((t) => {
    const count = failing.filter((r) => r.attribution.decisive_step_type === t).length
    return {
      type: t,
      label: STEP_TYPE_META[t].label,
      color: STEP_TYPE_META[t].color,
      count,
      share: totalFailures ? Math.round((count / totalFailures) * 100) : 0,
    }
  })

  const maxCount = Math.max(1, ...counts.map((c) => c.count))
  const dominant = [...counts].sort((a, b) => b.count - a.count)[0]

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-base font-semibold">Failure Drift</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Distribution of attributed faults across agent components. Watch for shifts in this
          shape over time — they signal which part of the pipeline is regressing.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Distribution chart */}
        <Card className="lg:col-span-2 p-5">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold">Faults by Component</h3>
            <span className="text-xs text-muted-foreground">{totalFailures} total faults</span>
          </div>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={counts} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(1 0 0 / 7%)" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  width={36}
                />
                <Tooltip
                  cursor={{ fill: 'oklch(1 0 0 / 5%)' }}
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null
                    const p = payload[0].payload
                    return (
                      <ChartTooltip
                        title={p.label}
                        rows={[
                          { label: 'Faults', value: p.count, color: p.color },
                          { label: 'Share', value: `${p.share}%` },
                        ]}
                      />
                    )
                  }}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]} maxBarSize={64}>
                  {counts.map((c) => (
                    <Cell key={c.type} fill={c.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Share breakdown */}
        <Card className="flex flex-col gap-4 p-5">
          <div className="flex items-center gap-2">
            <span className="flex size-8 items-center justify-center rounded-lg bg-primary/15 text-primary">
              <TrendingUp className="size-4" />
            </span>
            <div>
              <p className="text-sm font-semibold">Concentration</p>
              <p className="text-xs text-muted-foreground">Where faults cluster</p>
            </div>
          </div>

          <div className="flex flex-col gap-3">
            {counts
              .slice()
              .sort((a, b) => b.count - a.count)
              .map((c) => (
                <div key={c.type} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="flex items-center gap-1.5 font-medium">
                      <span className="size-2 rounded-full" style={{ backgroundColor: c.color }} />
                      {c.label}
                    </span>
                    <span className="font-mono tabular-nums text-muted-foreground">
                      {c.count} · {c.share}%
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${(c.count / maxCount) * 100}%`, backgroundColor: c.color }}
                    />
                  </div>
                </div>
              ))}
          </div>

          {dominant && dominant.count > 0 && (
            <div className="mt-auto rounded-lg border border-border bg-secondary/30 p-3">
              <p className="text-xs leading-relaxed text-muted-foreground">
                <span className="font-medium text-foreground">{dominant.label}</span> is the current
                hotspot at <span className="font-mono" style={{ color: dominant.color }}>{dominant.share}%</span> of
                faults. A sustained rise here over future runs indicates drift in that component.
              </p>
            </div>
          )}
        </Card>
      </div>

      <Card className="flex items-start gap-3 p-4">
        <Info className="mt-0.5 size-4 shrink-0 text-primary" />
        <p className="text-xs leading-relaxed text-muted-foreground">
          <span className="font-medium text-foreground">Monitoring for shifts:</span> this snapshot
          reflects a single evaluation batch. In production, compare the distribution across batches —
          a growing share for any component, or the emergence of a previously rare failure category,
          is an early signal that the agent or its tools have regressed and warrant investigation.
        </p>
      </Card>
    </div>
  )
}
