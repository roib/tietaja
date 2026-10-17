#!/usr/bin/env bash
# Builds the browser version of the game into dist/.
#
#   tools/build_web.sh
#   python3 -m http.server -d dist 8080     # then open http://localhost:8080
#
# Needs a Rust toolchain with the wasm32-unknown-unknown target, and
# wasm-bindgen-cli at exactly the version of the wasm-bindgen crate in Cargo.lock:
#   rustup target add wasm32-unknown-unknown
#   cargo install wasm-bindgen-cli --version <version from Cargo.lock> --locked
set -euo pipefail
cd "$(dirname "$0")/.."

# Prefer rustup's cargo (it can have the wasm target) over a system cargo.
CARGO=cargo
if [ -x "$HOME/.cargo/bin/cargo" ]; then
    CARGO="$HOME/.cargo/bin/cargo"
fi
WASM_BINDGEN=wasm-bindgen
if [ -x "$HOME/.cargo/bin/wasm-bindgen" ]; then
    WASM_BINDGEN="$HOME/.cargo/bin/wasm-bindgen"
fi

# With rustup, use an installed toolchain that has the wasm target (the default may not).
if [ -z "${RUSTUP_TOOLCHAIN:-}" ] && [ -d "$HOME/.rustup/toolchains" ]; then
    for toolchain in "$HOME"/.rustup/toolchains/*; do
        if [ -d "$toolchain/lib/rustlib/wasm32-unknown-unknown" ]; then
            export RUSTUP_TOOLCHAIN="$(basename "$toolchain")"
        fi
    done
    if [ -z "${RUSTUP_TOOLCHAIN:-}" ]; then
        echo "No rustup toolchain has the wasm target. Run: rustup target add wasm32-unknown-unknown" >&2
        exit 1
    fi
    echo "Using toolchain $RUSTUP_TOOLCHAIN"
fi

"$CARGO" build --profile web --target wasm32-unknown-unknown

rm -rf dist
mkdir -p dist
"$WASM_BINDGEN" --target web --no-typescript --out-dir dist target/wasm32-unknown-unknown/web/tietaja.wasm
cp index.html dist/
cp -r assets dist/

echo "Built dist/ ($(du -sh dist | cut -f1)). Serve it with: python3 -m http.server -d dist 8080"
