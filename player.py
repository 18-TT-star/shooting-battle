import pygame
from constants import (
    DASH_COOLDOWN_FRAMES, DASH_INVINCIBLE_FRAMES, DASH_DISTANCE,
    DASH_DOUBLE_TAP_WINDOW,
)


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
