"""Runway-backed photorealistic movie rendering with resumable local downloads."""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse
from urllib.request import Request, urlopen


RUNWAY_CREDIT_USD = 0.01
RUNWAY_CREDITS_PER_SECOND = {
    "gen4.5": 12,
    "gemini_omni_flash": 10,
    "happyhorse_1_0": 15,
    "seedance2_mini": 16,
}
MIN_CLIP_SECONDS = 2
MAX_CLIP_SECONDS = 10


class RunwayRenderError(RuntimeError):
    """Raised when a remote generation or local assembly step fails."""


@dataclass(frozen=True)
class RenderChunk:
    chunk_id: str
    shot_id: str
    index: int
    count: int
    duration_seconds: int
    prompt: str
    negative_prompt: str
    output_file: Path


def estimate_runway_cost(duration_seconds: int, model: str = "gen4.5") -> dict[str, Any]:
    credits_per_second = RUNWAY_CREDITS_PER_SECOND.get(model)
    if credits_per_second is None:
        raise ValueError(f"No verified local price is configured for Runway model {model!r}.")
    credits = max(0, int(duration_seconds)) * credits_per_second
    return {
        "model": model,
        "duration_seconds": max(0, int(duration_seconds)),
        "credits_per_second": credits_per_second,
        "estimated_credits": credits,
        "estimated_usd": round(credits * RUNWAY_CREDIT_USD, 2),
        "retries_not_included": True,
    }


def split_duration(duration_seconds: int) -> list[int]:
    """Split a shot into Gen-4.5-compatible 2-10 second generations."""
    remaining = max(MIN_CLIP_SECONDS, int(math.ceil(duration_seconds)))
    parts: list[int] = []
    while remaining > MAX_CLIP_SECONDS:
        size = MAX_CLIP_SECONDS
        if remaining - size == 1:
            size -= 1
        parts.append(size)
        remaining -= size
    if remaining:
        if remaining < MIN_CLIP_SECONDS and parts:
            parts[-1] += remaining
        else:
            parts.append(remaining)
    return parts


def _project_output_directory(project: dict[str, Any]) -> Path:
    assembly = project.get("render_manifest", {}).get("assembly", {})
    viewing_copy = assembly.get("viewing_copy")
    if viewing_copy:
        return Path(viewing_copy).expanduser().resolve().parent
    project_id = str(project.get("project_id") or "movie")
    return (Path.cwd() / "generated_movies" / project_id).resolve()


def build_render_chunks(
    project: dict[str, Any],
    output_directory: Path | None = None,
) -> list[RenderChunk]:
    output_root = Path(output_directory or _project_output_directory(project))
    clip_root = output_root / "runway_clips"
    chunks: list[RenderChunk] = []
    jobs = project.get("render_manifest", {}).get("jobs", [])
    for job_number, job in enumerate(jobs, start=1):
        if not isinstance(job, dict):
            continue
        shot_id = str(job.get("shot_id") or f"shot_{job_number:04d}")
        durations = split_duration(int(job.get("duration_seconds") or MIN_CLIP_SECONDS))
        for chunk_index, duration in enumerate(durations, start=1):
            chunk_id = f"{shot_id}_{chunk_index:02d}"
            continuity = (
                f" This is continuous segment {chunk_index} of {len(durations)} for the same shot; "
                "preserve cast identity, wardrobe, location, light, camera axis, and motion."
            )
            chunks.append(
                RenderChunk(
                    chunk_id=chunk_id,
                    shot_id=shot_id,
                    index=chunk_index,
                    count=len(durations),
                    duration_seconds=duration,
                    prompt=(str(job.get("prompt") or "Photorealistic cinematic scene") + continuity)[:1000],
                    negative_prompt=str(job.get("negative_prompt") or "")[:1000],
                    output_file=clip_root / f"{job_number:04d}_{chunk_index:02d}_{shot_id}.mp4",
                )
            )
    return chunks


def _load_checkpoint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "chunks": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": 1, "chunks": {}}
    if not isinstance(data, dict) or not isinstance(data.get("chunks"), dict):
        return {"schema_version": 1, "chunks": {}}
    return data


def _save_checkpoint(path: Path, checkpoint: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def _download_https(url: str, destination: Path, timeout_seconds: int) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise RunwayRenderError("Runway returned a non-HTTPS output URL.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = Request(url, headers={"User-Agent": "Canri-Movie-Brain/1.0"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    if temporary.stat().st_size < 10_000:
        temporary.unlink(missing_ok=True)
        raise RunwayRenderError("Downloaded video is unexpectedly small.")
    os.replace(temporary, destination)


def _concat_escape(path: Path) -> str:
    return str(path.resolve()).replace("'", "'\\''").replace("\\", "/")


def assemble_mp4(clips: Iterable[Path], output_file: Path) -> Path:
    clip_paths = [Path(path).resolve() for path in clips]
    if not clip_paths or not all(path.is_file() for path in clip_paths):
        raise RunwayRenderError("Cannot assemble the movie because one or more generated clips are missing.")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RunwayRenderError("FFmpeg is required to assemble the generated shots.")
    output_file = Path(output_file).resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".ffconcat", encoding="utf-8", delete=False, dir=output_file.parent
    ) as handle:
        concat_path = Path(handle.name)
        handle.write("ffconcat version 1.0\n")
        for clip in clip_paths:
            handle.write(f"file '{_concat_escape(clip)}'\n")
    command = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_path),
        "-vf",
        "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-movflags",
        "+faststart",
        str(output_file),
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=60 * 60, check=False)
    finally:
        concat_path.unlink(missing_ok=True)
    if completed.returncode != 0 or not output_file.is_file() or output_file.stat().st_size < 10_000:
        message = completed.stderr[-2000:] if completed.stderr else "unknown FFmpeg failure"
        raise RunwayRenderError(f"FFmpeg could not assemble the generated movie: {message}")
    return output_file


