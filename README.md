# ECLIPSE: BLOOD & BREATH — Roblox Alpha

An original dark-fantasy Roblox Action RPG prototype. The full Rojo source project is included in `EclipseBloodBreath-Alpha.tar.gz`.

## Build locally

```bash
tar -xzf EclipseBloodBreath-Alpha.tar.gz
cd eclipse-blood-breath-roblox
rojo build default.project.json --output build/EclipseBloodBreath.rbxlx
```

Open the resulting `.rbxlx` in Roblox Studio. To iterate live, run `rojo serve` from the project directory and connect the Rojo Studio plugin.

## Automated Roblox publishing

The GitHub Actions workflow builds the place on every push to `demon-slayer-rpg-alpha`. It publishes the build to an existing Roblox place only when both required repository secrets are configured:

1. Create the Roblox experience in Creator Dashboard first. This workflow updates an existing place; it does not create a new experience.
2. Open that experience, select its starting place, and copy the Place ID from the place's Configure page URL.
3. Create an Open Cloud API key in Creator Dashboard. Grant the **Assets** API **Read** and **Write** permissions for that experience.
4. In this GitHub repository, open **Settings → Secrets and variables → Actions** and add:
   - `ROBLOX_API_KEY`: the Open Cloud API key.
   - `ROBLOX_PLACE_ID`: the numeric starting Place ID.
5. Push a commit to `demon-slayer-rpg-alpha`. The workflow builds the `.rbxlx`, stores it as an artifact, uploads it to Roblox, and waits for Roblox to confirm that the new version is published.

Never commit the API key or paste it into source files. The upload publishes the place version, but does not change the experience's audience/access setting. Set the experience to **Public** in Creator Dashboard when it is ready for players, then verify it from the Roblox game page.

Official publishing guide: https://create.roblox.com/docs/cloud/guides/usage-place-publishing

## Included in this alpha

- Procedural starting village, forest route, training yard and boss arena.
- Two original faction paths: Guardião / Escola da Maré and Criatura / Arte do Abismo.
- Server-validated attacks, heavy attacks, blocking, dodge, energy and faction skill.
- Common enemy AI and a boss with a telegraphed area attack.
- Introductory trial, XP, levels, rank titles, gold and style mastery.
- DataStore profile persistence with a temporary-session fallback on read failure.
- Portuguese HUD, touch controls, keyboard/mouse and basic gamepad actions.

## Release status

This is a source-level vertical slice. Roblox Studio execution, two-client multiplayer testing, mobile profiling, DataStore validation in a published test place, final animation/mesh/audio work, and release review remain outstanding. The workflow now supports Open Cloud publishing when the owner configures the required secrets and an existing Roblox Place ID. No public release is claimed until Roblox confirms the uploaded version and the experience is made public.

## Intellectual property

All shipped names, factions, setting, skills, characters and procedural assets in this prototype are original. Demon Slayer is used only as a high-level genre and atmosphere reference; no character, logo, music, dialogue, footage, model or animation from that franchise is included.
