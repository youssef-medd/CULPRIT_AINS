'use client'

import { Target, Crosshair, BadgeCheck, DatabaseZap, TrendingUp, Grid3x3 } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { STEP_TYPE_META, STEP_TYPES, SOTA_BASELINES } from '@/lib/constants'
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
      sota: SOTA_BASELINES.attribution_accuracy,
    },
    {
      label: 'Step Localization',
      value: meta.step_localization_accuracy,
      icon: <Crosshair className="size-5" />,
      color: 'var(--retrieval)',
      desc: 'Exact decisive step identified',
      sota: SOTA_BASELINES.step_localization_accuracy,
    },
    {
      label: 'Confirmation Rate',
      value: meta.confirmation_rate,
      icon: <BadgeCheck className="size-5" />,
      color: 'var(--primary)',
      desc: 'Attributions confirmed by counterfactual',
      sota: null,
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
            <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-secondary">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${Math.round(s.value * 100)}%`, backgroundColor: s.color }}
              />
              {s.sota && (
                <span
                  className="absolute top-1/2 h-3 w-0.5 -translate-y-1/2 rounded-full bg-foreground/50"
                  style={{ left: `${Math.round(s.sota.value * 100)}%` }}
                  title={`${s.sota.label}: ${Math.round(s.sota.value * 100)}%`}
                />
              )}
            </div>
            {s.sota ? (
              <div className="flex items-center gap-1.5 text-xs">
                <span className="flex items-center gap-1 font-medium text-[var(--ok)]">
                  <TrendingUp className="size-3.5" />
                  +{((s.value - s.sota.value) * 100).toFixed(1)} pts
                </span>
                <span className="text-muted-foreground">
                  vs {Math.round(s.sota.value * 100)}% {s.sota.label}
                </span>
              </div>
            ) : (
              <div className="h-[1.125rem]" aria-hidden />
            )}
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

      {meta.confusion && <ConfusionMatrix confusion={meta.confusion} />}
    </div>
  )
}

function ConfusionMatrix({ confusion }: { confusion: Record<string, Record<string, number>> }) {
  const golds = STEP_TYPES.filter((c) => c in confusion)
  const hasNone = Object.values(confusion).some((row) => 'none' in row)
  const preds: string[] = [...STEP_TYPES.filter((c) => golds.some((g) => c in confusion[g])), ...(hasNone ? ['none'] : [])]

  const label = (c: string) => (c in STEP_TYPE_META ? STEP_TYPE_META[c as StepType].label : formatCategory(c))

  return (
    <Card className="overflow-hidden p-0">
      <div className="flex items-center gap-2 border-b border-border px-5 py-4">
        <span className="flex size-7 items-center justify-center rounded-md bg-secondary text-muted-foreground">
          <Grid3x3 className="size-4" />
        </span>
        <div>
          <h3 className="text-sm font-semibold">Confusion Matrix</h3>
          <p className="text-xs text-muted-foreground">
            Rows = ground-truth component · columns = what CULPRIT attributed · diagonal = correct
          </p>
        </div>
      </div>
      <div className="overflow-x-auto p-5">
        <table className="w-full min-w-[520px] border-separate border-spacing-1 text-sm">
          <thead>
            <tr>
              <th className="px-2 py-1.5 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Gold ╲ Pred
              </th>
              {preds.map((p) => (
                <th key={p} className="px-2 py-1.5 text-center text-xs font-medium text-muted-foreground">
                  <span className="inline-flex items-center gap-1.5">
                    <span
                      className="size-2 rounded-full"
                      style={{ backgroundColor: p in STEP_TYPE_META ? STEP_TYPE_META[p as StepType].color : 'var(--muted-foreground)' }}
                    />
                    {label(p)}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {golds.map((g) => {
              const row = confusion[g]
              const rowTotal = Object.values(row).reduce((a, b) => a + b, 0) || 1
              return (
                <tr key={g}>
                  <td className="px-2 py-1.5 text-xs font-medium">
                    <span className="flex items-center gap-1.5">
                      <span className="size-2.5 rounded-full" style={{ backgroundColor: STEP_TYPE_META[g as StepType].color }} />
                      {label(g)}
                    </span>
                  </td>
                  {preds.map((p) => {
                    const count = row[p] ?? 0
                    const isDiag = g === p
                    const intensity = count / rowTotal
                    const base = isDiag ? 'var(--ok)' : 'var(--error)'
                    const bg = count === 0
                      ? 'transparent'
                      : `color-mix(in oklch, ${base} ${Math.round(12 + intensity * 60)}%, transparent)`
                    return (
                      <td key={p} className="p-0">
                        <div
                          className={cn(
                            'flex h-11 items-center justify-center rounded-md font-mono tabular-nums',
                            count === 0 ? 'text-muted-foreground/40' : 'font-semibold text-foreground',
                          )}
                          style={{ backgroundColor: bg, border: count === 0 ? '1px dashed var(--border)' : 'none' }}
                          title={`${label(g)} → ${label(p)}: ${count}`}
                        >
                          {count}
                        </div>
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
        <p className="mt-3 text-xs text-muted-foreground">
          Green diagonal = correct attributions. Off-diagonal red cells show where the decisive
          component was mistaken for another; a <span className="font-medium text-foreground">none</span> column
          marks runs left unattributed.
        </p>
      </div>
    </Card>
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
