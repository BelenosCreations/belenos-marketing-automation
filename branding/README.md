# BAM brand identity

## Owner-approved artwork — November 15, 2026

**The owner-approved BAM identity is the metallic gold, silver, teal and charcoal visual system**, not the simplified SVG-derived artwork currently packaged by BAM Personal Android through 0.11.0. Do not redraw, re-create, re-generate or replace the approved design with a flatter approximation.

Canonical owner-supplied reference images, preserved in the project Library under **Belenos Marketing**:

- `BAM Premium Brand Identity Board.png`: full premium metallic BAM logo at top left, Android icon at top right and separate flat interface lockup at bottom left.
- `BAM Growth Pulse App Icon.png`: matching high-detail metallic icon.
- The owner's **November 15, 2026** source uploads `17472.png` (approved board) and `17473.png` (approved square icon) are the final visual acceptance reference. Original SHA-256: `17472.png` = `0a659fadfabd929a75461b5068c7c6e149ff14c113d0733423cf9450b36df121`; `17473.png` = `f36ea7bbbcee830831806fb3c9c1d6c5fdef148c8e2ae9c51518b92b93c71e08`.
- The Library file `BAM_Approved_Branding_Android_Patch.zip` under **Belenos Marketing** contains the untouched original uploads, size-adapted WebP copies derived *only* by cropping/resizing the source (not generative re-creation), and explicit Android integration instructions. The pack is a development handoff, not a deployed APK.

**Current blocking defect:** the Android APK still uses `bam_wordmark_dark.png`, `bam_launcher_foreground.png` and `bam_launcher_monochrome.png` generated from the wrong simplified SVGs below. Replace the actual packaged resources with the approved bitmaps, update the screen header and launcher including themed icon handling, build, and verify on the owner's phone. Avoid declaring the branding fixed until those images have been committed and a built APK has been visually checked. The binary source images are not yet present in GitHub; do not infer that adding this README changes the APK.

## Historical simplified implementation — superseded for the shipped UI

The approved product name is **BAM — Belenos Automatic Marketing**. The platform can serve multiple businesses within an account or independent installations. Its name does not restrict the product to Belenos Creations or Busy B Cleaning Service.

The earlier (superseded) canonical sources were the SVG files under `branding/source/`. The silver/navy wordmark, gold automation arc, teal signal and gold growth arrow are intended to remain consistent across web, desktop, and Android.

| Asset | Usage |
| --- | --- |
| `source/logo_light.svg` | Full name on light UI backgrounds; transparency retained |
| `source/logo_dark.svg` | Full name on dark UI backgrounds; transparency retained |
| `source/app_icon.svg` | Square marketing preview and legacy launcher art |
| `source/adaptive_foreground.svg` | Transparent adaptive Android foreground; mark kept within mask-safe center |
| `source/adaptive_monochrome.svg` | Android themed icon mask |
| `palette.json` | Single-source reference for official name, product scope and four brand colors |

Run `python -m pip install cairosvg pillow` and `python tools/build_branding.py` from repository root to generate transparent logo PNGs, legacy icon sizes, and adaptive Android layers. The generated outputs are distributable artifacts and intentionally separate from the source SVGs.

The Android app packages the **superseded simplified** wordmark and adaptive launcher icon starting in 0.5.0; the owner's 2026-11-15 correction requires replacement. See the [Android brand resources](../android/branding/README.md) for the artwork refresh and phone checks.
