import math
import pygame
from constants import (
    HEIGHT,
    DASH_COOLDOWN_FRAMES, DASH_INVINCIBLE_FRAMES, DASH_DISTANCE,
    DASH_DOUBLE_TAP_WINDOW,
)

# -------- Player (dash) --------

def update_dash_timers(dash_state: dict) -> None:
    """Update dash cooldown and invincibility timers in-place."""
    if dash_state.get('cooldown', 0) > 0:
        dash_state['cooldown'] -= 1
    if dash_state.get('invincible_timer', 0) > 0:
        dash_state['invincible_timer'] -= 1
        if dash_state['invincible_timer'] == 0:
            dash_state['active'] = False


def attempt_dash(
    dash_state: dict,
    dir_key: str,
    frame_count: int,
    player_rect: pygame.Rect,
    has_dash: bool,
    arena_width: int,
) -> bool:
    """Try to trigger dash on double-tap for given direction.
    Returns True if dash triggered (caller should set player invincible).
    Mutates dash_state and player_rect in-place.
    """
    if not has_dash:
        return False
    if dash_state.get('cooldown', 0) > 0:
        # Still record tap time for next double-tap window
        dash_state['last_tap'][dir_key] = frame_count
        return False

    prev = dash_state['last_tap'][dir_key]
    if frame_count - prev <= DASH_DOUBLE_TAP_WINDOW:
        dist = DASH_DISTANCE
        if dir_key == 'left':
            player_rect.x = max(0, player_rect.x - dist)
        else:
            player_rect.x = min(arena_width - player_rect.width, player_rect.x + dist)
        dash_state['cooldown'] = DASH_COOLDOWN_FRAMES
        dash_state['invincible_timer'] = DASH_INVINCIBLE_FRAMES
        dash_state['active'] = True
        dash_state['last_tap'][dir_key] = frame_count
        return True

    dash_state['last_tap'][dir_key] = frame_count
    return False


# -------- Player bullets --------

def spawn_player_bullets(bullets: list, player_rect: pygame.Rect, bullet_type: str, bullet_speed: int) -> None:
    if bullet_type == "normal":
        bullets.append({
            "rect": pygame.Rect(player_rect.centerx - 3, player_rect.top - 6, 6, 12),
            "type": "normal",
            "power": 1.0,
            "vy": -bullet_speed,
            "vx": 0,
        })
    elif bullet_type == "homing":
        bullets.append({
            "rect": pygame.Rect(player_rect.centerx - 3, player_rect.top - 6, 6, 12),
            "type": "homing",
            "power": 0.5,
            "vy": -bullet_speed,
            "vx": 0,
        })
    elif bullet_type == "spread":
        angles = [0, -0.18, 0.18]
        speed = 9
        for ang in angles:
            vx = int(speed * math.sin(ang))
            vy = -int(speed * math.cos(ang))
            bullets.append({
                "rect": pygame.Rect(player_rect.centerx - 3, player_rect.top - 6, 6, 12),
                "type": "spread",
                "power": 0.5,
                "vx": vx,
                "vy": vy,
            })


def move_player_bullets(bullets: list, bullet_speed: int, boss_alive: bool, boss_pos: tuple[int, int]) -> None:
    bx, by = boss_pos
    for bullet in bullets:
        if bullet.get("type") == "homing" and boss_alive and not bullet.get("reflect"):
            dx = bx - bullet["rect"].centerx
            dy = by - bullet["rect"].centery
            dist = max(1, (dx * dx + dy * dy) ** 0.5)
            bullet["vx"] = int(6 * dx / dist)
            bullet["vy"] = int(6 * dy / dist)
        bullet["rect"].x += bullet.get("vx", 0)
        bullet["rect"].y += bullet.get("vy", -bullet_speed)

    # remove off-screen
    bullets[:] = [b for b in bullets if b["rect"].bottom > 0 and b["rect"].top < HEIGHT]
