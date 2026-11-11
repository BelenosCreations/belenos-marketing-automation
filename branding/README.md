# BAM brand identity

The approved product name is **BAM — Belenos Automatic Marketing**. The platform can serve multiple businesses within an account or independent installations. Its name does not restrict the product to Belenos Creations or Busy B Cleaning Service.

The canonical sources are the SVG files under `branding/source/`. The silver/navy wordmark, gold automation arc, teal signal and gold growth arrow are intended to remain consistent across web, desktop, and Android.

| Asset | Usage |
| --- | --- |
| `source/logo_light.svg` | Full name on light UI backgrounds; transparency retained |
| `source/logo_dark.svg` | Full name on dark UI backgrounds; transparency retained |
| `source/app_icon.svg` | Square marketing preview and legacy launcher art |
| `source/adaptive_foreground.svg` | Transparent adaptive Android foreground; mark kept within mask-safe center |
| `source/adaptive_monochrome.svg` | Android themed icon mask |
| `palette.json` | Single-source reference for official name, product scope and four brand colors |

Run `python -m pip install cairosvg pillow` and `python tools/build_branding.py` from repository root to generate transparent logo PNGs, legacy icon sizes, and adaptive Android layers. The generated outputs are distributable artifacts and intentionally separate from the source SVGs.

**Not a deployed app:** At Phase 3.5 the repository does not contain an Android application, Gradle project, AndroidManifest, or production publishing service. The source images and Android resource templates are staged here for integration when the Kotlin/Compose client is created. No publishing permissions, provider credentials, or scheduling behavior are changed by branding.
