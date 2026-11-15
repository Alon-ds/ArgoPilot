# P2 Registry database design

## Goal

Run the P1 Registry against a local SQLite file by default and against PostgreSQL when configured. Keep the existing FastAPI routes, response schemas, status codes, RFC 9457 problem responses, and Retry-After behavior. The P2 Planner can then consume the same Registry API in both environments.

## Approach

Proposed approach: SQLAlchemy Core. The service already uses explicit SQL, so Core table definitions and bound queries preserve that structure while helping the same queries run on both databases. SQLAlchemy ORM would add model objects and session state, which may help with richer object relationships. The current API reads and updates straightforward rows, so the proposal favors Core.

## Design

- Add one service configuration module using pydantic-settings. Read DATABASE_URL from the service's local .env or environment, give process variables precedence, and use the existing SQLite file path when the URL is absent. Document safe values in .env.example. Validate required settings at startup and isolate test configuration from the developer's .env.
- Define the existing tables, keys, uniqueness rules, and relationships in SQLAlchemy. Route farm, plot, and catalog queries through that layer. Retain SQLite foreign-key enforcement and verify that the existing local database remains readable.
- Keep write operations transactional. Preserve safeguards around concurrent plot creation and patching, including duplicate names and farm deletion with dependent plots. Use database constraints as the final guard and translate known conflicts into the existing API responses.
- Update database error handling to cover both drivers. Connectivity failures should produce the existing 503 problem response with Retry-After. Expected constraint violations should keep their documented status and code.
- Provide one documented PostgreSQL bootstrap command that creates the tables in an empty database and loads the 15 P1 seed rows required by FR-2.2. These rows are for the course setup.

## Acceptance checks

- Run Registry contract tests against isolated SQLite and PostgreSQL databases. Cover success, validation, missing records, conflicts, database unavailability, and partial updates.
- Verify that the documented bootstrap works against an empty PostgreSQL database and produces the expected 2 farms, 4 plots, 2 crops, 3 soils, and 4 emitters.
- Benchmark PostgreSQL list and item GET requests at 10 requests per second. Record environment, method, and measured p95 for each case. The target is at most 100 ms.

## Scope

This design covers the Registry in P2. Weather, Planner, and Frontend have their own implementation stages. Source: [P2 assignment](https://github.com/alonitac/OzVeruach26/blob/main/tasks/p2.md).
