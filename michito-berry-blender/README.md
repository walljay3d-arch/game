# Michito Berry Blender — Version 5 (gameplay and teaching update)

## Windows quick start

1. Close any previous Berry Blender command window (port 8765 must be free).
2. Extract the ZIP, run `START_WINDOWS.bat`, and open `http://localhost:8765/control`.
3. Keep the complete resulting DM control URL (with its private `key=`) bookmarked.
4. Open the generated TV stage link on the TV, and let players join from their phones using the QR code.
5. On the TV stage, click **Activate TV audio** once before blending. Music starts automatically with the spinner, and hit sounds trigger automatically. Browsers prohibit autoplay before a user gesture.

## Show sequence

- **DM /control:** click BEGIN ROUND. The TV shows the round number and waits for Dee.
- **Jessica /jessica:** Dee selects exactly one Pokémon from her card grid. She never starts the blender. Already-selected Pokémon become disabled/gray for subsequent rounds.
- **TV /stage:** shows a flavor hint, *not* Pokémon identity or nickname.
- **Phones /play:** each trainer sees a five-flavor recipe guide, selects one Berry, then explicitly clicks **READY UP**. Players can unlock their selection to change their Berry. The DM's BEGIN BLENDING activates when all present players are ready.
- **DM /control:** optionally start a no-score practice, then click BEGIN BLENDING.
- **TV:** shows the continuous spinner, color-coded markers, speed-up from accurate taps, scores, and synthesized PERFECT / GOOD / MISS sounds. An unpressed timing window counts as MISS.
- **TV:** displays the resulting Pokéblock color, Level, Feel and timing score, *without revealing the Pokémon*.
- **DM /control:** click REVEAL HUNGRY POKÉMON. A successful match plays a victory chime. The TV reveals its art, nickname, name, preferred flavor, and cry button.
- **DM /control:** click NEXT ROUND to repeat the cycle.

## Jessica's Pokémon

- Miraidon — **Vega**
- Plusle **Poppy** and Minun **Pippa** — presented **together**
- Boltund — **Dash**
- Luxray (male) — **Lex**
- Raika (custom Ashikaga Pokémon) — **Kira**, using the `ImageURL` from `Ashikaga App Database` / `PokemonSpecies` (`https://i.imgur.com/hxRIh7T.png`)

Nature determines liked/disliked flavors in Ruby/Sapphire/Emerald. Nature and preference values currently assigned to Jessica's Pokémon are editable *campaign defaults* and are **not canon facts about the species**.

## Remote Dee (Ohio)

Running on a Utah PC using `localhost` alone does **not** let Dee join from Ohio. The app must be deployed to a public HTTPS Python/WebSocket host (a `render.yaml` starter is included). Open `/control` at the deployed domain; the DM screen will provide Dee's private `/jessica` invite URL. Only the DM can begin rounds, start blending, reset or reveal Pokémon. Do not share the DM URL with anyone else.

## Canon caveat

Berry names and their five main flavors are based on Generation III games. **The original Gen III Berry Blender supports 2–4 participants; this seven-player recipe/Level/Feel/quality model is a campaign adaptation, not the exact original game's formula.** The modified party rule requires at least half the trainers to select the target-flavor basic Berry. Repeated Berries are allowed in this version, unlike the original duplicate-Berry Black Pokéblock rule, so the recipe remains achievable for seven trainers.

Pokémon artwork and cries use external image and audio URLs (the custom Raika image is from the connected database); the device viewing the stage needs internet access to load these files.
