"""Headless frame capture for Super Fox Mario.

Runs the real game logic with a dummy display, drives the player a bit,
then saves a PNG of an actual in-game frame (knight + horse, classic stage).
"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

# The game module ends with a top-level `pygame.quit()` that runs on import
# (it sits after the __main__-guarded loop). Neutralize it so the display and
# font subsystems stay alive for our off-screen rendering.
import pygame as _pg
_pg.quit = lambda: None
try:
    _pg.display.quit = lambda: None
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "super_mario.py")
OUT = os.path.join(HERE, "screenshot_game.png")

import importlib.util
spec = importlib.util.spec_from_file_location("sm", SRC)
sm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sm)

pg = sm.pygame

# The dummy audio driver in this sandbox segfaults on a second .play() call.
# Swap every pygame.mixer.Sound global for a no-op stub so the real game
# logic + rendering still run headlessly.
class _NoSound:
    def play(self, *a, **k):
        return None
    def stop(self, *a, **k):
        return None
    def fadeout(self, *a, **k):
        return None
    def set_volume(self, *a, **k):
        return None
    def get_length(self, *a, **k):
        return 0.0
_stub = _NoSound()
for _name in dir(sm):
    _val = getattr(sm, _name)
    if isinstance(_val, pg.mixer.Sound):
        setattr(sm, _name, _stub)

g = sm.game
g.full_reset()  # fresh stage 1

p = g.player
p.become_knight()
p.mounted = True
p.horse_t = 0          # already mounted -> no entrance slide
p.invuln = 10 ** 9     # never die during capture
p.face = 1

# Drive the sim a little so legs animate and we scroll past some scenery.
# get_pressed() is unavailable under the dummy video driver, and the game keys
# by the SDL keycode (~1e9), so use a defaultdict that returns 0 for misses.
from collections import defaultdict
keys = defaultdict(int)
keys[pg.K_RIGHT] = 1
for i in range(140):
    if i % 35 == 0:
        p.jump_buf = 7
    if i == 40:
        g.throw_boot()
    g.update(keys)

# Keep the hero safely on the ground for a clean composition.
GROUND_Y = sm.GROUND_ROW * sm.TILE - p.h
p.y = float(GROUND_Y)
p.vy = 0.0
p.x = max(p.x, 6 * sm.TILE)

# Center the camera on the hero.
g.camx = max(0.0, min(p.x + p.w / 2 - sm.W / 2, sm.LEVEL_W - sm.W))

tick = 140
camx = g.camx
mode = "normal"
# The dummy driver's display Surface is unusable for blitting, so draw onto a
# fresh off-screen Surface instead (draw_* functions only need a valid Surface).
screen = pg.Surface((sm.W, sm.H))

sm.draw_background(screen, camx, mode)
sm.draw_flag(screen, camx, tick)
sm.draw_tiles(screen, g.tiles, camx, tick)
sm.draw_coins(screen, g.coin_map, camx, tick)
for cp in g.coin_pops:
    pg.draw.ellipse(screen, (255, 210, 40), (cp.x + 10 - camx, cp.y + 8, 20, 24))
    pg.draw.ellipse(screen, (200, 150, 20), (cp.x + 10 - camx, cp.y + 8, 20, 24), 2)
for m in g.mushrooms:
    sm.draw_mushroom(screen, m, camx)
for sw in g.swords:
    sm.draw_sword_item(screen, sw, camx)
for go in g.goombas:
    sm.draw_goomba(screen, go, camx)
if g.boss_active and g.boss:
    sm.draw_boss(screen, g.boss, camx)
for sp in g.spikes:
    sm.draw_spike(screen, sp, camx)
for b in g.boots:
    sm.draw_boot(screen, b, camx)
sm.draw_player(screen, p, camx, g.state)
sm.draw_particles(screen, camx)
sm.update_draw_popups(screen, camx)
sm.draw_hud(screen, g)
sm.draw_boss_hp(screen, g)

pg.image.save(screen, OUT)
print("SAVED", OUT, os.path.getsize(OUT), "bytes")
print("player x,y =", round(p.x), round(p.y), "camx =", round(g.camx), "form =", p.form, "mounted =", p.mounted)
