# -*- coding: utf-8 -*-
"""
Super Fox Mario - Two Stages
A Super-Mario-style platformer in pure pygame.

STAGE 1: classic run + Grow mushroom + Boots + Boss fight
STAGE 2 (HIGH RISK): lava fields, spike pits, spiky enemies, a Sword that
turns you into a mounted KNIGHT who can summon a horse and rescue the princess.

All audio is synthesized in code (no external assets).
All art is drawn with primitives (no external images except the logo).
"""

import math
import os
import random
import struct

import pygame

# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()

W, H = 960, 540
TILE = 40
ROWS = 14
GROUND_ROW = ROWS - 2
LEVEL_COLS = 200
LEVEL_W = LEVEL_COLS * TILE

screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Super Fox Mario - Two Stages")
clock = pygame.time.Clock()

def _make_font(name, size):
    """Try the requested font; fall back to a guaranteed-available one.

    Some environments (e.g. headless/minimal installs) lack 'arialblack',
    and pygame's bitmap fallback can fail to render glyphs. This keeps the
    game from crashing and falls back gracefully without changing the look
    on systems that do have the preferred font.
    """
    for cand in (name, "arial", "dejavusans", "liberationsans", None):
        try:
            f = pygame.font.Font(None, size) if cand is None else pygame.font.SysFont(cand, size)
            f.render("?", True, (255, 255, 255))  # verify it can actually render
            return f
        except Exception:
            continue
    return pygame.font.Font(None, size)


FONT = _make_font("arialblack", 20)
BIG_FONT = _make_font("arialblack", 56)
MID_FONT = _make_font("arialblack", 30)
SMALL_FONT = _make_font("arial", 16)

# ---------------------------------------------------------------------------
# Logo (user's platform attribution)
# ---------------------------------------------------------------------------
LOGO_DIR = os.path.dirname(os.path.abspath(__file__))
try:
    _logo_raw = pygame.image.load(os.path.join(LOGO_DIR, "logo.png")).convert_alpha()
    LOGO_SMALL = pygame.transform.smoothscale(_logo_raw, (56, 56))
    LOGO_MED = pygame.transform.smoothscale(_logo_raw, (130, 130))
    LOGO_OK = True
except Exception as _e:
    print("Logo load failed:", _e)
    LOGO_OK = False
    LOGO_SMALL = LOGO_MED = None

# ---------------------------------------------------------------------------
# Sound synthesis
# ---------------------------------------------------------------------------
SR = 44100


def _pack(samples, vol):
    out = bytearray(len(samples) * 2)
    for i, v in enumerate(samples):
        v = max(-1.0, min(1.0, v)) * vol
        struct.pack_into("<h", out, i * 2, int(v * 32767))
    return pygame.mixer.Sound(buffer=bytes(out))


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12.0)


def make_jump():
    n = int(SR * 0.18)
    return _pack([
        (1.0 if math.sin(2 * math.pi * (220 + 480 * (i / n)) * (i / SR)) >= 0 else -1.0)
        * (1 - 0.5 * (i / n)) for i in range(n)], 0.32)


def make_coin():
    n = int(SR * 0.30)
    out = []
    for i in range(n):
        t = i / SR
        f = 988 if t < 0.08 else 1319
        out.append(math.sin(2 * math.pi * f * t) * (1 - i / n) ** 0.5)
    return _pack(out, 0.40)


def make_stomp():
    n = int(SR * 0.15)
    return _pack([
        random.uniform(-1, 1) * math.exp(-10 * (i / n))
        + 0.6 * math.sin(2 * math.pi * (160 - 80 * (i / n)) * (i / SR)) * (1 - i / n)
        for i in range(n)], 0.5)


def make_bump():
    n = int(SR * 0.10)
    return _pack([
        (1.0 if math.sin(2 * math.pi * (150 - 70 * (i / n)) * (i / SR)) >= 0 else -1.0)
        * (1 - i / n) for i in range(n)], 0.4)


def make_break():
    n = int(SR * 0.30)
    return _pack([random.uniform(-1, 1) * math.exp(-6 * (i / n)) for i in range(n)], 0.5)


