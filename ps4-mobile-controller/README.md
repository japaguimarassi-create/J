# PS4 Mobile Controller

Android landscape controller-only interface for a PS4 Remote Play session.

## Behavior

- Sends DualShock 4 controller states through the Chiaki-ng Remote Play session.
- Disables both audio and video at the native session level; the app does not show or decode the game stream.
- Landscape flat layout: R2/R1 on the left, L2/L1 on the right, D-pad left, touchpad panel centered, △ ○ × □ on the right, PS/Share/Options centered below, and two analog sticks along the lower edges.
- Tapping the center of the left/right analog stick sends L3/R3. Dragging outside the center zone moves the corresponding stick.
- Uses the existing PS4 registration flow. Remote Play must be enabled on the console and the console must be registered with its displayed PIN.

## Build

The GitHub Actions workflow checks out the pinned Chiaki-ng source, applies \`apply_controller_only.py\`, and builds an ARM-compatible Android debug APK.

The app is derived from Chiaki-ng, which is licensed under AGPL-3.0-only with OpenSSL exception. The upstream source is pinned in the workflow; see https://github.com/chiaki-ng/chiaki-ng and the upstream license files. This repository contains the patch script and build workflow.

## Important

This is not a Bluetooth HID controller. It controls the PS4 through a registered Remote Play session. The no-video mode is implemented by setting \`CHIAKI_AUDIO_VIDEO_DISABLED\` in the native connection structure.
