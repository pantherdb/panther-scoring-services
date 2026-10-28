import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'

// One API for the whole app. Features add their endpoints with
// api.injectEndpoints in their own folder. The relative base URL is served by
// the Vite proxy in development and by the same origin when deployed.
export const api = createApi({
  reducerPath: 'api',
  baseQuery: fetchBaseQuery({ baseUrl: '/api/v1' }),
  endpoints: () => ({}),
})
