plugins {
    id("com.android.application") version "8.13.2"
    id("org.jetbrains.kotlin.android") version "2.4.0"
}
val facebookTestAppId = providers.gradleProperty("bamFacebookTestAppId").orElse("").get()
val facebookTestClientToken = providers.gradleProperty("bamFacebookTestClientToken").orElse("").get()
require(facebookTestAppId.isEmpty() == facebookTestClientToken.isEmpty() &&
    (facebookTestAppId.isEmpty() || (facebookTestAppId.matches(Regex("[0-9]{5,32}")) &&
        facebookTestClientToken.matches(Regex("[A-Za-z0-9]{16,128}"))))) {
    "Supply both Meta development app values as valid BAM debug build properties."
}

android {
    namespace = "com.belenos.bam"
    compileSdk = 35
    defaultConfig {
        applicationId = "com.belenos.bam.owner"
        minSdk = 28
        targetSdk = 35
        versionCode = 13
        versionName = "0.13.0"
        manifestPlaceholders["bamLabel"] = "BAM Personal"
        resValue("string", "bam_facebook_test_app_id", "")
        resValue("string", "bam_facebook_test_client_token", "")
        ndk { abiFilters += "arm64-v8a" }
    }
    buildTypes {
        debug {
            applicationIdSuffix = ".preview.personal13"
            manifestPlaceholders["bamLabel"] = "BAM 0.13 Preview"
            resValue("string", "bam_facebook_test_app_id", facebookTestAppId)
            resValue("string", "bam_facebook_test_client_token", facebookTestClientToken)
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    testOptions {
        unitTests.isIncludeAndroidResources = true
    }
}
kotlin {
    jvmToolchain(21)
    compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) }
}
dependencies {
    implementation("com.facebook.android:facebook-login:19.0.1")
    implementation("androidx.work:work-runtime:2.10.5")
    implementation("com.google.ai.edge.litertlm:litertlm-android:0.19.1")
    testImplementation("junit:junit:4.13.2")
    testImplementation("androidx.work:work-testing:2.10.5")
    testImplementation("org.robolectric:robolectric:4.16.1")
}
