/**
 * Whether the API is mocked by MSW in the browser instead of answered by the scoring service.
 * The one place the app asks: main.tsx starts MSW, and the shell shows the mock data banner,
 * only when it's true. `VITE_API_MOCKING` is set per mode in the `.env.*` files; in a build,
 * Vite replaces it with its value, so a build without mocking drops the code behind this.
 */
export function isApiMocked(): boolean {
  return import.meta.env.VITE_API_MOCKING === 'on'
}
