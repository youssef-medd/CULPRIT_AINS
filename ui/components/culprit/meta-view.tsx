'use client'

import { Target, Crosshair, BadgeCheck, DatabaseZap } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { STEP_TYPE_META } from '@/lib/constants'
import { formatCategory } from '@/lib/data'
import type { MetaEval, StepType } from '@/lib/types'
import { cn } from '@/lib/utils'

export function MetaView({ meta }: { meta: MetaEval | null }) {
  if (!meta) {
    return (
      <Card className="flex flex-col items-center justify-center gap-3 p-16 text-center">
        <span className="flex size-12 items-center justify-center rounded-full bg-secondary text-muted-foreground">
          <DatabaseZap className="size-6" />
        </span>
        <div>
          <h2 className="text-base font-semibold">No meta-evaluation available</h2>
          <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
            This dataset was generated without ground-truth labels, so attribution quality metrics
            could not be computed. Provide labeled cases to populate this view.
          </p>
        </div>
      </Card>
    )
  }

  const stats = [
    {
      label: 'Attribution Accuracy',
      value: meta.attribution_accuracy,
      icon: <Target className="size-5" />,
      color: 'var(--ok)',
      desc: 'Correct component attributed vs. ground truth',
    },
    {
      label: 'Step Localization',
      value: meta.step_localization_accuracy,
      icon: <Crosshair className="size-5" />,
      color: 'var(--retrieval)',
      desc: 'Exact decisive step identified',
    },
    {
      label: 'Confirmation Rate',
      value: meta.confirmation_rate,
      icon: <BadgeCheck className="size-5" />,
      color: 'var(--primary)',
      desc: 'Attributions confirmed by counterfactual',
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">Meta-Evaluation</h2>
          <span className="rounded-full border border-border bg-secondary/40 px-2.5 py-1 text-xs text-muted-foreground">
            {meta.n_cases} labeled cases
          </span>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          How well CULPRIT&apos;s attributions agree with human ground-truth labels.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {stats.map((s) => (
          <Card key={s.label} className="flex flex-col gap-4 p-6">
            <div className="flex items-center justify-between">
              <span
                className="flex size-10 items-center justify-center rounded-xl"
                style={{ color: s.color, backgroundColor: `color-mix(in oklch, ${s.color} 14%, transparent)` }}
              >
                {s.icon}
              </span>
              <span className="font-mono text-4xl font-semibold tabular-nums" style={{ color: s.color }}>
                {Math.round(s.value * 100)}
                <span className="text-lg text-muted-foreground">%</span>
              </span>
            </div>
            <div>
              <p className="text-sm font-semibold">{s.label}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">{s.desc}</p>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${Math.round(s.value * 100)}%`, backgroundColor: s.color }}
              />
            </div>
          </Card>
        ))}
      </div>

      {/* Per-category table */}
      <Card className="overflow-hidden p-0">
        <div className="border-b border-border px-5 py-4">
          <h3 className="text-sm font-semibold">Per-Component Quality</h3>
          <p className="text-xs text-muted-foreground">Precision, recall and F1 by decisive step type</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted-foreground">
                <th className="px-5 py-3 font-medium">Component</th>
                <th className="px-5 py-3 font-medium">Precision</th>
                <th className="px-5 py-3 font-medium">Recall</th>
                <th className="px-5 py-3 font-medium">F1</th>
                <th className="px-5 py-3 font-medium">Support</th>
              </tr>
            </thead>
            <tbody>
              {meta.per_category.map((row) => {
                const isStep = row.component in STEP_TYPE_META
                const color = isStep ? STEP_TYPE_META[row.component as StepType].color : 'var(--muted-foreground)'
                const label = isStep
                  ? STEP_TYPE_META[row.component as StepType].label
                  : formatCategory(String(row.component))
                return (
                  <tr key={row.component} className="border-b border-border/60 last:border-0 hover:bg-secondary/30">
                    <td className="px-5 py-3">
                      <span className="flex items-center gap-2 font-medium">
                        <span className="size-2.5 rounded-full" style={{ backgroundColor: color }} />
                        {label}
                      </span>
                    </td>
                    <MetricCell value={row.precision} />
                    <MetricCell value={row.recall} />
                    <MetricCell value={row.f1} highlight color={color} />
                    <td className="px-5 py-3 font-mono tabular-nums text-muted-foreground">{row.support}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}

function MetricCell({ value, highlight, color }: { value: number; highlight?: boolean; color?: string }) {
  return (
    <td className="px-5 py-3">
      <div className="flex items-center gap-2">
        <span className={cn('font-mono tabular-nums', highlight && 'font-semibold')} style={highlight ? { color } : undefined}>
          {value.toFixed(2)}
        </span>
        <span className="hidden h-1.5 w-16 overflow-hidden rounded-full bg-secondary sm:block">
          <span
            className="block h-full rounded-full"
            style={{ width: `${value * 100}%`, backgroundColor: color ?? 'var(--muted-foreground)' }}
          />
        </span>
      </div>
    </td>
  )
}
