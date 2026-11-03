import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'

import { apiBaseUrl } from '@/app/apiBaseUrl'

// One API for the whole app. Features add their endpoints with
// api.injectEndpoints in their own folder. The base URL is relative, served by
// the Vite proxy, unless the build sets the API's URL (src/app/apiBaseUrl.ts).
export const api = createApi({
  reducerPath: 'api',
  baseQuery: fetchBaseQuery({ baseUrl: apiBaseUrl() }),
  endpoints: () => ({}),
})
