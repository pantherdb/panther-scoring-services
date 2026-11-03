/**
 * The URL every API call starts with. The one place the app reads `VITE_API_BASE_URL`, the
 * scoring service's origin (and any path before `/api/v1`), set when the site is built.
 *
 * Unset or empty, the app calls `/api/v1` on its own origin: the Vite proxy in development,
 * preview and the e2e modes. Set, as the GitHub Pages build sets it, every call goes to
 * `<url>/api/v1`, on another origin. A trailing `/` is ignored.
 */
export function apiBaseUrl(): string {
  const origin = (import.meta.env.VITE_API_BASE_URL ?? '').trim().replace(/\/+$/, '')
  return `${origin}/api/v1`
}
