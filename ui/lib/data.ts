import rawData from '@/data/culprit-data.json'
import type { CulpritData, Run, StepType } from './types'
import { STEP_TYPES } from './constants'

/**
 * SINGLE SWAP POINT.
 * To use real data, replace `data/culprit-data.json` with a file of the same
 * shape — nothing else needs to change. Everything below derives from this.
 */
export const data = rawData as CulpritData

export function getData(): CulpritData {
  return data
}

export const runs: Run[] = data.runs

export function isFail(run: Run): boolean {
  return run.attribution.end_to_end_verdict === 'fail'
}

export function runLatency(run: Run): number {
  return run.total_ms
}

export interface Overview {
  totalRuns: number
  failures: number
  passes: number
  failureRate: number
  attributionAccuracy: number | null
  meanConfidence: number
  confidenceSeries: { run_id: string; index: number; confidence: number; verdict: string }[]
  lowestConfidence: { run_id: string; confidence: number; index: number } | null
  failuresByComponent: { component: StepType; count: number; label: string }[]
  topCategories: { category: string; count: number; component: StepType }[]
  passSeries: number[]
  failSeries: number[]
  confidenceTrend: number[]
  latencyTrend: number[]
}

export function computeOverview(): Overview {
  const totalRuns = runs.length
  const failingRuns = runs.filter(isFail)
  const failures = failingRuns.length
  const passes = totalRuns - failures

  const confidenceSeries = runs.map((r, i) => ({
    run_id: r.run_id,
    index: i + 1,
    confidence: Math.round(r.attribution.confidence * 100),
    verdict: r.attribution.end_to_end_verdict,
  }))

  const meanConfidence =
    totalRuns === 0
      ? 0
      : Math.round(
          (runs.reduce((s, r) => s + r.attribution.confidence, 0) / totalRuns) * 100,
        )

  let lowestConfidence: Overview['lowestConfidence'] = null
  confidenceSeries.forEach((c) => {
    if (!lowestConfidence || c.confidence < lowestConfidence.confidence) {
      lowestConfidence = { run_id: c.run_id, confidence: c.confidence, index: c.index }
    }
  })

  const compCounts = new Map<StepType, number>()
  STEP_TYPES.forEach((t) => compCounts.set(t, 0))
  failingRuns.forEach((r) => {
    const c = r.attribution.decisive_step_type
    if (c) compCounts.set(c, (compCounts.get(c) ?? 0) + 1)
  })
  const failuresByComponent = STEP_TYPES.map((t) => ({
    component: t,
    count: compCounts.get(t) ?? 0,
    label: t.replace('_', ' '),
  }))

  const catMap = new Map<string, { count: number; component: StepType }>()
  failingRuns.forEach((r) => {
    const cat = r.attribution.failure_category
    const comp = r.attribution.decisive_step_type
    if (cat && comp) {
      const existing = catMap.get(cat)
      catMap.set(cat, { count: (existing?.count ?? 0) + 1, component: comp })
    }
  })
  const topCategories = Array.from(catMap.entries())
    .map(([category, v]) => ({ category, count: v.count, component: v.component }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 3)

  // Cumulative mini-trends for KPI sparklines
  const passSeries: number[] = []
  const failSeries: number[] = []
  let pAcc = 0
  let fAcc = 0
  runs.forEach((r) => {
    if (isFail(r)) fAcc++
    else pAcc++
    passSeries.push(pAcc)
    failSeries.push(fAcc)
  })

  const confidenceTrend = confidenceSeries.map((c) => c.confidence)
  const latencyTrend = runs.map((r) => r.total_ms)

  return {
    totalRuns,
    failures,
    passes,
    failureRate: totalRuns === 0 ? 0 : Math.round((failures / totalRuns) * 100),
    attributionAccuracy: data.meta_eval ? data.meta_eval.attribution_accuracy : null,
    meanConfidence,
    confidenceSeries,
    lowestConfidence,
    failuresByComponent,
    topCategories,
    passSeries,
    failSeries,
    confidenceTrend,
    latencyTrend,
  }
}

export function formatCategory(cat: string): string {
  return cat
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}
