"""
Render: composites a movie poster from RDF blackboard items using PIL.

Week 8 upgrades from week 7:
- Reads data from an RDF graph (via blackboard SPARQL-style queries)
- Composites Noun Project icons as the central visual element
- Multi-layer gradient backgrounds instead of flat color
- Better typography hierarchy: title, subtitle, tagline, credits
- Chromatic aberration post-effect for a cinematic look
- Decorative border and framing elements

The poster is still procedurally generated from blackboard state --
no LLM, no templates, just the nerds' accumulated contributions
read back from the graph.
"""

from __future__ import annotations
import base64
import random
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops, ImageEnhance

from blackboard import Blackboard
from vocabulary import NERDS, SCHEMA


# Poster dimensions (2:3 aspect ratio like real posters)
POSTER_W = 600
POSTER_H = 900


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    """Convert '#rrggbb' to (r, g, b) tuple."""
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _get_font(
    size: int, bold: bool = False
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to load a system font, fall back to default."""
    if bold:
        candidates = [
            # Linux
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            # macOS
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    else:
        candidates = [
            # Linux
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            # macOS
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default(size=size)


def _get_condensed_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to load a condensed/narrow font for credits block."""
    candidates = [
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraLight.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        # macOS
        "/System/Library/Fonts/Supplemental/Arial Narrow.ttf",
        "/System/Library/Fonts/Supplemental/Avenir Next Condensed.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default(size=size)


def _draw_gradient(
    img: Image.Image,
    y_start: int,
    y_end: int,
    color_top: tuple,
    color_bot: tuple,
    alpha: float = 1.0,
):
    """Draw a vertical gradient band on the image."""
    draw = ImageDraw.Draw(img)
    h = y_end - y_start
    if h <= 0:
        return
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(color_top[0] * (1 - t) + color_bot[0] * t)
        g = int(color_top[1] * (1 - t) + color_bot[1] * t)
        b = int(color_top[2] * (1 - t) + color_bot[2] * t)
        a = int(alpha * 255)
        draw.line([(0, y_start + y), (POSTER_W, y_start + y)], fill=(r, g, b))


def _draw_radial_gradient(
    img: Image.Image,
    center: tuple,
    radius: float,
    color_inner: tuple,
    color_outer: tuple,
):
    """Draw a radial gradient centered at a point."""
    arr = np.array(img, dtype=np.float32)
    h, w = arr.shape[:2]
    Y, X = np.ogrid[:h, :w]
    cx, cy = center
    dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    t = np.clip(dist / radius, 0, 1)
    for c in range(3):
        arr[:, :, c] = color_inner[c] * (1 - t) + color_outer[c] * t
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def render_poster(bb: Blackboard, output_path: Path, picks: dict | None = None) -> Path:
    """Read the RDF blackboard and compose a high-quality poster image.

    If *picks* is provided, its values override bb.pick() for individual
    item types.  Keys: 'palette', 'title', 'layout', 'hero', 'movie',
    'typeface', 'effect', 'icon'.
    """
    picks = picks or {}

    # --- Gather items from the RDF graph ---
    palette_node = picks.get("palette") or bb.pick(NERDS.ColorPalette)
    title_node = picks.get("title") or bb.pick(NERDS.TitleChunks)
    layout_node = picks.get("layout") or bb.pick(NERDS.Layout)
    hero_node = picks.get("hero") or bb.pick(NERDS.HeroImage)
    movie_node = picks.get("movie") or bb.pick(NERDS.MovieData)
    typeface_node = picks.get("typeface") or bb.pick(NERDS.Typeface)
    effect_node = picks.get("effect") or bb.pick(NERDS.PostEffect)
    icon_node = picks.get("icon") or bb.pick(NERDS.IconImage)
    composite_node = picks.get("composite") or bb.pick(NERDS.CompositeImage)

    # --- Extract values from RDF (with defaults) ---
    key_color = _hex_to_rgb(
        str(bb.get_property(palette_node, NERDS.keyColor) or "#1e1e28")
    )
    accent_color = _hex_to_rgb(
        str(bb.get_property(palette_node, NERDS.accentColor) or "#cc6644")
    )
    mid_color = _hex_to_rgb(
        str(bb.get_property(palette_node, NERDS.midColor) or "#755538")
    )

    layout = {}
    if layout_node:
        for prop, key, default in [
            (NERDS.titleY, "title_y", 0.10),
            (NERDS.titleAlign, "title_align", "center"),
            (NERDS.imageY, "image_y", 0.20),
            (NERDS.imageH, "image_h", 0.50),
            (NERDS.taglineY, "tagline_y", 0.75),
            (NERDS.creditsY, "credits_y", 0.88),
        ]:
            val = bb.get_property(layout_node, prop)
            layout[key] = (
                float(val)
                if val and key != "title_align"
                else (str(val) if val else default)
            )
    else:
        layout = {
            "title_y": 0.10,
            "title_align": "center",
            "image_y": 0.20,
            "image_h": 0.50,
            "tagline_y": 0.75,
            "credits_y": 0.88,
        }

    # --- Background: multi-layer gradient ---
    # Darker shade of key color for depth
    dark_key = tuple(max(0, c - 30) for c in key_color)
    lighter_key = tuple(min(255, c + 15) for c in key_color)

    img = Image.new("RGB", (POSTER_W, POSTER_H), key_color)
    # Top-to-bottom gradient: dark -> key -> slightly lighter
    _draw_gradient(img, 0, POSTER_H // 2, dark_key, key_color)
    _draw_gradient(img, POSTER_H // 2, POSTER_H, key_color, lighter_key)

    # Radial glow in the center for depth
    glow = _draw_radial_gradient(
        Image.new("RGB", (POSTER_W, POSTER_H), key_color),
        (POSTER_W // 2, int(POSTER_H * 0.4)),
        POSTER_W * 0.7,
        mid_color,
        dark_key,
    )
    # Blend the glow at ~30% opacity
    img = Image.blend(img, glow, 0.3)

    draw = ImageDraw.Draw(img)

    # --- Visual elements: composite takes precedence over separate hero/icon ---
    # If we have a composite, use it as the main visual; otherwise use hero+icon
    if composite_node:
        # Use composite as the primary visual element
        comp_path = str(bb.get_property(composite_node, NERDS.compositeImagePath) or "")
        if comp_path and Path(comp_path).exists():
            try:
                comp_img = Image.open(comp_path).convert("RGBA")
                comp_w, comp_h = comp_img.size

                target_w = POSTER_W - 40
                target_h = int(float(layout["image_h"]) * POSTER_H)

                scale = min(target_w / comp_w, target_h / comp_h, 1.0)
                if scale < 1.0:
                    new_w = int(comp_w * scale)
                    new_h = int(comp_h * scale)
                    comp_img = comp_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                cx = (POSTER_W - comp_img.width) // 2
                cy = (
                    int(float(layout["image_y"]) * POSTER_H)
                    + (target_h - comp_img.height) // 2
                )

                img_rgba = img.convert("RGBA")
                img_rgba.paste(comp_img, (cx, cy), comp_img)
                img = img_rgba.convert("RGB")
                draw = ImageDraw.Draw(img)
            except Exception as e:
                print(f"  [Render] Composite image failed: {e}")
    else:
        # No composite - use separate hero and icon
        # --- Hero image: color field blocks ---
        if hero_node:
            block_data_str = str(bb.get_property(hero_node, NERDS.blockData) or "")
            img_y = int(float(layout["image_y"]) * POSTER_H)
            img_h = int(float(layout["image_h"]) * POSTER_H)

            if block_data_str:
                overlay = Image.new("RGBA", (POSTER_W, POSTER_H), (0, 0, 0, 0))
                overlay_draw = ImageDraw.Draw(overlay)

                for block_str in block_data_str.split(";"):
                    parts = block_str.strip().split(",")
                    if len(parts) < 6:
                        continue
                    bx = int(float(parts[0]) * POSTER_W)
                    by = img_y + int(float(parts[1]) * img_h)
                    bw = int(float(parts[2]) * POSTER_W)
                    bh = int(float(parts[3]) * img_h)
                    color_hex = parts[4].strip()
                    opacity = float(parts[5])
                    r, g, b = _hex_to_rgb(color_hex)
                    a = int(opacity * 255)
                    overlay_draw.rectangle(
                        [bx, by, bx + bw, by + bh], fill=(r, g, b, a)
                    )

                img = img.convert("RGBA")
                img = Image.alpha_composite(img, overlay)
                img = img.convert("RGB")
                draw = ImageDraw.Draw(img)

        # --- Icon: composite the Noun Project icon ---
        if icon_node:
            icon_b64 = str(bb.get_property(icon_node, NERDS.iconPngBase64) or "")
            if icon_b64:
                try:
                    icon_bytes = base64.b64decode(icon_b64)
                    icon_img = Image.open(BytesIO(icon_bytes)).convert("RGBA")

                    icon_target_h = int(float(layout["image_h"]) * POSTER_H * 0.65)
                    icon_target_w = icon_target_h
                    icon_img = icon_img.resize(
                        (icon_target_w, icon_target_h), Image.Resampling.LANCZOS
                    )

                    icon_x = (POSTER_W - icon_target_w) // 2
                    icon_y = (
                        int(float(layout["image_y"]) * POSTER_H)
                        + (int(float(layout["image_h"]) * POSTER_H) - icon_target_h)
                        // 2
                    )

                    img_rgba = img.convert("RGBA")
                    img_rgba.paste(icon_img, (icon_x, icon_y), icon_img)
                    img = img_rgba.convert("RGB")
                    draw = ImageDraw.Draw(img)
                except Exception as e:
                    print(f"  [Render] Icon composite failed: {e}")

    # --- Title ---
    if title_node:
        primary = str(bb.get_property(title_node, NERDS.primaryTitle) or "").upper()
        secondary = str(bb.get_property(title_node, NERDS.secondaryTitle) or "").upper()
        title_y = int(float(layout["title_y"]) * POSTER_H)

        font_big = _get_font(52, bold=True)
        font_small = _get_font(26)

        primary_lines = primary.split("\n") if "\n" in primary else [primary]

        # Calculate spacing
        line_height = 55
        total_height = len(primary_lines) * line_height

        # Get width of widest line for centering
        max_width = 0
        for line in primary_lines:
            bbox = draw.textbbox((0, 0), line, font=font_big)
            max_width = max(max_width, bbox[2] - bbox[0])

        if layout["title_align"] == "center":
            tx = (POSTER_W - max_width) // 2
        else:
            tx = 40

        # Drop shadow for legibility
        shadow_offset = 2
        shadow_color = tuple(max(0, c - 60) for c in key_color)

        for i, line in enumerate(primary_lines):
            line_y = title_y + (i * line_height)
            draw.text(
                (tx + shadow_offset, line_y + shadow_offset),
                line,
                fill=shadow_color,
                font=font_big,
            )
            draw.text((tx, line_y), line, fill=accent_color, font=font_big)

        if secondary:
            bbox2 = draw.textbbox((0, 0), secondary, font=font_small)
            tw2 = bbox2[2] - bbox2[0]
            if layout["title_align"] == "center":
                tx2 = (POSTER_W - tw2) // 2
            else:
                tx2 = 40
            sub_y = title_y + total_height + 10
            sub_color = tuple(min(255, c + 30) for c in accent_color)
            draw.text((tx2, sub_y), secondary, fill=sub_color, font=font_small)

    # --- Decorative line separator ---
    sep_y = int(float(layout["tagline_y"]) * POSTER_H) - 18
    # Tapered line: thicker in center, fading at edges
    for x in range(60, POSTER_W - 60):
        t = abs(x - POSTER_W // 2) / (POSTER_W // 2 - 60)
        alpha = int((1 - t) * 180)
        draw.point((x, sep_y), fill=(*accent_color[:3],))

    # --- Tagline ---
    if movie_node:
        tagline = str(bb.get_property(movie_node, SCHEMA.description) or "")
        if tagline:
            font_tag = _get_font(16)
            tag_y = int(float(layout["tagline_y"]) * POSTER_H)
            bbox = draw.textbbox((0, 0), tagline, font=font_tag)
            tw = bbox[2] - bbox[0]
            tx = (POSTER_W - tw) // 2
            # Muted version of accent
            tag_color = tuple(max(0, min(255, c - 20)) for c in accent_color)
            draw.text((tx, tag_y), tagline, fill=tag_color, font=font_tag)

    # --- Credits block ---
    if movie_node:
        credits_y = int(float(layout["credits_y"]) * POSTER_H)
        director = str(bb.get_property(movie_node, SCHEMA.director) or "")
        actors_str = str(bb.get_property(movie_node, SCHEMA.actor) or "")
        year = bb.get_property(movie_node, SCHEMA.datePublished)

        font_credits = _get_condensed_font(11)
        font_credits_bold = _get_font(11, bold=True)

        # Director line
        if director:
            dir_text = f"A FILM BY {director.upper()}"
            bbox = draw.textbbox((0, 0), dir_text, font=font_credits_bold)
            tw = bbox[2] - bbox[0]
            tx = (POSTER_W - tw) // 2
            credit_color = tuple(min(255, c + 50) for c in key_color)
            draw.text(
                (tx, credits_y), dir_text, fill=credit_color, font=font_credits_bold
            )

        # Cast line
        if actors_str:
            actors = [a.strip().upper() for a in actors_str.split(",")][:4]
            cast_text = "  \u2022  ".join(actors)
            bbox = draw.textbbox((0, 0), cast_text, font=font_credits)
            tw = bbox[2] - bbox[0]
            tx = (POSTER_W - tw) // 2
            credit_color = tuple(min(255, c + 40) for c in key_color)
            draw.text(
                (tx, credits_y + 16), cast_text, fill=credit_color, font=font_credits
            )

        # Year
        if year:
            year_text = str(year)
            font_year = _get_font(10)
            bbox = draw.textbbox((0, 0), year_text, font=font_year)
            tw = bbox[2] - bbox[0]
            tx = (POSTER_W - tw) // 2
            year_color = tuple(min(255, c + 30) for c in key_color)
            draw.text((tx, credits_y + 34), year_text, fill=year_color, font=font_year)

    # --- Icon attribution (small, bottom) ---
    if icon_node:
        attr = str(bb.get_property(icon_node, NERDS.iconAttribution) or "")
        term = str(bb.get_property(icon_node, NERDS.iconTerm) or "")
        if term:
            font_attr = _get_font(8)
            attr_text = f'Icon: "{term}" from the Noun Project'
            bbox = draw.textbbox((0, 0), attr_text, font=font_attr)
            tw = bbox[2] - bbox[0]
            attr_color = tuple(min(255, c + 25) for c in key_color)
            draw.text(
                ((POSTER_W - tw) // 2, POSTER_H - 16),
                attr_text,
                fill=attr_color,
                font=font_attr,
            )

    # --- Thin border frame ---
    border_color = tuple(min(255, c + 20) for c in key_color)
    draw.rectangle([8, 8, POSTER_W - 9, POSTER_H - 9], outline=border_color, width=1)

    # --- Post effects ---
    if effect_node:
        effects_str = str(bb.get_property(effect_node, NERDS.effects) or "")
        effects = [e.strip() for e in effects_str.split(",") if e.strip()]
        if "grain" in effects:
            img = _apply_grain(img)
        if "vignette" in effects:
            img = _apply_vignette(img)
        if "posterize" in effects:
            img = _apply_posterize(img)
        if "chromatic_aberration" in effects:
            img = _apply_chromatic_aberration(img)

    img.save(output_path, quality=95)
    return output_path


# ---------------------------------------------------------------------------
# Post-processing effects
# ---------------------------------------------------------------------------


def _apply_grain(img: Image.Image) -> Image.Image:
    """Add subtle film grain noise."""
    arr = np.array(img, dtype=np.int16)
    noise = np.random.normal(0, 8, arr.shape).astype(np.int16)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def _apply_vignette(img: Image.Image) -> Image.Image:
    """Darken the edges with a smooth vignette."""
    arr = np.array(img, dtype=np.float32)
    h, w = arr.shape[:2]
    Y, X = np.ogrid[:h, :w]
    cy, cx = h / 2, w / 2
    radius = max(cy, cx) * 1.1
    dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    vignette = 1.0 - np.clip(dist / radius, 0, 1) ** 2.5 * 0.55
    arr *= vignette[:, :, np.newaxis]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def _apply_posterize(img: Image.Image) -> Image.Image:
    """Reduce color depth for a stylized look."""
    arr = np.array(img)
    levels = random.choice([4, 5, 6])
    factor = 256 // levels
    arr = (arr // factor) * factor
    return Image.fromarray(arr)


def _apply_chromatic_aberration(img: Image.Image) -> Image.Image:
    """Subtle RGB channel offset for a cinematic look."""
    arr = np.array(img)
    offset = 2  # pixels
    result = np.zeros_like(arr)
    # Shift red channel right, blue channel left
    result[:, offset:, 0] = arr[:, :-offset, 0]  # red shifts right
    result[:, :, 1] = arr[:, :, 1]  # green stays
    result[:, :-offset, 2] = arr[:, offset:, 2]  # blue shifts left
    # Fill edges
    result[:, :offset, 0] = arr[:, :offset, 0]
    result[:, -offset:, 2] = arr[:, -offset:, 2]
    return Image.fromarray(result)
