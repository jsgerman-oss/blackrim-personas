"""Equip / match engine — pick the best-fit persona for a task by description match.

The README's equip step: "an agent matches the task to the best-fit persona
(description match, the same way skills auto-fire)." This module is that match rule.

It is deliberately transparent and deterministic — no model call, no network. Every
decision is explainable: :class:`MatchResult` carries the score and the exact terms
that fired, so ``personas match`` can show *why* a persona was chosen. Scoring:

- **Curated keywords (primary).** Each persona's ``match_keywords`` are matched against
  the task as whole-word phrases. A multi-word keyword (e.g. ``"threat model"``) is a
  stronger signal than a single word, so it scores higher.
- **Domain vocabulary (secondary).** Salient words from the persona's ``domain`` and
  ``when_to_equip`` that also appear in the task add a small bonus, so a task that uses
  a persona's vocabulary without hitting an explicit keyword still matches.
- **Tie-break.** Equal scores break by ``persona.weight`` then ``id`` — fully
  deterministic, never order-dependent.

With no signal at all the engine returns the registry's default (generalist) persona,
flagged ``is_fallback=True``, so the caller always gets a usable answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from personas.registry import Persona, PersonasConfig

_WORD = re.compile(r"[a-z0-9]+")

# Weights for the scoring channels. Kept here (not magic numbers inline) so the rule
# is auditable and tunable in one place.
_W_KEYWORD = 1.0          # single-word curated keyword hit
_W_KEYWORD_PHRASE = 2.0   # multi-word curated keyword hit (stronger signal)
_W_DOMAIN_TERM = 0.25     # salient domain/when-to-equip word that also appears in task

# Common words that carry no routing signal — excluded from the secondary channel so
# "the", "and", "code" etc. don't make every persona match everything.
_STOPWORDS = frozenset(
    """
    a an and are as at be by for from has have in into is it its of on or over so that
    the their then there these this to up via was were will with your you can change
    changes code codebase work task make new use using add adds added implement update
    fix fixing build run review small large file files line lines write writing
    """.split()
)


def normalize(text: str) -> list[str]:
    """Lowercase the text and split it into alphanumeric word tokens."""
    return _WORD.findall(text.lower())


def _singular(w: str) -> str:
    """Naive singularization so plural/singular forms match (``tests`` -> ``test``).

    A heuristic, not a lemmatizer — good enough to keep keyword matching from missing
    on a trailing ``s``. Conservative length guards avoid mangling short words, and the
    ``ss`` exclusion keeps ``class``/``loss`` intact.
    """
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 4 and (w[-4:] in ("ches", "shes") or w[-3:] in ("ses", "xes", "zes")):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def _singularize(tokens: list[str]) -> list[str]:
    return [_singular(t) for t in tokens]


def _phrase_in(phrase_tokens: list[str], haystack_padded: str) -> bool:
    """True if ``phrase_tokens`` occurs as a whole-word run inside the task text.

    ``haystack_padded`` is the task's normalized tokens space-joined and space-padded,
    so a simple substring check honors word boundaries (``" api "`` never matches
    ``"rapid"``).
    """
    if not phrase_tokens:
        return False
    needle = " " + " ".join(phrase_tokens) + " "
    return needle in haystack_padded


@dataclass(frozen=True)
class Scored:
    """One persona's score against a task, with the terms that fired."""

    persona: Persona
    score: float
    matched: tuple[str, ...]  # the keywords / domain terms that contributed


@dataclass(frozen=True)
class MatchResult:
    """The equip decision for a task.

    ``best`` is the chosen persona; ``ranked`` is every persona with a positive score,
    best first; ``is_fallback`` is True when nothing scored and the default was used.
    """

    best: Persona
    score: float
    matched: tuple[str, ...]
    ranked: tuple[Scored, ...]
    is_fallback: bool = False
    task: str = ""

    @property
    def runners_up(self) -> tuple[Scored, ...]:
        return tuple(s for s in self.ranked if s.persona.id != self.best.id)


def _domain_terms(persona: Persona) -> set[str]:
    """Salient (non-stopword) singularized vocab from a persona's domain + when_to_equip."""
    words = normalize(persona.domain) + normalize(persona.when_to_equip)
    return {_singular(w) for w in words if w not in _STOPWORDS and len(w) > 2}


def score_persona(persona: Persona, task_sing: set[str], task_padded_sing: str) -> Scored:
    """Score a single persona against the (singularized) task.

    ``task_padded_sing`` is the task's singularized tokens, space-joined and padded for
    whole-word phrase matching; ``task_sing`` is the same tokens as a set for the
    secondary domain-vocabulary channel.
    """
    score = 0.0
    matched: list[str] = []

    # Primary channel: curated keywords as whole-word phrases (singularized). Dedup by
    # the singularized phrase so near-duplicate keywords (e.g. "test"/"tests") count once.
    keyword_hits: set[str] = set()
    seen_phrases: set[str] = set()
    for kw in persona.match_keywords:
        kw_sing = _singularize(normalize(kw))
        if not kw_sing:
            continue
        phrase = " ".join(kw_sing)
        if phrase in seen_phrases:
            continue
        if _phrase_in(kw_sing, task_padded_sing):
            seen_phrases.add(phrase)
            score += _W_KEYWORD_PHRASE if len(kw_sing) > 1 else _W_KEYWORD
            matched.append(kw)
            keyword_hits.update(kw_sing)

    # Secondary channel: salient domain vocabulary that also appears in the task, not
    # already credited via a keyword hit. Bounded and low-weight by construction.
    for term in sorted(_domain_terms(persona)):
        if term in task_sing and term not in keyword_hits:
            score += _W_DOMAIN_TERM
            matched.append(term)

    return Scored(persona=persona, score=round(score, 4), matched=tuple(matched))


def match_persona(config: PersonasConfig, task: str) -> MatchResult:
    """Return the best-fit persona for ``task`` (the equip decision)."""
    task_sing_tokens = _singularize(normalize(task))
    task_sing = set(task_sing_tokens)
    task_padded_sing = " " + " ".join(task_sing_tokens) + " "

    scored = [score_persona(p, task_sing, task_padded_sing) for p in config.personas]
    # Deterministic order: score desc, then weight desc, then id asc.
    scored.sort(key=lambda s: (-s.score, -s.persona.weight, s.persona.id))

    positive = tuple(s for s in scored if s.score > 0)

    if not positive:
        fallback = config.default_persona
        return MatchResult(
            best=fallback,
            score=0.0,
            matched=(),
            ranked=(),
            is_fallback=True,
            task=task,
        )

    top = positive[0]
    return MatchResult(
        best=top.persona,
        score=top.score,
        matched=top.matched,
        ranked=positive,
        is_fallback=False,
        task=task,
    )
