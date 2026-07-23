"""Create a real MP4 storyboard animatic with Pillow and FFmpeg."""

from __future__ import annotations

import shutil
import subprocess
import textwrap
from pathlib import Path
from typing import Any


def _font(size: int):
    from PIL import ImageFont

    for candidate in ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf"):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrapped_lines(text: str, width: int, limit: int = 5) -> list[str]:
    return textwrap.wrap(str(text or ""), width=max(width, 10))[:limit]


def _draw_card(path: Path, project: dict[str, Any], scene: dict[str, Any], shot: dict[str, Any], index: int) -> None:
    from PIL import Image, ImageDraw

    width, height = 1280, 720
    act = int(scene.get("act", 1))
    palettes = {
        1: ((12, 24, 42), (40, 92, 130)),
        2: ((24, 18, 38), (116, 56, 84)),
        3: ((26, 30, 26), (120, 92, 48)),
    }
    top, bottom = palettes.get(act, palettes[1])
    image = Image.new("RGB", (width, height), top)
    pixels = image.load()
    for y in range(height):
        blend = y / max(height - 1, 1)
        color = tuple(int(top[i] * (1 - blend) + bottom[i] * blend) for i in range(3))
        for x in range(width):
            pixels[x, y] = color

    draw = ImageDraw.Draw(image)
    title_font = _font(52)
    heading_font = _font(34)
    body_font = _font(25)
    small_font = _font(20)
    title = str(project.get("request", {}).get("title", "Canri Movie"))
    draw.rectangle((0, 0, width, 74), fill=(5, 8, 14))
    draw.text((44, 18), title, font=heading_font, fill=(245, 245, 240))
    draw.text((width - 210, 24), f"SHOT {index:03d}", font=small_font, fill=(190, 205, 220))

    draw.text((58, 118), str(scene.get("heading", "SCENE")), font=title_font, fill=(255, 226, 154))
    camera = (
        f"{shot.get('framing', '')} | {shot.get('lens_mm', '')}mm | "
        f"{shot.get('camera_move', '')} | {shot.get('duration_seconds', '')} sec"
    )
    draw.text((62, 195), camera, font=body_font, fill=(205, 220, 232))

    y = 270
    for line in _wrapped_lines(shot.get("action", ""), 68, limit=5):
        draw.text((70, y), line, font=body_font, fill=(248, 248, 245))
        y += 38
    y += 24
    for line in _wrapped_lines(scene.get("turning_point", ""), 72, limit=3):
        draw.text((70, y), line, font=body_font, fill=(224, 188, 130))
        y += 36

    draw.rectangle((0, height - 54, width, height), fill=(5, 8, 14))
    draw.text(
        (38, height - 38),
        "CANRI ANIMATIC PREVIEW - NOT THE PHOTOREALISTIC FINAL MASTER",
        font=small_font,
        fill=(185, 195, 205),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "JPEG", quality=90, optimize=True)


def _concat_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace("'", "'\\''")


def create_animatic(project: dict[str, Any]) -> dict[str, Any]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return {"created": False, "reason": "ffmpeg_not_found"}
    try:
        import PIL  # noqa: F401
    except ImportError:
        return {"created": False, "reason": "pillow_not_found"}

    manifest = project.get("render_manifest", {})
    assembly = manifest.get("assembly", {})
    output_file = Path(str(assembly.get("animatic_preview", "")))
    if not output_file.name:
        return {"created": False, "reason": "animatic_output_missing"}
    output_directory = output_file.parent
    cards_directory = output_directory / "animatic_cards"
    concat_file = output_directory / "animatic.ffconcat"
    scenes = {
        str(scene.get("scene_id")): scene
        for scene in project.get("scenes", [])
        if isinstance(scene, dict)
    }
    shots = [shot for shot in project.get("shots", []) if isinstance(shot, dict)]
    if not shots:
        return {"created": False, "reason": "no_shots"}

    output_directory.mkdir(parents=True, exist_ok=True)
    records = ["ffconcat version 1.0"]
    card_paths = []
    for index, shot in enumerate(shots, start=1):
        scene = scenes.get(str(shot.get("scene_id")), {})
        card = cards_directory / f"shot_{index:05d}.jpg"
        _draw_card(card, project, scene, shot, index)
        card_paths.append(card)
        records.append(f"file '{_concat_path(card)}'")
        records.append(f"duration {max(float(shot.get('duration_seconds', 1)), 0.1):.3f}")
    records.append(f"file '{_concat_path(card_paths[-1])}'")
    concat_file.write_text("\n".join(records) + "\n", encoding="utf-8")

    command = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-vsync",
        "vfr",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "24",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_file),
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=max(120, min(int(project.get("request", {}).get("duration_seconds", 0) * 2), 1800)),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {
            "created": False,
            "reason": "ffmpeg_execution_failed",
            "error": f"{type(error).__name__}: {error}",
        }
    created = completed.returncode == 0 and output_file.is_file() and output_file.stat().st_size > 0
    return {
        "created": created,
        "preview_file": str(output_file) if created else None,
        "format": "mp4",
        "preview_type": "storyboard_animatic",
        "photorealistic_final": False,
        "card_count": len(card_paths),
        "ffmpeg_return_code": completed.returncode,
        "error": None if created else completed.stderr[-2000:],
    }
