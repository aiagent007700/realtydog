# SESSION_PROTOCOL.md — RealtyDog

Rules for every session that touches this repo. They exist because session summaries
turn *intent* into *completion* — the code and these tracking files are the truth.

## At session start

1. Read **`README.md`** (the spec), **`STUBS.md`** (backlog), **`WIRING_STATUS.md`**
   (what's wired), **`app/main.py`** (what starts).
2. The sanity check (`.claude/hooks/session_start.sh`) runs automatically in bash/cloud
   sessions. Run it manually otherwise: `bash .claude/hooks/session_start.sh`.

## While working

- **"Done" = the wire is traced.** `Trigger → Handler → data/enrichment → DB → side effect`,
  unbroken and recorded in `WIRING_STATUS.md`. Never mark done from memory.
- **Every stub / TODO / disconnected wire → `STUBS.md` in the same change**, with the
  *reasoning* (why, what it builds on, what gate it clears) — not just a description.
- **Schema change** → update the migration AND any ORM/dataclass together; keep consistent.
- **Missing data ≠ a green light** — fail closed on buy-box / financial gates; fail open
  on discovery-only reads.
- **Only legal public data** — CAD, tax-sale lists, courthouse, ProPublica 990, Craigslist
  RSS, human `/tip`. Never scrape MLS / LoopNet / Crexi / Zillow / Facebook.

## At session end

- Update `STUBS.md` (items closed/added) and `WIRING_STATUS.md` (newly wired chains).
- Commit as **`aiagent007700 <aiagent007700@gmail.com>`**; push with the Bash sandbox
  disabled (network). **Keep the repo PRIVATE.**
