# P2 implementation plan

1. Compare both upstream assignment documents with tracked files; record gaps.
2. Fix coverage gate placement and prove the configured gate without CLI override.
3. Migrate registry connections and seed command to SQLAlchemy and settings.
4. Implement weather provider adapter, strict validation, cache and recovery tests.
5. Implement deterministic planner, HTTP adapters, domain reference and tests.
6. Build server-rendered Next.js home/plot pages and visible failure states.
7. Configure safe examples, ignore secrets/build output, and add CI for services.
8. Run unit/integration tests, audits, build/lint, actual PostgreSQL and NFR checks.
9. Review diff, commit and push p2; open PR and inspect actual checks if authorized
   repository API access is available. Preserve protection; never bypass it.
10. Write Hebrew walkthrough with actual evidence and distinguish pending checks.
