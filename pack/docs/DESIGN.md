# personas — design

This is the v0 scaffold of the dynamic persona system described in the repository
[`README.md`](../../README.md). It implements the five deliverables that README calls
for — a persona **registry**, an **equip/match** engine, a **warm-cache + TTL**
lifecycle, a gas-town **equip-on-task-pickup hook**, and the **pack skeleton** — as a
pure-stdlib gas-city pack mirroring the `gascity-cockpit` / `model-advisor` conventions.

It composes with the rest of the blackrim toolchain rather than competing with it:
`model-advisor` picks the model **tier**, `provider-forge` picks the **provider/model**,
and `personas` picks the **role**. A dispatch is a tier, a provider/model, and a persona.

## 1. Registry (`personas.toml` + `personas/registry.py`)

The registry is the library of persona *definitions*. It is config-driven: nothing in
the decision path is hard-coded. Each `[[persona]]` is a role with:

| field | meaning |
|-------|---------|
| `id` | stable kebab-case identifier (`principal-backend-engineer`) |
| `domain` | one line: the territory the persona owns |
| `when_to_equip` | the conditions under which an agent should equip it |
| `match_keywords` | curated terms the equip engine scores a task against (lowercased on load) |
| `skills` / `tools` | the gas-city skills and tools the persona brings |
| `verification_bar` | the standard it holds its own work to before handing off |
| `playbook` | the principal-engineer mindset + method for the domain |
| `weight` | optional priority, used only as a deterministic tie-break |

The shipped roster is the README's initial suite of ten principal-engineer specialists
(backend, frontend, systems, security, data, platform, api-design, test, refactoring,
docs). The suite is extensible — adding a persona is adding a `[[persona]]` block.

`[cache]` carries the warm-cache TTL policy (see §3). A small built-in fallback roster
(`registry.DEFAULT_PERSONAS`) keeps the engine working if `personas.toml` is deleted,
exactly as `model-advisor` falls back to a built-in tier roster.

## 2. Equip / match (`personas/match.py`)

The README's equip step: "an agent matches the task to the best-fit persona (description
match, the same way skills auto-fire)." The match rule is deliberately transparent and
deterministic — no model call, no network — so every decision is explainable.

Scoring channels:

1. **Curated keywords (primary).** Each persona's `match_keywords` are matched against
   the task as whole-word phrases. A multi-word keyword (`"threat model"`) is a stronger
   signal than a single word, so it scores higher (`2.0` vs `1.0`).
2. **Domain vocabulary (secondary).** Salient (non-stopword) words from `domain` and
   `when_to_equip` that also appear in the task add a small bonus (`0.25`), so a task that
   uses a persona's vocabulary without hitting an explicit keyword still matches.

Both channels are **plural/singular aware** via a naive singularizer (`tests` → `test`,
`queries` → `query`), with conservative length guards and a `ss` exclusion so `class` /
`loss` survive. Near-duplicate keywords that singularize to the same phrase are counted
once, so `"test"` + `"tests"` is one hit, not two.

`MatchResult` carries the chosen persona, its score, the exact terms that fired, and the
ranked runners-up, so `personas match` shows *why*. Ties break by `score`, then
`weight`, then `id` — fully deterministic, never order-dependent. With no signal at all
the engine returns the registry's default (generalist) persona, flagged
`is_fallback=True`, so the caller always gets a usable answer.

## 3. Warm cache + TTL (`personas/cache.py`)

The README lifecycle is materialize → execute → dematerialize → **warm** → **age out**.
This module owns *warm* and *age out*: a JSON-backed cache of materialized personas with
last-used timestamps, shared so the next agent reuses a warm persona without paying the
materialize cost again.

### The aging policy and its reasoning (README "Lifecycle TTL")

- **Sliding idle TTL — 30 minutes (default).** A persona stays warm for 30 minutes since
  it was last equipped, refreshed on every reuse. Thirty minutes comfortably covers a
  clustered work session and its follow-ups, and evicts a persona no agent has wanted for
  half an hour. Shorter re-materializes too often for back-to-back work; longer lets
  unused personas accumulate.
