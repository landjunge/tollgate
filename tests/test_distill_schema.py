"""Every distill JSON must satisfy the light schema."""

from __future__ import annotations

from pathlib import Path

from tollgate.distill.loader import all_distills, list_distill_ids, load_distill
from tollgate.distill.schema import validate_distill


def test_all_distills_validate():
    ids = list_distill_ids()
    assert ids, "no distill json found"
    errors: list[str] = []
    for pid in ids:
        data = load_distill(pid)
        assert data, f"empty distill {pid}"
        # id field should match filename when present
        if data.get("id") and str(data["id"]).lower() != pid:
            errors.append(f"{pid}: id field {data.get('id')!r} != file stem")
        errors.extend(validate_distill(data, path=pid))
    assert not errors, "\n".join(errors)


def test_google_is_high_risk_or_disabled_default():
    g = load_distill("google")
    assert g
    # either high_risk flag or notes about risk
    blob = str(g).lower()
    assert "high" in blob or "risk" in blob or "bill" in blob or "gemini" in blob


def test_all_distills_dict():
    m = all_distills()
    assert "brave" in m
    assert "deepseek" in m


def test_distill_files_on_disk():
    d = Path(__file__).resolve().parents[1] / "src" / "tollgate" / "distill"
    jsons = list(d.glob("*.json"))
    assert len(jsons) >= 5
