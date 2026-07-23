"""Render an exported Canri movie project through Runway and save a local MP4."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from movie_engine.runway_backend import RunwayMovieBackend, build_render_chunks, estimate_runway_cost


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a Canri movie project with Runway Gen-4.5.")
    parser.add_argument("project", type=Path, help="Path to movie_project.json")
    parser.add_argument("--max-cost-usd", type=float, required=True, help="Hard ceiling for the estimated base cost")
    parser.add_argument("--model", default="gen4.5", help="Runway video model (default: gen4.5)")
    parser.add_argument("--ratio", default="1280:720", help="Output ratio/resolution accepted by the model")
    parser.add_argument("--execute", action="store_true", help="Acknowledge cost and start paid generation")
    return parser.parse_args()


def load_project(path: Path) -> dict:
    data = json.loads(path.resolve().read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("movie_project"), dict):
        data = data["movie_project"]
    if not isinstance(data, dict) or not isinstance(data.get("render_manifest"), dict):
        raise ValueError("The file is not a valid exported Canri movie project.")
    return data


def main() -> int:
    args = parse_args()
    project = load_project(args.project)
    chunks = build_render_chunks(project)
    estimate = estimate_runway_cost(sum(chunk.duration_seconds for chunk in chunks), args.model)
    print(f"Model: {args.model}")
    print(f"Generated clips: {len(chunks)}")
    print(f"Planned video: {estimate['duration_seconds']} seconds")
    print(f"Estimated base cost: ${estimate['estimated_usd']:.2f} (retries not included)")
    if estimate["estimated_usd"] > args.max_cost_usd:
        print(f"Stopped: estimate exceeds --max-cost-usd ${args.max_cost_usd:.2f}.", file=sys.stderr)
        return 2
    if not args.execute:
        print("Dry run only. Add --execute to authorize paid generation.")
        return 0
    if not os.getenv("RUNWAYML_API_SECRET", "").strip():
        print("RUNWAYML_API_SECRET is not set. Do not put the key in the project.", file=sys.stderr)
        return 2
    backend = RunwayMovieBackend(
        model=args.model,
        ratio=args.ratio,
        max_cost_usd=args.max_cost_usd,
    )
    result = backend(project)
    print(f"Photorealistic MP4: {result['output_file']}")
    print(f"Checkpoint: {result['checkpoint_file']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
