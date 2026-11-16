# Owner-only Facebook Page discovery preview

The Android dashboard opens **Facebook Pages** and offers **Connect Facebook**
only when a debug build is configured for the owner's Meta development app.
The connection uses Meta's Android SDK. The requested Page discovery scope is
`pages_show_list`. BAM makes a paginated GET request to `me/accounts` for
`id,name`, shows the Page names in the active screen and clears the SDK login
session after completion. BAM keeps no Page association or user access token in
its own storage. The SDK manages the sign-in transaction and its temporary
token cache. Each new attempt clears any prior cached SDK login.

## Prepare the private test

1. In the owner's Meta app, configure Facebook Login and the Android platform.
   Keep the app in Development mode and check that the person testing has a
   role on the app and access to the target business Page.
2. Register debug package `com.belenos.bam.owner.preview.personal13`, launcher
   class `com.belenos.bam.MainActivity`, and the Android key hash for the exact
   debug signing certificate used for this test. The CI debug key can change
   between builds. A locally built APK can use a private, stable debug key.
   Check the redirect and permissions available for the selected Meta use case.
3. In private local Gradle user properties, set `bamFacebookTestAppId` and
   `bamFacebookTestClientToken` to the Android app's public configuration
   values from Meta. Use the **client token** field on the Meta app, never the
   app secret, a user access token, or a Page access token. Leave the properties
   out of the repository. These client configuration values are visible in the
   resulting debug APK, so share a configured build only with the tester.
4. Run `gradle -p android :app:assembleDebug` and install its signed debug APK.
   Android requires the same signing certificate to update the installed
   package. Use a separate device or a matching locally signed test build if
   the installed preview uses another signer and its local drafts are needed.

See [Meta's Android SDK guide](https://developers.facebook.com/docs/android/getting-started/),
[development mode](https://developers.facebook.com/docs/apps/managing-development-cycle/),
and [permission reference](https://developers.facebook.com/docs/permissions/).

## Verify on the owner's phone

- Open **Facebook Pages**, tap **Connect Facebook**, consent to Page access
  and check whether an eligible managed Page such as Belenos Creations appears.
- Try cancellation and declined permission. Check for a readable message and
  retry from the same screen. Expired authorization also requires sign-in again.
  An authorized account with no Pages should show an empty result.
- Verify BAM never asks for Page publishing permission. The preview only reads
  the Page list. Existing manually approved Android sharing is separate.

Standard CI builds have no Meta app configuration. Release builds always omit
it. Test fixtures cover parsing, pagination, empty and malformed responses.
Only a configured owner phone test can verify live Meta consent and Page
visibility. The preview does not change production or hosting settings.
