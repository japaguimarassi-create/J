plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "com.japa.ps4controller"
    compileSdk = 35
    defaultConfig {
        applicationId = "com.japa.ps4controller"
        minSdk = 26
        targetSdk = 28
        versionCode = 1
        versionName = "0.1.0"
    }
}
