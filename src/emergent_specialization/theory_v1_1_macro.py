"""Theory V1.1 targeted MACRO execution adapter.

This module reuses the frozen Theory V1 trajectory/checkpoint state machine,
but binds it to the V1.1 fresh seeds, eight-cell grid, separate raw namespace,
and the V1.1 hard budget.  The adapter is intentionally narrow: it changes
execution provenance and scheduling inputs, not social state transitions,
router equations, memory semantics, or prompt rendering.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .theory_v1 import macro_runner as legacy
from .theory_v1_1 import (
    ECOLOGIES,
    HARD_CAP_USD,
    MACRO_CELLS_V11,
    MODEL,
    SOCIAL_SEEDS_V11,
    THINKING,
    REPORT_ROOT as V11_REPORT_ROOT,
    DATA_ROOT as V11_DATA_ROOT,
    stable_hash,
)

V11_MACRO_ROOT = V11_DATA_ROOT / "macro"
V11_MACRO_REPORT = V11_REPORT_ROOT / "macro_manifest.json"
V11_PREDICTION_ROOT = V11_REPORT_ROOT / "predictions"
V11_PREDICTION_PATH = V11_PREDICTION_ROOT / "prediction_manifest.json"
PROTOCOL = "THEORY-V1.1"
CHECKPOINTS = (0, 16, 32, 64, 128)
ROUNDS = 128


def _bind_legacy() -> None:
    """Bind legacy implementation globals to V1.1 paths and frozen inputs."""
    legacy.PROTOCOL = PROTOCOL
    legacy.ECOLOGIES = tuple(ECOLOGIES)
    legacy.SOCIAL_SEEDS = {name: tuple(values) for name, values in SOCIAL_SEEDS_V11.items()}
    legacy.MACRO_CHECKPOINTS = CHECKPOINTS
    legacy.MACRO_ROUNDS = ROUNDS
    legacy.MACRO_ROOT = V11_MACRO_ROOT
    legacy.DATA_ROOT = V11_DATA_ROOT
    legacy.REPORT_ROOT = V11_REPORT_ROOT
    legacy.MACRO_REPORT = V11_MACRO_REPORT
    legacy.HARD_CAP_USD = HARD_CAP_USD
    legacy.MODEL = MODEL
    legacy.THINKING = THINKING
    legacy.macro_cells = lambda: [dict(cell) for cell in MACRO_CELLS_V11]


def build_manifest() -> dict[str, Any]:
    _bind_legacy()
    manifest = legacy.build_manifest()
    if manifest.get("protocol") != PROTOCOL:
        raise RuntimeError("V1.1 MACRO manifest protocol mismatch")
    if manifest.get("logical_calls") != 62976:
        raise RuntimeError(f"V1.1 MACRO logical-call mismatch: {manifest.get('logical_calls')}")
    if len(manifest.get("cells", [])) != 8:
        raise RuntimeError("V1.1 MACRO cell cardinality mismatch")
    if manifest.get("social_seeds") != {name: list(values) for name, values in SOCIAL_SEEDS_V11.items()}:
        raise RuntimeError("V1.1 MACRO seed manifest mismatch")
    return manifest


def preflight() -> dict[str, Any]:
    _bind_legacy()
    manifest = build_manifest()
    result = legacy.preflight()
    # Keep the preflight visibly in the V1.1 report namespace even though the
    # frozen state-machine implementation writes its legacy-compatible file.
    V11_REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    (V11_REPORT_ROOT / "macro_preflight.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if result.get("decision") != "PROCEED_TO_MACRO":
        raise RuntimeError("V1.1 MACRO cost preflight failed")
    return result


async def run_macro(*, confirm_real: bool = False, concurrency: int = 32) -> dict[str, Any]:
    _bind_legacy()
    # The legacy runner checks this root-level path.  The canonical sealed
    # artifact remains under reports/theory-v1-1/predictions/; the byte-for-
    # byte copy is a compatibility input only and is hash-checked below.
    if not V11_PREDICTION_PATH.exists():
        raise RuntimeError("V1.1 prediction seal is missing")
    V11_REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    root_prediction = V11_REPORT_ROOT / "prediction_manifest.json"
    payload = V11_PREDICTION_PATH.read_bytes()
    if root_prediction.exists() and root_prediction.read_bytes() != payload:
        raise RuntimeError("root V1.1 prediction compatibility copy differs")
    if not root_prediction.exists():
        root_prediction.write_bytes(payload)
    result = await legacy.run_macro(confirm_real=confirm_real, concurrency=concurrency)
    result["protocol"] = PROTOCOL
    result["run_id"] = "theory-v1-1-macro-confirmatory-20260813"
    status_path = V11_MACRO_ROOT / "macro_status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status.update(protocol=PROTOCOL, run_id=result["run_id"], prediction_manifest_sha256=stable_hash(json.loads(payload)))
    status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return status


def health() -> dict[str, Any]:
    _bind_legacy()
    result = legacy.health()
    result["protocol"] = PROTOCOL
    return result

