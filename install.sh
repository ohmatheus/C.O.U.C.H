#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$SCRIPT_DIR/config.yaml"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "${CYAN}[couch]${RESET} $*"; }
success() { echo -e "${GREEN}[couch]${RESET} $*"; }
die()     { echo -e "${RED}[couch] ERROR:${RESET} $*" >&2; exit 1; }

# ── OS check ──────────────────────────────────────────────────────────────────
[[ "$(uname -s)" == "Linux" ]] || die "Linux only (got $(uname -s))."

# ── uv ────────────────────────────────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
    info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
success "uv $(uv --version | awk '{print $2}')"

# ── Python 3.12 ───────────────────────────────────────────────────────────────
info "Ensuring Python 3.12 is available..."
uv python install 3.12 --quiet
success "Python 3.12 ready"

# ── Python dependencies ───────────────────────────────────────────────────────
info "Installing Python dependencies..."
cd "$SCRIPT_DIR"
uv sync --all-packages --quiet
success "Python dependencies installed"

# ── System tools ─────────────────────────────────────────────────────────────
if ! command -v xdotool &>/dev/null; then
    info "Installing xdotool (required for press_key tool)..."
    sudo apt-get install -y xdotool 2>/dev/null || sudo dnf install -y xdotool 2>/dev/null || \
        info "Could not auto-install xdotool — install it manually: apt install xdotool"
fi

# ── Google Chrome ─────────────────────────────────────────────────────────────
if ! command -v google-chrome &>/dev/null && ! command -v google-chrome-stable &>/dev/null; then
    info "Installing Google Chrome..."
    if command -v dnf &>/dev/null; then
        sudo dnf install -y https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm
    elif command -v apt-get &>/dev/null; then
        curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg
        echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] https://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
        sudo apt-get update -q && sudo apt-get install -y google-chrome-stable
    else
        info "Could not auto-install Chrome — install it manually from https://google.com/chrome"
    fi
fi

# ── Playwright Chromium ───────────────────────────────────────────────────────
info "Installing Playwright Chromium browser..."
uv run playwright install chromium --quiet
success "Playwright Chromium ready"

# ── Ollama ────────────────────────────────────────────────────────────────────
if ! command -v ollama &>/dev/null; then
    info "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    success "Ollama $(ollama --version 2>/dev/null | head -1) already installed"
fi

# Ensure the Ollama service is running
if ! systemctl is-active --quiet ollama 2>/dev/null; then
    info "Starting Ollama service..."
    systemctl start ollama 2>/dev/null || ollama serve &>/dev/null &
    sleep 2
fi

# ── Pull the configured model ─────────────────────────────────────────────────
if [[ -f "$CONFIG" ]]; then
    MODEL=$(grep '^llm_model:' "$CONFIG" | awk '{print $2}' | tr -d '"' | tr -d "'")
else
    MODEL="qwen2.5:7b"
fi

info "Pulling model: ${BOLD}${MODEL}${RESET} (this may take a while on first run)..."
ollama pull "$MODEL"
success "Model $MODEL ready"

# ── Default config ────────────────────────────────────────────────────────────
if [[ ! -f "$CONFIG" ]]; then
    info "Writing default config.yaml..."
    cat > "$CONFIG" <<'EOF'
whisper_model: large-v3
whisper_device: cuda

llm_model: qwen2.5:7b
llm_keepalive: -1

server_host: 0.0.0.0
server_port: 8765
server_url: ws://localhost:8765

language: fr
wake_word: hey_jarvis

session_mode: continuous
session_timeout: 5
stop_phrase: "arrête d'écouter"

input_device: default
feedback_device: default
feedback_mode: beep
tts_model: fr_FR-siwis-medium
EOF
    success "config.yaml created — edit it to match your setup"
fi

echo
echo -e "${GREEN}${BOLD}All done.${RESET}"
echo
echo "  Start the server : cd server && uv run python server.py"
echo "  Start the client : cd client && uv run python client.py"
echo "  Skip wake word   : cd client && uv run python client.py --no-wake"
echo
