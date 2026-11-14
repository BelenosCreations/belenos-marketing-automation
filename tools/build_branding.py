"""Render canonical BAM SVG brand assets and optional Android launcher resources.

Run: python tools/build_branding.py
Requires: pip install cairosvg pillow
All output is under branding/generated/ and android/branding/generated/res/.
No network operations or publishing functionality.
"""
from __future__ import annotations

from pathlib import Path
import io
from PIL import Image
import cairosvg

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "branding" / "source"
DIST = ROOT / "branding" / "generated"
RES = ROOT / "android" / "branding" / "generated" / "res"
DENSITIES = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}


def rasterize(svg: Path, width: int) -> Image.Image:
    return Image.open(io.BytesIO(cairosvg.svg2png(url=str(svg), output_width=width))).convert("RGBA")


def save_rgba(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def main() -> None:
    DIST.mkdir(parents=True, exist_ok=True)
    logo_light = rasterize(SOURCE / "logo_light.svg", 2000)
    logo_dark = rasterize(SOURCE / "logo_dark.svg", 2000)
    icon = rasterize(SOURCE / "app_icon.svg", 1024)
    save_rgba(logo_light, DIST / "BAM_Logo_Light_Transparent.png")
    save_rgba(logo_dark, DIST / "BAM_Logo_Dark_Transparent.png")
    save_rgba(icon, DIST / "BAM_App_Icon_1024.png")
    save_rgba(icon.resize((512, 512), Image.Resampling.LANCZOS), DIST / "BAM_App_Icon_512.png")

    for density, size in DENSITIES.items():
        save_rgba(icon.resize((size, size), Image.Resampling.LANCZOS),
                  RES / f"mipmap-{density}" / "ic_launcher.png")
        save_rgba(icon.resize((size, size), Image.Resampling.LANCZOS),
                  RES / f"mipmap-{density}" / "ic_launcher_round.png")

    # Android masks the foreground; keep its art inside the central safe region.
    foreground = rasterize(SOURCE / "adaptive_foreground.svg", 432)
    monochrome = rasterize(SOURCE / "adaptive_monochrome.svg", 432)
    assert foreground.getpixel((0, 0))[3] == 0
    save_rgba(foreground, RES / "drawable-nodpi" / "bam_launcher_foreground.png")
    save_rgba(monochrome, RES / "drawable-nodpi" / "bam_launcher_monochrome.png")
    header = rasterize(SOURCE / "logo_dark.svg", 840)
    save_rgba(header.crop(header.getbbox()), RES / "drawable-nodpi" / "bam_wordmark_dark.png")
    print(f"BAM brand generated: {DIST} and {RES}")


if __name__ == "__main__":
    main()
