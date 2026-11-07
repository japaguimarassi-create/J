# ECLIPSE — Character selection portraits

Two original, transparent head portraits for the faction selection buttons.

| Guardião | Criatura |
| --- | --- |
| ![Tanjiro-inspired avatar](./tanjiro-bacon.png) | ![Muzan-inspired avatar](./muzan-bacon.png) |
| [Open Tanjiro portrait](./tanjiro-bacon.png) | [Open Muzan portrait](./muzan-bacon.png) |

[Open the side-by-side button preview](./selection-preview.png)

## What changed after the supplied references

The earlier artwork was too busy: it included a torso, large decorative background effects, a text plaque and a generic fantasy-card layout. Those elements did not match the examples.

The revised portraits follow the supplied references more closely:
- A single oversized Roblox-style head, with a broad, rounded-square face.
- Thick, near-black drawn outlines and simple, expressive facial features.
- Hair is the main silhouette: auburn layered waves and swept locks for Tanjiro; dark, wavy, center-parted locks with cool grey highlights for Muzan.
- Tanjiro has the forehead scar and rectangular sun earrings; Muzan has pale skin, narrow red eyes and a confident expression.
- No torso, no character screenshot, no embedded title and no background in the portrait files.

## Button direction

The preview sheet shows the portraits inside two selectable cards, following the compact, high-contrast Roblox UI direction from the third reference: teal for Guardião, crimson for Criatura, and a light nameplate. The PNG portraits themselves stay transparent so they can be placed on different Roblox GUI backgrounds.

For Roblox, use the PNG exports in ImageLabel or ImageButton objects. Keep the image background transparent and apply ScaleType = Fit. The SVG files are editable source artwork; Roblox GUI image properties need uploaded PNG asset IDs.

## Files

- tanjiro-bacon.svg / muzan-bacon.svg — editable vector source.
- tanjiro-bacon.png / muzan-bacon.png — 1024×1024 transparent PNG portraits, rendered by GitHub Actions.
- selection-preview.png — 1120×650 side-by-side visual review.
- render-character-selection.yml — renders the PNGs, verifies transparency and dimensions, and commits exports to this branch.

The PNGs are in GitHub only at this stage. They have not yet been uploaded to Roblox or connected to the live selection GUI.
