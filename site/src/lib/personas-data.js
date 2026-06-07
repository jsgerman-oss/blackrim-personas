/**
 * The 10 principal-engineer personas of the blackrim-personas registry.
 *
 * `id` matches a [[persona]] block in pack/personas.toml (a test asserts the set
 * stays in sync with the registry). `path: 'default'` marks the generalist
 * fallback persona, lit by default in the roster matrix while the others sit
 * available-but-recessive until a task matches them.
 *
 * House style: no em-dashes anywhere in copy (a test enforces this).
 */
export const personas = [
  {
    id: 'principal-backend-engineer',
    label: 'Backend',
    best: 'Server-side services, APIs, data access, and the contracts behind them.',
    tag: 'Server',
    skills: ['tdd', 'diagnose', 'code-review'],
    path: 'default'
  },
  {
    id: 'principal-frontend-engineer',
    label: 'Frontend',
    best: 'User interfaces, client state, accessibility, and perceived performance.',
    tag: 'Client',
    skills: ['impeccable', 'verify', 'code-review']
  },
  {
    id: 'principal-systems-engineer',
    label: 'Systems',
    best: 'Distributed systems, concurrency, and performance under load.',
    tag: 'Concurrency',
    skills: ['diagnose', 'tdd', 'code-review']
  },
  {
    id: 'principal-security-engineer',
    label: 'Security',
    best: 'Threat modeling, untrusted input, secure defaults, and authorization.',
    tag: 'Security',
    skills: ['security-review', 'diagnose', 'code-review']
  },
  {
    id: 'principal-data-engineer',
    label: 'Data',
    best: 'Data and ML pipelines, schemas, and analytical correctness.',
    tag: 'Data',
    skills: ['diagnose', 'tdd']
  },
  {
    id: 'principal-platform-engineer',
    label: 'Platform',
    best: 'Infrastructure, CI/CD, observability, and operational reliability.',
    tag: 'Platform',
    skills: ['diagnose', 'verify']
  },
  {
    id: 'principal-api-designer',
    label: 'API design',
    best: 'API contracts, versioning, and developer experience.',
    tag: 'Interfaces',
    skills: ['code-review', 'to-prd']
  },
  {
    id: 'principal-test-engineer',
    label: 'Test',
    best: 'Test strategy, coverage, and fast deterministic suites.',
    tag: 'Quality',
    skills: ['tdd', 'verify', 'diagnose']
  },
  {
    id: 'principal-refactoring-engineer',
    label: 'Refactoring',
    best: 'Simplification and code health, with behavior held constant.',
    tag: 'Code health',
    skills: ['simplify', 'improve-codebase-architecture', 'code-review', 'tdd']
  },
  {
    id: 'principal-docs-engineer',
    label: 'Docs',
    best: 'Technical writing, READMEs, and developer-facing explanation.',
    tag: 'Writing',
    skills: ['init', 'to-prd']
  }
];

/** The generalist fallback, equipped when a task matches nothing. */
export const defaultPersona = 'principal-backend-engineer';

/**
 * The lifecycle a persona moves through: materialize, execute, dematerialize,
 * warm, age out. The warm cache amortizes the materialize cost across the agents
 * that reuse a persona before it ages out.
 */
export const lifecycle = [
  {
    step: '01',
    name: 'materialize',
    note: 'Assemble the persona: playbook, domain knowledge, skills, and worked examples into one equipped overlay. This is the cost the warm cache amortizes.'
  },
  {
    step: '02',
    name: 'execute',
    note: 'The agent performs the task wearing the persona, holding its work to that persona verification bar.'
  },
  {
    step: '03',
    name: 'dematerialize',
    note: 'The persona is released from the active agent the moment the task completes. The agent goes back to being a generalist.'
  },
  {
    step: '04',
    name: 'warm',
    note: 'The materialized persona lingers in a shared cache so the next agent that needs it reuses it without paying the materialize cost again.'
  },
  {
    step: '05',
    name: 'age out',
    note: 'After a sliding 30 minute idle window (2 hour ceiling) the warm persona is evicted, then re-materialized on demand the next time it is needed.'
  }
];

/**
 * personas is one of three composable dimensions of a dispatch. model-advisor
 * picks the tier, provider-forge picks the provider and model, and personas
 * picks the role. A dispatch is a tier, a provider/model, and a persona.
 */
export const composition = [
  {
    id: 'model-advisor',
    dimension: 'Tier',
    note: 'Picks the cheapest model tier that credibly preserves quality for the task shape.'
  },
  {
    id: 'provider-forge',
    dimension: 'Provider / model',
    note: 'Picks the concrete provider and model the work runs on.'
  },
  {
    id: 'personas',
    dimension: 'Role',
    note: 'Picks the principal-engineer persona the agent equips for the task.'
  }
];
