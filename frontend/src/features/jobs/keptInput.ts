import { CSNP_FIELDS, REFMAP_FIELDS } from '@/app/formFields'
import type { JobService } from '@/app/api/wire'

// A job's input as the user typed it, kept in this tab's session storage so the job's page
// can offer "Edit and resubmit". The API never returns a job's input. Session storage
// survives a reload of the job's page and is cleared when the tab closes. It isn't strictly
// the tab's alone: "Duplicate tab" copies it, and a browser's session restore may write it to
// disk. That's acceptable for a convenience: nothing here is sent anywhere.

/** Each form's boxes. A kept input is used only when it has every one. */
export const KEPT_FIELDS = { csnp: CSNP_FIELDS, refmap: REFMAP_FIELDS } as const

/** A service whose form "Edit and resubmit" can fill. */
export type EditableService = keyof typeof KEPT_FIELDS

/** A service's boxes, by name, as typed. */
export type KeptValues<S extends EditableService> = Record<(typeof KEPT_FIELDS)[S][number], string>

const PREFIX = 'panther-scoring:input:'
const ORDER_KEY = `${PREFIX}order`
/** The most jobs whose input is kept; the oldest is dropped first. */
export const MOST_KEPT = 20
/**
 * The longest input kept, in characters. A longer one, such as a list of 100,000 IDs, isn't
 * kept: writing it would hold up the page right after submitting, and crowd out the rest.
 */
export const MOST_KEPT_CHARS = 1_000_000

export function isEditable(service: JobService): service is EditableService {
  return service in KEPT_FIELDS
}

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
 * Keeps a job's input. Best effort: when the storage is full, the oldest inputs are dropped
 * until this one fits. One too big for the storage on its own, or over MOST_KEPT_CHARS, or
 * storage that throws, leaves it unkept, and that job just doesn't offer "Edit and resubmit".
 */
export function keepInput<S extends EditableService>(
  jobId: string,
  service: S,
  values: KeptValues<S>
) {
  const texts: string[] = Object.values(values)
  if (texts.reduce((length, text) => length + text.length, 0) > MOST_KEPT_CHARS) return
  const store = storage()
  if (!store) return
  try {
    const order = readOrder(store).filter(id => id !== jobId)
    while (order.length >= MOST_KEPT) store.removeItem(PREFIX + order.shift())
    const entry = JSON.stringify({ service, values })
    for (;;) {
      try {
        store.setItem(PREFIX + jobId, entry)
        break
      } catch (error) {
        // Full: make room by dropping the oldest, and try again.
        const oldest = order.shift()
        if (oldest === undefined) throw error
        store.removeItem(PREFIX + oldest)
      }
    }
    store.setItem(ORDER_KEY, JSON.stringify([...order, jobId]))
  } catch {
    try {
      // Whatever was dropped, the order names only what's still kept.
      store.removeItem(PREFIX + jobId)
      store.setItem(
        ORDER_KEY,
        JSON.stringify(readOrder(store).filter(id => store.getItem(PREFIX + id) !== null))
      )
    } catch {
      // Nothing more to undo: the storage refuses every call.
    }
  }
}

/**
 * A job's kept input for that service's form, if it has every box the form has now; nothing
 * for another service, or for an input kept before a box was added.
 */
export function keptInput<S extends EditableService>(
  jobId: string,
  service: S
): KeptValues<S> | undefined {
  try {
    const raw = storage()?.getItem(PREFIX + jobId)
    if (!raw) return undefined
    const entry: unknown = JSON.parse(raw)
    if (typeof entry !== 'object' || entry === null) return undefined
    if (!('service' in entry) || entry.service !== service) return undefined
    if (!('values' in entry) || typeof entry.values !== 'object' || entry.values === null) {
      return undefined
    }
    const values = entry.values as Record<string, unknown>
    const picked: Record<string, string> = {}
    for (const field of KEPT_FIELDS[service]) {
      const value = values[field]
      if (typeof value !== 'string') return undefined
      picked[field] = value
    }
    return picked as KeptValues<S>
  } catch {
    return undefined
  }
}
