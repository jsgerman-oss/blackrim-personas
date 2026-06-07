# blackrim-personas

A dynamic persona system for agent fleets. When a polecat picks up a task, it equips a principal-engineer persona matched to that task, performs the work at that level, then dematerializes. Recently-used personas stay warm so other agents can reuse them, and they age out of the system after a period of disuse.

> Status: v0 scaffold landed. The design lives here; the implementation lives in [`pack/`](pack/) — a stdlib-only gas-city pack with the registry, the equip/match engine, the warm-cache + TTL lifecycle, the equip-on-task-pickup hook, and a CLI. See [`pack/README.md`](pack/README.md) and [`pack/docs/DESIGN.md`](pack/docs/DESIGN.md).

## The idea

A generalist agent is competent at everything and excellent at nothing. A persona makes an agent excellent at one thing for the duration of one task. blackrim-personas is a curated suite of principal-engineer personas, each a highly effective specialist, that an agent equips dynamically based on the task in front of it. The agent becomes a principal backend engineer for a backend task, a principal security engineer for an audit, and so on, then releases the persona when the task is done.

This composes with the rest of the blackrim toolchain rather than competing with it. model-advisor picks the model tier, provider-forge picks the provider and model, and blackrim-personas picks the role. A dispatch is a tier, a provider/model, and a persona.

## How it works

1. **Registry.** A library of persona definitions. Each persona is a role: its domain, the principal-engineer mindset and playbook for that domain, the conditions under which it should be equipped, the skills and tools it brings, and the verification bar it holds work to.
2. **Equip.** On task pickup, an agent matches the task to the best-fit persona (description match, the same way skills auto-fire) and equips it. The persona overlays the agent's role for that task only.
3. **Lifecycle.** materialize, then execute, then dematerialize, then warm, then age out:
   - **materialize**: assemble the persona's full working context (playbook, domain knowledge, relevant skills, worked examples) into a ready, equipped state. This is the cost the warm cache amortizes.
   - **execute**: the agent performs the task wearing the persona.
   - **dematerialize**: the persona is released from the active agent when the task completes.
   - **warm**: the materialized persona lingers in a shared cache so the next agent that needs it reuses it without paying the materialize cost again. This is what "kept around for other agents to pick up" means.
   - **age out**: after a period of disuse the warm persona is evicted. It is re-materialized on demand the next time it is needed.

## Lifecycle TTL (the reasoning)

The warm cache earns its keep when tasks for the same persona cluster in time, which is the common case in a busy fleet. The aging policy:

- **Sliding idle TTL: 30 minutes.** A persona stays warm for 30 minutes since it was last equipped, refreshed on every reuse. Thirty minutes comfortably covers a clustered work session and follow-up tasks, and evicts a persona that no agent has wanted for half an hour. Shorter than this re-materializes too often for back-to-back work; longer lets unused personas accumulate.
- **Absolute ceiling: 2 hours.** Even a continuously-reused persona is force-refreshed after 2 hours so it picks up registry updates and the cache footprint stays bounded. Two hours aligns with the polecat idle timeout.
- **Both are configurable.** The defaults above are the starting point, not a law.

After eviction a persona ceases to exist in the warm cache and is re-materialized from the registry only when specifically needed again.

## The persona suite (initial roster)

Each is a principal-engineer specialist, opinionated and production-grade, that holds its work to a real verification bar:

- principal-backend-engineer
- principal-frontend-engineer
- principal-systems-engineer (distributed systems, concurrency, performance)
- principal-security-engineer
- principal-data-engineer (data and ML pipelines)
- principal-platform-engineer (infra, SRE, CI/CD)
- principal-api-designer
- principal-test-engineer (test strategy, coverage)
- principal-refactoring-engineer (simplification, code health)
- principal-docs-engineer (technical writing)

The suite is extensible; adding a persona is adding a definition to the registry.

## The pack

Surfaced as a gas-city pack (mirroring the gascity-cockpit and nimbus pack conventions) so a city's agents get persona-equip for free:

- the persona **registry** (the definitions)
- the **equip / match** engine (selects the persona for a task)
- the **warm-cache and TTL lifecycle** (tracks materialized personas with last-used timestamps and evicts on the policy above)
- the **gas-town integration**: an equip-on-task-pickup hook, so a polecat selects and equips a persona as it claims work
- a **CLI** for inspecting the registry, the warm cache, and the equip decisions

## License

MIT. Copyright (c) 2026 Blackrim.dev. See [LICENSE](LICENSE).
