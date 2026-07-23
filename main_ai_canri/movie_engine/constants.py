"""Shared limits and defaults for movie production."""

MAX_MOVIE_SECONDS = 5 * 60 * 60
MIN_MOVIE_SECONDS = 30
DEFAULT_MOVIE_SECONDS = 90 * 60
DEFAULT_SCENE_SECONDS = 180
MIN_SCENE_SECONDS = 45
MAX_SCENE_SECONDS = 420
DEFAULT_SHOT_SECONDS = 12
MIN_SHOT_SECONDS = 2
MAX_SHOT_SECONDS = 30
MAX_SCENES = 140
MAX_SHOTS = 2400
MAX_CONTEXT_ITEMS = 80
SUPPORTED_ASPECT_RATIOS = {"16:9", "2.39:1", "1.85:1", "4:3", "9:16"}
SUPPORTED_FRAME_RATES = {23.976, 24.0, 25.0, 30.0, 48.0, 60.0}

ACT_WEIGHTS = (0.25, 0.50, 0.25)
ACT_NAMES = ("Setup", "Confrontation", "Resolution")

DEFAULT_RENDER_PROFILE = {
    "resolution": "3840x2160",
    "frame_rate": 24.0,
    "aspect_ratio": "2.39:1",
    "color_space": "ACEScg",
    "delivery_codec": "ProRes 422 HQ",
    "audio_layout": "5.1",
}
