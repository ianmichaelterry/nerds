"""
Render: composites a movie poster image from blackboard items using PIL.

Reads typed items off the blackboard and paints them into a poster-sized
image. This is deliberately crude -- the caricature's visual output is
itself a caricature of a movie poster.
"""

from __future__ import annotations
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from blackboard import Blackboard


# Poster dimensions (2:3 aspect ratio like real posters)
POSTER_W = 600
POSTER_H = 900


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to load a system font, fall back to default."""
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Courier New.ttf",
    ]
    if bold:
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ] + candidates
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def render_poster(bb: Blackboard, output_path: Path) -> Path:
    """Read the blackboard and compose a poster image."""

    # Gather items
    palette_item = bb.pick("ColorPalette")
    title_item = bb.pick("TitleChunks")
    layout_item = bb.pick("Layout")
    hero_item = bb.pick("HeroImage")
    movie_item = bb.pick("MovieData")
    typeface_item = bb.pick("Typeface")
    effect_item = bb.pick("PostEffect")

    # Defaults
    key_color = palette_item.value["key"] if palette_item else (30, 30, 40)
    accent_color = palette_item.value["accent"] if palette_item else (200, 80, 60)
    layout = layout_item.value if layout_item else {
        "title_y": 0.10, "title_align": "center",
        "image_y": 0.20, "image_h": 0.50,
        "tagline_y": 0.75, "credits_y": 0.88,
    }

    # Create base image with key color
    img = Image.new("RGB", (POSTER_W, POSTER_H), key_color)
    draw = ImageDraw.Draw(img)

    # --- Hero image: paint colored blocks ---
    if hero_item:
        img_y = int(layout["image_y"] * POSTER_H)
        img_h = int(layout["image_h"] * POSTER_H)
        for block in hero_item.value["blocks"]:
            bx = int(block["x"] * POSTER_W)
            by = img_y + int(block["y"] * img_h)
            bw = int(block["w"] * POSTER_W)
            bh = int(block["h"] * img_h)
            draw.rectangle([bx, by, bx + bw, by + bh], fill=block["color"])

    # --- Title ---
    if title_item:
        primary = title_item.value["primary"].upper()
        secondary = title_item.value.get("secondary", "").upper()
        title_y = int(layout["title_y"] * POSTER_H)

        # Primary title -- big
        font_big = _get_font(54, bold=True)
        font_small = _get_font(28)

        # Measure and position
        bbox = draw.textbbox((0, 0), primary, font=font_big)
        tw = bbox[2] - bbox[0]
        if layout["title_align"] == "center":
            tx = (POSTER_W - tw) // 2
        else:
            tx = 40

        draw.text((tx, title_y), primary, fill=accent_color, font=font_big)

        if secondary:
            bbox2 = draw.textbbox((0, 0), secondary, font=font_small)
            tw2 = bbox2[2] - bbox2[0]
            if layout["title_align"] == "center":
                tx2 = (POSTER_W - tw2) // 2
            else:
                tx2 = 40
            draw.text((tx2, title_y + 60), secondary, fill=accent_color, font=font_small)

    # --- Tagline ---
    if movie_item:
        tagline = movie_item.value.get("tagline", "")
        if tagline:
            font_tag = _get_font(18)
            tag_y = int(layout["tagline_y"] * POSTER_H)
            bbox = draw.textbbox((0, 0), tagline, font=font_tag)
            tw = bbox[2] - bbox[0]
            tx = (POSTER_W - tw) // 2
            # Slightly dimmer version of accent
            tag_color = tuple(max(0, c - 40) for c in accent_color)
            draw.text((tx, tag_y), tagline, fill=tag_color, font=font_tag)

    # --- Credits line ---
    if movie_item:
        credits_y = int(layout["credits_y"] * POSTER_H)
        director = movie_item.value.get("director", "")
        actors = movie_item.value.get("actors", [])
        credit_text = f"A film by {director}"
        if actors:
            credit_text += "  |  " + "  ".join(actors[:3])
        font_credits = _get_font(12)
        bbox = draw.textbbox((0, 0), credit_text, font=font_credits)
        tw = bbox[2] - bbox[0]
        tx = (POSTER_W - tw) // 2
        # Credits in a muted tone
        credit_color = tuple(min(255, c + 60) for c in key_color)
        draw.text((tx, credits_y), credit_text, fill=credit_color, font=font_credits)

    # --- Decorative line separator ---
    sep_y = int(layout["tagline_y"] * POSTER_H) - 15
    draw.line([(80, sep_y), (POSTER_W - 80, sep_y)], fill=accent_color, width=1)

    # --- Post effects ---
    if effect_item:
        effects = effect_item.value.get("effects", [])
        if "grain" in effects:
            img = _apply_grain(img)
        if "vignette" in effects:
            img = _apply_vignette(img)
        if "posterize" in effects:
            img = _apply_posterize(img)

    img.save(output_path)
    return output_path


def _apply_grain(img: Image.Image) -> Image.Image:
    """Add film grain noise."""
    import numpy as np
    arr = np.array(img, dtype=np.int16)
    noise = np.random.normal(0, 12, arr.shape).astype(np.int16)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def _apply_vignette(img: Image.Image) -> Image.Image:
    """Darken the edges."""
    import numpy as np
    arr = np.array(img, dtype=np.float32)
    h, w = arr.shape[:2]
    Y, X = np.ogrid[:h, :w]
    cy, cx = h / 2, w / 2
    radius = max(cy, cx) * 1.2
    dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    vignette = 1.0 - np.clip(dist / radius, 0, 1) ** 2 * 0.6
    arr *= vignette[:, :, np.newaxis]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def _apply_posterize(img: Image.Image) -> Image.Image:
    """Reduce color depth."""
    import numpy as np
    arr = np.array(img)
    levels = random.choice([3, 4, 5])
    factor = 256 // levels
    arr = (arr // factor) * factor
    return Image.fromarray(arr)
