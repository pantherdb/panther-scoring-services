// The header with the application title. Shared by the layout and the root error page, so
// the title stays even when the layout itself fails to render.
export function AppHeader() {
  return (
    <header className="bg-primary-700 text-white">
      <div className="mx-auto w-full max-w-5xl px-4 py-4">
        <h1 className="text-xl font-semibold">PANTHER Scoring</h1>
      </div>
    </header>
  )
}
