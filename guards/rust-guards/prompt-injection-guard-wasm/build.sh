#!/usr/bin/env bash
#
# Build script for Prompt Injection Guard (Rust) WASM component
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

WASMTIME_VERSION="27.0.0"
ADAPTER_URL="https://github.com/bytecodealliance/wasmtime/releases/download/v${WASMTIME_VERSION}/wasi_snapshot_preview1.reactor.wasm"
ADAPTER_FILE="wasi_snapshot_preview1.reactor.wasm"

echo "Building Prompt Injection Guard (Rust) WASM component..."

# Determine the correct WASM target name
WASM_TARGET="wasm32-wasip1"
if ! rustup target list | grep -q "${WASM_TARGET}"; then
    WASM_TARGET="wasm32-wasi"
fi

# Check prerequisites
if ! command -v rustc &> /dev/null; then
    echo "Error: Rust not installed. Install from https://rustup.rs"
    exit 1
fi

if ! rustup target list --installed | grep -q "${WASM_TARGET}"; then
    echo "Installing ${WASM_TARGET} target..."
    rustup target add "${WASM_TARGET}"
fi

if ! command -v wasm-tools &> /dev/null; then
    echo "Installing wasm-tools..."
    cargo install wasm-tools
fi

# Download WASI adapter if not present
if [ ! -f "$ADAPTER_FILE" ]; then
    echo "Downloading WASI preview1 adapter (wasmtime ${WASMTIME_VERSION})..."
    curl -L -o "$ADAPTER_FILE" "$ADAPTER_URL"
fi

echo "Prerequisites OK"

# Build WASM module
echo "  Compiling..."
cargo build --target "${WASM_TARGET}" --release

# Convert to Component Model with WASI adapter
echo "  Creating component..."
wasm-tools component new \
    "target/${WASM_TARGET}/release/prompt_injection_guard_wasm.wasm" \
    --adapt "$ADAPTER_FILE" \
    -o prompt-injection-guard-wasm.component.wasm

# Optimize (if wasm-opt is available)
if command -v wasm-opt &> /dev/null; then
    echo "  Optimizing..."
    wasm-opt -Oz \
        -o prompt_injection_guard.wasm \
        prompt-injection-guard-wasm.component.wasm
    rm prompt-injection-guard-wasm.component.wasm
else
    mv prompt-injection-guard-wasm.component.wasm prompt_injection_guard.wasm
fi

size=$(wc -c < prompt_injection_guard.wasm | awk '{print int($1/1024)"KB"}')
echo "Build complete: prompt_injection_guard.wasm ($size)"
