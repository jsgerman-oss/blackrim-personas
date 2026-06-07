"""personas — registry load + validation tests.

Owns the contract of ``personas.toml``: the shipped roster parses and carries the full
10-persona suite the README specifies; the cache TTL policy resolves from minute/hour
convenience keys; and malformed config is rejected loudly. Pure stdlib + pytest.
"""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from personas import registry as R  # noqa: E402

_SHIPPED = os.path.join(_ROOT, "personas.toml")

# The roster the README "initial roster" promises.
EXPECTED_IDS = {
    "principal-backend-engineer",
    "principal-frontend-engineer",
    "principal-systems-engineer",
    "principal-security-engineer",
    "principal-data-engineer",
    "principal-platform-engineer",
    "principal-api-designer",
    "principal-test-engineer",
    "principal-refactoring-engineer",
    "principal-docs-engineer",
}


# ---- shipped roster -------------------------------------------------------- #


def test_shipped_roster_has_full_suite():
    config = R.load_config(_SHIPPED)
    assert set(config.ids) == EXPECTED_IDS
    assert len(config.personas) == 10


def test_every_persona_is_complete():
    config = R.load_config(_SHIPPED)
    for p in config.personas:
        assert p.domain, f"{p.id} missing domain"
        assert p.when_to_equip, f"{p.id} missing when_to_equip"
        assert p.verification_bar, f"{p.id} missing verification_bar"
        assert p.playbook, f"{p.id} missing playbook"
        assert p.match_keywords, f"{p.id} has no match_keywords"
        assert p.skills, f"{p.id} brings no skills"
        assert p.tools, f"{p.id} brings no tools"


def test_keywords_are_lowercased_on_load():
    config = R.load_config(_SHIPPED)
    for p in config.personas:
        for kw in p.match_keywords:
            assert kw == kw.lower()


def test_shipped_cache_policy_is_the_documented_default():
    config = R.load_config(_SHIPPED)
    assert config.cache.idle_ttl_seconds == 30 * 60
    assert config.cache.ceiling_ttl_seconds == 2 * 3600


def test_default_persona_resolves():
    config = R.load_config(_SHIPPED)
    assert config.default_persona_id == "principal-backend-engineer"
    assert config.default_persona.id == "principal-backend-engineer"


def test_title_is_humanized():
    p = R.load_config(_SHIPPED).get("principal-backend-engineer")
    assert p.title == "Principal Backend Engineer"


# ---- defaults / missing file ----------------------------------------------- #


def test_missing_file_falls_back_to_builtin():
    config = R.load_config("/nonexistent/personas.toml")
    assert len(config.personas) >= 1
    assert config.has(config.default_persona_id)


def test_none_path_is_builtin_default():
    config = R.load_config(None)
    assert config is not None
    assert len(config.personas) >= 1


# ---- cache policy parsing -------------------------------------------------- #


def test_cache_seconds_override_convenience_keys():
    cfg = R.from_mapping(
        {
            "persona": [{"id": "p", "domain": "d"}],
            "cache": {"idle_ttl_minutes": 30, "idle_ttl_seconds": 5, "ceiling_ttl_seconds": 10},
        }
    )
    assert cfg.cache.idle_ttl_seconds == 5
    assert cfg.cache.ceiling_ttl_seconds == 10


def test_cache_ceiling_below_idle_is_rejected():
    with pytest.raises(R.RegistryError):
        R.from_mapping(
            {
                "persona": [{"id": "p", "domain": "d"}],
                "cache": {"idle_ttl_seconds": 100, "ceiling_ttl_seconds": 10},
            }
        )


# ---- malformed config ------------------------------------------------------ #


def test_empty_roster_rejected():
    with pytest.raises(R.RegistryError):
        R._finalise(personas=[], cache=R.CachePolicy(), default_persona_id=None)


def test_duplicate_ids_rejected():
    with pytest.raises(R.RegistryError):
        R.from_mapping({"persona": [{"id": "dup"}, {"id": "dup"}]})


def test_unknown_default_persona_rejected():
    with pytest.raises(R.RegistryError):
        R.from_mapping(
            {"persona": [{"id": "a"}], "registry": {"default_persona": "nope"}}
        )


def test_persona_missing_id_rejected():
    with pytest.raises(R.RegistryError):
        R.from_mapping({"persona": [{"domain": "no id here"}]})


def test_match_keywords_must_be_array():
    with pytest.raises(R.RegistryError):
        R.from_mapping({"persona": [{"id": "a", "match_keywords": "backend"}]})
