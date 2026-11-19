"""2x PNG Lineup Share Card generator replacing html-to-image.js in Team Builder v2."""

from __future__ import annotations

import io
from typing import Any

from PIL import Image, ImageDraw, ImageFont


def _hex_to_rgb(hx: str | None, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    if not hx or not hx.startswith("#") or len(hx) != 7:
        return fallback
    try:
        return int(hx[1:3], 16), int(hx[3:5], 16), int(hx[5:7], 16)
    except ValueError:
        return fallback


def generate_lineup_png(
    club_name: str,
    formation: str,
    primary_color: str,
    secondary_color: str,
    nodes: list[dict[str, Any]],
    with_cover: bool = True,
) -> bytes:
    """Render a 1080x1440 shareable lineup card image in memory and return PNG bytes."""
    W, H = 1080, 1440
    img = Image.new("RGB", (W, H), (13, 27, 46))
    draw = ImageDraw.Draw(img)

    p_rgb = _hex_to_rgb(primary_color, (232, 101, 46))
    s_rgb = _hex_to_rgb(secondary_color, (255, 255, 255))

    font_lg = ImageFont.load_default(size=44)
    font_md = ImageFont.load_default(size=24)
    font_sm = ImageFont.load_default(size=18)
    font_xs = ImageFont.load_default(size=15)

    # Header bar
    draw.rectangle([0, 0, W, 140], fill=(9, 17, 30))
    draw.rectangle([0, 0, W, 8], fill=p_rgb)
    draw.text((48, 34), club_name.upper(), fill=(255, 255, 255), font=font_lg)
    draw.text((48, 92), f"Formation {formation}  ·  Squad Depth Board", fill=(203, 213, 225), font=font_md)

    # Pitch surface
    px0, py0, px1, py1 = 56, 172, W - 56, H - 110
    draw.rounded_rectangle([px0, py0, px1, py1], radius=24, fill=(18, 61, 40), outline=(255, 255, 255), width=3)

    pw, ph = px1 - px0, py1 - py0
    mid_y = py0 + ph // 2
    draw.line([(px0, mid_y), (px1, mid_y)], fill=(120, 180, 145), width=2)
    draw.ellipse([W // 2 - 90, mid_y - 90, W // 2 + 90, mid_y + 90], outline=(120, 180, 145), width=2)
    # Penalty boxes
    draw.rectangle([px0 + int(pw * 0.25), py0, px0 + int(pw * 0.75), py0 + int(ph * 0.14)], outline=(120, 180, 145), width=2)
    draw.rectangle([px0 + int(pw * 0.25), py1 - int(ph * 0.14), px0 + int(pw * 0.75), py1], outline=(120, 180, 145), width=2)

    level_colors = {0: (220, 38, 38), 1: (217, 119, 6), 2: (22, 163, 74)}

    for node in nodes:
        cx = int(px0 + (node["x"] / 100.0) * pw)
        cy = int(py0 + (node["y"] / 100.0) * ph)
        ring = level_colors.get(int(node.get("level", 2)), (22, 163, 74))

        r = 34
        draw.ellipse([cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4], fill=ring)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=p_rgb, outline=s_rgb, width=3)

        short = str(node.get("short", "Player"))[:14]
        stars = node.get("stars")
        st_txt = f"★ {stars:.1f}" if stars else ""
        if st_txt:
            draw.text((cx, cy - 8), st_txt, fill=s_rgb, font=font_xs, anchor="mm")

        # Label pill
        draw.rounded_rectangle([cx - 64, cy + r + 8, cx + 64, cy + r + 34], radius=6, fill=(13, 27, 46))
        draw.text((cx, cy + r + 21), short, fill=(255, 255, 255), font=font_sm, anchor="mm")

        if with_cover and node.get("cover_short"):
            cv_txt = f"Cover: {node['cover_short'][:12]}"
            draw.text((cx, cy + r + 46), cv_txt, fill=(203, 213, 225), font=font_xs, anchor="mm")

    # Footer watermark matching free-tier banner
    draw.rectangle([0, H - 72, W, H], fill=p_rgb)
    draw.text((W // 2, H - 36), "CREATED FREE WITH SCOUTINGSTATS STREAMLIT CLONE", fill=(10, 10, 10), font=font_md, anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
