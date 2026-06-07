"""personas — equip/match engine tests.

Owns the equip decision: the right persona wins for a clearly-domain task, the choice
is explainable (the matched terms are reported), plural/singular forms match, ties break
deterministically, and a no-signal task falls back to the default. Pure stdlib + pytest.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from personas import match as M  # noqa: E402
from personas import registry as R  # noqa: E402

_SHIPPED = os.path.join(_ROOT, "personas.toml")


def cfg() -> R.PersonasConfig:
    return R.load_config(_SHIPPED)


# ---- singularization helper ------------------------------------------------ #


def test_singular_handles_common_plurals():
    assert M._singular("tests") == "test"
    assert M._singular("apis") == "api"
    assert M._singular("queries") == "query"
    assert M._singular("vulnerabilities") == "vulnerability"
    assert M._singular("batches") == "batch"


def test_singular_preserves_double_s_and_short_words():
    assert M._singular("class") == "class"
    assert M._singular("loss") == "loss"
    assert M._singular("is") == "is"
    assert M._singular("as") == "as"


# ---- routing to the right persona ------------------------------------------ #


def test_backend_task_routes_to_backend():
    r = M.match_persona(cfg(), "implement a REST endpoint backed by Postgres with idempotent writes")
    assert r.best.id == "principal-backend-engineer"
    assert not r.is_fallback


def test_security_task_routes_to_security():
    r = M.match_persona(cfg(), "audit the upload handler for SSRF and sql injection")
    assert r.best.id == "principal-security-engineer"


def test_frontend_task_routes_to_frontend():
    r = M.match_persona(cfg(), "build an accessible React modal component with keyboard focus")
    assert r.best.id == "principal-frontend-engineer"


def test_systems_task_routes_to_systems():
    r = M.match_persona(cfg(), "fix the race condition and deadlock in the concurrent worker pool")
    assert r.best.id == "principal-systems-engineer"


def test_platform_task_routes_to_platform():
    r = M.match_persona(cfg(), "set up the kubernetes deployment and ci/cd pipeline with a rollback")
    assert r.best.id == "principal-platform-engineer"


def test_data_task_routes_to_data():
    r = M.match_persona(cfg(), "build an idempotent ETL pipeline that backfills the warehouse")
    assert r.best.id == "principal-data-engineer"


def test_test_task_routes_to_test_engineer():
    r = M.match_persona(cfg(), "write integration tests and raise coverage for the module")
    assert r.best.id == "principal-test-engineer"


def test_refactor_task_routes_to_refactoring():
    r = M.match_persona(cfg(), "refactor and simplify this tangled module to cut duplication")
    assert r.best.id == "principal-refactoring-engineer"


def test_docs_task_routes_to_docs():
    r = M.match_persona(cfg(), "rewrite the README and write a getting-started tutorial")
    assert r.best.id == "principal-docs-engineer"


def test_api_design_task_routes_to_api_designer():
    r = M.match_persona(cfg(), "design a backward-compatible openapi contract and deprecation path")
    assert r.best.id == "principal-api-designer"


# ---- explainability + structure -------------------------------------------- #


def test_result_reports_matched_terms():
    r = M.match_persona(cfg(), "audit for sql injection")
    assert r.matched  # non-empty
    assert any("injection" in m for m in r.matched)
    assert r.score > 0


def test_phrase_keyword_scores_more_than_single_word():
    # "sql injection" (phrase) should outscore a lone single-word hit.
    single = M.score_persona(
        cfg().get("principal-security-engineer"),
        {"audit"},
        " audit ",
    )
    phrase = M.score_persona(
        cfg().get("principal-security-engineer"),
        set("sql injection".split()),
        " sql injection ",
    )
    assert phrase.score > single.score


def test_runners_up_excludes_best():
    r = M.match_persona(cfg(), "audit the auth flow for sql injection vulnerabilities")
    assert r.best.id not in {s.persona.id for s in r.runners_up}


# ---- fallback + determinism ------------------------------------------------ #


def test_no_signal_falls_back_to_default():
    r = M.match_persona(cfg(), "do the thing with the stuff")
    assert r.is_fallback
    assert r.best.id == cfg().default_persona_id
    assert r.score == 0.0
    assert r.ranked == ()


def test_empty_task_is_fallback():
    r = M.match_persona(cfg(), "")
    assert r.is_fallback


def test_match_is_deterministic():
    task = "audit the auth flow for sql injection vulnerabilities in the api"
    first = M.match_persona(cfg(), task)
    again = M.match_persona(cfg(), task)
    assert first.best.id == again.best.id
    assert first.score == again.score
    assert [s.persona.id for s in first.ranked] == [s.persona.id for s in again.ranked]


def test_ranked_is_sorted_by_score_desc():
    r = M.match_persona(cfg(), "audit the auth flow for sql injection in the api endpoint")
    scores = [s.score for s in r.ranked]
    assert scores == sorted(scores, reverse=True)


def test_tie_breaks_by_id_when_scores_equal():
    # Two single-keyword personas; an ambiguous task that hits exactly one keyword each.
    config = R.from_mapping(
        {
            "persona": [
                {"id": "bbb", "domain": "d", "match_keywords": ["widget"]},
                {"id": "aaa", "domain": "d", "match_keywords": ["widget"]},
            ]
        }
    )
    r = M.match_persona(config, "build a widget")
    assert r.best.id == "aaa"  # equal score + weight -> id ascending
