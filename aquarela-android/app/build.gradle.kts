plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.devtools.ksp")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.aquarela.viewer"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.aquarela.viewer"
        minSdk = 29
        targetSdk = 34
        versionCode = 3
        versionName = "3.0"
    }

    signingConfigs {
        create("release") {
            storeFile = file("../aquarela-release.jks")
            storePassword = "aquarela2026"
            keyAlias = "aquarela"
            keyPassword = "aquarela2026"
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("release")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
    }

    applicationVariants.all {
        val variant = this
        variant.outputs.all {
            val out = this as com.android.build.gradle.internal.api.BaseVariantOutputImpl
            out.outputFileName = "Aquarela-v${variant.versionName}.apk"
        }
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
    implementation("androidx.webkit:webkit:1.9.0")

    implementation(platform("androidx.compose:compose-bom:2025.04.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.activity:activity-compose:1.10.1")
    implementation("androidx.navigation:navigation-compose:2.9.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.9.0")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.9.0")

    implementation("androidx.room:room-runtime:2.7.1")
    implementation("androidx.room:room-ktx:2.7.1")
    ksp("androidx.room:room-compiler:2.7.1")

    implementation("org.osmdroid:osmdroid-android:6.1.20")

    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.10.2")
}