def make_death():
    n = int(SR * 0.9)
    notes = [76, 74, 72, 70, 67, 64, 60]
    out = []
    seg = n // len(notes)
    for i in range(n):
        f = midi(notes[min(i // seg, len(notes) - 1)])
        p = i / n
        out.append((1.0 if math.sin(2 * math.pi * f * (i / SR)) >= 0 else -1.0) * (1 - p))
    return _pack(out, 0.35)


def make_fanfare():
    notes = [(72, 0.12), (76, 0.12), (79, 0.12), (84, 0.25),
             (79, 0.12), (84, 0.5), (72, 0.4)]
    out = []
    for note, dur in notes:
        m = int(SR * dur)
        for i in range(m):
            env = min(1.0, (m - i) / (SR * 0.06)) * min(1.0, i / (SR * 0.01))
            out.append((1.0 if math.sin(2 * math.pi * midi(note) * (i / SR)) >= 0
                        else -1.0) * 0.8 * env)
    return _pack(out, 0.4)


def make_powerup():
    n = int(SR * 0.45)
    notes = [60, 64, 67, 72, 76]
    out = []
    seg = n // len(notes)
    for i in range(n):
        f = midi(notes[min(i // seg, len(notes) - 1)])
        out.append((1.0 if math.sin(2 * math.pi * f * (i / SR)) >= 0 else -1.0) * (1 - i / n))
    return _pack(out, 0.30)


def make_throw():
    n = int(SR * 0.12)
    return _pack([
        (1.0 if math.sin(2 * math.pi * (600 + 400 * (i / n)) * (i / SR)) >= 0 else -1.0)
        * (1 - i / n) for i in range(n)], 0.30)


def make_pipe():
    n = int(SR * 0.20)
    return _pack([
        math.sin(2 * math.pi * (300 - 200 * (i / n)) * (i / SR)) * (1 - i / n)
        for i in range(n)], 0.35)


def make_boss_hit():
    n = int(SR * 0.20)
    return _pack([
        random.uniform(-1, 1) * math.exp(-8 * (i / n))
        + (1.0 if math.sin(2 * math.pi * (120 - 60 * (i / n)) * (i / SR)) >= 0
           else -1.0) * 0.6 * (1 - i / n) for i in range(n)], 0.5)


def make_boss_roar():
    n = int(SR * 0.6)
    out = []
    for i in range(n):
        t = i / SR
        f = 80 + 30 * math.sin(2 * math.pi * 4 * t)
        out.append((1.0 if math.sin(2 * math.pi * f * t) >= 0 else -1.0)
                   * (1 - i / n) * 0.8 + random.uniform(-0.3, 0.3) * math.exp(-3 * (i / n)))
    return _pack(out, 0.5)


def make_sword_sound():
    n = int(SR * 0.3)
    return _pack([
        (1.0 if math.sin(2 * math.pi * (900 - 500 * (i / n)) * (i / SR)) >= 0 else -1.0)
        * (1 - i / n) for i in range(n)], 0.35)


def make_horse_neigh():
    n = int(SR * 0.4)
    out = []
    for i in range(n):
        t = i / SR
        f = 300 + 120 * math.sin(2 * math.pi * 6 * t) + 200 * (1 - i / n)
        out.append((1.0 if math.sin(2 * math.pi * f * t) >= 0 else -1.0) * (1 - i / n) * 0.5)
    return _pack(out, 0.4)


def make_rescue():
    notes = [(72, 0.12), (76, 0.12), (79, 0.12), (84, 0.2), (79, 0.12),
             (84, 0.12), (88, 0.4), (84, 0.4)]
    out = []
    for note, dur in notes:
        m = int(SR * dur)
        for i in range(m):
            env = min(1.0, (m - i) / (SR * 0.06)) * min(1.0, i / (SR * 0.01))
            out.append((1.0 if math.sin(2 * math.pi * midi(note) * (i / SR)) >= 0
                        else -1.0) * 0.8 * env)
    return _pack(out, 0.42)


def make_music():
    eighth = 0.15
    melody = [72, 76, 79, 76, 81, 79, 76, 72, 74, 77, 81, 77, 79, 77, 74, 71,
              72, 76, 79, 76, 81, 84, 79, 76, 77, 74, 71, 74, 72, 76, 72, 72]
    bass = [48, 43, 45, 43, 41, 43, 48, 43] * 2
    seg = int(SR * eighth)
    n = seg * len(melody)
    out2 = []
    for i in range(n):
        slot = i // seg
        t = (i % seg) / SR
        f_lead = midi(melody[slot])
        f_bass = midi(bass[(slot // 2) % len(bass)])
        env = min(1.0, (i % seg) / (SR * 0.02)) * (1.0 - 0.6 * ((i % seg) / seg))
        lead = (1.0 if math.sin(2 * math.pi * f_lead * t) >= 0 else -1.0)
        tri = 2 * abs(2 * ((f_bass * t) % 1)) - 1
        out2.append((0.5 * lead + 0.45 * tri) * env)
    return _pack(out2, 0.22)


def make_boss_music():
    eighth = 0.22
    melody = [60, 63, 65, 63, 60, 58, 60, 67, 65, 63, 60, 58, 56, 58, 60, 63,
              60, 63, 65, 63, 60, 58, 55, 58, 60, 56, 58, 55, 53, 55, 58, 60]
    bass = [36, 36, 39, 39, 41, 41, 43, 43, 36, 36, 39, 39, 34, 34, 36, 36] * 2
    seg = int(SR * eighth)
    n = seg * len(melody)
    out3 = []
    for i in range(n):
        slot = i // seg
        t = (i % seg) / SR
        f_lead = midi(melody[slot])
        f_bass = midi(bass[(slot // 2) % len(bass)])
        env = min(1.0, (i % seg) / (SR * 0.04)) * (1.0 - 0.7 * ((i % seg) / seg))
        lead = (1.0 if math.sin(2 * math.pi * f_lead * t) >= 0 else -1.0)
        saw = 2 * ((f_bass * t) % 1) - 1
        out3.append((0.45 * lead + 0.55 * saw) * env * 0.9)
    return _pack(out3, 0.30)


S_JUMP = make_jump()
S_COIN = make_coin()
S_STOMP = make_stomp()
S_BUMP = make_bump()
S_BREAK = make_break()
S_DEATH = make_death()
S_WIN = make_fanfare()
S_POWERUP = make_powerup()
S_THROW = make_throw()
S_PIPE = make_pipe()
S_BOSS_HIT = make_boss_hit()
S_BOSS_ROAR = make_boss_roar()
S_SWORD = make_sword_sound()
S_HORSE = make_horse_neigh()
S_RESCUE = make_rescue()
MUSIC = make_music()
BOSS_MUSIC = make_boss_music()

# ---------------------------------------------------------------------------
# Level constants
# ---------------------------------------------------------------------------
SOLID = {"#", "B", "?", "U", "P", "X"}
MUSHROOM_BLOCKS = {(9, 6), (31, 6), (92, 6)}
SWORD_BLOCK = (70, 8)      # stage-1 block that yields the Sword

FLAG_COL = 124
FLAG_X = FLAG_COL * TILE + TILE // 2

BOSS_COL = 138
BOSS_ARENA_LEFT = 126
BOSS_ARENA_RIGHT = 158
BOSS_ACTIVATE_COL = 125

GIR_COL = 134             # stage-2 princess cage column


def build_level(stage):
    """Returns (tiles, coins, goombas, spikies, sword_blocks, boss_spawn, gf_pos)."""
    tiles = {}
    coins = set()
    goombas = []
    spikies = []
    sword_blocks = set()
    boss_spawn = None
    gf_pos = None

    def ground(c0, c1):
        for c in range(c0, c1 + 1):
            tiles[(c, GROUND_ROW)] = "#"
            tiles[(c, GROUND_ROW + 1)] = "#"

    def blocks(c0, row, s):
        for i, ch in enumerate(s):
            if ch != ".":
                tiles[(c0 + i, row)] = ch

    def pipe(c, h):
        for r in range(GROUND_ROW - h, GROUND_ROW):
            tiles[(c, r)] = "P"
            tiles[(c + 1, r)] = "P"

    def stairs_up(c, h):
        for i in range(h):
            for r in range(GROUND_ROW - (i + 1), GROUND_ROW):
                tiles[(c + i, r)] = "#"

    def wall(c0, c1, row0, row1):
        for c in range(c0, c1 + 1):
            for r in range(row0, row1 + 1):
                tiles[(c, r)] = "X"

    def coin_row(c0, row, count):
        for i in range(count):
            coins.add((c0 + i, row))

    def plat(c0, c1, row):
        for c in range(c0, c1 + 1):
            tiles[(c, row)] = "#"

    def lava(c0, c1):
        for c in range(c0, c1 + 1):
            tiles[(c, GROUND_ROW)] = "L"
            tiles[(c, GROUND_ROW + 1)] = "L"

    def spike(c):
        tiles[(c, GROUND_ROW - 1)] = "S"

    if stage == 1:
        ground(0, 24)
        blocks(8, 6, "B?B?B")
        coin_row(9, 4, 3)
        blocks(16, 8, "?")
        pipe(20, 2)
        goombas += [15]

        ground(28, 60)
        blocks(30, 6, "?B?B?")
        coin_row(31, 4, 3)
        goombas += [33, 37]
        pipe(40, 3)
        pipe(44, 2)
        blocks(52, 6, "BBBB")
        coin_row(52, 5, 4)
        goombas += [50, 57]

        ground(64, 100)
        blocks(70, 8, "?")          # <-- SWORD block
        blocks(74, 6, "B?B")
        coin_row(74, 4, 3)
        goombas += [72, 78, 82]
        pipe(85, 3)
        blocks(92, 6, "?B?")
        coin_row(92, 4, 3)
        goombas += [95]

        ground(104, 123)
        goombas += [110, 114]
        stairs_up(118, 4)

        wall(125, 125, 9, 11)
        ground(126, BOSS_ARENA_RIGHT)
        wall(BOSS_ARENA_LEFT, BOSS_ARENA_LEFT, 4, GROUND_ROW - 1)
        wall(BOSS_ARENA_RIGHT, BOSS_ARENA_RIGHT, 4, GROUND_ROW - 1)

        sword_blocks = {SWORD_BLOCK}
        boss_spawn = (BOSS_COL, GROUND_ROW)

    else:  # STAGE 2 - HIGH RISK
        ground(0, 14)
        coin_row(2, 4, 3)
        lava(15, 26)
        plat(17, 19, 9)
        plat(21, 24, 8)
        ground(27, 40)
        spike(33); spike(34); spike(35)
        goombas += [30, 38]
        lava(41, 52)
        plat(43, 45, 9)
        plat(47, 50, 8)
        ground(53, 70)
        spikies += [58, 64]
        lava(71, 84)
        plat(73, 75, 9)
        plat(77, 80, 8)
        plat(82, 84, 10)
        ground(85, 104)
        goombas += [90, 96, 100]
        spike(92); spike(93)
        lava(105, 118)
        plat(107, 109, 9)
        plat(111, 114, 8)
        plat(116, 118, 10)
        ground(119, LEVEL_COLS - 1)
        gf_pos = (GIR_COL, GROUND_ROW - 1)

    return tiles, coins, goombas, spikies, sword_blocks, boss_spawn, gf_pos


# ---------------------------------------------------------------------------
# Particles / popups
# ---------------------------------------------------------------------------
particles = []
popups = []


def spawn_particles(x, y, colors, count, speed=4, grav=0.25, life=40, size=4):
    for _ in range(count):
        a = random.uniform(0, math.tau)
        s = random.uniform(1, speed)
        particles.append({
            "x": x, "y": y, "vx": math.cos(a) * s, "vy": math.sin(a) * s - 2,
            "life": random.randint(life // 2, life), "max": life,
            "color": random.choice(colors),
            "size": random.randint(max(2, size - 2), size + 2), "grav": grav})


def poof(x, y):
    spawn_particles(x, y, [(255, 255, 255), (230, 230, 230)], 8, 3, 0.1, 25, 5)


def sparkle(x, y):
    spawn_particles(x, y, [(255, 220, 60), (255, 255, 160)], 10, 3, 0.05, 30, 4)


def brick_debris(x, y):
    spawn_particles(x, y, [(170, 80, 40), (200, 110, 60), (120, 55, 25)], 14, 5, 0.35, 55, 6)


def boss_hit_particles(x, y):
    spawn_particles(x, y, [(255, 60, 60), (255, 150, 80), (180, 30, 30)], 24, 6, 0.3, 60, 6)


def steam_particles(x, y):
    spawn_particles(x, y, [(255, 120, 30), (255, 200, 60), (200, 60, 20)], 10, 2, -0.05, 40, 6)


def confetti_burst():
    for _ in range(6):
        particles.append({
            "x": random.randint(0, W), "y": -10, "vx": random.uniform(-1, 1),
            "vy": random.uniform(1, 3), "life": 160, "max": 160,
            "color": random.choice([(255, 80, 80), (80, 255, 120), (90, 150, 255),
                                    (255, 220, 60), (255, 130, 240)]),
            "size": random.randint(4, 8), "grav": 0.02})


def update_particles():
    for p in particles[:]:
        p["x"] += p["vx"]; p["y"] += p["vy"]; p["vy"] += p["grav"]; p["life"] -= 1
        if p["life"] <= 0:
            particles.remove(p)


def draw_particles(surf, camx):
    for p in particles:
        a = p["life"] / p["max"]
        s = max(1, int(p["size"] * a))
        surf.fill(p["color"], (int(p["x"] - camx), int(p["y"]), s, s))


def popup(x, y, text, color=(255, 255, 255)):
    popups.append({"x": x, "y": y, "text": text, "life": 50, "color": color})


def update_draw_popups(surf, camx):
    for p in popups[:]:
        p["y"] -= 0.8
        p["life"] -= 1
        if p["life"] <= 0:
            popups.remove(p)
            continue
        img = FONT.render(p["text"], True, p["color"])
        surf.blit(img, (p["x"] - camx - img.get_width() // 2, p["y"]))


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------


class CoinPop:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.vy = -9
        self.life = 30
        self.dead = False

    def update(self):
        self.y += self.vy
        self.vy += 0.5
        self.life -= 1
        if self.life <= 0:
            self.dead = True
            sparkle(self.x + TILE // 2, self.y + TILE // 2)


class Mushroom:
    def __init__(self, x, y):
        self.x, self.y = x, y - TILE
        self.target_y = y
        self.appearing = True
        self.vx = 1.5
        self.vy = 0
        self.w = 28
        self.h = 28
        self.dead = False

    def update(self, tiles):
        if self.appearing:
            self.y += 1
            if self.y >= self.target_y:
                self.y = self.target_y
                self.appearing = False
            return
        self.vy = min(self.vy + 0.5, 10)
        self.x += self.vx
        r = pygame.Rect(int(self.x), int(self.y), self.w, self.h)
        for c in range(r.left // TILE, (r.right - 1) // TILE + 1):
            for rr in range(r.top // TILE, (r.bottom - 1) // TILE + 1):
                if tiles.get((c, rr)) in SOLID:
                    t = pygame.Rect(c * TILE, rr * TILE, TILE, TILE)
                    if r.colliderect(t):
                        if self.vx > 0:
                            self.x = t.left - self.w - 0.01
                        else:
                            self.x = t.right + 0.01
                        self.vx *= -1
        self.y += self.vy
        r = pygame.Rect(int(self.x), int(self.y), self.w, self.h)
        for c in range(r.left // TILE, (r.right - 1) // TILE + 1):
            for rr in range(r.top // TILE, (r.bottom - 1) // TILE + 1):
                if tiles.get((c, rr)) in SOLID:
                    t = pygame.Rect(c * TILE, rr * TILE, TILE, TILE)
                    if r.colliderect(t):
                        if self.vy > 0:
                            self.y = t.top - self.h
                            self.vy = 0
                        elif self.vy < 0:
                            self.y = t.bottom + 0.01
                            self.vy = 0
        ahead_x = self.x + (self.w + 4 if self.vx > 0 else -4)
        below = tiles.get((int(ahead_x // TILE), int((self.y + self.h + 6) // TILE)))
        if below not in SOLID:
            self.vx *= -1


class Sword:
    """Power-up that turns the player into a KNIGHT."""
    def __init__(self, x, y):
        self.x, self.y = x, y - TILE
        self.target_y = y
        self.appearing = True
        self.vx = 1.5
        self.vy = 0
        self.w = 28
        self.h = 28
        self.dead = False
        self.spin = 0

    def update(self, tiles):
        self.spin += 0.2
        if self.appearing:
            self.y += 1
            if self.y >= self.target_y:
                self.y = self.target_y
                self.appearing = False
            return
        self.vy = min(self.vy + 0.5, 10)
        self.x += self.vx
        r = pygame.Rect(int(self.x), int(self.y), self.w, self.h)
        for c in range(r.left // TILE, (r.right - 1) // TILE + 1):
            for rr in range(r.top // TILE, (r.bottom - 1) // TILE + 1):
                if tiles.get((c, rr)) in SOLID:
                    t = pygame.Rect(c * TILE, rr * TILE, TILE, TILE)
                    if r.colliderect(t):
                        if self.vx > 0:
                            self.x = t.left - self.w - 0.01
                        else:
                            self.x = t.right + 0.01
                        self.vx *= -1
        self.y += self.vy
        r = pygame.Rect(int(self.x), int(self.y), self.w, self.h)
        for c in range(r.left // TILE, (r.right - 1) // TILE + 1):
            for rr in range(r.top // TILE, (r.bottom - 1) // TILE + 1):
                if tiles.get((c, rr)) in SOLID:
                    t = pygame.Rect(c * TILE, rr * TILE, TILE, TILE)
                    if r.colliderect(t):
                        if self.vy > 0:
                            self.y = t.top - self.h
                            self.vy = 0
                        elif self.vy < 0:
                            self.y = t.bottom + 0.01
                            self.vy = 0
        ahead_x = self.x + (self.w + 4 if self.vx > 0 else -4)
        below = tiles.get((int(ahead_x // TILE), int((self.y + self.h + 6) // TILE)))
        if below not in SOLID:
            self.vx *= -1


class Boot:
    """Thrown by Big/Knight player - bigger now, bounces, kills enemies."""
    def __init__(self, x, y, direction):
        self.x, self.y = x, y
        self.vx = direction * 8.0
        self.vy = -4.0
        self.w = 22
        self.h = 16
        self.dead = False
        self.bounces = 3
        self.life = 130

    def update(self, tiles):
        self.vy = min(self.vy + 0.5, 10)
        self.x += self.vx
        r = pygame.Rect(int(self.x), int(self.y), self.w, self.h)
        for c in range(r.left // TILE, (r.right - 1) // TILE + 1):
            for rr in range(r.top // TILE, (r.bottom - 1) // TILE + 1):
                if tiles.get((c, rr)) in SOLID:
                    t = pygame.Rect(c * TILE, rr * TILE, TILE, TILE)
                    if r.colliderect(t):
                        if self.vx > 0:
                            self.x = t.left - self.w - 0.01
                        else:
                            self.x = t.right + 0.01
                        self.vx *= -1
        self.y += self.vy
        r = pygame.Rect(int(self.x), int(self.y), self.w, self.h)
        for c in range(r.left // TILE, (r.right - 1) // TILE + 1):
            for rr in range(r.top // TILE, (r.bottom - 1) // TILE + 1):
                if tiles.get((c, rr)) in SOLID:
                    t = pygame.Rect(c * TILE, rr * TILE, TILE, TILE)
                    if r.colliderect(t):
                        if self.vy > 0:
                            self.y = t.top - self.h
                            self.vy = -7
                            self.bounces -= 1
                            if self.bounces <= 0:
                                self.dead = True
                        elif self.vy < 0:
                            self.y = t.bottom + 0.01
                            self.vy = 0
        self.life -= 1
        if self.life <= 0:
            self.dead = True


class Spike:
    def __init__(self, x, y, vx):
        self.x, self.y, self.vx = x, y, vx
        self.vy = 0
        self.w, self.h = 18, 18
        self.dead = False
        self.life = 240

    def update(self, tiles):
        self.vy = min(self.vy + 0.4, 9)
        self.x += self.vx
        self.y += self.vy
        r = pygame.Rect(int(self.x), int(self.y), self.w, self.h)
        for c in range(r.left // TILE, (r.right - 1) // TILE + 1):
            for rr in range(r.top // TILE, (r.bottom - 1) // TILE + 1):
                if tiles.get((c, rr)) in SOLID:
                    t = pygame.Rect(c * TILE, rr * TILE, TILE, TILE)
                    if r.colliderect(t) and self.vy > 0:
                        self.y = t.top - self.h
                        self.vy = -5
        self.life -= 1
        if self.x < 0 or self.x > LEVEL_W or self.life <= 0:
            self.dead = True


class Goomba:
    def __init__(self, col):
        self.x = col * TILE + 4.0
        self.y = GROUND_ROW * TILE - 30
        self.w, self.h = 32, 30
        self.vx = -1.3
        self.vy = 0.0
        self.on_ground = False
        self.squash_t = 0
        self.walk_t = random.random() * 10
        self.spiky = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, tiles):
        if self.squash_t:
            self.squash_t -= 1
            return
        self.walk_t += 0.15
        self.vy = min(self.vy + 0.5, 12)
        self.x += self.vx
        r = self.rect
        for c in range(r.left // TILE, (r.right - 1) // TILE + 1):
            for rr in range(r.top // TILE, (r.bottom - 1) // TILE + 1):
                if tiles.get((c, rr)) in SOLID:
                    t = pygame.Rect(c * TILE, rr * TILE, TILE, TILE)
                    if r.colliderect(t):
                        if self.vx > 0:
                            self.x = t.left - self.w - 0.01
                        else:
                            self.x = t.right + 0.01
                        self.vx *= -1
        if self.on_ground:
            ahead_x = self.x + (self.w + 6 if self.vx > 0 else -6)
            below = tiles.get((int(ahead_x // TILE), int((self.y + self.h + 6) // TILE)))
            if below not in SOLID:
                self.vx *= -1
        self.y += self.vy
        self.on_ground = False
        r = self.rect
        for c in range(r.left // TILE, (r.right - 1) // TILE + 1):
            for rr in range(r.top // TILE, (r.bottom - 1) // TILE + 1):
                if tiles.get((c, rr)) in SOLID:
                    t = pygame.Rect(c * TILE, rr * TILE, TILE, TILE)
                    if r.colliderect(t):
                        if self.vy > 0:
                            self.y = t.top - self.h
                            self.vy = 0
                            self.on_ground = True
                        elif self.vy < 0:
                            self.y = t.bottom + 0.01
                            self.vy = 0


class Spiky(Goomba):
    def __init__(self, col):
        super().__init__(col)
        self.spiky = True
        self.vx = -1.6


class Boss:
    def __init__(self, col):
        self.x = col * TILE
        self.w, self.h = 80, 80
        self.y = -self.h                # drop in from above the arena
        self.vx = -1.5
        self.vy = 0
        self.on_ground = False
        self.landed = False             # puff dust on first landing
        self.hp = 6
        self.max_hp = 6
        self.flash_t = 0
        self.attack_t = 90
        self.jump_t = 180
        self.dead = False
        self.death_t = 0
        self.face = -1
        self.walk_t = 0

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, tiles, player):
        if self.dead:
            self.death_t += 1
            return None
        if self.flash_t:
            self.flash_t -= 1
        self.walk_t += 0.1
        self.vy = min(self.vy + 0.5, 12)
        if self.on_ground:
            self.x += self.vx
            r = self.rect
            for c in range(r.left // TILE, (r.right - 1) // TILE + 1):
                for rr in range(r.top // TILE, (r.bottom - 1) // TILE + 1):
                    if tiles.get((c, rr)) in SOLID:
                        t = pygame.Rect(c * TILE, rr * TILE, TILE, TILE)
                        if r.colliderect(t):
                            if self.vx > 0:
                                self.x = t.left - self.w - 0.01
                            else:
                                self.x = t.right + 0.01
                            self.vx *= -1
                            self.face = -self.face
            ahead_x = self.x + (self.w + 4 if self.vx > 0 else -4)
            below = tiles.get((int(ahead_x // TILE), int((self.y + self.h + 6) // TILE)))
            if below not in SOLID:
                self.vx *= -1
                self.face = -self.face
            if player.x < self.x:
                self.face = -1
                self.vx = -abs(self.vx)
            else:
                self.face = 1
                self.vx = abs(self.vx)
        self.y += self.vy
        self.on_ground = False
        r = self.rect
        for c in range(r.left // TILE, (r.right - 1) // TILE + 1):
            for rr in range(r.top // TILE, (r.bottom - 1) // TILE + 1):
                if tiles.get((c, rr)) in SOLID:
                    t = pygame.Rect(c * TILE, rr * TILE, TILE, TILE)
                    if r.colliderect(t):
                        if self.vy > 0:
                            self.y = t.top - self.h
                            self.vy = 0
                            self.on_ground = True
                        elif self.vy < 0:
                            self.y = t.bottom + 0.01
                            self.vy = 0
        if not self.landed and self.on_ground:
            self.landed = True
            poof(self.x + self.w // 2, self.y + self.h)
        self.jump_t -= 1
        if self.jump_t <= 0 and self.on_ground and abs(player.x - self.x) < 220:
            self.vy = -11
            self.jump_t = random.randint(140, 220)
        self.attack_t -= 1
        if self.attack_t <= 0 and self.on_ground:
            self.attack_t = random.randint(90, 160)
            direction = 1 if player.x > self.x else -1
            return Spike(self.x + (self.w // 2 + 6 if direction > 0 else -24),
                         self.y + 30, direction * 5.5)
        return None

    def take_damage(self):
        if self.flash_t > 0 or self.dead:
            return
        self.hp -= 1
        self.flash_t = 50
        boss_hit_particles(self.x + self.w // 2, self.y + self.h // 2)
        S_BOSS_HIT.play()
        if self.hp <= 0:
            self.dead = True
            self.death_t = 0
            for _ in range(10):
                boss_hit_particles(self.x + self.w // 2, self.y + self.h // 2)


class Player:
    SMALL_H = 36
    BIG_H = 56

    def __init__(self):
        self.form = "small"      # small | big | knight
        self.mounted = False
        self.w = 28
        self.h = self.SMALL_H
        self.x = 2.0 * TILE
        self.y = float(GROUND_ROW * TILE - self.h)
        self.vx = 0.0
        self.vy = 0.0
        self.face = 1
        self.on_ground = False
        self.coyote = 0
        self.jump_buf = 0
        self.run_t = 0.0
        self.squash = 0.0
        self.invuln = 0
        self.grow_t = 0
        self.horse_t = 0        # >0 while the horse is galloping in from the left

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def _resize(self, h):
        bottom = self.y + self.h
        self.h = h
        self.y = bottom - self.h

    def grow(self):
        if self.form in ("big", "knight"):
            popup(self.x + self.w // 2, self.y, "POWER!", (255, 255, 160))
            return
        self.form = "big"
        self._resize(self.BIG_H)
        self.grow_t = 25
        S_POWERUP.play()

    def become_knight(self):
        was = self.form
        self.form = "knight"
        if was == "small":
            self._resize(self.BIG_H)
        self.grow_t = 30
        S_SWORD.play()
        popup(self.x + self.w // 2, self.y, "KNIGHT!", (190, 190, 255))

    def toggle_mount(self):
        if self.form != "knight":
            return
        self.mounted = not self.mounted
        if self.mounted:
            self.horse_t = 26          # horse gallops in from the left
            S_HORSE.play()             # neigh on summon
            popup(self.x + self.w // 2, self.y, "CHARGE!", (220, 180, 120))
        else:
            self.horse_t = 0
            poof(self.x + self.w // 2, self.y + self.h)

    def take_damage(self, game):
        if self.invuln > 0 or self.grow_t > 0:
            return False
        if self.form == "knight":
            self.form = "big"
            self.mounted = False
            self._resize(self.BIG_H)
            self.invuln = 120
            self.grow_t = 25
            S_PIPE.play()
            return False
        if self.form == "big":
            self.form = "small"
            self._resize(self.SMALL_H)
            self.invuln = 120
            self.grow_t = 25
            S_PIPE.play()
            return False
        game.kill_player()
        return True

    def update(self, keys, tiles, game):
        max_sp = 9.5 if self.mounted else 5.2
        jump_v = -17.0 if self.mounted else -14.8
        cut = -6.0 if self.mounted else -5.0

        accel = 0.7 if self.mounted else 0.55
        friction = 0.82

        left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        if left:
            self.vx -= accel
            self.face = -1
        if right:
            self.vx += accel
            self.face = 1
        if not left and not right:
            self.vx *= friction
            if abs(self.vx) < 0.1:
                self.vx = 0
        self.vx = max(-max_sp, min(max_sp, self.vx))

        if self.on_ground:
            self.coyote = 7
        else:
            self.coyote = max(0, self.coyote - 1)
        self.jump_buf = max(0, self.jump_buf - 1)

        if self.jump_buf > 0 and self.coyote > 0:
            self.vy = jump_v
            self.coyote = 0
            self.jump_buf = 0
            self.on_ground = False
            S_JUMP.play()
            poof(self.x + self.w / 2, self.y + self.h)

        if not (keys[pygame.K_SPACE] or keys[pygame.K_UP]
                or keys[pygame.K_w]) and self.vy < cut:
            self.vy = cut

        self.vy = min(self.vy + 0.58, 14)

        self.x += self.vx
        self.x = max(0, min(self.x, LEVEL_W - self.w))
        r = self.rect
        for c in range(r.left // TILE, (r.right - 1) // TILE + 1):
            for rr in range(r.top // TILE, (r.bottom - 1) // TILE + 1):
                if tiles.get((c, rr)) in SOLID:
                    t = pygame.Rect(c * TILE, rr * TILE, TILE, TILE)
                    if r.colliderect(t):
                        if self.vx > 0:
                            self.x = float(t.left - self.w)
                        elif self.vx < 0:
                            self.x = float(t.right)
                        self.vx = 0

        was_air = not self.on_ground
        fall_speed = self.vy
        self.y += self.vy
        self.on_ground = False
        r = self.rect
        for c in range(r.left // TILE, (r.right - 1) // TILE + 1):
            for rr in range(r.top // TILE, (r.bottom - 1) // TILE + 1):
                if tiles.get((c, rr)) in SOLID:
                    t = pygame.Rect(c * TILE, rr * TILE, TILE, TILE)
                    if r.colliderect(t):
                        if self.vy > 0:
                            self.y = float(t.top - self.h)
                            self.vy = 0
                            self.on_ground = True
                        elif self.vy < 0:
                            self.y = float(t.bottom)
                            self.vy = 0
                            game.bump_block(c, rr)

        if was_air and self.on_ground and fall_speed > 6:
            self.squash = 6
            poof(self.x + self.w / 2, self.y + self.h)

        self.squash = max(0, self.squash - 1)
        self.invuln = max(0, self.invuln - 1)
        self.grow_t = max(0, self.grow_t - 1)
        if abs(self.vx) > 0.5 and self.on_ground:
            self.run_t += abs(self.vx) * 0.05

        # horse entrance: gallop in from the left, kicking up dust
        if self.mounted and self.horse_t > 0:
            self.horse_t -= 1
            if self.horse_t % 3 == 0:
                off = -self.horse_t * 9
                poof(self.x + off + self.w // 2, self.y + self.h)
            if self.horse_t == 0:
                poof(self.x + self.w // 2, self.y + self.h)



# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------


class Game:
    def __init__(self):
        self.full_reset()

    def full_reset(self):
        self.score = 0
        self.coins = 0
        self.lives = 3
        self.time = 0.0
        self.stage = 1
        self.state = "play"
        self.state_t = 0
        self.boss_active = False
        self.boss_music_started = False
        self.shake = 0
        self.load_stage(1)
        MUSIC.play(-1)

    def load_stage(self, stage):
        (self.tiles, self.coin_map, g_spawns, sp_spawns,
         self.sword_blocks, boss_spawn, gf_pos) = build_level(stage)
        self.goombas = [Goomba(c) for c in g_spawns]
        self.spikies = [Spiky(c) for c in sp_spawns]
        self.mushrooms = []
        self.swords = []
        self.boots = []
        self.spikes = []
        self.coin_pops = []
        self.bump_anims = {}
        self.player = Player()
        self.player.invuln = 90
        self.camx = 0.0
        self.boss = Boss(boss_spawn[0]) if boss_spawn else None
        self.boss_active = (stage == 1)
        self.boss_music_started = False
        self.girlfriend = Girlfriend(gf_pos) if gf_pos else None

    def reset_level(self):
        # respawn after death (keep stage/score/lives)
        self.load_stage(self.stage)
        if self.stage == 1:
            MUSIC.play(-1)
        else:
            BOSS_MUSIC.play(-1)

    def bump_block(self, c, r):
        ch = self.tiles.get((c, r))
        cx, cy = c * TILE, r * TILE
        if ch == "?":
            self.tiles[(c, r)] = "U"
            if (c, r) in self.sword_blocks:
                self.swords.append(Sword(cx, cy))
                S_SWORD.play()
                self.score += 1000
                popup(cx + TILE // 2, cy - TILE, "+1000", (190, 190, 255))
            elif (c, r) in MUSHROOM_BLOCKS:
                self.mushrooms.append(Mushroom(cx, cy))
                S_POWERUP.play()
                self.score += 1000
                popup(cx + TILE // 2, cy - TILE, "+1000", (255, 100, 200))
            else:
                self.coin_pops.append(CoinPop(cx, cy - TILE))
                self.coins += 1
                self.score += 200
                S_COIN.play()
                popup(cx + TILE // 2, cy - TILE, "+200", (255, 220, 60))
        elif ch == "B":
            del self.tiles[(c, r)]
            brick_debris(cx + TILE // 2, cy + TILE // 2)
            S_BREAK.play()
            self.shake = 8
            self.score += 50
        else:
            S_BUMP.play()
        self.bump_anims[(c, r)] = 10

    def kill_player(self):
        if self.state != "play" or self.player.invuln > 0:
            return
        self.state = "dying"
        self.state_t = 0
        self.player.vy = -11
        MUSIC.stop()
        BOSS_MUSIC.stop()
        self.boss_music_started = False
        S_DEATH.play()

    def advance_stage(self):
        self.stage = 2
        self.boss_active = False
        self.state = "transition"
        self.state_t = 0
        MUSIC.stop()
        BOSS_MUSIC.stop()
        self.load_stage(2)
        BOSS_MUSIC.play(-1)

    def win(self):
        if self.state != "play":
            return
        self.state = "rescue"
        self.state_t = 0
        self.score += 3000
        MUSIC.stop()
        BOSS_MUSIC.stop()
        S_RESCUE.play()

    def throw_boot(self):
        p = self.player
        if p.form == "small" or self.state != "play":
            return
        if len(self.boots) >= 2:
            return
        bx = p.x + (p.w - 22 if p.face > 0 else 0)
        by = p.y + p.h * 0.5
        self.boots.append(Boot(bx, by, p.face))
        S_THROW.play()

    def update(self, keys):
        p = self.player

        if self.state == "transition":
            self.state_t += 1
            if self.state_t > 150:
                self.state = "play"
            return

        if self.state == "play":
            self.time += 1 / 60
            p.update(keys, self.tiles, self)

            pr = p.rect
            c0, c1 = pr.left // TILE, (pr.right - 1) // TILE
            r0, r1 = pr.top // TILE, (pr.bottom - 1) // TILE
            for c in range(c0, c1 + 1):
                for r in range(r0, r1 + 1):
                    if (c, r) in self.coin_map:
                        self.coin_map.remove((c, r))
                        self.coins += 1
                        self.score += 100
                        S_COIN.play()
                        sparkle(c * TILE + TILE // 2, r * TILE + TILE // 2)
                        popup(c * TILE + TILE // 2, r * TILE, "+100", (255, 220, 60))

            # enemies (goombas + spikies)
            for g in self.goombas[:]:
                g.update(self.tiles)
                if g.y > ROWS * TILE + 200:
                    self.goombas.remove(g)
                    continue
                if g.squash_t == 0 and pr.colliderect(g.rect):
                    if p.mounted and p.form == "knight":
                        g.squash_t = 30
                        self.score += 100
                        S_STOMP.play()
                        poof(g.rect.centerx, g.rect.centery)
                    elif g.spiky:
                        if p.form in ("big", "knight") and p.vy > 0 and pr.bottom - g.rect.top < 20:
                            p.take_damage(self)
                        elif p.form == "knight":
                            g.squash_t = 30
                            self.score += 200
                            S_STOMP.play()
                            poof(g.rect.centerx, g.rect.centery)
                        else:
                            p.take_damage(self)
                    else:
                        if p.form in ("big", "knight") and p.vy > 0 and pr.bottom - g.rect.top < 20:
                            g.squash_t = 30
                            p.vy = -8.5
                            self.score += 100
                            S_STOMP.play()
                            self.shake = 6
                            poof(g.rect.centerx, g.rect.centery)
                            popup(g.rect.centerx, g.rect.top, "+100")
                        else:
                            p.take_damage(self)
                if g.squash_t == 1:
                    self.goombas.remove(g)

            for s in self.spikies[:]:
                s.update(self.tiles)
                if s.y > ROWS * TILE + 200:
                    self.spikies.remove(s)
                    continue
                if s.squash_t == 0 and pr.colliderect(s.rect):
                    if p.mounted and p.form == "knight":
                        s.squash_t = 30
                        self.score += 150
                        S_STOMP.play()
                    elif p.form == "knight":
                        s.squash_t = 30
                        self.score += 200
                        S_STOMP.play()
                    else:
                        p.take_damage(self)

            # mushrooms / swords
            for m in self.mushrooms[:]:
                m.update(self.tiles)
                if m.dead or m.y > ROWS * TILE + 200:
                    self.mushrooms.remove(m)
                    continue
                if pr.colliderect(pygame.Rect(int(m.x), int(m.y), m.w, m.h)):
                    p.grow()
                    self.mushrooms.remove(m)
                    sparkle(m.x + m.w // 2, m.y + m.h // 2)

            for sw in self.swords[:]:
                sw.update(self.tiles)
                if sw.dead or sw.y > ROWS * TILE + 200:
                    self.swords.remove(sw)
                    continue
                if pr.colliderect(pygame.Rect(int(sw.x), int(sw.y), sw.w, sw.h)):
                    p.become_knight()
                    self.swords.remove(sw)
                    sparkle(sw.x + sw.w // 2, sw.y + sw.h // 2)

            # boots
            for b in self.boots[:]:
                b.update(self.tiles)
                if b.dead or b.x < -50 or b.x > LEVEL_W + 50:
                    self.boots.remove(b)
                    continue
                br = pygame.Rect(int(b.x), int(b.y), b.w, b.h)
                hit = False
                for g in self.goombas + self.spikies:
                    if g.squash_t == 0 and br.colliderect(g.rect):
                        g.squash_t = 30
                        self.score += 200
                        S_STOMP.play()
                        hit = True
                        break
                if hit:
                    self.boots.remove(b)
                    continue
                if self.boss and not self.boss.dead and br.colliderect(self.boss.rect):
                    self.boss.take_damage()
                    self.score += 200
                    self.boots.remove(b)

            for cp in self.coin_pops[:]:
                cp.update()
                if cp.dead:
                    self.coin_pops.remove(cp)

            # hazards: lava + spikes
            for c in range(c0, c1 + 1):
                for r in range(r0, r1 + 1):
                    ch = self.tiles.get((c, r))
                    if ch == "L":
                        self.player.invuln = 0
                        self.kill_player()
                    elif ch == "S":
                        p.take_damage(self)

            # pit death
            if p.y > ROWS * TILE + 120:
                self.player.invuln = 0
                self.kill_player()

            # boss
            if self.boss_active and self.boss and not self.boss.dead:
                new_spike = self.boss.update(self.tiles, p)
                if new_spike is not None:
                    self.spikes.append(new_spike)
                br = self.boss.rect
                if pr.colliderect(br):
                    if p.form in ("big", "knight") and \
                       (p.vy > 0 and pr.bottom - br.top < 24 or p.form == "knight"):
                        self.boss.take_damage()
                        if not p.mounted:
                            p.vy = -10
                        self.score += 300
                        popup(br.centerx, br.top, "BOOM!")
                    else:
                        p.take_damage(self)
            elif self.boss_active and self.boss and self.boss.dead and self.state == "play":
                if self.boss.death_t > 60:
                    self.advance_stage()

            for sp in self.spikes[:]:
                sp.update(self.tiles)
                if sp.dead:
                    self.spikes.remove(sp)
                    continue
                sr = pygame.Rect(int(sp.x), int(sp.y), sp.w, sp.h)
                if pr.colliderect(sr):
                    p.take_damage(self)
                    self.spikes.remove(sp)

            # girlfriend rescue (stage 2)
            if self.girlfriend and pr.colliderect(self.girlfriend.rect):
                self.win()

            target = p.x - W * 0.38
            self.camx += (target - self.camx) * 0.12
            self.camx = max(0, min(self.camx, LEVEL_W - W))

        elif self.state == "dying":
            self.state_t += 1
            p.vy = min(p.vy + 0.45, 14)
            p.y += p.vy
            if self.state_t > 140:
                self.lives -= 1
                if self.lives > 0:
                    self.reset_level()
                    self.state = "play"
                else:
                    self.state = "gameover"

        elif self.state == "rescue":
            self.state_t += 1
            if self.state_t < 220:
                confetti_burst()

        self.shake = max(0, self.shake - 1)
        for k in list(self.bump_anims):
            self.bump_anims[k] -= 1
            if self.bump_anims[k] <= 0:
                del self.bump_anims[k]
        update_particles()


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------


def make_sky(top_rgb, bottom_rgb):
    surf = pygame.Surface((W, H))
    for y in range(H):
        t = y / H
        surf.fill(tuple(int(top_rgb[i] + (bottom_rgb[i] - top_rgb[i]) * t)
                        for i in range(3)), (0, y, W, 1))
    return surf


SKY = make_sky((96, 165, 250), (170, 220, 255))
BOSS_SKY = make_sky((80, 20, 40), (180, 80, 70))
VOLCANO_SKY = make_sky((40, 20, 50), (180, 60, 50))
CLOUDS = [(i * 320 + (i % 3) * 90, 50 + (i * 53) % 120, 1 + (i % 3) * 0.3)
          for i in range(10)]


def draw_background(surf, camx, mode):
    if mode == "volcano":
        surf.blit(VOLCANO_SKY, (0, 0))
        for hx in range(-1, 10):
            x = hx * 420 - (camx * 0.3) % 420
            pygame.draw.polygon(surf, (30, 12, 18), [
                (x, H), (x + 120, H - 220), (x + 240, H - 110), (x + 360, H)])
    elif mode == "boss":
        surf.blit(BOSS_SKY, (0, 0))
        for hx in range(-1, 8):
            x = hx * 420 - (camx * 0.3) % 420
            pygame.draw.polygon(surf, (40, 10, 20), [
                (x, H), (x + 100, H - 180), (x + 220, H - 80), (x + 340, H)])
    else:
        surf.blit(SKY, (0, 0))
        for cx, cy, s in CLOUDS:
            x = (cx - camx * 0.3) % (W + 300) - 150
            for dx, dy, rr in ((0, 0, 26), (24, -8, 30), (52, 0, 24)):
                pygame.draw.circle(surf, (255, 255, 255),
                                   (int(x + dx * s), int(cy + dy * s)), int(rr * s))
        for hx in range(-1, 8):
            x = hx * 420 - (camx * 0.5) % 420
            pygame.draw.ellipse(surf, (80, 190, 90), (x, H - 190, 340, 200))
            pygame.draw.ellipse(surf, (60, 170, 75), (x + 120, H - 150, 260, 160))


def draw_tiles(surf, tiles, camx, tick):
    c0 = max(0, int(camx // TILE) - 1)
    c1 = min(LEVEL_COLS, c0 + W // TILE + 3)
    for (c, r), ch in tiles.items():
        if not (c0 <= c <= c1):
            continue
        x = c * TILE - camx
        y = r * TILE
        if (c, r) in game.bump_anims:
            t = game.bump_anims[(c, r)] / 10
            y -= int(8 * math.sin(math.pi * (1 - t)))
        if ch == "#":
            pygame.draw.rect(surf, (200, 120, 50), (x, y, TILE, TILE))
            pygame.draw.rect(surf, (150, 85, 30), (x, y, TILE, TILE), 2)
            if tiles.get((c, r - 1)) not in SOLID:
                pygame.draw.rect(surf, (90, 200, 80), (x, y, TILE, 8))
        elif ch == "B":
            pygame.draw.rect(surf, (185, 90, 45), (x, y, TILE, TILE))
            pygame.draw.rect(surf, (130, 55, 25), (x, y, TILE, TILE), 2)
            for line_y in (13, 26):
                pygame.draw.line(surf, (130, 55, 25), (x, y + line_y),
                                 (x + TILE, y + line_y), 2)
            pygame.draw.line(surf, (130, 55, 25), (x + 20, y), (x + 20, y + 13), 2)
            pygame.draw.line(surf, (130, 55, 25), (x + 10, y + 13), (x + 10, y + 26), 2)
            pygame.draw.line(surf, (130, 55, 25), (x + 30, y + 13), (x + 30, y + 26), 2)
            pygame.draw.line(surf, (130, 55, 25), (x + 20, y + 26), (x + 20, y + TILE), 2)
        elif ch == "?":
            pulse = int(20 * math.sin(tick * 0.08))
            pygame.draw.rect(surf, (240, 180 + pulse, 40), (x, y, TILE, TILE))
            pygame.draw.rect(surf, (160, 100, 20), (x, y, TILE, TILE), 3)
            q = FONT.render("?", True, (255, 255, 255))
            surf.blit(q, (x + TILE // 2 - q.get_width() // 2, y + TILE // 2 - q.get_height() // 2))
        elif ch == "U":
            pygame.draw.rect(surf, (140, 95, 50), (x, y, TILE, TILE))
            pygame.draw.rect(surf, (100, 65, 30), (x, y, TILE, TILE), 3)
        elif ch == "P":
            top_open = tiles.get((c, r - 1)) != "P"
            left_edge = tiles.get((c - 1, r)) != "P"
            pygame.draw.rect(surf, (40, 170, 60), (x, y, TILE, TILE))
            if top_open:
                pygame.draw.rect(surf, (30, 140, 50), (x - 2, y, TILE + 4, 12))
                pygame.draw.rect(surf, (80, 220, 100), (x - 2, y, TILE + 4, 5))
            if left_edge:
                pygame.draw.rect(surf, (80, 220, 100), (x, y, 6, TILE))
            pygame.draw.rect(surf, (20, 110, 40), (x + TILE - 4, y, 4, TILE))
        elif ch == "X":
            pygame.draw.rect(surf, (60, 50, 60), (x, y, TILE, TILE))
            pygame.draw.rect(surf, (30, 25, 35), (x, y, TILE, TILE), 2)
            pygame.draw.line(surf, (40, 30, 40), (x + 10, y), (x + 10, y + TILE), 1)
            pygame.draw.line(surf, (40, 30, 40), (x + 30, y), (x + 30, y + TILE), 1)
        elif ch == "L":
            wob = math.sin(tick * 0.1 + c) * 3
            pygame.draw.rect(surf, (220, 70, 20), (x, y - wob, TILE, TILE + 8))
            pygame.draw.rect(surf, (255, 150, 40), (x, y - wob, TILE, 6))
            pygame.draw.rect(surf, (255, 200, 80), (x + 6, y + 6 - wob, 8, 4))
        elif ch == "S":
            pygame.draw.polygon(surf, (200, 200, 210), [
                (x + 4, y + TILE), (x + TILE // 2, y + 6), (x + TILE - 4, y + TILE)])
            pygame.draw.polygon(surf, (120, 120, 140), [
                (x + 4, y + TILE), (x + TILE // 2, y + 6), (x + TILE - 4, y + TILE)], 2)


def draw_coins(surf, coins, camx, tick):
    for (c, r) in coins:
        x = c * TILE + TILE // 2 - camx
        y = r * TILE + TILE // 2
        wpx = max(3, int(10 * abs(math.sin(tick * 0.1 + c))))
        pygame.draw.ellipse(surf, (255, 210, 40), (x - wpx, y - 12, wpx * 2, 24))
        pygame.draw.ellipse(surf, (200, 150, 20), (x - wpx, y - 12, wpx * 2, 24), 2)


def draw_flag(surf, camx, tick):
    x = FLAG_X - camx
    pygame.draw.rect(surf, (30, 130, 50), (x - 3, 3 * TILE, 6, (GROUND_ROW - 3) * TILE))
    pygame.draw.circle(surf, (255, 215, 0), (int(x), 3 * TILE), 8)
    wave = int(4 * math.sin(tick * 0.15))
    pygame.draw.polygon(surf, (230, 50, 50), [
        (x - 3, 3 * TILE + 10), (x - 44, 3 * TILE + 24 + wave), (x - 3, 3 * TILE + 40)])


def draw_goomba(surf, g, camx):
    r = g.rect.move(-camx, 0)
    if g.squash_t:
        pygame.draw.ellipse(surf, (150, 85, 40), (r.x, r.bottom - 10, r.w, 10))
        return
    wob = int(2 * math.sin(g.walk_t * 4))
    step = int(4 * math.sin(g.walk_t * 6))
    body = (120, 120, 130) if g.spiky else (170, 95, 45)
    body_d = (80, 80, 90) if g.spiky else (200, 125, 70)
    pygame.draw.ellipse(surf, (90, 50, 20), (r.x + step, r.bottom - 8, 14, 8))
    pygame.draw.ellipse(surf, (90, 50, 20), (r.right - 14 - step, r.bottom - 8, 14, 8))
    pygame.draw.ellipse(surf, body, (r.x, r.y + wob, r.w, r.h - 4))
    pygame.draw.ellipse(surf, body_d, (r.x + 4, r.y + 4 + wob, r.w - 8, 10))
    if g.spiky:
        for sx in (-6, 0, 6):
            pygame.draw.polygon(surf, (220, 220, 230), [
                (r.centerx + sx, r.y - 4), (r.centerx + sx - 3, r.y + 4),
                (r.centerx + sx + 3, r.y + 4)])
    pygame.draw.circle(surf, (255, 255, 255), (r.x + 9, r.y + 12 + wob), 5)
    pygame.draw.circle(surf, (255, 255, 255), (r.right - 9, r.y + 12 + wob), 5)
    pygame.draw.circle(surf, (20, 20, 20), (r.x + 10, r.y + 13 + wob), 2)
    pygame.draw.circle(surf, (20, 20, 20), (r.right - 8, r.y + 13 + wob), 2)
    pygame.draw.line(surf, (60, 30, 10), (r.x + 4, r.y + 5 + wob), (r.x + 13, r.y + 9 + wob), 3)
    pygame.draw.line(surf, (60, 30, 10), (r.right - 4, r.y + 5 + wob), (r.right - 13, r.y + 9 + wob), 3)


def draw_mushroom(surf, m, camx):
    x = int(m.x - camx)
    y = int(m.y)
    pygame.draw.rect(surf, (250, 220, 180), (x + 8, y + 14, 12, 14))
    pygame.draw.ellipse(surf, (220, 40, 40), (x, y, m.w, 22))
    pygame.draw.ellipse(surf, (180, 30, 30), (x, y, m.w, 22), 2)
    pygame.draw.circle(surf, (255, 255, 255), (x + 6, y + 8), 3)
    pygame.draw.circle(surf, (255, 255, 255), (x + 20, y + 10), 3)


def draw_sword_item(surf, sw, camx):
    x = int(sw.x - camx)
    y = int(sw.y)
    bob = int(4 * math.sin(sw.spin))
    pygame.draw.rect(surf, (180, 120, 40), (x + 12, y + 24 + bob // 2, 6, 8))   # handle
    pygame.draw.rect(surf, (60, 40, 20), (x + 10, y + 18 + bob // 2, 10, 8))    # guard
    pygame.draw.polygon(surf, (210, 220, 255), [
        (x + 13, y - 2 + bob), (x + 18, y + 18 + bob // 2), (x + 8, y + 18 + bob // 2)])
    pygame.draw.polygon(surf, (255, 255, 255), [
        (x + 13, y - 2 + bob), (x + 16, y + 10 + bob // 2), (x + 13, y + 18 + bob // 2),
        (x + 10, y + 10 + bob // 2)], 1)


def draw_boot(surf, b, camx):
    x = int(b.x - camx)
    y = int(b.y)
    pygame.draw.rect(surf, (90, 50, 20), (x, y + 6, b.w, b.h - 6))
    pygame.draw.rect(surf, (140, 80, 40), (x, y + 6, b.w, 5))
    pygame.draw.rect(surf, (140, 80, 40), (x + b.w - 6, y, 6, b.h))
    pygame.draw.rect(surf, (200, 120, 60), (x, y + 6, b.w, b.h - 6), 1)


def draw_spike(surf, sp, camx):
    x = int(sp.x - camx)
    y = int(sp.y)
    pygame.draw.polygon(surf, (200, 60, 60), [
        (x + sp.w // 2, y), (x + sp.w, y + sp.h), (x, y + sp.h)])
    pygame.draw.polygon(surf, (120, 30, 30), [
        (x + sp.w // 2, y), (x + sp.w, y + sp.h), (x, y + sp.h)], 2)
    pygame.draw.circle(surf, (255, 200, 200), (x + sp.w // 2 - 2, y + sp.h - 4), 2)


def draw_boss(surf, boss, camx):
    if boss.dead and boss.death_t > 200:
        return
    r = boss.rect.move(-camx, 0)
    flash = boss.flash_t > 0 and (boss.flash_t // 4) % 2 == 0
    body = (255, 255, 255) if flash else (180, 30, 30)
    shadow = (120, 15, 15) if not flash else (180, 30, 30)
    if boss.dead:
        t = boss.death_t
        for i in range(8):
            a = i * math.pi / 4 + t * 0.2
            pygame.draw.circle(surf, (255, 100 + t * 4, 50),
                               (int(r.centerx + math.cos(a) * t * 2),
                                int(r.centery + math.sin(a) * t * 2)), max(2, 30 - t))
        return
    step = int(4 * math.sin(boss.walk_t * 6))
    pygame.draw.rect(surf, shadow, (r.x + 10, boss.y + boss.h - 18 + step, 14, 18 - step))
    pygame.draw.rect(surf, shadow, (r.right - 24, boss.y + boss.h - 18 - step, 14, 18 + step))
    pygame.draw.ellipse(surf, (90, 50, 20), (r.x + 8, boss.y + boss.h - 10 + step, 18, 10))
    pygame.draw.ellipse(surf, (90, 50, 20), (r.right - 26, boss.y + boss.h - 10 - step, 18, 10))
    pygame.draw.ellipse(surf, body, (r.x + 4, r.y + 14, boss.w - 8, boss.h - 24))
    pygame.draw.ellipse(surf, shadow, (r.x + 4, r.y + 14, boss.w - 8, boss.h - 24), 3)
    shell = (220, 200, 50) if not flash else (255, 255, 255)
    pygame.draw.ellipse(surf, shell, (r.x + 14, r.y + 24, boss.w - 28, 18))
    pygame.draw.ellipse(surf, (140, 130, 30) if not flash else (200, 200, 200),
                        (r.x + 14, r.y + 24, boss.w - 28, 18), 2)
    pygame.draw.polygon(surf, (250, 220, 60), [
        (r.x + 14, r.y + 18), (r.x + 6, r.y), (r.x + 24, r.y + 14)])
    pygame.draw.polygon(surf, (250, 220, 60), [
        (r.right - 14, r.y + 18), (r.right - 6, r.y), (r.right - 24, r.y + 14)])
    eye_off = -8 if boss.face > 0 else 8
    pygame.draw.circle(surf, (255, 240, 200), (r.x + 30 + eye_off, r.y + 36), 8)
    pygame.draw.circle(surf, (255, 240, 200), (r.x + 50 + eye_off, r.y + 36), 8)
    pygame.draw.circle(surf, (180, 30, 30), (r.x + 32 + eye_off, r.y + 37), 4)
    pygame.draw.circle(surf, (180, 30, 30), (r.x + 52 + eye_off, r.y + 37), 4)
    pygame.draw.circle(surf, (10, 10, 10), (r.x + 32 + eye_off, r.y + 37), 2)
    pygame.draw.circle(surf, (10, 10, 10), (r.x + 52 + eye_off, r.y + 37), 2)
    pygame.draw.arc(surf, (40, 10, 10), (r.x + 28, r.y + 50, boss.w - 56, 20), 3.14, 6.28, 3)
    for i in range(4):
        pygame.draw.polygon(surf, (255, 240, 200), [
            (r.x + 32 + i * 8, r.y + 60), (r.x + 35 + i * 8, r.y + 66), (r.x + 38 + i * 8, r.y + 60)])


def draw_horse(surf, p, camx, off=0):
    r = p.rect.move(-camx + off, 0)
    hx = r.x - 6
    hy = r.y + 6
    brown = (120, 70, 30)
    dark = (80, 45, 20)
    bob = int(3 * math.sin(p.run_t * 8)) if p.on_ground else 0
    pygame.draw.ellipse(surf, brown, (hx - 4, hy + 6, 40, 26))
    pygame.draw.rect(surf, brown, (hx + 28, hy - 6, 12, 16))     # neck
    pygame.draw.ellipse(surf, brown, (hx + 30, hy - 14, 14, 12))  # head
    leg = int(6 * math.sin(p.run_t * 8))
    pygame.draw.rect(surf, dark, (hx + 2, hy + 28, 6, 12 + leg))
    pygame.draw.rect(surf, dark, (hx + 28, hy + 28, 6, 12 - leg))
    pygame.draw.polygon(surf, (240, 220, 200), [
        (hx + 36, hy - 12), (hx + 44, hy - 16), (hx + 38, hy - 6)])  # mane


def draw_player(surf, p, camx, state):
    if p.invuln > 0 and (p.invuln // 4) % 2 == 0 and state == "play":
        return
    off = -p.horse_t * 9 if (p.mounted and p.horse_t > 0) else 0
    r = p.rect.move(-camx + off, 0)
    if p.mounted:
        draw_horse(surf, p, camx, off)
    sy = 1.0
    if state == "play":
        if p.vy < -2:
            sy = 1.08
        elif p.squash > 0:
            sy = 0.88
        elif p.grow_t > 0:
            sy = 1 + 0.2 * math.sin(math.pi * p.grow_t / 25)
    h = int(r.h * sy)
    y = r.bottom - h
    x = r.x
    w = r.w

    running = abs(p.vx) > 0.5 and p.on_ground
    leg = int(3 * math.sin(p.run_t * 6)) if running else 0
    knight = p.form == "knight"

    skin = (255, 205, 160)
    red = (220, 40, 40)
    blue = (50, 80, 200)
    armor = (170, 175, 190)

    pygame.draw.rect(surf, blue, (x + 4, y + h - 10 + leg, 8, 10 - leg))
    pygame.draw.rect(surf, blue, (x + w - 12, y + h - 10 - leg, 8, 10 + leg))
    pygame.draw.rect(surf, (110, 60, 20), (x + 2, y + h - 4 + leg, 11, 4))
    pygame.draw.rect(surf, (110, 60, 20), (x + w - 13, y + h - 4 - leg, 11, 4))
    # shirt / armor
    if knight:
        pygame.draw.rect(surf, armor, (x + 3, y + 12, w - 6, 14))
        pygame.draw.rect(surf, armor, (x + 3, y + 26, w - 6, 12))
        pygame.draw.rect(surf, (120, 125, 140), (x + 3, y + 12, w - 6, h - 22), 2)
    else:
        pygame.draw.rect(surf, red, (x + 3, y + 12, w - 6, 10))
        if p.form == "big":
            pygame.draw.rect(surf, red, (x + 3, y + 28, w - 6, 8))
        pygame.draw.rect(surf, blue, (x + 5, y + 18, w - 10, max(8, h - 32)))
    pygame.draw.circle(surf, (255, 220, 60), (x + 9, y + 21), 2)
    pygame.draw.circle(surf, (255, 220, 60), (x + w - 9, y + 21), 2)
    # head
    pygame.draw.rect(surf, skin, (x + 5, y + 2, w - 10, 12), border_radius=3)
    if knight:
        pygame.draw.rect(surf, (220, 220, 230), (x + 3, y - 2, w - 6, 8), border_radius=3)  # helmet
        pygame.draw.rect(surf, (200, 200, 210), (x + w // 2 - 2, y + 6, 4, 8))  # visor
    else:
        pygame.draw.rect(surf, red, (x + 3, y, w - 6, 6), border_radius=3)      # cap
        brim_x = x + w - 3 if p.face > 0 else x - 5
        pygame.draw.rect(surf, red, (brim_x - (0 if p.face > 0 else -8), y + 4, 8, 3))
    ex = x + w - 10 if p.face > 0 else x + 8
    pygame.draw.circle(surf, (20, 20, 20), (ex, y + 8), 2)
    # sword in hand (knight)
    if knight:
        sx = x + w - 2 if p.face > 0 else x - 6
        pygame.draw.rect(surf, (150, 100, 40), (sx + 2, y + 18, 5, 8))
        pygame.draw.polygon(surf, (220, 235, 255), [
            (sx + 4, y + 4), (sx + 8, y + 18), (sx, y + 18)])


class Girlfriend:
    def __init__(self, pos):
        self.x = pos[0] * TILE
        self.y = pos[1] * TILE
        self.w, self.h = TILE, TILE
        self.saved = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h - 6)

    def draw(self, surf, camx):
        x = int(self.x - camx)
        y = int(self.y)
        # cage
        pygame.draw.rect(surf, (90, 90, 110), (x - 2, y - 6, TILE + 4, TILE + 6), 3)
        for i in range(1, 4):
            pygame.draw.line(surf, (120, 120, 140), (x + i * 10, y - 6), (x + i * 10, y + TILE), 2)
        # princess
        pygame.draw.ellipse(surf, (255, 120, 160), (x + 12, y + 18, 16, 18))
        pygame.draw.circle(surf, (255, 205, 160), (x + 20, y + 14), 6)
        pygame.draw.polygon(surf, (255, 80, 120), [
            (x + 14, y + 8), (x + 20, y + 2), (x + 26, y + 8)])  # hair/helmet


def draw_boss_hp(surf, game):
    if not game.boss_active or not game.boss or game.boss.dead:
        return
    bx, by, bw, bh = W // 2 - 200, 18, 400, 22
    pygame.draw.rect(surf, (40, 10, 20), (bx - 4, by - 4, bw + 8, bh + 8))
    pygame.draw.rect(surf, (90, 30, 40), (bx, by, bw, bh))
    ratio = max(0, game.boss.hp / game.boss.max_hp)
    fill = int(bw * ratio)
    for i in range(fill):
        c = (255, int(60 + 180 * (i / bw)), 30)
        pygame.draw.rect(surf, c, (bx + i, by, 1, bh))
    pygame.draw.rect(surf, (220, 220, 220), (bx, by, bw, bh), 2)
    label = FONT.render("BOSS HP", True, (255, 255, 255))
    surf.blit(label, (bx - 110, by - 1))
    hp_label = FONT.render(f"{game.boss.hp}/{game.boss.max_hp}", True, (255, 255, 255))
    surf.blit(hp_label, (bx + bw + 8, by))


def draw_logo_corner(surf):
    if not LOGO_OK:
        return
    bg = pygame.Surface((64, 64), pygame.SRCALPHA)
    bg.fill((20, 20, 30, 180))
    bg.blit(LOGO_SMALL, (4, 4))
    surf.blit(bg, (W - 72, H - 72))
    credit = SMALL_FONT.render("Built with Python & pygame", True, (220, 230, 255))
    surf.blit(credit, (W - 220, H - 18))


def draw_hud(surf, game):
    def txt(s, x, y, color=(255, 255, 255)):
        img = FONT.render(s, True, (0, 0, 0))
        surf.blit(img, (x + 2, y + 2))
        img = FONT.render(s, True, color)
        surf.blit(img, (x, y))

    txt(f"SCORE {game.score:06d}", 20, 12)
    pygame.draw.ellipse(surf, (255, 210, 40), (22, 46, 14, 20))
    pygame.draw.ellipse(surf, (200, 150, 20), (22, 46, 14, 20), 2)
    txt(f"x {game.coins:02d}", 42, 44, (255, 220, 60))
    form_color = (200, 200, 200) if game.player.form == "small" else \
        ((255, 220, 60) if game.player.form == "big" else (190, 190, 255))
    form_text = "SMALL" if game.player.form == "small" else \
        ("BIG" if game.player.form == "big" else "KNIGHT")
    txt(f"FORM: {form_text}", 20, 76, form_color)
    if game.player.form == "knight":
        txt("[H] HORSE" + (" ON" if game.player.mounted else ""), 20, 104,
            (220, 180, 120))
    if game.player.form != "small":
        txt("[F] BOOT", 20, 132, (180, 220, 255))
    txt(f"LIVES x {game.lives}", 20, 160, (120, 255, 120))
    txt(f"STAGE {game.stage}", W - 150, 12, (255, 200, 160))
    txt(f"TIME {int(game.time):03d}", W - 150, 40)
    draw_logo_corner(surf)


def overlay(surf, title, subtitle, color):
    shade = pygame.Surface((W, H), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 170))
    surf.blit(shade, (0, 0))
    img = BIG_FONT.render(title, True, color)
    surf.blit(img, (W // 2 - img.get_width() // 2, H // 2 - 70))
    img2 = MID_FONT.render(subtitle, True, (255, 255, 255))
    surf.blit(img2, (W // 2 - img2.get_width() // 2, H // 2 + 10))


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


game = Game()
tick = 0
running = True

while __name__ == "__main__" and running:
    tick += 1
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                running = False
            if e.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w) and game.state == "play":
                game.player.jump_buf = 7
            if e.key in (pygame.K_f, pygame.K_x) and game.state == "play":
                game.throw_boot()
            if e.key == pygame.K_h and game.state == "play":
                game.player.toggle_mount()
            if e.key == pygame.K_r and game.state in ("rescue", "gameover"):
                MUSIC.stop()
                BOSS_MUSIC.stop()
                game.full_reset()

    keys = pygame.key.get_pressed()
    game.update(keys)

    mode = "boss" if (game.boss_active and game.stage == 1) else \
        ("volcano" if game.stage == 2 else "normal")
    shake_x = random.randint(-4, 4) if game.shake else 0
    shake_y = random.randint(-3, 3) if game.shake else 0
    camx = game.camx + shake_x

    draw_background(screen, camx, mode)
    if game.stage == 1:
        draw_flag(screen, camx, tick)
    draw_tiles(screen, game.tiles, camx, tick)
    draw_coins(screen, game.coin_map, camx, tick)

    for cp in game.coin_pops:
        pygame.draw.ellipse(screen, (255, 210, 40), (cp.x + 10 - camx, cp.y + 8, 20, 24))
        pygame.draw.ellipse(screen, (200, 150, 20), (cp.x + 10 - camx, cp.y + 8, 20, 24), 2)

    for m in game.mushrooms:
        draw_mushroom(screen, m, camx)
    for sw in game.swords:
        draw_sword_item(screen, sw, camx)
    for g in game.goombas:
        draw_goomba(screen, g, camx)
    if game.boss_active and game.boss:
        draw_boss(screen, game.boss, camx)
    for sp in game.spikes:
        draw_spike(screen, sp, camx)
    for b in game.boots:
        draw_boot(screen, b, camx)
    if game.stage == 2 and game.girlfriend:
        game.girlfriend.draw(screen, camx)

    draw_player(screen, game.player, camx, game.state)
    draw_particles(screen, camx)
    update_draw_popups(screen, camx)
    draw_hud(screen, game)
    draw_boss_hp(screen, game)

    if game.state == "transition":
        overlay(screen, "STAGE 1 CLEAR!", "STAGE 2 - HIGH RISK", (255, 160, 80))
    elif game.state == "rescue":
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))
        screen.blit(shade, (0, 0))
        img = BIG_FONT.render("YOU SAVED HER!", True, (120, 255, 160))
        screen.blit(img, (W // 2 - img.get_width() // 2, H // 2 - 150))
        score_text = MID_FONT.render(f"Final Score {game.score}", True, (255, 255, 255))
        screen.blit(score_text, (W // 2 - score_text.get_width() // 2, H // 2 - 80))
        if LOGO_OK:
            screen.blit(LOGO_MED, (W // 2 - LOGO_MED.get_width() // 2, H // 2 - 30))
            credit = SMALL_FONT.render("Built with Python & pygame", True, (200, 220, 255))
            screen.blit(credit, (W // 2 - credit.get_width() // 2,
                                 H // 2 - 30 + LOGO_MED.get_height() + 8))
        hint = SMALL_FONT.render("Press R to play again", True, (200, 200, 200))
        screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 50))
    elif game.state == "gameover":
        overlay(screen, "GAME OVER", "Press R to try again", (255, 90, 90))
        if LOGO_OK:
            screen.blit(LOGO_MED, (W // 2 - LOGO_MED.get_width() // 2, H // 2 + 50))

    pygame.display.flip()
    clock.tick(60)

MUSIC.stop()
BOSS_MUSIC.stop()
pygame.quit()