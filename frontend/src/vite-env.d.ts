/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** `on` starts the MSW worker before the app renders. Set per mode in the .env.* files. */
  readonly VITE_API_MOCKING?: 'on' | 'off'
  /** The API's URL, without `/api/v1`, for a site on another origin. Read in src/app/apiBaseUrl.ts. */
  readonly VITE_API_BASE_URL?: string
}
