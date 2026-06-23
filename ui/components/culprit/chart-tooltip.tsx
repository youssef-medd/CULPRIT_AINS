interface TooltipRow {
  label: string
  value: string | number
  color?: string
}

export function ChartTooltip({
  title,
  rows,
}: {
  title?: string
  rows: TooltipRow[]
}) {
  return (
    <div className="rounded-lg border border-border bg-popover/95 px-3 py-2 text-xs shadow-xl backdrop-blur-sm">
      {title && <p className="mb-1 font-medium text-foreground">{title}</p>}
      <div className="flex flex-col gap-1">
        {rows.map((r) => (
          <div key={r.label} className="flex items-center justify-between gap-4">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              {r.color && (
                <span className="size-2 rounded-full" style={{ backgroundColor: r.color }} />
              )}
              {r.label}
            </span>
            <span className="font-mono font-medium tabular-nums text-foreground">{r.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
