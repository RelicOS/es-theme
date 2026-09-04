# Previewing the theme on a PC

The theme engine only exists in the Batocera lineage of EmulationStation, so
the preview runs the same fork RelicOS ships, built for x86 and opened in a
640x480 window.

## The short version

```sh
tools/host-preview/preview.sh
```

First run: fetches the ES source (from the RelicOS build tree if present,
otherwise a clone at the pinned commit), builds it inside a `nix-shell`,
generates the fake HOME, opens the window. Later runs just open the window;
each one takes a few seconds for the `nix-shell` to resolve. Everything is
kept in `~/.cache/relicos/es-preview` (override with `ES_PREVIEW_DIR`).
`preview.sh build`, `preview.sh home` and `preview.sh clean` redo the parts.

Edit the theme, press **F5** in the window, see the change. The rest of this
file is what the script does, for when it breaks.

## 1. Build the fork for the host

Source: `knulli-cfw/batocera-emulationstation`, branch `knulli`, the commit
pinned in RelicOS (`system/package/emulationstation/emulationstation.mk`).
If you have the RelicOS build tree, copy `system/output/build/emulationstation-<hash>/`
somewhere and strip the cross-build artifacts (`CMakeFiles`, `CMakeCache.txt`,
`Makefile`, `*.a`, `*.so*`, `*.o`).

```sh
NIXPKGS_ALLOW_INSECURE=1 nix-shell --impure -I nixpkgs=channel:nixos-25.05 \
  -p cmake pkg-config gettext SDL2 SDL2_mixer freeimage freetype libvlc curl \
     rapidjson alsa-lib libGL libGLU udev
```

Inside the shell, from an out-of-tree build directory:

```sh
cmake ../src -DGL=ON -DCEC=OFF -DDISABLE_KODI=ON -DENABLE_PULSE=OFF \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DSDLMIXER_INCLUDE_DIR=$(pkg-config --variable=includedir SDL2_mixer)/SDL2
make -j$(nproc) emulationstation
```

Notes from the first build:

- `freeimage` is marked insecure in nixpkgs; the 25.05 channel still has it.
- The `FindSDL2MIXER` module does not find the nix include layout, hence the
  explicit `SDLMIXER_INCLUDE_DIR`.
- `gettext` must be present, otherwise the ES declares its own `ngettext`
  and the build fails against glibc.
- Build only the `emulationstation` target: the `checkgamesdb` target runs a
  script that assumes an in-source build.
- The binary lands in the **source** directory, next to `resources/`.

## 2. Fake HOME

```sh
tools/host-preview/make-fake-home.py /tmp/es-home /path/to/this/theme
```

## 3. Run

```sh
HOME=/tmp/es-home SDL_VIDEODRIVER=x11 ./emulationstation --windowed \
  --resolution 640 480 --no-splash --home /tmp/es-home
```

- `SDL_VIDEODRIVER=x11`: under native Wayland SDL failed to create the GL
  window ("Invalid window"); XWayland works.
- The loading screen (`splash.xml`) is skipped by `--no-splash`; run
  `ES_SPLASH=1 tools/host-preview/preview.sh` to see it. The game launch
  screen (`gamesplash.xml`) shows whenever a fake ROM is started.
- Keyboard (this fork uses the Nintendo layout, so B is "OK"): arrows move,
  **Esc = OK**, **Enter = back**, F1 = main menu, F2 = options, F5 reloads
  the theme without restarting.
- The games-page layout is read from `GamelistViewStyle` in
  `es_settings.cfg` when the view is created; change it and restart, or use
  the ES menu.

## What the host does not tell you

- The host renders with desktop OpenGL; the R36S uses GLES2. Rounded corners
  and shaders can differ.
- Performance on the A35 (row templates, carousel scrolling) is not measured
  here.
- The ES scales theme fonts by 1.31 on any screen under 720px, on both the
  host and the device; the theme's type scale is pre-divided for that.
