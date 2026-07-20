"""
Image_brain.py
Canri AI

Image_brain creates image-generation prompts and safe local SVG previews.
It does not call external image APIs. If a real raster/image model is added
later, this brain already returns the structured prompt, safety, style, and
composition data that model should use.
"""

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from Brain_storage import atomic_write_json, load_json_resilient


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "generated_images"

STYLE_FILE = DATA_DIR / "Image_styles.json"
SUBJECT_FILE = DATA_DIR / "Image_subject_templates.json"
COMPOSITION_FILE = DATA_DIR / "Image_composition_rules.json"
PROMPT_FILE = DATA_DIR / "Image_prompt_templates.json"
SAFETY_FILE = DATA_DIR / "Image_safety_rules.json"
STATS_FILE = DATA_DIR / "Image_statistics.json"
HISTORY_FILE = DATA_DIR / "Image_history.json"
PROFILES_FILE = DATA_DIR / "Image_generation_profiles.json"


GENERIC_IMAGE_WORDS = {
    "image", "picture", "photo", "art", "drawing", "draw", "make",
    "create", "generate", "please", "me", "for", "of", "with", "and",
    "a", "an", "the", "in", "on", "style", "look", "visual",
    "image_generation", "vision", "planning", "request", "en", "he",
    "creative", "general", "question"
}


