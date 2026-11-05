import type { JobService } from '@/app/api/wire'

// A job's input as the user typed it, kept in this tab's session storage so the job's page
// can offer "Edit and resubmit". The API never returns a job's input. Session storage
// survives a reload of the job's page, belongs to one tab, and is cleared when it closes.

/** The form's boxes, by name, as typed. */
export type KeptValues = Record<string, string>

type Entry = { service: JobService; values: KeptValues }

const PREFIX = 'panther-scoring:input:'
const ORDER_KEY = `${PREFIX}order`
/** The most jobs whose input is kept; the oldest is dropped first. */
export const MOST_KEPT = 20

function storage(): Storage | undefined {
  try {
    return window.sessionStorage
  } catch {
    // Some private modes throw on access.
    return undefined
  }
}

function readOrder(store: Storage): string[] {
  try {
    const order: unknown = JSON.parse(store.getItem(ORDER_KEY) ?? '[]')
    return Array.isArray(order) ? order.filter(id => typeof id === 'string') : []
  } catch {
    return []
  }
}

/**
 * Keeps a job's input. Best effort: a list too big for the storage, or storage that throws,
 * leaves nothing kept, and that job just doesn't offer "Edit and resubmit".
 */
export function keepInput(jobId: string, service: JobService, values: KeptValues) {
  const store = storage()
  if (!store) return
  try {
    const order = [...readOrder(store).filter(id => id !== jobId), jobId]
    const dropped = order.splice(0, Math.max(0, order.length - MOST_KEPT))
    for (const id of dropped) store.removeItem(PREFIX + id)
    store.setItem(PREFIX + jobId, JSON.stringify({ service, values } satisfies Entry))
    store.setItem(ORDER_KEY, JSON.stringify(order))
  } catch {
    try {
      store.removeItem(PREFIX + jobId)
    } catch {
      // Nothing more to undo: the storage refuses every call.
    }
  }
}

/** A job's kept input, if it was kept for that service; nothing for anything else. */
export function keptInput(jobId: string, service: JobService): KeptValues | undefined {
  try {
    const raw = storage()?.getItem(PREFIX + jobId)
    if (!raw) return undefined
    const entry: unknown = JSON.parse(raw)
    if (typeof entry !== 'object' || entry === null) return undefined
    if (!('service' in entry) || entry.service !== service) return undefined
    if (!('values' in entry) || typeof entry.values !== 'object' || entry.values === null) {
      return undefined
    }
    const values = Object.entries(entry.values as Record<string, unknown>)
    if (!values.every(([, value]) => typeof value === 'string')) return undefined
    return Object.fromEntries(values) as KeptValues
  } catch {
    return undefined
  }
}
