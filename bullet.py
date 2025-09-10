import math
import pygame
from constants import HEIGHT


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
