<div align="center">

# blackrim-personas

**Equip a principal-engineer persona for one task. Work at that level. Dematerialize.**

A dynamic persona system for agent fleets.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Site](https://img.shields.io/badge/site-live-brightgreen.svg)](https://jsgerman-oss.github.io/blackrim-personas/)
[![Gas City pack](https://img.shields.io/badge/gas%20city-pack-7c3aed.svg)](https://github.com/gastownhall/gascity-packs)
[![Python](https://img.shields.io/badge/python-stdlib%20only-3776ab.svg)](pack/)

</div>

---

A generalist agent is competent at everything and excellent at nothing. A persona makes an agent excellent at one thing for the duration of one task. When a polecat picks up a task it equips the best-fit principal-engineer persona, performs the work at that level, then releases it. Recently-used personas stay warm so the next agent reuses them, and they age out after a period of disuse.

It composes with the rest of the blackrim toolchain rather than competing with it: **model-advisor** picks the model tier, **provider-forge** picks the provider and model, and **blackrim-personas** picks the role. A dispatch is a tier, a provider/model, and a persona.

## Quickstart

```bash
# Install the pack into a gas city (also published in gascity-packs)
./pack/install.sh

# Equip the best-fit persona for a task; inspect the cache; lint the registry
personas match --from-bead <bead-id>
personas lint
```

## How it works

```
equip  →  materialize  →  execute  →  dematerialize  →  warm  →  age out
```

1. **Registry.** A library of persona definitions. Each persona is a role: its domain, the principal-engineer mindset and playbook, the conditions under which it should be equipped, the skills and tools it brings, and the verification bar it holds work to.
2. **Equip.** On task pickup, an agent matches the task to the best-fit persona (description match, the same way skills auto-fire) and equips it. The persona overlays the agent's role for that task only.
3. **Lifecycle.**
   - **materialize**: assemble the persona's full working context (playbook, domain knowledge, skills, worked examples) into a ready, equipped state. This is the cost the warm cache amortizes.
   - **execute**: the agent performs the task wearing the persona.
   - **dematerialize**: the persona is released when the task completes.
   - **warm**: the materialized persona lingers in a shared cache so the next agent reuses it without paying the materialize cost again.
   - **age out**: after a period of disuse the warm persona is evicted, then re-materialized on demand the next time it is needed.

## The persona roster

Each is an opinionated, production-grade principal-engineer specialist that holds its work to a real verification bar. The suite is extensible: adding a persona is adding a definition to the registry.

| Persona | Domain |
|---|---|
| `principal-backend-engineer` | services, data layers, APIs |
| `principal-frontend-engineer` | UI, client state, accessibility |
| `principal-systems-engineer` | distributed systems, concurrency, performance |
| `principal-security-engineer` | threat modeling, audits, hardening |
| `principal-data-engineer` | data and ML pipelines |
| `principal-platform-engineer` | infra, SRE, CI/CD |
| `principal-api-designer` | API surface, contracts, versioning |
| `principal-test-engineer` | test strategy, coverage |
| `principal-refactoring-engineer` | simplification, code health |
| `principal-docs-engineer` | technical writing |

## Warm cache and TTL

The warm cache earns its keep when tasks for the same persona cluster in time, the common case in a busy fleet.

- **Sliding idle TTL: 30 minutes**, refreshed on every reuse. Long enough to cover a clustered work session and its follow-ups; short enough to evict a persona no agent has wanted for half an hour.
- **Absolute ceiling: 2 hours.** Even a continuously-reused persona is force-refreshed so it picks up registry updates and the cache footprint stays bounded. Two hours aligns with the polecat idle timeout.
- **Both are configurable.** The defaults are a starting point, not a law.

After eviction a persona leaves the warm cache and is re-materialized from the registry only when needed again.

## The pack

Surfaced as a gas-city pack (mirroring the gascity-cockpit and nimbus conventions) so a city's agents get persona-equip for free:

- the persona **registry** (the definitions)
- the **equip / match** engine (selects the persona for a task)
- the **warm-cache and TTL lifecycle** (tracks materialized personas by last-used timestamp, evicts on the policy above)
- the **gas-town integration**: an equip-on-task-pickup hook, so a polecat selects and equips a persona as it claims work
- a **CLI** for inspecting the registry, the warm cache, and the equip decisions

Implementation in [`pack/`](pack/) (stdlib-only Python). Design notes: [`pack/docs/DESIGN.md`](pack/docs/DESIGN.md).

## Links

- Site: <https://jsgerman-oss.github.io/blackrim-personas/>
- Pack source: [`pack/`](pack/)
- Gas City registry: [gastownhall/gascity-packs](https://github.com/gastownhall/gascity-packs)

## License

MIT. Copyright (c) 2026 Blackrim.dev. See [LICENSE](LICENSE).
