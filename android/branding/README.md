# BAM Android brand resources

## Current, approved metallic art — BAM 0.12.0

The Android app now packages the owner's exact November 15 metallic BAM
branding. Assets are in `android/app/src/main/res/drawable-nodpi/`:

- `bam_approved_metallic_primary.webp`: full metallic logo used in
  `MainActivity`'s dark navigation header.
- `bam_approved_launcher_foreground.webp`: the owner-approved square
  metallic icon centered in a transparent adaptive foreground for both
  normal and round launchers.
- `bam_approved_flat_lockup.webp`: the approved flat interface variant
  included for future light-surface views.

All are cropped/resized directly from the owner's supplied `17472.png`
and `17473.png` and are SHA-256 pinned by `test_branding.py`. No AI
generation or redrawing. The original files and high-resolution asset
package remain in the **Belenos Marketing** project Library.

The app deliberately has no `<monochrome>` adaptive icon entry:
Samsung/Android must not replace this approved multicolored icon with the
earlier simplified monochrome design. Inspect launcher appearance with
themed icons enabled and disabled, and check the full metallic header in
light/dark phone settings.

## Historical files — NOT for Android app packaging

The `branding/source/*.svg`, `tools/build_branding.py`, and
`android/branding/res` are retained for older historical exercises only.
**Do not run that SVG renderer and copy its outputs into the Android app**:
it recreates the superseded, unapproved logo and icon. When building
future previews, keep the approved bitmaps and check their pinned hashes.
