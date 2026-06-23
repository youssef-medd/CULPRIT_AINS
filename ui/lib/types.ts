export type StepType = 'retrieval' | 'planning' | 'tool_execution' | 'synthesis'
export type StepStatus = 'ok' | 'error' | 'skipped'
export type Verdict = 'pass' | 'fail' | 'unknown'

export interface Evidence {
  field: string
  expected: string
  actual: string
}

export interface CounterfactualRepairEdit {
  field: string
  from_value: unknown
  to_value: unknown
}

export interface CounterfactualRepair {
  description: string
  edits: CounterfactualRepairEdit[]
}

export interface Counterfactual {
  performed: boolean
  result: string | null
  confirms_attribution: boolean
  minimal: boolean
  repair: CounterfactualRepair | null
}

export interface Attribution {
  end_to_end_verdict: Verdict
  decisive_step_id: string | null
  decisive_step_type: StepType | null
  failure_category: string | null
  why: string
  evidence: Evidence[]
  confidence: number
  crs: number | null
  counterfactual: Counterfactual
  confirmed: boolean
  recommended_fix: string
}

export interface TrajectoryStep {
  step_id: string
  step_index: number
  step_type: StepType
  span_name: string
  action: { tool_name?: string; arguments?: Record<string, unknown> } | null
  result: Record<string, unknown>
  status: StepStatus
  latency_ms: number
  context_snapshot?: { inputs?: Record<string, unknown>; available_fields?: string[] }
}

export interface Trajectory {
  steps: TrajectoryStep[]
  final_status: string
}

export interface Ticket {
  id: string
  title: string
  description: string
  product_area: string
  reporter: string
}

export interface Label {
  fault_type: string
  step_id: string
  component: StepType
  failure_category: string
}

export interface Run {
  run_id: string
  ticket: Ticket
  label: Label | null
  attribution: Attribution
  trajectory: Trajectory
  total_ms: number
}

export interface PerCategory {
  component: StepType | string
  precision: number
  recall: number
  f1: number
  support: number
}

export interface MetaEval {
  n_cases: number
  attribution_accuracy: number
  step_localization_accuracy: number
  confirmation_rate: number
  per_category: PerCategory[]
  /** gold component -> { predicted component (or "none") -> count } */
  confusion?: Record<string, Record<string, number>>
}

export interface CulpritData {
  generated_at: string
  meta_eval: MetaEval | null
  runs: Run[]
}
