import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.asflum.cashewregister"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.asflum.cashewregister"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "0.1"

        // Load values from apikeys.properties
        val apiKeysFile = project.rootProject.file("apikeys.properties")
        val apiKeys = Properties()
        apiKeys.load(apiKeysFile.inputStream())

        // Return empty key in case something goes wrong
        val webClientId = apiKeys.getProperty("WEB_CLIENT_ID") ?: ""
        buildConfigField(
            "String",
            "WEB_CLIENT_ID",
            "\"$webClientId\""
        )

        // Load values from local.properties
        val localPropsFile = project.rootProject.file("local.properties")
        val localProps = Properties()
        localProps.load(localPropsFile.inputStream())
        val backendUrl = localProps.getProperty("backendUrl") ?: ""
        buildConfigField(
            "String",
            "BACKEND_URL",
            "\"${backendUrl}\""
        )
    }

    buildFeatures {
        buildConfig = true
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"))
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlin {
        compilerOptions {
            jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
        }
    }

    packaging {
        resources {
            excludes += "META-INF/DEPENDENCIES"
        }
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.16.0")
    implementation("androidx.appcompat:appcompat:1.7.1")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.2.1")
    implementation("com.google.api-client:google-api-client-android:2.8.0")
    implementation("com.google.oauth-client:google-oauth-client-jetty:1.39.0")
    implementation("com.google.apis:google-api-services-gmail:v1-rev110-1.25.0")
    implementation("com.google.android.gms:play-services-auth:21.3.0")
    implementation("com.squareup.okhttp3:okhttp:5.1.0")
    implementation("com.google.code.gson:gson:2.13.1")
    implementation("androidx.credentials:credentials:1.5.0")
    implementation("androidx.credentials:credentials-play-services-auth:1.5.0")
    implementation("com.google.android.libraries.identity.googleid:googleid:1.1.1")
    implementation("com.google.apis:google-api-services-gmail:v1-rev20220404-2.0.0")
    implementation("com.google.http-client:google-http-client-gson:1.47.1")
    implementation("com.google.http-client:google-http-client-android:1.47.1")
    implementation("androidx.browser:browser:1.8.0")
}