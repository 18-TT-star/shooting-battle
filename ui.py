# ui.py
# メニュー / リザルト / 汎用テキスト描画
import pygame
from fonts import jp_font, text_surface
from constants import WIDTH, HEIGHT, WHITE, RED

def draw_menu(screen, selected_level, level_cleared):
    screen.fill((0, 0, 0))
    title_font = jp_font(50)
    title = title_font.render("レベル選択", True, WHITE)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 60))
    font2 = jp_font(38)
    base_y = 140
    line_h = 50
    for row, i in enumerate(range(6, 0, -1)):
        if i == 6:
            color = RED if selected_level == i else (180, 50, 50)
        else:
            color = WHITE if selected_level == i else (120, 120, 120)
        label = font2.render(f"レベル {i}", True, color)
        x = WIDTH // 2 - label.get_width() // 2
        y = base_y + row * line_h
        screen.blit(label, (x, y))
        if len(level_cleared) > i and level_cleared[i]:
            star = text_surface("★", 38, (255, 215, 0))
            screen.blit(star, (x + label.get_width() + 10, y))
    info = text_surface("↑↓: 選択  Enter: 開始  ★=クリア済み", 22, WHITE)
    screen.blit(info, (WIDTH // 2 - info.get_width() // 2, HEIGHT - 60))


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
    screen.fill((0, 0, 0))
    font = jp_font(48)
    if result == "win":
        text = font.render("ゲームクリア！", True, (0, 255, 0))
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 80))
        screen.blit(text, text_rect)
    else:
        text = font.render("ゲームオーバー", True, RED)
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60))
        screen.blit(text, text_rect)
    if reward_text:
        font_reward = jp_font(26)
        lines = _split_reward(font_reward, reward_text, WIDTH - 40)
        line_h = font_reward.get_linesize()
        total_h = line_h * len(lines)
        start_y = (HEIGHT // 2 - 10) - total_h // 2 + line_h // 2
        for i,l in enumerate(lines):
            surf = text_surface(l, 26, (0,255,0))
            rect = surf.get_rect(center=(WIDTH//2, start_y + i*line_h))
            screen.blit(surf, rect)
    font2 = jp_font(30)
    menu_text = text_surface("1: メニューへ   2: リトライ   3: 終了", 30, WHITE)
    menu_rect = menu_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30))
    screen.blit(menu_text, menu_rect)
