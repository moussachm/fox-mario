"""Headless smoke test for super_mario.py.
Exercises the new features: stage 2 (high-risk), bigger boot, sword->knight,
horse mount, girlfriend rescue, and renders every game state to catch crashes.
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import super_mario as G

pygame.init()

# Headless note: the dummy SDL driver can't reliably rasterize 'arialblack',
# so for this test only we swap in the built-in default font, which renders
# cleanly here. The shipped game keeps its real fonts on a normal display.
G.FONT = pygame.font.Font(None, 20)
G.BIG_FONT = pygame.font.Font(None, 56)
G.MID_FONT = pygame.font.Font(None, 30)
G.SMALL_FONT = pygame.font.Font(None, 16)

screen = pygame.Surface((G.W, G.H))


class KeyState:
    """Minimal stand-in for pygame.key.get_pressed(): index by key code."""
    def __init__(self, on=()):
        self.on = set(on)

    def __getitem__(self, idx):
        return idx in self.on


def keyset(*on):
    return KeyState(on)


def step(n, keys=None):
    if keys is None:
        keys = KeyState()
    for _ in range(n):
        G.game.update(keys)


def safe(label, fn):
    try:
        fn()
        print("  ok:", label)
    except Exception as ex:  # noqa
        import traceback
        traceback.print_exc()
        raise SystemExit(f"FAILED at: {label} -> {ex}")


print("module loaded. stage:", G.game.stage, "state:", G.game.state)
assert G.game.stage == 1
assert G.game.girlfriend is None, "stage 1 must not have a girlfriend"


# 0) Boss must drop in from above and then rest on the ground
def boss_descent():
    b = G.game.boss
    assert b is not None
    assert b.y < 0, f"boss should start above the arena, got y={b.y}"
    for _ in range(140):
        b.update(G.game.tiles, G.game.player)
    assert b.on_ground, "boss should land on the ground"
    assert abs((b.y + b.h) - (G.GROUND_ROW * G.TILE)) < 2, \
        f"boss feet should rest on ground, bottom={b.y + b.h}"
safe("boss descends & lands", boss_descent)


# 1) Stage 1: walk right + jump
safe("stage1 walk/jump", lambda: (
    step(30, keyset(pygame.K_RIGHT)),
    setattr(G.game.player, "jump_buf", 7),
    step(20, keyset(pygame.K_RIGHT)),
))
print("  player x:", round(G.game.player.x, 1),
      "on_ground:", G.game.player.on_ground)

# 2) Sword -> knight -> horse -> boot
safe("become knight", lambda: G.game.player.become_knight())
assert G.game.player.form == "knight", G.game.player.form
safe("toggle mount (horse)", lambda: G.game.player.toggle_mount())
assert G.game.player.mounted is True
assert G.game.player.horse_t > 0, "horse should be galloping in from the left"
safe("throw boot", lambda: G.game.throw_boot())
print("  form:", G.game.player.form, "mounted:", G.game.player.mounted,
      "boots:", len(G.game.boots))
assert len(G.game.boots) == 1
assert G.game.boots[0].w >= 20, "boot should be bigger now"

# 3) Advance to high-risk stage 2
safe("advance_stage", lambda: G.game.advance_stage())
assert G.game.stage == 2
assert G.game.girlfriend is not None, "stage 2 must spawn the girlfriend"
print("  stage:", G.game.stage, "state:", G.game.state,
      "girlfriend at col:", G.game.girlfriend.col if hasattr(G.game.girlfriend, "col") else "?")
safe("transition resolves", lambda: step(200))
print("  state after transition:", G.game.state)

# knight on horse in stage 2: move + jump
safe("stage2 ride", lambda: (
    step(40, keyset(pygame.K_RIGHT)),
    setattr(G.game.player, "jump_buf", 7),
    step(30, keyset(pygame.K_RIGHT)),
))
print("  stage2 player x:", round(G.game.player.x, 1))

# 4) Rescue win
safe("win -> rescue", lambda: G.game.win())
assert G.game.state == "rescue"
safe("rescue confetti", lambda: step(60))

# 5) Render every state for both stages (catch draw crashes)
def render_all():
    for stg in (1, 2):
        G.game.stage = stg
        G.game.load_stage(stg)
        for gs in ("play", "transition", "rescue", "gameover", "dying"):
            G.game.state = gs
            G.draw_background(screen, 0, "normal")
            G.draw_background(screen, 0, "volcano")
            G.draw_tiles(screen, G.game.tiles, 0, 0)
            if stg == 1:
                G.draw_flag(screen, 0, 0)
            if G.game.girlfriend:
                G.game.girlfriend.draw(screen, 0)
            G.draw_player(screen, G.game.player, 0, gs)
            G.draw_hud(screen, G.game)
            G.draw_boss_hp(screen, G.game)
safe("render all states/stages", render_all)

# 6) Death -> respawn path
safe("death/respawn", lambda: (
    G.game.full_reset(),
    setattr(G.game.player, "invuln", 0),
    G.game.kill_player(),
    step(200),
))
print("  state after dying sequence:", G.game.state,
      "lives:", G.game.lives)

print("SMOKE TEST OK")
