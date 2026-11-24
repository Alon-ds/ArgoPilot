---
globs: "**/.env*"
---

**Never read, print, copy, or commit real `.env` or `.env.local` files.**

- Use only the committed `.env.example` files to understand configuration.
- If configuration is needed for a new service, add a variable to `.env.example` with a safe default or placeholder, never a real secret.
- Real credentials, API keys, database passwords, and SSH keys must never appear in source code, tests, logs, or documentation.
