# Tietäjä: the origin of fire

A demo game for experimenting with [Bevy](https://bevyengine.org) and [WebAssembly](https://webassembly.org): a small point-and-click adventure in two tales. In *The Origin of Fire*, Vilja must sing a dead hearth back to life; in *The Sauna Spirit*, she must make peace with the offended keeper of the sauna. Both are set in Finnish folklore, and their painted rooms follow [Werner Holmberg](https://en.wikipedia.org/wiki/Werner_Holmberg)'s landscapes. It runs natively and in the browser, including on phones.

**Play it in your browser:** https://roib.github.io/tietaja/

## Controls

- **Click** to walk, or choose a verb (Look, Take, Use, Talk) and then click something
- **Right-click** to look at something
- **Click an item** in the inventory to use it on something
- **Space / Enter**: skip a line of dialogue
- **Esc**: cancel the current verb or item
- **M**: turn sound on or off

On a touch screen, tap where you would click. Phones play in landscape.

## Running

Native:

```sh
cargo run
```

Browser:

```sh
rustup target add wasm32-unknown-unknown
cargo install wasm-bindgen-cli --version <wasm-bindgen version in Cargo.lock> --locked
tools/build_web.sh
python3 -m http.server -d dist 8080   # then open http://localhost:8080
```

Every push to `main` builds the browser version and deploys it to GitHub Pages (`.github/workflows/pages.yml`).

## Making the game

- Each tale is one story file holding all its characters, items, rooms, hotspots and dialogue: `assets/story.txt` (the format is documented at its top) and `assets/sauna.txt`.
- `src/`: the engine. `levels.rs` lists the tales and choreographs each one's opening, `menu.rs` is the screen where you choose a tale, `intro.rs` plays the openings, `story.rs` parses and runs a story, `main.rs` handles rooms, the player and the UI, and `scenery.rs` adds room effects and the crossfades between rooms.
- `tools/make_art.py` paints the art (it needs Pillow). `tools/make_audio.py` synthesizes the music and the babble voices (it needs ffmpeg). Both can make just some parts, e.g. `tools/make_art.py sauna_tale`. You can replace any generated file with real art or audio.

## License

The code, art, music and story are dual-licensed under either of

- [MIT License](LICENSE-MIT)
- [Apache License, Version 2.0](LICENSE-APACHE)

at your option.

The font is Noto Serif by Google, under the [SIL Open Font License 1.1](assets/fonts/OFL.txt).
