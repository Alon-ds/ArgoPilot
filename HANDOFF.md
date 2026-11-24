# ArgoPilot — Conversation Handoff

Short brief to resume work in a new Claude Code conversation. Read this first; the detail is in the repo and in the memory directory at `~/.claude/projects/-Users-alon-ArgoPilot/memory/`.

## The project in one line

Four-service irrigation planner: `Registry` (18000) + `Weather` (18001) → `Planner` (18002) → `Frontend` (3000). Run with `./dev.sh`.

## Course the user is working through

`https://github.com/alonitac/OzVeruach26` — tutorials, in this order:

Done:
- #12 Coding Agents (`intro_to_coding_assistant.md`)
- #13 Writing Skills (`writing_skills.md`)
- #14 Intro to UI (`intro_to_ui.md`)

Next up:
- **#15 Intro to Git (`git_intro.md`) ← start here**
- #16 CI with GitHub Actions (`github_actions_intro.md`)
- #17 AWS Introduction — **deferred by user, do not start**
- #18 CD with GitHub Actions (`github_actions_cd.md`)

Also present in the repo but not on the user's ordered list: `aws_intro`, `bash_*`, `git_intro`, `http_and_api`, `io_redirection`, `linux_*`, `onboarding-*`, `python_env`.

## Standing rules (from the user, and from repo files)

1. **Reply in Hebrew to this user.** Wrap code-like English in backticks (` `` `). Translate common concepts to Hebrew (`trade-offs` → "פשרות", `bottleneck` → "צוואר בקבוק"). Keep well-known product names unquoted (React, Next.js, Postgres). The goal is RTL readability — bare English inside Hebrew flips direction and punctuation.
2. **Never read, print, copy, or commit real `.env` / `.env.local` files.** Use only `.env.example`.
3. **Don't touch AWS yet.** User deferred it explicitly.
4. **`.claude/skills/` is authoritative** for Claude Code skills; `.agents/skills/` is for Codex. Don't duplicate across both.
5. **Explain step by step** when teaching a tutorial, anchor explanations to real files in the project.

## State of key things

- **`registry-api` skill** at `.claude/skills/registry-api/` — complete through writing_skills TDD cycle. Trigger evals pass 4/4 after fixing a detection bug in `.claude/skills/skill-creator/scripts/run_eval.py` (now matches the real skill name, not just the temporary command-file alias).
- **`dev.sh`** at repo root starts all four services on ports 18000/18001/18002/3000 with health checks; `./dev.sh stop` kills them.
- **Project skills still only in `.agents/skills/`** (not yet migrated to `.claude/skills/`): `frontend-design`, `irrigation-calc-reference`, `planner-api`, `research`.
- **Current branch:** `fix/ci-workflow`. Recent commits include `bdf3916` (writing_skills TDD cycle), `63d4727` (initial registry-api skill), `d448657` (planner-api skill + rules), `95ea1fc` (dev.sh).
- **Pending work:** five branches on GitHub without PRs; tag `v1.1.0` after merging `feat/farm-summary`.
- **`.claude/rules/`** has three rule files that agents automatically follow: `registry-tests.md` (100% coverage), `frontend.md` (Next.js server components first, Zod validation), `env-files.md` (never read real env files).

## Superpowers / skill-creator

- `superpowers@superpowers-marketplace` installed at user scope (duplicate `@claude-plugins-official` entry was cleared).
- `skill-creator` installed at `.claude/skills/skill-creator/`, tracked via `skills-lock.json`.

## How to resume

Open a new conversation and say:
> המשך לפי `HANDOFF.md` ו-`~/.claude/projects/-Users-alon-ArgoPilot/memory/`. הנושא הבא ברשימה הוא `#15 Intro to Git`.

The new agent should read this file plus `MEMORY.md` + the feedback memory about Hebrew/English mixing before answering.
