'use client'

import { motion } from 'framer-motion'
import { Flag, Inbox, Crosshair, CheckCircle2, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { STEP_TYPE_META, STATUS_META } from '@/lib/constants'
import type { Run } from '@/lib/types'
import { StepTypeBadge, StatusBadge } from './badges'

export function TraceTimeline({ run }: { run: Run }) {
  const { trajectory, attribution, ticket } = run
  const decisiveId = attribution.decisive_step_id
  const failed = attribution.end_to_end_verdict === 'fail'

  return (
    <div className="relative pl-1">
      {/* Intake node */}
      <TimelineRow
        index={-1}
        accent="var(--muted-foreground)"
        icon={<Inbox className="size-3.5" />}
        isFirst
      >
        <div className="rounded-lg border border-border bg-secondary/30 px-3 py-2">
          <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            Ticket Intake
          </p>
          <p className="text-sm font-medium">
            <span className="font-mono text-muted-foreground">{ticket.id}</span> · {ticket.title}
          </p>
        </div>
      </TimelineRow>

      {trajectory.steps.map((step, i) => {
        const meta = STEP_TYPE_META[step.step_type]
        const isDecisive = step.step_id === decisiveId
        return (
          <TimelineRow
            key={step.step_id}
            index={i}
            accent={meta.color}
            icon={isDecisive ? <Crosshair className="size-3.5" /> : <span className="text-[10px] font-bold">{i + 1}</span>}
            highlight={isDecisive}
          >
            <motion.div
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.04 * i, duration: 0.25 }}
              className={cn(
                'rounded-lg border px-3 py-2.5 transition-colors',
                isDecisive
                  ? 'border-transparent'
                  : 'border-border bg-card hover:bg-secondary/40',
              )}
              style={
                isDecisive
                  ? {
                      backgroundColor: `color-mix(in oklch, ${meta.color} 10%, var(--card))`,
                      boxShadow: `inset 0 0 0 1px color-mix(in oklch, ${meta.color} 45%, transparent)`,
                    }
                  : undefined
              }
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <StepTypeBadge type={step.step_type} size="sm" />
                  <span className="font-mono text-xs text-foreground/90">{step.span_name}</span>
                </div>
                <div className="flex items-center gap-2">
                  {isDecisive && (
                    <span
                      className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide"
                      style={{
                        color: meta.color,
                        backgroundColor: `color-mix(in oklch, ${meta.color} 18%, transparent)`,
                      }}
                    >
                      Decisive
                    </span>
                  )}
                  <StatusBadge status={step.status} />
                </div>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
                {step.action?.tool_name && (
                  <span>
                    tool <span className="font-mono text-foreground/80">{step.action.tool_name}</span>
                  </span>
                )}
                <span>
                  <span className="font-mono text-foreground/80">{step.latency_ms}</span> ms
                </span>
                {step.action?.arguments && Object.keys(step.action.arguments).length > 0 && (
                  <span className="font-mono truncate">
                    {JSON.stringify(step.action.arguments)}
                  </span>
                )}
              </div>
            </motion.div>
          </TimelineRow>
        )
      })}

      {/* Final outcome */}
      <TimelineRow
        index={trajectory.steps.length}
        accent={failed ? 'var(--fail)' : 'var(--pass)'}
        icon={failed ? <XCircle className="size-3.5" /> : <CheckCircle2 className="size-3.5" />}
        isLast
      >
        <div
          className="flex items-center gap-2 rounded-lg border px-3 py-2"
          style={{
            borderColor: `color-mix(in oklch, ${failed ? 'var(--fail)' : 'var(--pass)'} 35%, transparent)`,
            backgroundColor: `color-mix(in oklch, ${failed ? 'var(--fail)' : 'var(--pass)'} 10%, transparent)`,
          }}
        >
          <Flag className="size-3.5" style={{ color: failed ? 'var(--fail)' : 'var(--pass)' }} />
          <span className="text-sm font-medium" style={{ color: failed ? 'var(--fail)' : 'var(--pass)' }}>
            {trajectory.final_status.replace(/_/g, ' ')}
          </span>
        </div>
      </TimelineRow>
    </div>
  )
}

function TimelineRow({
  accent,
  icon,
  children,
  highlight,
  isFirst,
  isLast,
}: {
  index: number
  accent: string
  icon: React.ReactNode
  children: React.ReactNode
  highlight?: boolean
  isFirst?: boolean
  isLast?: boolean
}) {
  return (
    <div className="relative flex gap-3 pb-3 last:pb-0">
      {/* connector line */}
      {!isLast && (
        <span className="absolute left-[13px] top-7 h-[calc(100%-12px)] w-px bg-border" aria-hidden />
      )}
      <span
        className="relative z-10 mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full border"
        style={{
          color: accent,
          borderColor: `color-mix(in oklch, ${accent} 50%, transparent)`,
          backgroundColor: `color-mix(in oklch, ${accent} 15%, var(--background))`,
          boxShadow: highlight ? `0 0 0 4px color-mix(in oklch, ${accent} 18%, transparent)` : undefined,
        }}
      >
        {icon}
      </span>
      <div className={cn('min-w-0 flex-1', isFirst || isLast ? '' : '')}>{children}</div>
    </div>
  )
}
