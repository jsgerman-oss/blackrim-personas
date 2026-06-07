"""personas CLI — inspect the roster, see equip decisions, and drive the warm cache.

    personas list                       the roster (id, domain, when to equip)
    personas show <id>                  one persona's full definition + playbook
    personas match <task...>            the equip decision for a task (read-only)
    personas equip <task...>            match + materialize into the warm cache
        [--from-bead ID] [--emit-context]
    personas cache                      the warm cache: what's materialized + TTL
    personas sweep [--all]              evict expired (or all) warm personas

``list`` / ``show`` / ``match`` / ``cache`` are pure reads (``cache`` lazily prunes
expired entries — a no-op on a fresh cache). ``equip`` and ``sweep`` mutate the warm
cache. ``equip --emit-context`` prints a Claude Code SessionStart hook payload so the
equip-on-task-pickup hook can overlay the persona onto the agent.

Exit codes: 0 ok; 2 a usage / resolution error (unknown persona id, ``--from-bead``
could not resolve a task). Pure stdlib; invoked as ``python -m personas.cli`` by the
``bin/personas`` wrapper.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from typing import Any, Optional, Sequence

from personas import cache as C
from personas import match as M
from personas import registry as R

#: The roster shipped with the pack (pack root / personas.toml), used unless --registry.
_DEFAULT_REGISTRY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "personas.toml"
)


def _load(args: argparse.Namespace) -> R.PersonasConfig:
    try:
        return R.load_config(args.registry)
    except R.RegistryError as e:
        sys.stderr.write(f"personas: invalid registry: {e}\n")
        raise SystemExit(2)


def _cache(args: argparse.Namespace, config: R.PersonasConfig) -> C.WarmCache:
    path = args.cache_file or C.default_cache_path()
    return C.WarmCache(path, config.cache)


# --------------------------------------------------------------------------- #
# Serialization / rendering helpers                                             #
# --------------------------------------------------------------------------- #


def _persona_dict(p: R.Persona) -> dict[str, Any]:
    return {
        "id": p.id,
        "title": p.title,
        "domain": p.domain,
        "when_to_equip": p.when_to_equip,
        "match_keywords": list(p.match_keywords),
        "skills": list(p.skills),
        "tools": list(p.tools),
        "verification_bar": p.verification_bar,
        "weight": p.weight,
        "playbook": p.playbook,
    }


def _compose_context(persona_overlay: str, result: M.MatchResult) -> str:
    """Compose the equip overlay shown/emitted for a task: provenance note + the overlay.

    ``persona_overlay`` is the materialized, task-independent context the warm cache
    serves (``EquipOutcome.overlay``); :func:`personas.match.render_provenance` adds the
    cheap, per-task "why this persona" note on top. Composing here (rather than baking
    provenance into the cached overlay) is what lets the cache reuse one overlay across
    different tasks — the amortization the warm cache exists for.
    """
    provenance = M.render_provenance(result)
    return f"{provenance}\n\n{persona_overlay}" if provenance else persona_overlay


def _fmt_secs(s: float) -> str:
    """Compact human duration for TTL remaining (e.g. ``28m12s``, ``-3m`` if expired)."""
    sign = "-" if s < 0 else ""
    s = abs(int(s))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{sign}{h}h{m:02d}m"
    if m:
        return f"{sign}{m}m{sec:02d}s"
    return f"{sign}{sec}s"


# --------------------------------------------------------------------------- #
# bead resolution (for `equip --from-bead`)                                     #
# --------------------------------------------------------------------------- #


def _task_from_bead(bead_id: str) -> str:
    """Resolve a task description (title + description) from a bead via ``bd show``.

    Best-effort and isolated here so the engine stays subprocess-free and tests can
    monkeypatch it. Raises ``ValueError`` with a clear message on any failure.
    """
    try:
        proc = subprocess.run(
            ["bd", "show", bead_id, "--json"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as e:
        raise ValueError(f"could not run 'bd show {bead_id}': {e}")
    if proc.returncode != 0:
        raise ValueError(
            f"'bd show {bead_id}' failed ({proc.returncode}): {proc.stderr.strip()}"
        )
    try:
        data = json.loads(proc.stdout)
    except ValueError as e:
        raise ValueError(f"'bd show {bead_id}' did not return JSON: {e}")
    rec = data[0] if isinstance(data, list) and data else data
    if not isinstance(rec, dict):
        raise ValueError(f"unexpected 'bd show {bead_id}' shape")
    title = str(rec.get("title", "")).strip()
    desc = str(rec.get("description", "")).strip()
    text = ". ".join(t for t in (title, desc) if t)
    if not text:
        raise ValueError(f"bead {bead_id} has no title/description to match on")
    return text


# --------------------------------------------------------------------------- #
# commands                                                                       #
# --------------------------------------------------------------------------- #


def cmd_list(args: argparse.Namespace, out) -> int:
    config = _load(args)
    if args.json:
        out.write(json.dumps([_persona_dict(p) for p in config.personas], indent=2) + "\n")
        return 0
    out.write(f"persona roster ({len(config.personas)}):\n\n")
    width = max((len(p.id) for p in config.personas), default=0)
    for p in config.personas:
        marker = " *" if p.id == config.default_persona_id else "  "
        out.write(f"{marker}{p.id.ljust(width)}  {p.domain}\n")
    if config.default_persona_id:
        out.write("\n* = default (equipped when a task matches nothing)\n")
    return 0


def cmd_show(args: argparse.Namespace, out) -> int:
    config = _load(args)
    if not config.has(args.id):
        sys.stderr.write(
            f"personas: unknown persona {args.id!r}. Known: {', '.join(config.ids)}\n"
        )
        return 2
    p = config.get(args.id)
    if args.json:
        out.write(json.dumps(_persona_dict(p), indent=2) + "\n")
        return 0
    out.write(M.render_overlay(p))
    if p.when_to_equip:
        out.write(f"\n**When to equip:** {p.when_to_equip}\n")
    if p.match_keywords:
        out.write(f"**Match keywords:** {', '.join(p.match_keywords)}\n")
    return 0


def cmd_match(args: argparse.Namespace, out) -> int:
    config = _load(args)
    task = " ".join(args.task)
    result = M.match_persona(config, task)
    if args.json:
        out.write(json.dumps(_match_dict(result), indent=2) + "\n")
        return 0
    if result.is_fallback:
        out.write(
            f"no strong match for {task!r}\n"
            f"-> default persona: {result.best.id} ({result.best.title})\n"
        )
        return 0
    out.write(f"task: {task}\n\n")
    out.write(f"-> {result.best.id}  (score {result.score:g}; matched: {', '.join(result.matched)})\n")
    if result.runners_up:
        out.write("\nrunners-up:\n")
        for s in result.runners_up:
            out.write(f"   {s.persona.id}  (score {s.score:g}; {', '.join(s.matched)})\n")
    return 0


def cmd_equip(args: argparse.Namespace, out) -> int:
    config = _load(args)
    if args.from_bead:
        try:
            task = _task_from_bead(args.from_bead)
        except ValueError as e:
            sys.stderr.write(f"personas equip: {e}\n")
            return 2
    else:
        task = " ".join(args.task)
    if not task.strip():
        sys.stderr.write("personas equip: empty task (give a description or --from-bead ID)\n")
        return 2

    result = M.match_persona(config, task)
    cache = _cache(args, config)
    # Materialize through the warm cache: the overlay is rendered (the cost) only on a
    # cold/stale equip; a warm reuse returns the stored overlay untouched. The fingerprint
    # invalidates a warm entry whose persona definition has since changed.
    outcome = cache.equip(
        result.best.id,
        now=time.time(),
        materialize=lambda: M.render_overlay(result.best),
        fingerprint=M.persona_fingerprint(result.best),
    )
    context = _compose_context(outcome.overlay, result)

    if args.emit_context:
        # Claude Code SessionStart hook payload: inject the persona as added context.
        payload = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            }
        }
        out.write(json.dumps(payload) + "\n")
        return 0

    if args.json:
        doc = _match_dict(result)
        doc["equipped"] = {
            "persona_id": outcome.entry.persona_id,
            "was_warm": outcome.was_warm,
            "use_count": outcome.entry.use_count,
            "evicted": [e.persona_id for e in outcome.evicted],
        }
        out.write(json.dumps(doc, indent=2) + "\n")
        return 0

    state = "reused warm" if outcome.was_warm else "materialized"
    out.write(context)
    out.write(f"\n[{state}; use_count={outcome.entry.use_count}]\n")
    if outcome.evicted:
        out.write(f"[evicted (cold): {', '.join(e.persona_id for e in outcome.evicted)}]\n")
    return 0


def cmd_cache(args: argparse.Namespace, out) -> int:
    config = _load(args)
    cache = _cache(args, config)
    now = time.time()
    statuses = cache.status(now)
    pol = config.cache
    if args.json:
        out.write(
            json.dumps(
                {
                    "policy": {
                        "idle_ttl_seconds": pol.idle_ttl_seconds,
                        "ceiling_ttl_seconds": pol.ceiling_ttl_seconds,
                    },
                    "path": cache.path,
                    "entries": [
                        {
                            "persona_id": s.entry.persona_id,
                            "use_count": s.entry.use_count,
                            "live": s.live,
                            "expiry_reason": s.expiry_reason,
                            "remaining_idle_seconds": round(s.remaining_idle, 3),
                            "remaining_ceiling_seconds": round(s.remaining_ceiling, 3),
                            # Whether this entry carries a materialized overlay (the cached
                            # payload a warm reuse serves) vs. a metadata-only row.
                            "materialized": bool(s.entry.overlay),
                            "overlay_bytes": len(s.entry.overlay),
                        }
                        for s in statuses
                    ],
                },
                indent=2,
            )
            + "\n"
        )
        return 0
    out.write(
        f"warm cache: {cache.path}\n"
        f"policy: idle {_fmt_secs(pol.idle_ttl_seconds)} (sliding), "
        f"ceiling {_fmt_secs(pol.ceiling_ttl_seconds)}\n\n"
    )
    live = [s for s in statuses if s.live]
    if not live:
        out.write("(no warm personas)\n")
        return 0
    for s in live:
        out.write(
            f"  {s.entry.persona_id}  used x{s.entry.use_count}  "
            f"idle-left {_fmt_secs(s.remaining_idle)}  "
            f"ceiling-left {_fmt_secs(s.remaining_ceiling)}\n"
        )
    return 0


def cmd_sweep(args: argparse.Namespace, out) -> int:
    config = _load(args)
    cache = _cache(args, config)
    if args.all:
        n = cache.clear()
        out.write(f"cleared warm cache ({n} entr{'y' if n == 1 else 'ies'})\n")
        return 0
    evicted = cache.sweep(now=time.time())
    if args.json:
        out.write(json.dumps({"evicted": [e.persona_id for e in evicted]}, indent=2) + "\n")
        return 0
    if not evicted:
        out.write("nothing to evict (no expired personas)\n")
        return 0
    out.write(f"evicted {len(evicted)}: {', '.join(e.persona_id for e in evicted)}\n")
    return 0


def _match_dict(result: M.MatchResult) -> dict[str, Any]:
    return {
        "task": result.task,
        "best": result.best.id,
        "score": result.score,
        "matched": list(result.matched),
        "is_fallback": result.is_fallback,
        "ranked": [
            {"persona_id": s.persona.id, "score": s.score, "matched": list(s.matched)}
            for s in result.ranked
        ],
    }


# --------------------------------------------------------------------------- #
# argparse plumbing                                                             #
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="personas",
        description="Equip a best-fit principal-engineer persona for a task; keep recent ones warm.",
    )
    p.add_argument(
        "--registry",
        default=_DEFAULT_REGISTRY,
        help="path to the persona roster toml (default: the pack's personas.toml)",
    )
    p.add_argument(
        "--cache-file",
        default=None,
        help="warm-cache file (default: resolved from PERSONAS_CACHE_*/GC_RIG_ROOT/.beads)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("list", help="list the persona roster")
    pl.add_argument("--json", action="store_true", help="emit JSON")
    pl.set_defaults(func=cmd_list)

    ps = sub.add_parser("show", help="show one persona's full definition + playbook")
    ps.add_argument("id", help="persona id (e.g. principal-backend-engineer)")
    ps.add_argument("--json", action="store_true", help="emit JSON")
    ps.set_defaults(func=cmd_show)

    pm = sub.add_parser("match", help="show the equip decision for a task (read-only)")
    pm.add_argument("task", nargs="+", help="the task description to match")
    pm.add_argument("--json", action="store_true", help="emit JSON")
    pm.set_defaults(func=cmd_match)

    pe = sub.add_parser("equip", help="match + materialize a persona into the warm cache")
    pe.add_argument("task", nargs="*", help="the task description to match")
    pe.add_argument("--from-bead", default=None, metavar="ID", help="pull the task text from a bead")
    pe.add_argument(
        "--emit-context",
        action="store_true",
        help="print a SessionStart hook payload (additionalContext) instead of text",
    )
    pe.add_argument("--json", action="store_true", help="emit JSON")
    pe.set_defaults(func=cmd_equip)

    pc = sub.add_parser("cache", help="show the warm cache (materialized personas + TTL)")
    pc.add_argument("--json", action="store_true", help="emit JSON")
    pc.set_defaults(func=cmd_cache)

    pw = sub.add_parser("sweep", help="evict expired warm personas")
    pw.add_argument("--all", action="store_true", help="clear the whole warm cache")
    pw.add_argument("--json", action="store_true", help="emit JSON")
    pw.set_defaults(func=cmd_sweep)

    return p


def main(argv: Optional[Sequence[str]] = None, out=None) -> int:
    out = out if out is not None else sys.stdout
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args, out))
    except SystemExit as e:  # raised by _load on an invalid registry
        return int(e.code) if e.code is not None else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
