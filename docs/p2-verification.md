# P2 verification evidence

Implementation merged in [PR #8](https://github.com/Alon-ds/ArgoPilot/pull/8),
commit `f71f792f11b3480a26a248e95bde5c38dd1dcaae`.

## Verified checks

| Check | Observed result |
| --- | --- |
| Registry | 17 tests passed; 100% line and branch coverage, Python 3.12 and 3.13 |
| PostgreSQL | Seeded 15 rows; live API read and transaction contract passed |
| Weather | 59 tests passed; real Open-Meteo integration checked |
| Planner | 67 tests passed |
| Frontend | Lint and production build passed; 13 Playwright tests passed |
| Mobile | 375px viewport test checked advice above fold and no horizontal overflow |
| Dependencies | uv audits for all Python services and npm audit passed |

GitHub PR runs both completed successfully:

- [Registry tests](https://github.com/Alon-ds/ArgoPilot/actions/runs/44814428056)
- [P2 services](https://github.com/Alon-ds/ArgoPilot/actions/runs/44814428045)

## Performance

PostgreSQL registry: 300 requests over 30 seconds at 10 total requests/second,
round-robin across ten read routes. Zero errors; highest route p95 23.332 ms.
Raw measurements: [benchmark JSON](p2-postgresql-benchmark.json).
Access logging was disabled to avoid blocked console output affecting the test.
This is 10 total rps, not 10 rps per endpoint.

Weather warm-cache benchmark reported p95 7.555 ms at 10 rps with no provider
calls during measurement. Real-provider-backed cache reported 6.385 ms.
These weather figures are session observations; the committed benchmark script
can reproduce the test, but no raw weather measurement artifact was committed.

## Limits and interpretation

The planner assumes a full soil bucket at the beginning of each request. It
does not measure soil moisture or persist irrigation history. See the reference
skill and research for selected crop parameters and the simplified half-full rule.

Green CI does not establish that branch protection is enforced. The earlier
private-repository plan warning remains a separate GitHub administration issue;
required checks and effective enforcement have not been independently verified.
Passing audits concern known vulnerabilities at scan time only.

For the Hebrew explanation and demonstration order, read
[the walkthrough](p2-walkthrough-he.md).
