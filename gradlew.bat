@echo off
where gradle >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  gradle %*
  exit /b %ERRORLEVEL%
)
echo Gradle 8.8 must be installed or bootstrapped with the Unix gradlew script.
echo Install Gradle 8.8 and run: gradle build
exit /b 1
