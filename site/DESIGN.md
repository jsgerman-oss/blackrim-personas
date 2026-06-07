---
name: blackrim-personas
description: Marketing + docs site for blackrim-personas, the dynamic principal-engineer persona system and its gas-city pack. Inherits the blackrim "Working Lab Notebook" system and the same vapor-cyan token set as the nimbus site, carried over verbatim.
colors:
  vapor: "oklch(0.76 0.15 200)"
  vapor-lift: "oklch(0.83 0.13 200)"
  vapor-deep: "oklch(0.54 0.12 204)"
  bg-dark: "oklch(0.15 0.012 215)"
  surface-dark: "oklch(0.188 0.016 214)"
  lifted-dark: "oklch(0.236 0.02 213)"
  hairline-dark: "oklch(0.31 0.018 215)"
  hairline-strong-dark: "oklch(0.42 0.026 215)"
  ink-dark: "oklch(0.975 0.006 220)"
  mute-dark: "oklch(0.745 0.026 220)"
  caption-dark: "oklch(0.57 0.03 222)"
  bg-light: "oklch(0.976 0.005 95)"
  ink-light: "oklch(0.22 0.02 215)"
  accent-light: "oklch(0.55 0.15 206)"
  signal-amber: "oklch(0.82 0.14 76)"
  signal-red: "oklch(0.68 0.2 22)"
  signal-green: "oklch(0.88 0.18 158)"
typography:
  display:
    fontFamily: "'Inter Variable', Inter, sans-serif"
    fontSize: "clamp(2.75rem, 1.6rem + 5.4vw, 5.25rem)"
    fontWeight: 600
    letterSpacing: "-0.03em"
  headline:
    fontFamily: "'Inter Variable', Inter, sans-serif"
    fontSize: "clamp(2rem, 1.3rem + 3.2vw, 3.5rem)"
    fontWeight: 600
    letterSpacing: "-0.02em"
  mono:
    fontFamily: "'JetBrains Mono Variable', monospace"
    fontSize: "15px"
  label:
    fontFamily: "'JetBrains Mono Variable', monospace"
    fontSize: "13px"
    fontWeight: 500
    letterSpacing: "0.14em"
rounded:
  none: "0"
  code: "4px"
---

# Design System: blackrim-personas

The personas site inherits the **blackrim "Working Lab Notebook"** system wholesale:
operations-room calm, evidence-first, the surface is the proof. Read
`/Users/jayse/Code/blackrim/DESIGN.md` for the full rationale; everything there holds
unless overridden below.

## The token system, carried over verbatim

This site does not invent a palette. `src/styles/tokens.css` is copied verbatim from the
same-family `blackrim-nimbus-skills/site`, so the accent, the neutral ramp, the type scale,
and the easing curves are byte-identical. The accent is **vapor cyan**
(`oklch(0.76 0.15 200)`), the cloud-edge cyan that carries the single color of meaning:
links, the `/` eyebrow, the hero accent line, focus rings, the grid texture, the hero halo.
Keeping the family palette is deliberate: the personas surface should read as a sibling of
the nimbus surface, not a fork.

## Carried over unchanged

- **Inter + JetBrains Mono.** Sans for argument, mono for evidence. Mono is genuine here:
  persona ids, the equip transcript, and the CLI are real machine text, not costume.
- **Square corners.** Radius `0` everywhere; only `<pre>` and `<code>` get 4px.
- **Hairline-driven hierarchy.** 1px borders carry structure; flat by default; hover lifts
  via `translateY(-2px)`, never shadow.
- **The `/` eyebrow.** Mono uppercase, accent color, prefixed with a `/` glyph in
  caption-slate. It is a deliberate, named brand device, not a per-section reflex.
- **Two themes.** Dark primary, light full fidelity, the same accent role in both.

## Signature artifact: the equip terminal

Where the nimbus hero is a faux-but-real deploy terminal, the personas hero is a
faux-but-real **equip terminal** running the real flow: `personas match --from-bead`, then
`personas equip`, then `personas cache`. It shows the match score and the keywords that
fired, the materialize cost on a cold equip, the equipped status, and the warm cache with
each persona's idle TTL and use count. Real token coloring (accent for prompts and persona
ids, ink for command text, signal-green for the equipped status and the winning score,
signal-amber for the cold materialize cost, caption for dim output) and a blinking vapor
caret. It is the only element that gets the reserved halo. Nothing else on the page does.

## Signature component: the persona matrix

The ten-persona roster renders as a **connected hairline grid**, one cell per persona, with
the short domain label, the full `principal-...-engineer` id in mono, a one-line domain, and
a category tag. The default persona (backend) is the lit channel while the others sit
available-but-recessive until a task matches them. Hover lights one cell and dims the rest
(the instrument-panel hover, `:has()`), mirroring the blackrim crew-card behavior. Shared
1px hairlines, no per-cell outlines: the connected-panel feel.

## Motion

Staged hero reveal (eyebrow, headline lines, lede, equip terminal fading up), the terminal
lines settling in sequence, a blinking vapor caret, the warm-pulse on the status line.
Section reveals enhance already-visible content and have a `prefers-reduced-motion` fallback.
Easing is `ease-out-expo` and `ease-out-quart`; no bounce.

## Layout

Multi-page, prerendered static for GitHub Pages (Vite build): `/` (landing), `/roster` (the
persona matrix in full), `/pack` (the gas-city pack, the CLI, and install). Shared sticky nav
(translucent with a 12px backdrop blur, brand mark plus wordmark, mute-to-ink links with a
vapor active-underline, theme toggle plus a GitHub ghost button) and footer. Content shell
caps at 76rem; prose at 64ch, leads 52 to 64ch, headings 14 to 26ch.

## House style

No em-dashes anywhere, and no en-dashes used as punctuation; ranges read as "x to y". A
Vitest check enforces this across every shipped page, script, and stylesheet. The persona
lifecycle is the one place numbers lead a sequence (01 to 05), because it is a real ordered
flow; numbered markers are not used as section scaffolding elsewhere.
