plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val gmailClientId: String = project.rootProject.file("local.properties")
    .reader().useLines { lines ->
        lines.first { it.startsWith("GMAIL_CLIENT_ID=") }
            .split("=")[1]
    }

android {
    namespace = "com.asflum.cashewregister"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.asflum.cashewregister"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "0.1"
        buildConfigField("String", "GMAIL_CLIENT_ID", "\"$gmailClientId\"")
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

    kotlinOptions {
        jvmTarget = "17"
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
    implementation("com.google.api-client:google-api-client-android:1.35.0")
    implementation("com.google.oauth-client:google-oauth-client-jetty:1.35.0")
    implementation("com.google.apis:google-api-services-gmail:v1-rev110-1.25.0")
    implementation("com.google.android.gms:play-services-auth:21.3.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
}