- **Absolute ceiling — 2 hours (default).** Even a continuously-reused persona is
  force-refreshed after 2 hours so it picks up registry updates and the cache footprint
  stays bounded. Two hours aligns with the polecat idle timeout.
- **Both are configurable** via `[cache]` (`idle_ttl_minutes` / `ceiling_ttl_hours`, or
  explicit `*_seconds` overrides). The defaults are the starting point, not a law.

`equip(persona_id, now)` is the write path: it sweeps expired entries first (lazy
eviction), then either *touches* a still-warm persona (slide `last_used_at`, bump
`use_count`, `was_warm=True`) or materializes a fresh one. A ceiling-expired persona is
swept and re-materialized with a new `materialized_at`, so it genuinely re-reads the
registry. `now` is injected into every time-dependent method, so the policy is
deterministically testable (the suite drives the full idle/ceiling state machine with
fixed clocks).

### Concurrency and location

Writes are atomic (temp file + `os.replace` + `fsync`) so a concurrent reader never sees
a half-written cache; a corrupt or missing file is treated as empty and self-heals on the
next write. Concurrent *writers* are last-writer-wins — acceptable because every entry is
re-derivable from the registry; the cache is an optimization, not a source of truth.

The cache path resolves (first hit wins): `PERSONAS_CACHE_FILE` → `PERSONAS_CACHE_DIR` →
`$GC_RIG_ROOT/.beads/personas/` → the nearest ancestor `.beads/personas/` → `~/.gc/runtime/personas/`.
A location under a rig's `.beads` is shared by all of that rig's agents, which is what
makes "kept around for other agents to pick up" real.

## 4. Equip-on-task-pickup hook (`hooks/` + `overlay/`)

The gas-town integration. `hooks/equip-on-task-pickup.sh` is a Claude Code
**SessionStart** hook: for a gas-town worker, session start *is* task pickup — the
polecat is spawned with work already on its hook. The hook resolves the agent's current
in-progress work bead (by session name / id / alias), runs
`personas equip --from-bead <id> --emit-context`, and emits the engine's
`hookSpecificOutput.additionalContext` so the persona's playbook + verification bar
overlay the session. It is strictly best-effort and always exits 0 — equip must never
block or fail a session start. `PERSONAS_DISABLE_EQUIP=1` makes it a no-op.

`overlay/per-provider/claude/.claude/settings.json` wires the hook into projected agent
settings; `gc reload` deep-merges it (the same mechanism `model-advisor` uses for its
`Stop`/`SubagentStop` telemetry hook). The hook command walks up from
`$CLAUDE_PROJECT_DIR` to find `packs/personas/hooks/equip-on-task-pickup.sh`, so it works
from any agent worktree.

> **Scope note.** SessionStart is the equip seam this scaffold ships because it is the
> reliable "pickup" moment for a worker that is born with its task. A mid-session pickup
> (an agent that claims a *second* bead via `gc bd update --claim` without restarting)
> would want a `PostToolUse` hook keyed on the claim command; that is a deliberate
> follow-up, not built here.

## 5. Pack skeleton

Standard gas-city pack layout (mirrors `gascity-cockpit/pack` + `model-advisor`):
`pack.toml`, `bin/personas` (venv-or-system-python3 wrapper), the `personas/` engine,
`personas.toml`, `skills/equip-persona/`, `template-fragments/use-personas.template.md`,
the overlay + hook, `setup.sh` / `install.sh` / `uninstall.sh` (idempotent, backed-up,
`--dry-run`), `requirements.txt`, `tests/`, and this doc. Stdlib-only; no runtime
third-party deps.

## Open scope (not built in v0)

- **Mid-session re-equip** on a `--claim` `PostToolUse` hook (see the scope note in §4).
- **Richer match** (embedding/semantic similarity) if curated-keyword + domain-vocab
  matching proves too blunt. The current rule is intentionally simple and auditable.
- **Cross-rig shared cache** beyond a single rig's `.beads`. The path resolver already
  supports an explicit `PERSONAS_CACHE_DIR` for that.
- **Per-persona metrics** (equip counts, reuse-hit rate) for tuning the roster and TTLs.
