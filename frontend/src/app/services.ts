// The four scoring services, in the project's priority order: the header's tabs, the home
// page's cards and the coming-soon pages all read this list. A service's name, page or
// mark changes here, and nowhere else.

export type ServiceId = 'csnp' | 'refmap' | 'hmmscore' | 'treegrafter'

export type Service = {
  id: ServiceId
  /** The tab's label: short, so four fit a phone's header. */
  label: string
  /** The heading on the home page's card and on the service's page. */
  title: string
  /** What the service does, in one or two sentences. */
  summary: string
  /** The service's page: its form, or its coming-soon page. */
  path: string
  /** The home page's link to the form; none while the service has no form. */
  action?: string
  /** The API can't score it yet. `refmap` has a form, but the API answers it with 501 (#40). */
  comingSoon: boolean
}

export const SERVICES: readonly Service[] = [
  {
    id: 'csnp',
    label: 'cSNP scoring',
    title: 'Coding SNP impact scoring',
    summary:
      'Estimates how long an amino-acid position has been preserved in evolution, to predict whether a substitution there is likely to be damaging.',
    path: '/csnp',
    action: 'Score coding SNPs',
    comingSoon: false,
  },
  {
    id: 'refmap',
    label: 'ID mapping',
    title: 'Protein ID mapping',
    summary:
      'Maps protein IDs, such as UniProt accessions, to their PANTHER families and subfamilies in one organism.',
    path: '/refmap',
    action: 'Map protein IDs',
    comingSoon: true,
  },
  {
    id: 'hmmscore',
    label: 'HMM scoring',
    title: 'HMM scoring',
    summary:
      'Scores protein sequences against the PANTHER HMM library, to find the family and subfamily each belongs to.',
    path: '/hmmscore',
    comingSoon: true,
  },
  {
    id: 'treegrafter',
    label: 'TreeGrafter',
    title: 'Tree grafting',
    summary:
      'Places a protein sequence in its PANTHER family tree, and infers its subfamily and GO annotations from where it lands.',
    path: '/treegrafter',
    comingSoon: true,
  },
]

export function service(id: ServiceId): Service {
  // Every id is in the list, so find always succeeds.
  return SERVICES.find(entry => entry.id === id)!
}
