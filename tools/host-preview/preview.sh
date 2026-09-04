#!/bin/sh
# Preview the theme on this PC in a 640x480 window, using the same
# EmulationStation fork RelicOS ships, built for x86.
#
#   tools/host-preview/preview.sh          run (builds the ES and the fake HOME on first use)
#   ES_SPLASH=1 tools/host-preview/preview.sh   ... and show the loading screen
#   tools/host-preview/preview.sh build    (re)build the ES
#   tools/host-preview/preview.sh home     regenerate the fake HOME
#   tools/host-preview/preview.sh clean    remove everything under $ES_PREVIEW_DIR
#
# Keys once it is open: arrows move, Esc = OK, Enter = back, F1 menu, F2 options,
# F5 reloads the theme after you edit it. The games-page layout is
# MAIN MENU > USER INTERFACE SETTINGS > GAMELIST VIEW STYLE.
#
# Everything lives in $ES_PREVIEW_DIR (default ~/.cache/relicos/es-preview):
#   es/        ES source + the built binary (the ES puts it next to resources/)
#   home/      fake HOME (systems, fake ROMs, covers, settings, keyboard map)
#
# ES source: knulli-cfw/batocera-emulationstation @ the commit pinned in
# RelicOS. Taken from the RelicOS build tree when it is there, cloned otherwise.
set -eu

THEME_DIR=$(cd "$(dirname "$0")/../.." && pwd)
DIR=${ES_PREVIEW_DIR:-$HOME/.cache/relicos/es-preview}
ES_SRC="$DIR/es"
FAKE_HOME="$DIR/home"
ES_COMMIT=${ES_COMMIT:-f7c5ae103815761ccd34bc55b021c6e150442c96}
ES_REPO=https://github.com/knulli-cfw/batocera-emulationstation
RELICOS_BUILD=${RELICOS_BUILD:-$HOME/Projects/relicos/system/output/build/emulationstation-$ES_COMMIT}

# freeimage is flagged insecure in nixpkgs; the 25.05 channel still ships it.
NIX_PKGS="cmake pkg-config gettext SDL2 SDL2_mixer freeimage freetype libvlc curl rapidjson alsa-lib libGL libGLU udev git"
nix_run() {
  NIXPKGS_ALLOW_INSECURE=1 nix-shell --impure -I nixpkgs=channel:nixos-25.05 -p $NIX_PKGS --run "$1"
}

fetch_source() {
  mkdir -p "$ES_SRC"
  if [ -d "$RELICOS_BUILD/es-core" ]; then
    echo "copying ES source from $RELICOS_BUILD"
    rsync -a --exclude CMakeFiles --exclude CMakeCache.txt --exclude Makefile \
      --exclude cmake_install.cmake --exclude '*.a' --exclude '*.so*' --exclude '*.o' \
      --exclude '.stamp_*' --exclude 'CPack*' --exclude '.br_*' --exclude install_manifest.txt \
      "$RELICOS_BUILD/" "$ES_SRC/"
    rm -f "$ES_SRC/emulationstation"
  else
    echo "cloning $ES_REPO @ $ES_COMMIT"
    nix_run "git clone --recurse-submodules $ES_REPO '$ES_SRC' && cd '$ES_SRC' && git checkout --recurse-submodules $ES_COMMIT"
  fi
}

build() {
  [ -d "$ES_SRC/es-core" ] || fetch_source
  mkdir -p "$ES_SRC/build-host"
  echo "building the ES for the host (a few minutes the first time)"
  nix_run "cd '$ES_SRC/build-host' && \
    cmake .. -DGL=ON -DCEC=OFF -DDISABLE_KODI=ON -DENABLE_PULSE=OFF \
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
      -DSDLMIXER_INCLUDE_DIR=\$(pkg-config --variable=includedir SDL2_mixer)/SDL2 && \
    make -j\$(nproc) emulationstation"
  [ -x "$ES_SRC/emulationstation" ] || { echo "build finished but no binary at $ES_SRC/emulationstation" >&2; exit 1; }
  echo "built: $ES_SRC/emulationstation"
}

make_home() {
  python3 "$THEME_DIR/tools/host-preview/make-fake-home.py" "$FAKE_HOME" "$THEME_DIR"
  ln -sfn "$ES_SRC/resources" "$FAKE_HOME/.emulationstation/resources"
}

run() {
  [ -x "$ES_SRC/emulationstation" ] || build
  [ -f "$FAKE_HOME/.emulationstation/es_systems.cfg" ] || make_home
  [ -d "$THEME_DIR/art/fonts" ] && [ -n "$(ls "$THEME_DIR/art/fonts"/*.ttf 2>/dev/null)" ] \
    || echo "note: no fonts in art/fonts, run tools/fetch-fonts.sh for IBM Plex"
  pkill -f "^\./emulationstation --windowed" 2>/dev/null && sleep 1 || true
  echo "opening the ES at 640x480 (log: $FAKE_HOME/.emulationstation/es_log.txt)"
  cd "$ES_SRC"
  # Native Wayland SDL fails to create the GL window; XWayland works.
  # --no-splash skips the ES's loading screen, which is part of the theme
  # (splash.xml). ES_SPLASH=1 keeps it so it can be looked at.
  [ -n "${ES_SPLASH:-}" ] && SPLASH_ARG="" || SPLASH_ARG="--no-splash"
  HOME="$FAKE_HOME" SDL_VIDEODRIVER=x11 nix_run \
    "./emulationstation --windowed --resolution 640 480 $SPLASH_ARG --home '$FAKE_HOME'"
}

case "${1:-run}" in
  run)   run ;;
  build) build ;;
  home)  make_home ;;
  clean) rm -rf "$DIR"; echo "removed $DIR" ;;
  *) echo "usage: $0 [run|build|home|clean]" >&2; exit 2 ;;
esac
