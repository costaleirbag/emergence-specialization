#!/usr/bin/env python3
"""Create presentation data from completed raw runs; never performs inference."""
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def read_json(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default

def events(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []

def complete_runs(condition):
    found = []
    for directory in (ROOT / "data" / "runs").glob(f"{condition}-*"):
        summary = read_json(directory / "summary.json")
        if summary and summary.get("status") == "completed":
            found.append((directory.stat().st_mtime, directory, summary))
    return sorted(found, reverse=True)

def event_stats(path):
    rows = events(path / "events.jsonl")
    inf = [r for r in rows if r.get("event") == "inference"]
    errors = [r for r in inf if r.get("error")]
    lat = [r["latency_s"] for r in inf if isinstance(r.get("latency_s"), (int, float))]
    usage = [r["token_usage"] for r in inf if r.get("token_usage")]
    costs = [u.get("cost", {}).get("total") for u in usage if u.get("cost", {}).get("total") is not None]
    return {
        "events": len(rows), "inference_attempts": len(inf),
        "interaction_attempts": sum(r.get("phase") in {"interaction", "round"} for r in inf),
        "probe_attempts": sum(r.get("phase") == "probe" for r in inf),
        "errors": len(errors),
        "timeouts": sum("timeout" in str(r.get("error", "")).lower() for r in errors),
        "parsing_errors": sum("parse" in str(r.get("error", "")).lower() for r in errors),
        "retries": sum(r.get("retry_count", 0) for r in inf),
        "latency": {"total_s": round(sum(lat), 2), "mean_s": round(sum(lat) / len(lat), 2) if lat else None,
                    "min_s": round(min(lat), 2) if lat else None, "max_s": round(max(lat), 2) if lat else None},
        "usage": {"records": len(usage), "coverage": round(len(usage) / len(inf), 4) if inf else None,
                  "input_tokens": sum(u.get("input", 0) or 0 for u in usage),
                  "output_tokens": sum(u.get("output", 0) or 0 for u in usage),
                  "total_tokens": sum(u.get("totalTokens", 0) or 0 for u in usage),
                  "cost_usd": round(sum(costs), 6) if costs else None},
    }

def simplify_checkpoint(row):
    keys = ["checkpoint", "best_individual_accuracy", "oracle_society_accuracy", "oracle_gain", "normalized_hse",
            "normalized_task_agent_mutual_information", "normalized_utilization_entropy", "temporal_role_stability",
            "individual_accuracy", "competence_matrix", "routing_counts_by_world_agent"]
    return {key: row.get(key) for key in keys}

def load_run(directory, summary):
    metadata = read_json(directory / "metadata.json", {})
    config = metadata.get("config", {})
    backend = metadata.get("backend", {})
    final = summary.get("final_metrics", {})
    rows = events(directory / "events.jsonl")
    metrics = [json.loads(line) for line in (directory / "metrics.jsonl").read_text().splitlines() if line.strip()] if (directory / "metrics.jsonl").exists() else []
    return {
        "run_id": summary.get("run_id", directory.name), "condition": summary.get("condition"), "status": summary.get("status"),
        "directory": str(directory.relative_to(ROOT)), "git_head": metadata.get("git_head") or summary.get("git_head"),
        "config": {"agents": config.get("experiment", {}).get("num_agents"), "rounds": config.get("experiment", {}).get("num_rounds"),
                   "checkpoints": config.get("experiment", {}).get("checkpoints"), "seed": config.get("experiment", {}).get("seed"),
                   "model": config.get("agent", {}).get("model"), "backend": config.get("agent", {}).get("backend"),
                   "memory_mode": config.get("condition", {}).get("memory_mode"), "memory_strategy": config.get("agent", {}).get("memory_strategy"),
                   "memory_k": config.get("agent", {}).get("memory_k"), "router": config.get("router", {}).get("strategy"),
                   "epsilon": config.get("router", {}).get("epsilon"), "thinking": config.get("agent", {}).get("thinking"),
                   "probe_set_path": config.get("logging", {}).get("probe_set_path")},
        "backend": {"version": backend.get("omp_version"), "session_policy": backend.get("session_policy")},
        "probe_set_hash": final.get("probe_set_hash") or metadata.get("probe_set_hash"),
        "final": {"routing_counts": summary.get("routing_counts"), "memory_counts": summary.get("memory_counts"), **{key: final.get(key) for key in ["normalized_utilization_entropy", "normalized_task_agent_mutual_information",
                                                   "normalized_hse", "oracle_gain", "best_individual_accuracy", "oracle_society_accuracy", "individual_accuracy",
                                                   "competence_matrix", "routing_counts_by_world_agent", "temporal_role_stability"]}},
        "checkpoints": [simplify_checkpoint(row) for row in metrics], "event_stats": event_stats(directory),
    }

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--private-run"); parser.add_argument("--shared-run"); parser.add_argument("--output", default=str(ROOT / "presentation/data/presentation-data.json")); args = parser.parse_args()
    private_dir = Path(args.private_run) if args.private_run else complete_runs("private")[0][1]
    shared_dir = Path(args.shared_run) if args.shared_run else (complete_runs("shared")[0][1] if complete_runs("shared") else None)
    private = load_run(private_dir, read_json(private_dir / "summary.json"))
    shared = load_run(shared_dir, read_json(shared_dir / "summary.json")) if shared_dir else None
    payload = {"generated_from": "raw data/runs artifacts; no inference performed", "private": private, "shared": shared,
               "shared_status": "complete" if shared else "not_available_or_incomplete",
               "notes": ["Metrics are descriptive observables, not proof of specialization.", "Private/shared comparison is withheld until shared completes."]}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"private: {private['run_id']}"); print(f"shared: {shared['run_id'] if shared else 'not complete'}"); print(f"wrote: {output}")

if __name__ == "__main__": main()
