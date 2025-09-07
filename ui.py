# ui.py
# メニュー / リザルト / 汎用テキスト描画
import pygame
from fonts import jp_font
from constants import WIDTH, HEIGHT, WHITE, RED

def draw_menu(screen, selected_level, level_cleared):
    screen.fill((0,0,0))
    title_font = pygame.font.SysFont(None, 50)
    title = title_font.render("LEVEL SELECT", True, WHITE)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 60))
    font2 = pygame.font.SysFont(None, 34)
    # level 10
    level10_color = RED if selected_level == 0 else (180, 50, 50)
    lvl10 = font2.render("LEVEL 10", True, level10_color)
    x10 = WIDTH//2 - lvl10.get_width()//2
    y10 = 130
    screen.blit(lvl10, (x10, y10))
    if level_cleared[0]:
        star = font2.render("★", True, (255,215,0))
        screen.blit(star, (x10 + lvl10.get_width() + 10, y10))
    for i in range(9,0,-1):
        color = WHITE if selected_level == i else (120,120,120)
        lvl_text = font2.render(f"LEVEL {i}", True, color)
        y = 180 + (9 - i) * 42
        x = WIDTH//2 - lvl_text.get_width()//2
        screen.blit(lvl_text, (x, y))
        if level_cleared[i]:
            star = font2.render("★", True, (255,215,0))
            screen.blit(star, (x + lvl_text.get_width() + 10, y))
    font3 = pygame.font.SysFont(None, 20)
    info = font3.render("←→:Select  Enter:Start   ★=Cleared", True, WHITE)
    screen.blit(info, (WIDTH//2 - info.get_width()//2, HEIGHT - 46))
    pygame.display.flip()


def _split_reward(font, text, max_width):
    parts = text.split(' ')
    lines = []
    cur = ''
    for p in parts:
        test = (cur + ' ' + p).strip()
        w, _ = font.size(test)
        if w > max_width and cur:
            lines.append(cur)
            cur = p
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def draw_end_menu(screen, result, reward_text=None):
    screen.fill((0,0,0))
    font = jp_font(48)
    if result == "win":
        text = font.render("GAME CLEAR!", True, (0, 255, 0))
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 80))
        screen.blit(text, text_rect)
    else:
        text = font.render("GAME OVER", True, RED)
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60))
        screen.blit(text, text_rect)
    if reward_text:
        font_reward = jp_font(26)
        lines = _split_reward(font_reward, reward_text, WIDTH - 40)
        line_h = font_reward.get_linesize()
        total_h = line_h * len(lines)
        start_y = (HEIGHT // 2 - 10) - total_h // 2 + line_h // 2
        for i,l in enumerate(lines):
            surf = font_reward.render(l, True, (0,255,0))
            rect = surf.get_rect(center=(WIDTH//2, start_y + i*line_h))
            screen.blit(surf, rect)
    font2 = jp_font(30)
    menu_text = font2.render("1: Menu   2: Retry   3: Quit", True, WHITE)
    menu_rect = menu_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30))
    screen.blit(menu_text, menu_rect)
    pygame.display.flip()
