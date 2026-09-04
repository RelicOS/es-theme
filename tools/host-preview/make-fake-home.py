#!/usr/bin/env python3
"""Build a fake EmulationStation HOME for previewing the theme on a PC.

    make-fake-home.py <target-dir> <path-to-this-theme>

Creates <target-dir>/.emulationstation (es_systems.cfg, es_settings.cfg,
es_input.cfg for a keyboard, themes/relicos -> the theme) and
<target-dir>/roms/<system>/ with empty ROM files, gamelist.xml metadata and
generated placeholder covers. Then run the host-built ES with:

    HOME=<target-dir> SDL_VIDEODRIVER=x11 ./emulationstation --windowed \
        --resolution 640 480 --no-splash --home <target-dir>

See host-preview.md for the build recipe and the keyboard mapping.
"""
import os, sys, struct, zlib, random

H = os.path.abspath(sys.argv[1])
THEME = os.path.abspath(sys.argv[2])

def png(path, w, h, rgb):
    def chunk(t, d):
        b = t + d
        return struct.pack(">I", len(d)) + b + struct.pack(">I", zlib.crc32(b) & 0xffffffff)
    rows = []
    for y in range(h):
        row = bytearray(b"\x00")
        for x in range(w):
            edge = x < 6 or y < 6 or x >= w - 6 or y >= h - 6
            stripe = ((x + y) // 14) % 2 == 0
            c = [min(255, v + 40) for v in rgb] if edge else ([v for v in rgb] if stripe else [max(0, v - 18) for v in rgb])
            row += bytes(c)
        rows.append(bytes(row))
    data = b"".join(rows)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(data, 9)) + chunk(b"IEND", b""))

systems = {
 "snes": ("Super Nintendo", ".sfc", [
   ("Aero Fighters","1993","Shooter","1-2",0.7,False),("Axelay","1992","Shooter","1",0.8,False),
   ("Breath of Fire II","1994","RPG","1",0.8,False),("Chrono Trigger","1995","RPG","1",1.0,True),
   ("Contra III","1992","Run and gun","1-2",0.9,False),("Donkey Kong Country","1994","Platform","1-2",0.9,True),
   ("F-Zero","1990","Racing","1",0.8,False),("Illusion of Gaia","1993","Action RPG","1",0.7,False),
   ("Kirby Super Star","1996","Platform","1-2",0.9,False),("Mega Man X","1993","Platform","1",0.9,False),
   ("Secret of Mana","1993","Action RPG","1-3",0.9,True),("Super Metroid","1994","Action adventure","1",1.0,True)]),
 "gb": ("Game Boy", ".gb", [
   ("Tetris","1989","Puzzle","1-2",0.9,True),("Pokemon Red","1996","RPG","1",0.9,False),
   ("Link's Awakening","1993","Action adventure","1",1.0,True),("Kirby's Dream Land","1992","Platform","1",0.7,False),
   ("Metroid II","1991","Action adventure","1",0.8,False)]),
 "psx": ("PlayStation", ".cue", [
   ("Castlevania SotN","1997","Action RPG","1",1.0,True),("Final Fantasy VII","1997","RPG","1",0.9,False),
   ("Crash Bandicoot","1996","Platform","1",0.7,False),("Tekken 3","1998","Fighting","1-2",0.9,False)]),
 "n64": ("Nintendo 64", ".z64", [("Super Mario 64","1996","Platform","1",1.0,True),("Ocarina of Time","1998","Action adventure","1",1.0,True)]),
 "ports": ("Ports", ".sh", [("Doom","1993","FPS","1",0.9,False)]),
}
random.seed(7)
sysxml = ['<?xml version="1.0"?>', '<systemList>']
for name, (full, ext, games) in systems.items():
    d = f"{H}/roms/{name}"; os.makedirs(d, exist_ok=True)
    gl = ['<?xml version="1.0"?>', '<gameList>']
    for i, (title, year, genre, players, rating, fav) in enumerate(games):
        fn = title.replace("'", "").replace(" ", "_") + ext
        open(f"{d}/{fn}", "w").write("x")
        has_img = not (name == "snes" and i in (1, 7))   # a couple without art on purpose
        if has_img:
            w, h = (180, 250) if name != "gb" else (200, 200)
            png(f"{d}/images/{fn}-image.png", w, h, [random.randint(40, 200) for _ in range(3)])
        gl.append(f"  <game><path>./{fn}</path><name>{title}</name>"
                  + (f"<image>./images/{fn}-image.png</image>" if has_img else "")
                  + f"<releasedate>{year}0101T000000</releasedate><genre>{genre}</genre><players>{players}</players><rating>{rating}</rating>"
                  + ("<favorite>true</favorite>" if fav else "") + "<desc>Lorem ipsum.</desc></game>")
    gl.append('</gameList>')
    open(f"{d}/gamelist.xml", "w").write("\n".join(gl))
    sysxml.append(f"  <system><name>{name}</name><fullname>{full}</fullname><path>{d}</path><extension>{ext}</extension><command>/bin/true</command><platform>{name}</platform><theme>{name}</theme></system>")
sysxml.append('</systemList>')
es = f"{H}/.emulationstation"
os.makedirs(f"{es}/themes", exist_ok=True)
link = f"{es}/themes/relicos"
if os.path.islink(link) or os.path.exists(link):
    os.remove(link)
os.symlink(THEME, link)
open(f"{es}/es_systems.cfg", "w").write("\n".join(sysxml))
open(f"{es}/es_settings.cfg", "w").write("""<?xml version="1.0"?>
<config>
  <string name="ThemeSet" value="relicos" />
  <string name="GamelistViewStyle" value="automatic" />
  <string name="TransitionStyle" value="auto" />
  <string name="GameTransitionStyle" value="auto" />
  <bool name="ShowHelpPrompts" value="true" />
  <bool name="audio.bgmusic" value="false" />
  <string name="Language" value="en_US" />
</config>
""")
open(f"{es}/es_input.cfg", "w").write("""<?xml version="1.0"?>
<inputList>
  <inputConfig type="keyboard" deviceName="Keyboard" deviceGUID="-1">
    <input name="up" type="key" id="1073741906" value="1" />
    <input name="down" type="key" id="1073741905" value="1" />
    <input name="left" type="key" id="1073741904" value="1" />
    <input name="right" type="key" id="1073741903" value="1" />
    <input name="a" type="key" id="13" value="1" />
    <input name="b" type="key" id="27" value="1" />
    <input name="x" type="key" id="120" value="1" />
    <input name="y" type="key" id="121" value="1" />
    <input name="start" type="key" id="1073741882" value="1" />
    <input name="select" type="key" id="1073741883" value="1" />
    <input name="pageup" type="key" id="93" value="1" />
    <input name="pagedown" type="key" id="91" value="1" />
  </inputConfig>
</inputList>
""")
print(f"fake home ready at {H}")
