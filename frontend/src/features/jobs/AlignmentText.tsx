type Props = {
  alignment: string
}

// An hmmscore hit's alignment as hmmsearch printed it: monospaced, its spaces and line breaks
// kept and no line wrapped, so the columns line up. A long line scrolls within this box, not the
// page. The box takes the focus, with a name, so a keyboard can scroll it in browsers that
// don't focus scrollers themselves, such as Safari (WCAG 2.1.1).
export function AlignmentText({ alignment }: Props) {
  return (
    <section className="flex flex-col gap-2">
      <h3 className="font-semibold">Alignment</h3>
      <div
        // A scrolling region, so it must be reachable by keyboard to be scrolled.
        // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- a scroll container must take the focus
        tabIndex={0}
        role="region"
        aria-label="Alignment"
        className="overflow-x-auto rounded-md border border-hairline bg-white p-3 focus-visible:outline-2"
      >
        <pre className="w-max font-mono text-sm whitespace-pre">{alignment}</pre>
      </div>
    </section>
  )
}
