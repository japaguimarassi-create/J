# PS4 Mobile Controller

Android landscape touchscreen controller prototype inspired by the DualShock 4 layout.

## Current build
- Flat controller-only layout; no game video.
- D-pad, face buttons, SHARE, OPTIONS, PS, touchpad, L1/L2/R1/R2.
- Two analog zones with L3/R3 press behavior and multi-touch UI.
- GitHub Actions builds a debug APK.

## Important limitation
This first APK is the controller interface prototype. It does not yet establish a PlayStation Remote Play session or transmit DualShock 4 input to a PS4. A real connection requires integrating and validating a compatible Remote Play transport/input implementation (for example, the Chiaki-ng/LibChiaki codebase) and its authentication flow. The interface must not be mistaken for a working PS4 connection.

## Build
GitHub Actions -> Build Android APK -> Artifacts.
