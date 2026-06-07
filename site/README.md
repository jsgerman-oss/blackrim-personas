# blackrim-personas site

The marketing and docs site for `blackrim-personas`: the dynamic principal-engineer
persona system and its gas-city pack. Static, prerendered, multi-page.

Design system: `site/DESIGN.md` (the blackrim "Working Lab Notebook" system, Inter +
JetBrains Mono, square corners, an OKLCH vapor-cyan accent). The token system is carried
over verbatim from the same family site, `blackrim-nimbus-skills/site`, so the surfaces
stay visually consistent.

## Stack

- **Vite** (multi-page build, vanilla, no framework runtime)
- **Vitest** (copy and data-integrity tests)
- **@fontsource-variable** Inter + JetBrains Mono (self-hosted, no CDN)
- Hand-written CSS reasoned in OKLCH, two full-fidelity themes

No Tailwind, no router: three real HTML pages with relative inter-page links, so the
build is base-agnostic and works under any path.

## Pages

| Route | File | What it is |
|-------|------|------------|
| `/` | `index.html` | Landing, with the equip terminal and the lifecycle |
| `/roster` | `roster/index.html` | The matrix of all 10 principal-engineer personas |
| `/pack` | `pack/index.html` | The gas-city pack: what it provides, the CLI, install |

## Develop

```bash
cd site
npm install
npm run dev      # vite dev server
npm run build    # static build to dist/
npm run preview  # serve the built dist/
npm test         # vitest: house style + data integrity
```

## Deploy

GitHub Pages, via `.github/workflows/deploy-site.yml`. Set the Pages source to
"GitHub Actions" in the repository settings; the workflow builds `site/` and
publishes `site/dist/`.

The site uses relative links between pages, so only hashed asset URLs depend on the
base path. The workflow sets `SITE_BASE` to `/<repo>/` for a project page by default
(so `/blackrim-personas/`). For a custom domain, or an org root page, set a repository
variable `SITE_BASE` to `/`.

## Data integrity

The roster on `/roster` is described by `src/lib/personas-data.js`, and a test asserts
its persona ids stay in sync with the `[[persona]]` blocks in `pack/personas.toml` (the
registry). Edit the registry and the test tells you if the site drifted. A second test
forbids em-dashes and en-dashes across the shipped copy.
