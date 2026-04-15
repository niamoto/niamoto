"""Applique un masque arrondi aux icônes multi-plateformes.

- Windows (.ico) + Linux (PNGs) : rayon configurable (défaut 0.18, Win 11 style).
- macOS (.icns) : rayon squircle Apple (0.2237). Nécessaire en dev mode
  car macOS n'applique son masque qu'aux .app enregistrés, pas aux
  binaires dev bruts.

Usage :
    uv run --with pillow python scripts/build/round_platform_icons.py
    uv run --with pillow python scripts/build/round_platform_icons.py --radius 0.18
    uv run --with pillow python scripts/build/round_platform_icons.py --skip-macos

La source doit être `src-tauri/icons/icon.png` (carrée).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

ICONS_DIR = Path(__file__).resolve().parents[2] / "src-tauri" / "icons"
SOURCE = ICONS_DIR / "icon.png"

# PNGs utilisés par Tauri pour Linux (AppImage, .deb)
LINUX_PNGS = {
    "32x32.png": 32,
    "128x128.png": 128,
    "128x128@2x.png": 256,
}

# Tailles embarquées dans le .ico Windows (Windows Explorer utilise 256)
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]


def rounded_mask(size: int, radius_ratio: float) -> Image.Image:
    """Crée un masque alpha avec coins arrondis."""
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    radius = int(size * radius_ratio)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def round_image(
    src: Image.Image,
    size: int,
    radius_ratio: float,
    padding_ratio: float = 0.0,
) -> Image.Image:
    """Redimensionne et applique le masque arrondi.

    padding_ratio : marge transparente sur chaque côté (0.10 = 10% Apple guidelines).
    Le rayon est appliqué à la zone visible (taille - 2*padding), pas au canvas.
    """
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pad = int(size * padding_ratio)
    inner = size - 2 * pad
    if inner <= 0:
        return canvas
    img = src.resize((inner, inner), Image.LANCZOS).convert("RGBA")
    mask = rounded_mask(inner, radius_ratio)
    rounded = Image.new("RGBA", (inner, inner), (0, 0, 0, 0))
    rounded.paste(img, (0, 0), mask)
    canvas.paste(rounded, (pad, pad), rounded)
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--radius",
        type=float,
        default=0.18,
        help="Rayon Windows/Linux (défaut 0.18, style Win 11). Squircle Apple ≈ 0.2237.",
    )
    parser.add_argument(
        "--macos-radius",
        type=float,
        default=0.2237,
        help="Rayon macOS .icns (défaut 0.2237, squircle Apple). Pour cohérence dev/release.",
    )
    parser.add_argument(
        "--macos-padding",
        type=float,
        default=0.0977,
        help="Marge transparente macOS (défaut 0.0977 ≈ 100/1024 Apple HIG).",
    )
    parser.add_argument(
        "--skip-macos",
        action="store_true",
        help="Ne pas régénérer le .icns (laisse macOS appliquer son masque en release).",
    )
    args = parser.parse_args()

    if not SOURCE.exists():
        raise SystemExit(f"Source introuvable : {SOURCE}")

    source = Image.open(SOURCE).convert("RGBA")
    print(f"Source : {SOURCE.name} {source.size}  rayon={args.radius:.4f}")

    # Linux PNGs
    for name, size in LINUX_PNGS.items():
        out = ICONS_DIR / name
        round_image(source, size, args.radius).save(out, "PNG", optimize=True)
        print(f"  Linux → {name} ({size}×{size})")

    # Windows .ico multi-résolution
    ico_frames = [round_image(source, s, args.radius) for s in ICO_SIZES]
    ico_out = ICONS_DIR / "icon.ico"
    ico_frames[0].save(
        ico_out,
        format="ICO",
        sizes=[(s, s) for s in ICO_SIZES],
        append_images=ico_frames[1:],
    )
    print(f"  Windows → icon.ico ({ICO_SIZES})")

    # macOS .icns (Pillow écrit un ICNS multi-résolution)
    if args.skip_macos:
        print("\nmacOS (icon.icns) laissé intact (--skip-macos).")
    else:
        icns_source = round_image(
            source,
            min(source.size[0], 1024),
            args.macos_radius,
            padding_ratio=args.macos_padding,
        )
        icns_out = ICONS_DIR / "icon.icns"
        icns_source.save(icns_out, format="ICNS")
        print(
            f"  macOS   → icon.icns "
            f"(rayon {args.macos_radius:.4f}, padding {args.macos_padding:.4f})"
        )


if __name__ == "__main__":
    main()
