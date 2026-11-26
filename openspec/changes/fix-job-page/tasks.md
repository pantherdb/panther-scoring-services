# Tasks

## 1. Types and Conversion

- [ ] 1.1 `src/app/api/wire.ts`:
  - `WireJob` becomes `GET /api/v1/jobs/{job_id}`'s `200` body, and `JobRequest` `POST /api/v1/jobs`' request body, both from `paths` in `schema.d.ts` (design.md, decision 3);
  - `fromWireJob` returns `Job | null`: `null` for a service none of its cases knows, or a status missing from a `Record<JobStatus, true>` of known statuses (decision 1).

  Verify:
  - `npm run type-check` passes;
  - adding a stand-in service to the union locally makes `type-check` fail at `fromWireJob`, and so does a stand-in status at the `Record`. Not committed.
- [ ] 1.2 `src/mocks/jobs.ts` imports `WireJob` from `wire.ts` instead of its own union. Verify `npm run type-check` and `npm test -- --run` pass, and `npm run check:no-mocks` after `npm run build`.
- [ ] 1.3 `jobsApi.ts`:
  - `getJob` is `build.query<Job | null, string>`;
  - `startJob` is `build.mutation<string, JobRequest>`, returning the new job's `id` (decision 2).

  Verify `type-check`, with the four callers updated in 3.x.

## 2. The Job Page

- [ ] 2.1 `useJob.ts` stops polling when the cached job is `null`, as for a finished one. `JobPage.tsx` shows a new `JobCantBeShown` for `null`: fixed text saying the job may come from a newer version of the scoring service, and a button that reloads the page. `undefined` still shows "Loading the job…". Verify in `tests/features/jobs/JobPage.test.tsx`, each case beside a known job's:
  - a job with `service: "future"`: the page says it can't show the job, shows no status, result or "future", and the poll count stays at 1 after 2.5 s;
  - a `csnp` job with `status: "paused"`: the same.

  Spec: A job the page can't show.
- [ ] 2.2 `src/app/router.tsx`: `jobs/:id` renders a `JobRoute` that keys `JobPage` by the id (decision 4). `JobPage` takes `id` as a prop. Verify in `JobPage.test.tsx`, with the router `renderRoute` returns:
  - **The navigation:** from a succeeded `csnp` job at `/jobs/<a>`, `router.navigate('/jobs/<b>')`, with B's `refmap` answer held back.
  - **While B loads:** the page says the job is loading, and shows neither the `csnp` heading nor its score table.
  - **Once B is released:** the `refmap` job shows.
  - **Back at A:** returning to `/jobs/<a>` shows A again.

  Spec: Job page at its own URL, From one job's page to another's.

## 3. Opening a Started Job

- [ ] 3.1 `tests/utils/render.tsx`: `renderRoute` takes a `strict` option that wraps the app in `StrictMode`. Verify an existing `JobPage` test passes with `strict: true`.
- [ ] 3.2 A hook in `src/features/jobs/` that opens a started job only from where it was started (decision 5), exported from `features/jobs`. It covers:
  - the location key kept in a ref by an effect, and set to `null` in its cleanup;
  - the key read when the submit starts;
  - navigating to `/jobs/<id>` only if the ref still holds that key.

  Verify through 3.3 to 3.6.
- [ ] 3.3 `StartToolsCheck.tsx` uses the hook. Verify in `tests/features/jobs/StartToolsCheck.test.tsx`, under `strict: true`:
  - with the `POST` held back, clicking the cSNP tab, then releasing a `202`, stays at `/csnp`;
  - the existing start-a-check test still opens the job.

  Spec: Start a tools check from the home page, Leaving while the check starts.
- [ ] 3.4 `useSubmitCsnp.ts` uses the hook and `startJob`'s id. Verify in `tests/features/csnp/CsnpPage.test.tsx`, under `strict: true`:
  - submitting, going to `/refmap` before a held `202` is released, stays at `/refmap`;
  - the job's input is still kept;
  - the existing "opens its job" test passes.

  Spec: Leaving the cSNP form while the job starts.
- [ ] 3.5 `useSubmitRefmap.ts`, the same. Verify in `tests/features/refmap/RefmapPage.test.tsx`: going to `/` before the `202` stays at `/`. Spec: Leaving the refmap form while the job starts.
- [ ] 3.6 `useSubmitHmmscore.ts`, the same. Verify in `tests/features/hmmscore/HmmscorePage.test.tsx`: going to `/refmap` before the `202` stays at `/refmap`. Spec: Leaving the HMM scoring form while the job starts.

## 4. Docs and Final Check

- [ ] 4.1 `docs/manual-qa/02-csnp-form.md`, `03-refmap-form.md` and `04-hmmscore-form.md`: one test case each, numbered after the file's last. Submit, then click another tab before the job page opens; the page stays where the tester clicked. In the browser's network panel, throttle the connection to see it. Verify `npx markdownlint-cli2` passes.
- [ ] 4.2 `frontend/CLAUDE.md`: under State and Data, a line saying:
  - a job the app doesn't know is `null`, not loading;
  - the job page is keyed by the job id;
  - a started job opens through the hook, never through `navigate` directly.

  Verify `npx markdownlint-cli2` passes.
- [ ] 4.3 Final check:
  - **In `frontend/`:** `npm run api:types:check`, `format:check`, `lint`, `type-check`, `npm test -- --run` and `npm run test:e2e` pass.
  - **From the root:** `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass, and `npx openspec validate fix-job-page --strict` passes.

## Workflow follow-up

- **Review:** the frontend developer approves the code and the `scoring-ui` delta.
- **After the implementation merges,** archive with `/opsx:archive`. Before that, move into `frontend/CLAUDE.md` or `docs/` any lesson that applies beyond this change.
- **`add-treegrafter-job`:** its regenerated types will fail `type-check` until `fromWireJob` and the job page handle `treegrafter` (design.md, Risks).

## Notes

### Next action

Planning is done (2026-11-25). Next: review of the plan, then `/opsx:apply`, starting at 1.1.

### Blockers

None.

### Failed approaches

None yet.

### Lessons learned

None yet.
