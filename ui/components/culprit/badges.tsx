import { cn } from '@/lib/utils'
import { STEP_TYPE_META, STATUS_META, VERDICT_META } from '@/lib/constants'
import type { StepType, StepStatus, Verdict } from '@/lib/types'

function Dot({ color }: { color: string }) {
  return (
    <span
      className="size-1 shrink-0 rounded-full"
      style={{ backgroundColor: color }}
    />
  )
}

export function StepTypeBadge({
  type,
  className,
  size = 'md',
}: {
  type: StepType
  className?: string
  size?: 'sm' | 'md'
}) {
  const meta = STEP_TYPE_META[type]
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded border font-medium',
        size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs',
        className,
      )}
      style={{
        color: meta.color,
        borderColor: `${meta.color}40`,
        backgroundColor: `${meta.color}12`,
      }}
    >
      <Dot color={meta.color} />
      {meta.label}
    </span>
  )
}

export function StatusBadge({ status, className }: { status: StepStatus; className?: string }) {
  const meta = STATUS_META[status]
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[10px] font-medium',
        className,
      )}
      style={{
        color: meta.color,
        borderColor: `${meta.color}40`,
        backgroundColor: `${meta.color}12`,
      }}
    >
      <Dot color={meta.color} />
      {meta.label}
    </span>
  )
}

export function VerdictBadge({
  verdict,
  className,
  size = 'md',
}: {
  verdict: Verdict
  className?: string
  size?: 'sm' | 'md'
}) {
  const meta = VERDICT_META[verdict]
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded border font-semibold uppercase tracking-wider',
        size === 'sm' ? 'px-2 py-0.5 text-[9px]' : 'px-2.5 py-1 text-[10px]',
        className,
      )}
      style={{
        color: meta.color,
        borderColor: `${meta.color}40`,
        backgroundColor: `${meta.color}12`,
      }}
    >
      <Dot color={meta.color} />
      {meta.label}
    </span>
  )
}

export function MetricBadge({
  label,
  value,
  accent,
  className,
}: {
  label: string
  value: string
  accent?: string
  className?: string
}) {
  return (
    <div
      className={cn(
        'flex flex-col gap-0.5 rounded-lg border border-border bg-secondary/40 px-3 py-2',
        className,
      )}
    >
      <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <span
        className="font-mono text-base font-semibold tabular-nums"
        style={accent ? { color: accent } : undefined}
      >
        {value}
      </span>
    </div>
  )
}
