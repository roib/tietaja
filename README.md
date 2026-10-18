# Tietäjä: the origin of fire

A demo game for experimenting with [Bevy](https://bevyengine.org) and WebAssembly: a small point-and-click adventure about how fire came to the village. It's set in Finnish folklore, and its painted rooms follow [Werner Holmberg](https://en.wikipedia.org/wiki/Werner_Holmberg)'s landscapes. It runs natively and in the browser, including on phones.

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

- `assets/story.txt` holds the whole game: characters, items, rooms, hotspots and dialogue. The format is documented at the top of the file.
- `src/`: the engine. `story.rs` parses and runs the story, `main.rs` handles rooms, the player and the UI, `scenery.rs` adds room effects, and `intro.rs` plays the title and intro.
- `tools/make_art.py` paints the placeholder art (it needs Pillow). `tools/make_audio.py` synthesizes the kantele music and the babble voices (it needs ffmpeg). You can replace any generated file with real art or audio.

## Credits

The font is Noto Serif by Google, under the [SIL Open Font License 1.1](https://openfontlicense.org) (see `assets/fonts/README.md`).
