"""Offline configuration doctor and opt-in one-completion API check.

The default mode is deliberately side-effect free with respect to the model:
it validates configs and prints only credential *status*.  ``--confirm-real``
is required before the single live completion is attempted.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from .config import load_config
from .credentials import CredentialStore
from .parsing import parse_agent_output
from .providers.deepseek_direct import DeepSeekDirectBackend
from .probes import load_probe_set


DEFAULT_PRIVATE = "configs/research/replication_private.yaml"
DEFAULT_SHARED = "configs/research/replication_shared.yaml"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_config_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (Path.cwd() / path).resolve()


def _resolve_probe_path(config_path: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (config_path.parent.parent.parent / path).resolve()


def _offline_report(private_path: str, shared_path: str) -> dict[str, Any]:
    private_file = _resolve_config_path(private_path)
    shared_file = _resolve_config_path(shared_path)
    private = load_config(private_file)
    shared = load_config(shared_file)
    private_probes, private_hash = load_probe_set(_resolve_probe_path(private_file, private.logging.probe_set_path))
    shared_probes, shared_hash = load_probe_set(_resolve_probe_path(shared_file, shared.logging.probe_set_path))
    differences = []
    for label, left, right in (
        ("model", private.agent.model, shared.agent.model),
        ("backend", private.agent.backend, shared.agent.backend),
        ("seed", private.experiment.seed, shared.experiment.seed),
        ("probe_set_hash", private_hash, shared_hash),
        ("num_agents", private.experiment.num_agents, shared.experiment.num_agents),
        ("num_rounds", private.experiment.num_rounds, shared.experiment.num_rounds),
        ("checkpoints", private.experiment.checkpoints, shared.experiment.checkpoints),
    ):
        if left != right:
            differences.append({"field": label, "private": left, "shared": right})
    return {
        "watermark": "INFRASTRUCTURE DOCTOR — NOT SCIENTIFIC DATA",
        "mode": "offline",
        "model_calls": 0,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "configs": {
            "private": str(private_file),
            "shared": str(shared_file),
        },
        "direct_backend": private.agent.backend == "deepseek_direct" and shared.agent.backend == "deepseek_direct",
        "model": private.agent.model,
        "probe_set_hash": private_hash,
        "probe_count": len(private_probes),
        "paired_config_differences": differences,
        "credential_source": private.runtime.credential_source,
        "credential_service": private.runtime.credential_service,
        "credential_status": "not read in offline mode; run credentials status separately",
    }


async def _one_live_call(config_path: str, output_dir: Path) -> dict[str, Any]:
    config = load_config(_resolve_config_path(config_path))
    if config.agent.backend != "deepseek_direct":
        raise ValueError("doctor requires a deepseek_direct config")
    store = CredentialStore(config.runtime.credential_service, config.runtime.credential_account)
    api_key = store.get(source=config.runtime.credential_source)
    backend = DeepSeekDirectBackend(
        api_key=api_key,
        base_url=config.runtime.api_base_url,
        thinking=config.agent.thinking,
        max_tokens=min(config.agent.max_tokens or 128, 128),
        connect_timeout_s=config.runtime.connect_timeout_s,
        read_timeout_s=config.runtime.read_timeout_s,
        request_timeout_s=config.runtime.request_timeout_s,
        pool_timeout_s=config.runtime.pool_timeout_s,
        user_id=config.runtime.user_id,
        credential_source=config.runtime.credential_source,
    )
    started = time.perf_counter()
    try:
        response = await backend.complete(
            system_prompt="Return JSON only. This is an infrastructure doctor, not a scientific task.",
            user_prompt='Return exactly this JSON object: {"answer": 0, "confidence": 0.0}',
            model=config.agent.model,
            model_parameters={"max_tokens": min(config.agent.max_tokens or 128, 128)},
        )
    finally:
        await backend.close()
    parsed = None
    parse_error = None
    if response.raw_response is not None:
        try:
            parsed_response = parse_agent_output(response.raw_response)
            parsed = {"answer": parsed_response.answer, "confidence": parsed_response.confidence}
        except Exception as exc:  # defensive validation boundary
            parse_error = type(exc).__name__
    result = {
        "watermark": "INFRASTRUCTURE DOCTOR — NOT SCIENTIFIC DATA",
        "mode": "one_live_completion",
        "model_calls": 1,
        "elapsed_s": time.perf_counter() - started,
        "backend": backend.metadata(),
        "response": {
            "success": response.error is None and parsed is not None,
            "parsed": parsed,
            "parse_error": parse_error,
            "error_category": response.error_category,
            "http_status": response.http_status,
            "latency_s": response.latency_s,
            "usage": response.token_usage,
            "provider_metadata": response.provider_metadata,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "doctor.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Validate DeepSeek Direct without a model call by default")
    parser.add_argument("--config", default=str(REPO_ROOT / DEFAULT_PRIVATE))
    parser.add_argument("--shared-config", default=str(REPO_ROOT / DEFAULT_SHARED))
    parser.add_argument("--confirm-real", action="store_true", help="Permit exactly one live completion")
    parser.add_argument("--output-dir", default="reports/infrastructure-doctor")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if not args.confirm_real:
        report = _offline_report(args.config, args.shared_config)
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    result = asyncio.run(_one_live_call(args.config, Path(args.output_dir)))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
