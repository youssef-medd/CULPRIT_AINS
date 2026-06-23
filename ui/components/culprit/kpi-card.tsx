import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { Sparkline } from './sparkline'

interface KpiCardProps {
  label: string
  value: string
  sub?: string
  trend: number[]
  color?: string
  icon?: React.ReactNode
  className?: string
}

export function KpiCard({ label, value, sub, trend, color = 'var(--primary)', icon, className }: KpiCardProps) {
  return (
    <Card className={cn('flex flex-col justify-between gap-4 p-6', className)}>
      <div className="flex items-start justify-between">
        <div className="flex flex-col gap-2">
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </span>
          <span className="text-3xl font-semibold tabular-nums tracking-tight text-foreground">
            {value}
          </span>
        </div>
        {icon && (
          <span
            className="flex size-8 items-center justify-center rounded border"
            style={{ color, borderColor: `${color}40`, backgroundColor: `${color}12` }}
          >
            {icon}
          </span>
        )}
      </div>
      <div className="flex items-end justify-between gap-3">
        {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
        <Sparkline data={trend} color={color} width={96} height={32} className="ml-auto" />
      </div>
    </Card>
  )
}
