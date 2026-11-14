# BAM Android brand resources

The Android app uses the approved artwork in `android/app/src/main/res/`.

1. Install CairoSVG and Pillow, then run `python tools/build_branding.py` from the project root.
2. To refresh the packaged artwork, copy the three PNGs from `android/branding/generated/res/drawable-nodpi/` into `android/app/src/main/res/drawable-nodpi/`. Run the renderer with DejaVu Sans installed so the approved wordmark and icon use the intended typeface.
3. The app includes adaptive round and standard launcher resources for its supported API levels. Android applies the shape and, where available, the themed monochrome layer.
4. Build the APK and inspect the launcher icon on the phone with themed icons on and off. Check the wordmark and controls in Android light and dark modes.

The templates in `res/mipmap-anydpi-v26/` preserve the original adaptive resources. The app manifest references the packaged launcher resources. The screen uses the official dark-background wordmark over the navy header in both modes.
