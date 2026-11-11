# Android brand resources for future BAM client

The Android client is not yet implemented. These resources are ready to copy when a Gradle Android app module exists.

1. Generate PNGs with `python tools/build_branding.py` from the project root (`pip install cairosvg pillow` once).
2. Copy `android/branding/res/` and `android/branding/generated/res/` into the target app's `src/main/res/` directory, keeping their folder names.
3. Set `android:icon="@mipmap/ic_launcher"` and `android:roundIcon="@mipmap/ic_launcher_round"` on the `<application>` in the target app's AndroidManifest.xml. Set app label to `BAM` in the app's string resources.
4. Build the Android app and inspect actual launcher results on circular/squircle masks, themed icons, light/dark wallpapers, and multiple density devices. The `foreground` asset is intentionally transparent, and only the icon background is painted by Android.

The templates in `res/mipmap-anydpi-v26/` use `@drawable/bam_launcher_foreground` and `@drawable/bam_launcher_monochrome` generated into `res/drawable-nodpi/`. No manifest or Gradle project is committed by this branding milestone. There is no APK yet.
