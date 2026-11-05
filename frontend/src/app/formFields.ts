// Each form's boxes, by name. The form's draft uses them, and so does "Edit and resubmit"
// (features/jobs/keptInput.ts), which fills a form only from an input that has every box the
// form has now. A new box is added here.

export const CSNP_FIELDS = ['sequence', 'substitutions', 'species'] as const

export const REFMAP_FIELDS = ['ids', 'organism'] as const