class ImageBrain:

    def __init__(self):

        self.styles = self.load_json(STYLE_FILE, {})
        self.subject_templates = self.load_json(SUBJECT_FILE, {})
        self.composition_rules = self.load_json(COMPOSITION_FILE, {})
        self.prompt_templates = self.load_json(PROMPT_FILE, {})
        self.safety_rules = self.load_json(SAFETY_FILE, {})
        self.statistics = self.load_json(STATS_FILE, {})
        self.history = self.load_json(HISTORY_FILE, [])
        self.generation_profiles = self.load_json(PROFILES_FILE, [])

        print("Image Brain Loaded")

    # ---------- file helpers ----------

    def load_json(self, path, default):

        if not path.exists():
            return default

        return load_json_resilient(path, default)

    def save_json(self, path, data):

        atomic_write_json(path, data)

    def save_statistics(self):

        self.save_json(STATS_FILE, self.statistics)

    def save_history(self):

        self.save_json(HISTORY_FILE, self.history[-200:])

    # ---------- context ----------

    def get_understanding_report(self, data):

        if not isinstance(data, dict):
            return {}

        understanding = data.get("understanding")
        if isinstance(understanding, dict):
            return understanding

        if "main_topic" in data or "intent" in data or "words" in data:
            return data

        return {}

    def get_memory_report(self, data):

        if isinstance(data, dict) and isinstance(data.get("memory"), dict):
            return data["memory"]

        return {}

    def extract_text(self, data, report):

        parts = []
        seen = set()

        def add_part(value):
            value = str(value or "").strip()
            if not value:
                return
            key = value.lower()
            if key in seen:
                return
            seen.add(key)
            parts.append(value)

        if isinstance(data, str):
            add_part(data)

        if isinstance(data, dict):
            for key in [
                "original_text",
                "corrected_text",
                "user_message",
                "prompt",
                "text",
                "query",
                "goal"
            ]:
                value = data.get(key)
                if value:
                    add_part(value)

        for key in ["original_text", "corrected_text"]:
            value = report.get(key)
            if value:
                add_part(value)

        return " ".join(parts).strip()

    def collect_terms(self, text, report, memory_report, raw_text=None):

        terms = []
        lowered = text.lower()
        raw_text = str(raw_text or text or "")
        raw_lowered = raw_text.lower()

        for term in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", raw_lowered):
            terms.append(term)

        def from_original(value):
            value = str(value or "").lower().strip()
            return not raw_lowered or value in raw_lowered

        semantic_frame = report.get("semantic_frame", {})
        if isinstance(semantic_frame, dict):
            for key in ["main_target", "subject"]:
                value = semantic_frame.get(key)
                if value and from_original(value):
                    terms.append(str(value).lower())
            for key in ["targets", "modifiers"]:
                values = semantic_frame.get(key, [])
                if isinstance(values, list):
                    terms.extend(
                        str(value).lower()
                        for value in values[:30]
                        if from_original(value)
                    )

        for tag in report.get("advanced_word_tags", [])[:80]:
            if not isinstance(tag, dict):
                continue
            word = tag.get("word")
            semantic_tag = tag.get("semantic_tag")
            if word and from_original(word) and semantic_tag in {
                "target_or_concept",
                "proper_or_technical_name",
                "description",
                "action_modifier"
            }:
                terms.append(str(word).lower())

        for key in ["features"]:
            values = report.get(key, [])
            if isinstance(values, list):
                terms.extend(str(value).lower() for value in values[:30])

        for keyword in memory_report.get("current_keywords", [])[:20]:
            if from_original(keyword):
                terms.append(str(keyword).lower())

        if not raw_lowered:
            terms.extend(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", lowered))

        clean = []
        for term in terms:
            term = re.sub(r"[^a-zA-Z0-9_ -]", " ", str(term).lower())
            term = re.sub(r"\s+", " ", term).strip()
            if term and term not in GENERIC_IMAGE_WORDS and term not in clean:
                clean.append(term)

        return clean[:80]

    # ---------- safety ----------

    def safety_check(self, text):

        lowered = text.lower()
        warnings = []
        blocked = []
        score = 100

        for rule in self.safety_rules.get("blocked", []):
            name = rule.get("name", "blocked_rule")
            terms = rule.get("terms", [])
            if any(term.lower() in lowered for term in terms):
                blocked.append(name)
                score = min(score, int(rule.get("score", 0)))

        for rule in self.safety_rules.get("warn", []):
            name = rule.get("name", "warning_rule")
            terms = rule.get("terms", [])
            if any(term.lower() in lowered for term in terms):
                warnings.append(name)
                score = min(score, int(rule.get("score", 70)))

        return {
            "safe": not blocked,
            "blocked": blocked,
            "warnings": warnings,
            "score": score
        }

    # ---------- image planning ----------

    def choose_style(self, text, terms):

        lowered = text.lower()

        for style_id, style in self.styles.items():
            keywords = style.get("keywords", [])
            if any(keyword.lower() in lowered for keyword in keywords):
                return style_id, style

        if any(term in terms for term in ["game", "sprite", "pixel"]):
            return "pixel_game", self.styles.get("pixel_game", {})

        if any(term in terms for term in ["logo", "brand", "icon"]):
            return "clean_logo", self.styles.get("clean_logo", {})

        return "cinematic_illustration", self.styles.get("cinematic_illustration", {})

    def choose_subject(self, text, terms):

        lowered = text.lower()
        best = None
        priority = {
            "logo": 90,
            "robot": 80,
            "character": 70,
            "creature": 65,
            "city": 55,
            "architecture": 50,
            "space": 45,
            "nature": 40,
            "general_scene": 0
        }

        for subject_id, template in self.subject_templates.items():
            keywords = template.get("keywords", [])
            hits = sum(1 for keyword in keywords if keyword.lower() in lowered)
            if hits:
                score = hits * 100 + priority.get(subject_id, 10)
                if best is None or score > best[0]:
                    best = (score, subject_id, template)

        if best:
            _, subject_id, template = best
            subject_terms = [
                term
                for term in terms
                if term not in GENERIC_IMAGE_WORDS
            ][:10]
            return subject_id, template, subject_terms

        subject_terms = [
            term
            for term in terms
            if term not in GENERIC_IMAGE_WORDS
        ][:10]

        if not subject_terms:
            subject_terms = ["original scene"]

        return "general_scene", self.subject_templates.get("general_scene", {}), subject_terms

    def choose_composition(self, text, subject_id):

        lowered = text.lower()

        if "poster" in lowered:
            return "poster", self.composition_rules.get("poster", {})
        if "icon" in lowered or "logo" in lowered:
            return "centered_icon", self.composition_rules.get("centered_icon", {})
        if "wide" in lowered or "landscape" in lowered:
            return "wide_scene", self.composition_rules.get("wide_scene", {})
        if subject_id in {"character", "creature", "robot"}:
            return "character_focus", self.composition_rules.get("character_focus", {})

        return "balanced_scene", self.composition_rules.get("balanced_scene", {})

    def parse_request_spec(self, text):

        lowered = str(text or "").lower()
        dimensions = re.search(r"\b(\d{2,5})\s*[x×]\s*(\d{2,5})\b", lowered)
        width = int(dimensions.group(1)) if dimensions else None
        height = int(dimensions.group(2)) if dimensions else None

        aspect_ratio = "4:3"
        if "16:9" in lowered or any(word in lowered for word in ["widescreen", "wide landscape"]):
            aspect_ratio = "16:9"
        elif "9:16" in lowered or any(word in lowered for word in ["phone wallpaper", "vertical poster"]):
            aspect_ratio = "9:16"
        elif "1:1" in lowered or "square" in lowered:
            aspect_ratio = "1:1"
        elif "3:2" in lowered:
            aspect_ratio = "3:2"
        elif "2:3" in lowered or "portrait" in lowered:
            aspect_ratio = "2:3"

        if width and height:
            aspect_ratio = f"{width}:{height}"
        elif aspect_ratio == "16:9":
            width, height = 1280, 720
        elif aspect_ratio == "9:16":
            width, height = 720, 1280
        elif aspect_ratio == "1:1":
            width, height = 1024, 1024
        elif aspect_ratio == "2:3":
            width, height = 800, 1200

        groups = {
            "lighting": ["soft light", "studio light", "golden hour", "moonlight", "neon", "dramatic lighting"],
            "camera": ["close-up", "wide shot", "top-down", "low angle", "eye level", "macro"],
            "mood": ["calm", "friendly", "mysterious", "dramatic", "joyful", "dark", "hopeful"],
            "medium": ["photo", "photorealistic", "illustration", "watercolor", "oil painting", "pixel art", "3d render", "vector"],
            "purpose": ["logo", "poster", "icon", "game sprite", "wallpaper", "book cover", "concept art"]
        }
        detected = {
            name: [term for term in values if term in lowered]
            for name, values in groups.items()
        }
        colors = re.findall(
            r"\b(?:red|blue|green|yellow|orange|purple|pink|black|white|gray|grey|gold|silver|cyan|magenta)\b",
            lowered
        )
        text_match = re.search(
            r'(?:text|title|words?)\s*[:=]\s*[\"\']([^\"\']+)',
            str(text or ""),
            re.IGNORECASE
        )

        return {
            "aspect_ratio": aspect_ratio,
            "width": width,
            "height": height,
            "lighting": detected["lighting"],
            "camera": detected["camera"],
            "mood": detected["mood"],
            "medium": detected["medium"],
            "purpose": detected["purpose"],
            "colors": list(dict.fromkeys(colors))[:6],
            "required_text": text_match.group(1).strip() if text_match else None,
            "detail_coverage": sum(bool(value) for value in detected.values()) + bool(colors) + bool(dimensions)
        }

    def build_prompt(self, text, subject_id, subject_template, subject_terms, style_id, style, composition_id, composition):

        prompt_template = self.prompt_templates.get(
            "default",
            "{subject}, {style}, {composition}, high detail"
        )
        subject_text = ", ".join(subject_terms) if subject_terms else subject_template.get("name", subject_id)
        style_text = style.get("prompt", style_id.replace("_", " "))
        composition_text = composition.get("prompt", composition_id.replace("_", " "))
        quality = self.prompt_templates.get("quality_suffix", "")

        prompt = prompt_template.format(
            subject=subject_text,
            style=style_text,
            composition=composition_text,
            request=text
        )

        if quality:
            prompt = f"{prompt}, {quality}"

        detail_pack = [
            "clear main subject",
            "coherent lighting",
            "balanced composition",
            "professional finish"
        ]

        if subject_id in {"character", "robot", "creature"}:
            detail_pack.extend(["expressive pose", "readable silhouette", "appealing design"])
        if composition_id in {"poster", "centered_icon"}:
            detail_pack.extend(["clean negative space", "strong focal point"])

        prompt = f"{prompt}, {', '.join(detail_pack)}"

        negative_prompt = self.prompt_templates.get(
            "negative_prompt",
            "low quality, blurry, distorted, extra text, watermark"
        )

        return prompt, negative_prompt

    def prompt_quality_report(self, prompt, subject_terms, style_id, composition_id):

        score = 50
        checks = []

        if subject_terms:
            score += 15
            checks.append("subject_terms_present")
        if style_id:
            score += 10
            checks.append("style_selected")
        if composition_id:
            score += 10
            checks.append("composition_selected")
        if len(prompt.split(",")) >= 5:
            score += 10
            checks.append("rich_prompt")
        if "low quality" not in prompt.lower():
            score += 5

        return {
            "score": min(score, 100),
            "checks": checks,
            "needs_real_image_model": True,
            "note": "Image_brain builds a strong prompt and SVG preview; photoreal raster generation needs an image model."
        }

    # ---------- local SVG preview ----------

    def safe_filename(self, subject_terms):

        base = "_".join(subject_terms[:4]) or "image"
        base = re.sub(r"[^a-zA-Z0-9_-]+", "_", base).strip("_").lower()
        if not base:
            base = "image"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"canri_{base}_{stamp}.svg"

    def svg_palette(self, style):

        palette = style.get("palette") or ["#111827", "#2563eb", "#f8fafc", "#f59e0b"]
        while len(palette) < 4:
            palette.append(palette[-1])
        return palette[:4]

    def svg_scene_markup(self, subject_id, subject_terms, palette):

        p0, p1, p2, p3 = palette
        subject = " ".join(subject_terms).lower()
        label = html.escape(" ".join(subject_terms[:5]).title() or "Canri Image")

        if subject_id in {"city", "architecture"} or "city" in subject:
            return f'''
  <rect x="80" y="370" width="90" height="170" fill="{p0}" opacity="0.92"/>
  <rect x="190" y="300" width="120" height="240" fill="{p1}" opacity="0.86"/>
  <rect x="330" y="250" width="160" height="290" fill="{p0}" opacity="0.88"/>
  <rect x="520" y="330" width="110" height="210" fill="{p1}" opacity="0.82"/>
  <path d="M0 545 C160 510 280 575 430 530 C560 495 700 530 800 500 L800 600 L0 600 Z" fill="{p3}" opacity="0.45"/>
  <text x="400" y="105" text-anchor="middle" class="title">{label}</text>'''

        if subject_id in {"nature", "forest"} or any(term in subject for term in ["forest", "tree", "park"]):
            return f'''
  <circle cx="650" cy="105" r="52" fill="{p3}" opacity="0.9"/>
  <path d="M0 520 C160 430 290 560 430 475 C560 395 665 480 800 410 L800 600 L0 600 Z" fill="{p1}" opacity="0.55"/>
  <path d="M160 520 L240 250 L320 520 Z" fill="{p0}" opacity="0.9"/>
  <path d="M300 535 L405 205 L510 535 Z" fill="{p0}" opacity="0.82"/>
  <path d="M485 530 L585 280 L690 530 Z" fill="{p0}" opacity="0.78"/>
  <text x="400" y="105" text-anchor="middle" class="title">{label}</text>'''

        if subject_id in {"character", "person", "hero"} or any(term in subject for term in ["boy", "girl", "hero", "character"]):
            return f'''
  <ellipse cx="400" cy="520" rx="230" ry="38" fill="{p0}" opacity="0.25"/>
  <circle cx="400" cy="210" r="78" fill="{p2}" opacity="0.96"/>
  <path d="M315 485 C330 340 470 340 485 485 Z" fill="{p1}" opacity="0.92"/>
  <path d="M335 325 C370 360 430 360 465 325" fill="none" stroke="{p3}" stroke-width="14" stroke-linecap="round"/>
  <circle cx="374" cy="200" r="8" fill="{p0}"/>
  <circle cx="426" cy="200" r="8" fill="{p0}"/>
  <text x="400" y="92" text-anchor="middle" class="title">{label}</text>'''

        if subject_id == "robot" or "robot" in subject:
            return f'''
  <ellipse cx="400" cy="520" rx="240" ry="34" fill="{p0}" opacity="0.25"/>
  <rect x="275" y="210" width="250" height="210" rx="42" fill="{p2}" opacity="0.94"/>
  <rect x="315" y="248" width="170" height="74" rx="24" fill="{p0}" opacity="0.88"/>
  <circle cx="365" cy="285" r="16" fill="{p3}"/>
  <circle cx="435" cy="285" r="16" fill="{p3}"/>
  <path d="M350 350 C380 378 420 378 450 350" fill="none" stroke="{p1}" stroke-width="11" stroke-linecap="round"/>
  <path d="M275 285 L215 240" stroke="{p2}" stroke-width="24" stroke-linecap="round"/>
  <path d="M525 285 L585 240" stroke="{p2}" stroke-width="24" stroke-linecap="round"/>
  <circle cx="205" cy="233" r="22" fill="{p3}"/>
  <circle cx="595" cy="233" r="22" fill="{p3}"/>
  <path d="M360 210 L335 155" stroke="{p2}" stroke-width="12" stroke-linecap="round"/>
  <circle cx="330" cy="145" r="16" fill="{p3}"/>
  <text x="400" y="105" text-anchor="middle" class="title">{label}</text>'''

        if subject_id == "space" or any(term in subject for term in ["space", "planet", "star", "galaxy"]):
            return f'''
  <circle cx="600" cy="175" r="86" fill="{p3}" opacity="0.92"/>
  <circle cx="565" cy="145" r="20" fill="{p2}" opacity="0.25"/>
  <circle cx="625" cy="210" r="13" fill="{p2}" opacity="0.25"/>
  <path d="M175 430 C295 340 500 505 700 365" fill="none" stroke="{p2}" stroke-width="3" opacity="0.65"/>
  <circle cx="150" cy="120" r="4" fill="{p2}"/>
  <circle cx="250" cy="220" r="3" fill="{p2}"/>
  <circle cx="360" cy="125" r="5" fill="{p2}"/>
  <circle cx="490" cy="290" r="3" fill="{p2}"/>
  <text x="400" y="535" text-anchor="middle" class="title">{label}</text>'''

        if subject_id == "logo" or any(term in subject for term in ["logo", "icon", "brand"]):
            return f'''
  <circle cx="400" cy="300" r="155" fill="{p1}" opacity="0.94"/>
  <path d="M315 320 L380 205 L485 395 L430 395 L390 310 L350 395 L300 395 Z" fill="{p2}"/>
  <circle cx="400" cy="300" r="198" fill="none" stroke="{p3}" stroke-width="12" opacity="0.8"/>
  <text x="400" y="535" text-anchor="middle" class="title">{label}</text>'''

        return f'''
  <circle cx="605" cy="125" r="58" fill="{p3}" opacity="0.85"/>
  <path d="M110 440 C200 300 300 455 400 325 C510 180 610 340 720 260 L720 540 L110 540 Z" fill="{p1}" opacity="0.65"/>
  <rect x="230" y="230" width="340" height="225" rx="32" fill="{p2}" opacity="0.18" stroke="{p2}" stroke-width="3"/>
  <circle cx="400" cy="342" r="86" fill="{p1}" opacity="0.82"/>
  <path d="M350 360 C385 395 430 395 465 360" fill="none" stroke="{p3}" stroke-width="10" stroke-linecap="round"/>
  <text x="400" y="105" text-anchor="middle" class="title">{label}</text>'''

    def create_svg(self, subject_id, subject_terms, style, composition):

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        filename = self.safe_filename(subject_terms)
        path = OUTPUT_DIR / filename
        palette = self.svg_palette(style)
        p0, p1, p2, p3 = palette
        markup = self.svg_scene_markup(subject_id, subject_terms, palette)

        width = int(composition.get("width", 800))
        height = int(composition.get("height", 600))

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 800 600" role="img">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{p0}"/>
      <stop offset="55%" stop-color="{p1}"/>
      <stop offset="100%" stop-color="{p3}"/>
    </linearGradient>
    <style>
      .title {{
        display: none;
        font-family: Arial, sans-serif;
        font-size: 34px;
        font-weight: 700;
        fill: {p2};
        letter-spacing: 0;
      }}
    </style>
  </defs>
  <rect width="800" height="600" fill="url(#bg)"/>
  <circle cx="105" cy="105" r="140" fill="{p2}" opacity="0.08"/>
  <circle cx="715" cy="505" r="170" fill="{p2}" opacity="0.07"/>
{markup}
</svg>
'''

        path.write_text(svg, encoding="utf-8")
        return str(path)

    # ---------- statistics ----------

    def update_statistics(self, style_id, subject_id, safe):

        stats = self.statistics.get("Image_brain", {})
        stats["uses"] = stats.get("uses", 0) + 1
        stats["last_style"] = style_id
        stats["last_subject"] = subject_id
        stats["last_safe"] = safe
        stats["last_used_utc"] = datetime.now(timezone.utc).isoformat()
        self.statistics["Image_brain"] = stats
        self.save_statistics()

    # ---------- public ----------

    def process(self, data):

        report = self.get_understanding_report(data)
        memory_report = self.get_memory_report(data)
        text = self.extract_text(data, report)
        raw_text = ""
        if isinstance(data, dict):
            raw_text = data.get("original_text") or report.get("original_text") or text
        elif isinstance(data, str):
            raw_text = data
        terms = self.collect_terms(text, report, memory_report, raw_text)
        safety = self.safety_check(text)
        request_spec = self.parse_request_spec(raw_text or text)

        if not safety["safe"]:
            return {
                "brain": "Image_brain",
                "safe": False,
                "blocked": True,
                "safety": safety,
                "answer": "I cannot create that image request because it is unsafe.",
                "confidence": 96,
                "rules": [
                    "Block unsafe visual requests before prompt generation.",
                    "Do not create image files for blocked requests."
                ]
            }

        style_id, style = self.choose_style(text, terms)
        subject_id, subject_template, subject_terms = self.choose_subject(text, terms)
        composition_id, composition = self.choose_composition(text, subject_id)
        composition = dict(composition)
        if request_spec.get("width") and request_spec.get("height"):
            composition["width"] = request_spec["width"]
            composition["height"] = request_spec["height"]
        prompt_request = raw_text or text
        prompt, negative_prompt = self.build_prompt(
            prompt_request,
            subject_id,
            subject_template,
            subject_terms,
            style_id,
            style,
            composition_id,
            composition
        )
        visual_details = []
        for key in ["medium", "lighting", "camera", "mood", "colors", "purpose"]:
            visual_details.extend(request_spec.get(key, []))
        visual_details.append(f"aspect ratio {request_spec['aspect_ratio']}")
        if request_spec.get("required_text"):
            visual_details.append(f"exact readable text: {request_spec['required_text']}")
        prompt = f"{prompt}, {', '.join(visual_details)}"
        quality_report = self.prompt_quality_report(
            prompt,
            subject_terms,
            style_id,
            composition_id
        )
        image_file = self.create_svg(
            subject_id,
            subject_terms,
            style,
            composition
        )

        result = {
            "brain": "Image_brain",
            "safe": True,
            "mode": "image_generation",
            "image_file": image_file,
            "asset_type": "svg",
            "asset_created": bool(image_file and Path(image_file).exists()),
            "engine_status": {
                "local_svg_renderer": "available",
                "external_raster_model": "not_configured",
                "output_is_real_file": bool(image_file and Path(image_file).exists()),
                "limitation": "Canri created a real local SVG asset; photorealistic raster generation needs an external image model."
            },
            "generated_image_prompt": prompt,
            "negative_prompt": negative_prompt,
            "request_spec": request_spec,
            "style": {
                "id": style_id,
                "name": style.get("name", style_id),
                "palette": style.get("palette", [])
            },
            "subject": {
                "id": subject_id,
                "terms": subject_terms,
                "template": subject_template.get("name", subject_id)
            },
            "composition": {
                "id": composition_id,
                "name": composition.get("name", composition_id),
                "width": composition.get("width", 800),
                "height": composition.get("height", 600)
            },
            "quality_report": quality_report,
            "safety": safety,
            "confidence": max(82, quality_report["score"]),
            "answer": (
                "Created an SVG image preview.\n"
                f"File: {image_file}\n\n"
                "Image prompt:\n"
                f"{prompt}\n\n"
                "Negative prompt:\n"
                f"{negative_prompt}\n\n"
                f"Prompt quality: {quality_report['score']}/100"
            ),
            "rules": [
                "Use Understanding_brain semantic targets as the image subject.",
                "Create a professional prompt and a local SVG preview.",
                "Never call external image APIs from Image_brain.",
                "Run visual safety checks before generating assets."
            ],
            "data_files_used": [
                "Image_styles.json",
                "Image_subject_templates.json",
                "Image_composition_rules.json",
                "Image_prompt_templates.json",
                "Image_generation_profiles.json"
            ]
        }

        self.history.append({
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "request": text,
            "image_file": image_file,
            "style": style_id,
            "subject": subject_id,
            "safe": safety["safe"]
        })
        self.save_history()
        self.update_statistics(style_id, subject_id, safety["safe"])

        return result


brain = ImageBrain()
