import type { StepType, StepStatus, Verdict } from './types'

/**
 * Single source of truth for CULPRIT's visual identity.
 * These CSS variable references are themed in app/globals.css.
 */

export const STEP_TYPES: StepType[] = ['retrieval', 'planning', 'tool_execution', 'synthesis']

export const STEP_TYPE_META: Record<
  StepType,
  { label: string; color: string; description: string }
> = {
  retrieval: {
    label: 'Retrieval',
    color: 'var(--retrieval)',
    description: 'Fetching tickets, docs, and context',
  },
  planning: {
    label: 'Planning',
    color: 'var(--planning)',
    description: 'Deciding the next action',
  },
  tool_execution: {
    label: 'Tool Execution',
    color: 'var(--tool)',
    description: 'Invoking tools and APIs',
  },
  synthesis: {
    label: 'Synthesis',
    color: 'var(--synthesis)',
    description: 'Composing the final answer',
  },
}

export const STATUS_META: Record<StepStatus, { label: string; color: string }> = {
  ok: { label: 'OK', color: 'var(--ok)' },
  error: { label: 'Error', color: 'var(--error)' },
  skipped: { label: 'Skipped', color: 'var(--skipped)' },
}

export const VERDICT_META: Record<Verdict, { label: string; color: string }> = {
  pass: { label: 'Pass', color: 'var(--pass)' },
  fail: { label: 'Fail', color: 'var(--fail)' },
}

/**
 * Published state-of-the-art baselines CULPRIT is benchmarked against.
 * - attribution: Who&When (Zhang et al., ICML 2025) best automated component attribution ~53.5%
 * - step localization: best automated decisive-step pinpointing ~14.2%
 */
export const SOTA_BASELINES: Record<
  'attribution_accuracy' | 'step_localization_accuracy',
  { value: number; label: string }
> = {
  attribution_accuracy: { value: 0.535, label: 'Who&When SOTA' },
  step_localization_accuracy: { value: 0.142, label: 'published SOTA' },
}

export function stepColor(type: StepType | string | null | undefined): string {
  if (type && type in STEP_TYPE_META) return STEP_TYPE_META[type as StepType].color
  return 'var(--muted-foreground)'
}

export function stepLabel(type: StepType | string | null | undefined): string {
  if (type && type in STEP_TYPE_META) return STEP_TYPE_META[type as StepType].label
  return '—'
}
