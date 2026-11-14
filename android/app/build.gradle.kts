plugins {
    id("com.android.application") version "8.13.2"
    id("org.jetbrains.kotlin.android") version "2.4.0"
}
android {
    namespace = "com.belenos.bam"
    compileSdk = 35
    defaultConfig {
        applicationId = "com.belenos.bam.owner"
        minSdk = 28
        targetSdk = 35
        versionCode = 5
        versionName = "0.5.0"
        manifestPlaceholders["bamLabel"] = "BAM Personal"
        ndk { abiFilters += "arm64-v8a" }
    }
    buildTypes {
        debug {
            applicationIdSuffix = ".preview"
            manifestPlaceholders["bamLabel"] = "BAM Preview"
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
    implementation("androidx.work:work-runtime:2.10.5")
    implementation("com.google.ai.edge.litertlm:litertlm-android:0.19.1")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.robolectric:robolectric:4.16.1")
}
