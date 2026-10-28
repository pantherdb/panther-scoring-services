/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** `on` starts the MSW worker before the app renders. Set per mode in the .env.* files. */
  readonly VITE_API_MOCKING?: 'on' | 'off'
}