class RunwayMovieBackend:
    """Generate every planned shot through Runway and assemble a local MP4."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "gen4.5",
        ratio: str = "1280:720",
        max_cost_usd: float | None = None,
        task_timeout_seconds: int = 20 * 60,
        download_timeout_seconds: int = 10 * 60,
    ):
        self.api_key = api_key or os.getenv("RUNWAYML_API_SECRET", "").strip()
        self.model = model
        self.ratio = ratio
        self.max_cost_usd = max_cost_usd
        self.task_timeout_seconds = max(60, int(task_timeout_seconds))
        self.download_timeout_seconds = max(60, int(download_timeout_seconds))

    def _client(self):
        if not self.api_key:
            raise RunwayRenderError(
                "RUNWAYML_API_SECRET is not configured. Store the key in the environment, never in the project."
            )
        try:
            from runwayml import RunwayML
        except ImportError as error:
            raise RunwayRenderError("Install the official SDK with: python -m pip install runwayml") from error
        return RunwayML(api_key=self.api_key)

    def __call__(self, project: dict[str, Any]) -> dict[str, Any]:
        output_root = _project_output_directory(project)
        chunks = build_render_chunks(project, output_root)
        planned_seconds = sum(chunk.duration_seconds for chunk in chunks)
        estimate = estimate_runway_cost(planned_seconds, self.model)
        if self.max_cost_usd is None:
            raise RunwayRenderError(
                f"Rendering requires an explicit cost ceiling. Estimated base cost: ${estimate['estimated_usd']:.2f}."
            )
        if estimate["estimated_usd"] > float(self.max_cost_usd):
            raise RunwayRenderError(
                f"Estimated base cost ${estimate['estimated_usd']:.2f} exceeds the configured ceiling "
                f"${float(self.max_cost_usd):.2f}."
            )

        client = self._client()
        checkpoint_path = output_root / "runway_render_checkpoint.json"
        checkpoint = _load_checkpoint(checkpoint_path)
        generated_files: list[Path] = []
        for chunk in chunks:
            previous = checkpoint["chunks"].get(chunk.chunk_id, {})
            if previous.get("status") == "downloaded" and chunk.output_file.is_file():
                generated_files.append(chunk.output_file)
                continue

            seed = int(hashlib.sha256(chunk.chunk_id.encode("utf-8")).hexdigest()[:8], 16)
            try:
                from runwayml import omit

                task = client.image_to_video.create(
                    model=self.model,
                    prompt_image=omit,
                    prompt_text=chunk.prompt,
                    negative_prompt=chunk.negative_prompt,
                    ratio=self.ratio,
                    duration=chunk.duration_seconds,
                    seed=seed,
                ).wait_for_task_output(timeout=self.task_timeout_seconds)
                urls = list(getattr(task, "output", None) or [])
                if not urls:
                    raise RunwayRenderError(f"Runway task for {chunk.chunk_id} returned no output URL.")
                _download_https(str(urls[0]), chunk.output_file, self.download_timeout_seconds)
            except Exception as error:
                checkpoint["chunks"][chunk.chunk_id] = {
                    "status": "failed",
                    "error": f"{type(error).__name__}: {error}",
                }
                _save_checkpoint(checkpoint_path, checkpoint)
                raise

            checkpoint["chunks"][chunk.chunk_id] = {
                "status": "downloaded",
                "task_id": str(getattr(task, "id", "")),
                "duration_seconds": chunk.duration_seconds,
                "output_file": str(chunk.output_file),
            }
            _save_checkpoint(checkpoint_path, checkpoint)
            generated_files.append(chunk.output_file)

        assembly = project.get("render_manifest", {}).get("assembly", {})
        target = Path(assembly.get("viewing_copy") or output_root / "runway_photorealistic_movie.mp4")
        master = assemble_mp4(generated_files, target)
        return {
            "provider": "runway",
            "model": self.model,
            "rendered": True,
            "verified_output": True,
            "output_file": str(master),
            "generated_chunks": len(generated_files),
            "checkpoint_file": str(checkpoint_path),
            "cost_estimate": estimate,
        }


def backend_from_payload(payload: dict[str, Any]) -> RunwayMovieBackend:
    return RunwayMovieBackend(
        model=str(payload.get("movie_render_model") or "gen4.5"),
        ratio=str(payload.get("movie_render_ratio") or "1280:720"),
        max_cost_usd=payload.get("movie_render_budget_usd"),
        task_timeout_seconds=int(payload.get("movie_render_task_timeout_seconds") or 20 * 60),
        download_timeout_seconds=int(payload.get("movie_render_download_timeout_seconds") or 10 * 60),
    )
