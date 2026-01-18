# ui.py
# メニュー / リザルト / 汎用テキスト描画
import pygame
from fonts import jp_font, text_surface
from constants import WIDTH, HEIGHT, WHITE, RED

def draw_title_screen(screen, frame_count, true_ending_achieved=False):
    """タイトル画面を描画"""
    screen.fill((5, 5, 20))  # 暗い青背景
    
    # 真エンディング達成時は背景色を虹色に変化
    if true_ending_achieved:
        import time
        hue = (time.time() * 50) % 360
        import colorsys
        rgb = colorsys.hsv_to_rgb(hue / 360.0, 0.3, 0.15)
        bg_color = (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))
        screen.fill(bg_color)
    
    # タイトルを特殊フォント（大きく）で表示
    title_size = 52  # さらに小さくしてウィンドウに収める
    title_font = jp_font(title_size)
    
    # ゲームタイトル
    title_text = "Bob's Big Adventure"
    # 真エンディング達成時はタイトル色を虹色に
    if true_ending_achieved:
        import time
        hue = (time.time() * 100) % 360
        import colorsys
        rgb = colorsys.hsv_to_rgb(hue / 360.0, 1.0, 1.0)
        title_color = (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))
    else:
        title_color = (255, 215, 0)  # ゴールド色
    
    title_surf = title_font.render(title_text, True, title_color)
    
    # タイトルの影を追加（立体感）
    shadow_surf = title_font.render(title_text, True, (100, 80, 0))
    shadow_x = WIDTH // 2 - shadow_surf.get_width() // 2 + 2
    shadow_y = HEIGHT // 3 - shadow_surf.get_height() // 2 + 2
    screen.blit(shadow_surf, (shadow_x, shadow_y))
    
    # タイトル本体
    title_x = WIDTH // 2 - title_surf.get_width() // 2
    title_y = HEIGHT // 3 - title_surf.get_height() // 2
    screen.blit(title_surf, (title_x, title_y))
    
    # サブタイトル
    subtitle_font = jp_font(32)
    if true_ending_achieved:
        subtitle = subtitle_font.render("★ Game Complete ★", True, (255, 255, 100))
    else:
        subtitle = subtitle_font.render("シューティングバトル", True, (200, 200, 255))
    subtitle_x = WIDTH // 2 - subtitle.get_width() // 2
    subtitle_y = title_y + title_surf.get_height() + 20
    screen.blit(subtitle, (subtitle_x, subtitle_y))
    
    # 点滅する「Press Any Key」メッセージ
    if (frame_count // 30) % 2 == 0:  # 30フレームごとに点滅
        press_font = jp_font(28)
        press_text = press_font.render("Press Any Key", True, WHITE)
        press_x = WIDTH // 2 - press_text.get_width() // 2
        press_y = HEIGHT * 2 // 3 + 40
        screen.blit(press_text, (press_x, press_y))
        
        # ロード説明
        load_font = jp_font(22)
        load_text = load_font.render("Lキー: ロード", True, (200, 200, 200))
        load_x = WIDTH // 2 - load_text.get_width() // 2
        load_y = HEIGHT * 2 // 3 + 75
        screen.blit(load_text, (load_x, load_y))
    
    # 装飾：星のエフェクト
    for i in range(8):
        star_angle = (frame_count + i * 45) % 360
        star_radius = 150 + 20 * (i % 3)
        star_x = WIDTH // 2 + int(star_radius * pygame.math.Vector2(1, 0).rotate(star_angle).x)
        star_y = HEIGHT // 3 + int(star_radius * pygame.math.Vector2(1, 0).rotate(star_angle).y)
        star_alpha = int(128 + 127 * abs((frame_count % 120 - 60) / 60))
        star_color = (star_alpha, star_alpha, 255)
        pygame.draw.circle(screen, star_color, (star_x, star_y), 3)


def draw_menu(screen, selected_level, level_cleared, level_cleared_no_equipment=None, level_cleared_rainbow_star=None, true_ending_achieved=False):
    screen.fill((0, 0, 0))
    
    # 真エンディング達成時は特別な表示
    if true_ending_achieved:
        # 背景に虹色のパルス（より目立つように）
        import time
        import math
        import random
        hue = (time.time() * 100) % 360
        import colorsys
        # パルスエフェクト
        pulse = abs(math.sin(time.time() * 2))
        saturation = 0.3 + pulse * 0.3
        brightness = 0.15 + pulse * 0.15
        rgb = colorsys.hsv_to_rgb(hue / 360.0, saturation, brightness)
        bg_overlay = pygame.Surface((WIDTH, HEIGHT))
        bg_overlay.fill((int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255)))
        bg_overlay.set_alpha(150)
        screen.blit(bg_overlay, (0, 0))
        
        # ボス乱入演出
        # 6秒ごとにランダムなボスが登場
        cycle_time = time.time() % 6
        boss_index = int(time.time() / 6) % 6  # 0-5でボス選択
        
        if boss_index == 0:  # 台形ボス（Boss A）
            # 上から降ってくる
            y_pos = -100 + cycle_time * 130
            x_pos = WIDTH // 2
            if y_pos < HEIGHT + 100:
                # 実際のボス描画と同じ台形を描画
                boss_radius = 40
                top_width = boss_radius
                bottom_width = boss_radius * 2
                height = boss_radius * 1.5
                points = [
                    (x_pos - top_width//2, y_pos - int(height//2)),
                    (x_pos + top_width//2, y_pos - int(height//2)),
                    (x_pos + bottom_width//2, y_pos + int(height//2)),
                    (x_pos - bottom_width//2, y_pos + int(height//2)),
                ]
                pygame.draw.polygon(screen, (255, 110, 110), points)
                
        elif boss_index == 1:  # 四角形ボス（蛇ボス）
            # 上から降ってくる
            y_pos = -100 + cycle_time * 125
            x_pos = WIDTH // 2 + 100
            if y_pos < HEIGHT + 100:
                # 実際のボス描画と同じ四角形を描画
                boss_radius = 40
                main_size = int(boss_radius * 1.2)
                main_rect = pygame.Rect(x_pos - main_size//2, y_pos - main_size//2, main_size, main_size)
                pygame.draw.rect(screen, (128, 0, 128), main_rect)
                # 回転体節も描画
                ROTATE_SEGMENTS_NUM = 5
                ROTATE_RADIUS = boss_radius + 30
                rotate_angle_local = time.time() * 2
                for i in range(ROTATE_SEGMENTS_NUM):
                    angle = rotate_angle_local + (2 * math.pi * i / ROTATE_SEGMENTS_NUM)
                    seg_x = x_pos + ROTATE_RADIUS * math.cos(angle)
                    seg_y = y_pos + ROTATE_RADIUS * math.sin(angle)
                    seg_rect = pygame.Rect(int(seg_x-20), int(seg_y-20), 40, 40)
                    pygame.draw.rect(screen, (180, 0, 180), seg_rect)
                
        elif boss_index == 2:  # 楕円ボス
            # 右から左に移動しながらビーム
            x_pos = WIDTH + 100 - cycle_time * 150
            y_pos = HEIGHT // 2
            if x_pos > -100:
                # 実際のボス描画と同じ楕円を描画
                boss_radius = 40
                ellipse_width = int(boss_radius * 1.25)
                ellipse_height = int(boss_radius * 2.0)
                
                # 中央に差し掛かった時に開く演出（2〜4秒の間）
                center_progress = 0
                if 2.0 <= cycle_time <= 4.0:
                    # 中央付近で最も開く
                    center_distance = abs(x_pos - WIDTH // 2)
                    max_distance = WIDTH // 4
                    if center_distance < max_distance:
                        center_progress = 1.0 - (center_distance / max_distance)
                
                gap = int(center_progress * 60)  # 最大60ピクセル開く
                
                if gap > 5:
                    # 楕円を左右に分割して描画
                    base = pygame.Surface((ellipse_width, ellipse_height), pygame.SRCALPHA)
                    pygame.draw.ellipse(base, (255, 170, 80), (0, 0, ellipse_width, ellipse_height))
                    half_w = ellipse_width // 2
                    left_half = base.subsurface((0, 0, half_w, ellipse_height))
                    right_half = base.subsurface((half_w, 0, ellipse_width - half_w, ellipse_height))
                    gap_offset = gap // 2
                    left_rect = left_half.get_rect(midright=(int(x_pos - gap_offset), int(y_pos)))
                    right_rect = right_half.get_rect(midleft=(int(x_pos + gap_offset), int(y_pos)))
                    screen.blit(left_half, left_rect)
                    screen.blit(right_half, right_rect)
                    
                    # コアを描画（赤色）
                    core_radius = 15
                    pygame.draw.circle(screen, (255, 80, 80), (int(x_pos), int(y_pos)), core_radius)
                else:
                    # 通常の閉じた楕円
                    pygame.draw.ellipse(screen, (255, 170, 80), (x_pos - ellipse_width//2, y_pos - ellipse_height//2, ellipse_width, ellipse_height))
                
                # 小楕円も描画
                small_w, small_h = boss_radius//2, boss_radius*2//3
                for side_offset in (-boss_radius, boss_radius):
                    cx = x_pos + side_offset
                    cy = y_pos
                    pygame.draw.ellipse(screen, (0, 200, 0), (cx - small_w//2, cy - small_h//2, small_w, small_h))
                # ビームを撃つ（左右の小楕円から水色で）
                for i in range(5):
                    beam_y = y_pos + math.sin(time.time() * 5 + i) * 50
                    # 左の小楕円から
                    left_cx = x_pos - boss_radius
                    pygame.draw.line(screen, (100, 220, 255), (left_cx, y_pos), (left_cx - 80, beam_y), 3)
                    # 右の小楕円から
                    right_cx = x_pos + boss_radius
                    pygame.draw.line(screen, (100, 220, 255), (right_cx, y_pos), (right_cx - 80, beam_y + 10), 3)
                    
        elif boss_index == 3:  # 丸ボス（バウンドボス）
            # 飛び跳ねる（画面全体を縦横無尽に）
            boss_radius = 40
            # 6秒間全体でバウンドし続ける
            bounce_time = cycle_time
            # 速度を上げて画面全体を移動
            base_x = WIDTH // 2
            base_y = HEIGHT // 2
            # 複雑な軌道で移動（Lissajous曲線風）
            x_pos = base_x + math.sin(bounce_time * 4.5) * (WIDTH // 2 - 60)
            y_pos = base_y + math.cos(bounce_time * 3.2) * (HEIGHT // 2 - 60)
            
            # バウンドアニメーション（周期的に）
            bounce_phase = (bounce_time * 6) % 1.0  # より速いバウンス
            is_bouncing = bounce_phase < 0.2  # バウンスの瞬間
            
            # 振動エフェクト（バウンス時）
            shake_x = random.randint(-3, 3) if is_bouncing else 0
            shake_y = random.randint(-3, 3) if is_bouncing else 0
            
            # 円を描画（潰れ演出も追加）
            if is_bouncing:  # バウンス時は潰れる
                squash_ratio = 0.55 + (bounce_phase / 0.2) * 0.45
                stretch_ratio = 1.45 - (bounce_phase / 0.2) * 0.45
                # バウンス方向を判定（移動方向から）
                dx = math.cos(bounce_time * 4.5) * 4.5
                dy = -math.sin(bounce_time * 3.2) * 3.2
                if abs(dy) > abs(dx):  # 縦方向のバウンス
                    w = int(boss_radius * 2 * stretch_ratio)
                    h = int(boss_radius * 2 * squash_ratio)
                else:  # 横方向のバウンス
                    w = int(boss_radius * 2 * squash_ratio)
                    h = int(boss_radius * 2 * stretch_ratio)
                rect = pygame.Rect(0, 0, w, h)
                rect.center = (int(x_pos + shake_x), int(y_pos + shake_y))
                pygame.draw.ellipse(screen, (100, 220, 255), rect)
            else:
                pygame.draw.circle(screen, (100, 220, 255), (int(x_pos + shake_x), int(y_pos + shake_y)), boss_radius)
                
        elif boss_index == 4:  # 月ボス（三日月形ボス）
            # 上から下にゆっくり降りて星座生成
            y_pos = -100 + cycle_time * 60
            x_pos = WIDTH // 2
            if y_pos < HEIGHT + 100:
                # 実際のボス描画と同じ三日月を描画（黄色）
                boss_radius = 40
                outer_r = boss_radius
                inner_r = int(boss_radius * 0.75)
                offset = int(boss_radius * 0.45)
                cres = pygame.Surface((outer_r*2+2, outer_r*2+2), pygame.SRCALPHA)
                pygame.draw.circle(cres, (255, 255, 100), (outer_r+1, outer_r+1), outer_r)
                pygame.draw.circle(cres, (0, 0, 0, 0), (outer_r+1 - offset, outer_r+1), inner_r)
                screen.blit(cres, (int(x_pos - outer_r - 1), int(y_pos - outer_r - 1)))
                # 星座（星を複数生成し、青い線でつなぐ）
                star_count = int(cycle_time * 8)
                star_positions = []
                for i in range(star_count):
                    star_x = x_pos + random.randint(-150, 150)
                    star_y = y_pos - i * 30
                    if 0 <= star_y <= HEIGHT:
                        star_positions.append((star_x, star_y))
                        # 星型を描画（5つ星）
                        star_size = 5
                        star_points = []
                        for j in range(10):
                            angle = (j / 10) * math.pi * 2 - math.pi / 2
                            radius = star_size if j % 2 == 0 else star_size * 0.4
                            px = star_x + math.cos(angle) * radius
                            py = star_y + math.sin(angle) * radius
                            star_points.append((px, py))
                        pygame.draw.polygon(screen, (255, 255, 100), star_points)
                
                # 星と星をランダムに青い線でつなぐ（星座のイメージ）
                if len(star_positions) > 1:
                    # いくつかの星のペアをランダムに選んで線でつなぐ
                    connection_count = min(len(star_positions) - 1, star_count // 2)
                    for i in range(connection_count):
                        if i < len(star_positions) - 1:
                            # 近い星同士をつなぐ
                            star1 = star_positions[i]
                            star2 = star_positions[i + 1]
                            pygame.draw.line(screen, (100, 150, 255), star1, star2, 2)
                            # ランダムで他の星ともつなぐ
                            if i % 3 == 0 and i + 2 < len(star_positions):
                                star3 = star_positions[i + 2]
                                pygame.draw.line(screen, (100, 150, 255), star1, star3, 2)
                        
        elif boss_index == 5:  # バツボス
            if cycle_time < 3:  # 最初の3秒
                # 中央に現れて壁から槍を出す
                x_pos = WIDTH // 2
                y_pos = HEIGHT // 2
                boss_radius = 40
                # バツ印を描画（実際のゲームと同じ）
                arm = boss_radius + 10
                thickness = max(12, boss_radius // 3)
                pygame.draw.line(screen, (255, 90, 90), (x_pos - arm, y_pos - arm), (x_pos + arm, y_pos + arm), thickness)
                pygame.draw.line(screen, (255, 90, 90), (x_pos - arm, y_pos + arm), (x_pos + arm, y_pos - arm), thickness)
                pygame.draw.circle(screen, (255, 180, 180), (x_pos, y_pos), thickness//2)
                # 壁から槍を出す（左右から複数）
                spear_count = min(int(cycle_time * 3), 5)  # 最大5本
                spear_progress = (cycle_time * 3) % 1.0  # 槍の伸び具合
                for i in range(spear_count):
                    # 各槍のY位置
                    lane_y = HEIGHT * (i + 1) / (spear_count + 1)
                    spear_length = 120
                    spear_width = 10
                    # 槍の伸び具合（時間差で伸びる）
                    extend_ratio = min(1.0, max(0.0, spear_progress + (i * 0.15)))
                    current_length = spear_length * extend_ratio
                    
                    # 左からの槍
                    left_tip_x = current_length
                    tip_size = 28
                    shaft_end = max(0, left_tip_x - tip_size)
                    # 槍の軸
                    pygame.draw.rect(screen, (255, 70, 70), (0, lane_y - spear_width//2, shaft_end, spear_width))
                    # 槍の先端（三角形）
                    if left_tip_x > 0:
                        pygame.draw.polygon(screen, (255, 70, 70), [
                            (shaft_end, lane_y - spear_width//2),
                            (shaft_end, lane_y + spear_width//2),
                            (left_tip_x, lane_y)
                        ])
                    
                    # 右からの槍
                    right_tip_x = WIDTH - current_length
                    shaft_start = min(WIDTH, right_tip_x + tip_size)
                    # 槍の軸
                    pygame.draw.rect(screen, (255, 70, 70), (shaft_start, lane_y - spear_width//2, WIDTH - shaft_start, spear_width))
                    # 槍の先端（三角形）
                    if right_tip_x < WIDTH:
                        pygame.draw.polygon(screen, (255, 70, 70), [
                            (shaft_start, lane_y - spear_width//2),
                            (shaft_start, lane_y + spear_width//2),
                            (right_tip_x, lane_y)
                        ])
            else:  # 3秒後に虹ボスに変身
                # 虹色の星に変身
                x_pos = WIDTH // 2
                y_pos = HEIGHT // 2
                boss_radius = 40
                # 星を描画（実際のゲームと同じ虹色ストライプ）
                star_hue = (time.time() * 200) % 360
                rotation = (time.time() * 100) % 360
                
                # 虹色のストライプパターン（実際のゲームと同じ）
                star_size = (boss_radius + 40) * 2
                striped = pygame.Surface((star_size, star_size), pygame.SRCALPHA)
                spectrum = [
                    (255, 80, 80),
                    (255, 150, 60),
                    (255, 220, 90),
                    (120, 240, 120),
                    (100, 190, 255),
                    (170, 120, 250)
                ]
                stripe_w = max(2, star_size // (len(spectrum) * 2))
                x = 0
                color_index = 0
                while x < star_size:
                    col = spectrum[color_index % len(spectrum)]
                    pygame.draw.rect(striped, col, (x, 0, stripe_w, star_size))
                    x += stripe_w
                    color_index += 1
                
                # 星型マスクを作成
                mask = pygame.Surface((star_size, star_size), pygame.SRCALPHA)
                inner_radius = int(star_size * 0.25)
                # 星型（10点）
                points = []
                for i in range(10):
                    angle = math.radians(rotation) + (math.pi / 5) * i
                    radius = (star_size // 2) if i % 2 == 0 else inner_radius
                    px = star_size // 2 + radius * math.cos(angle)
                    py = star_size // 2 + radius * math.sin(angle)
                    points.append((px, py))
                pygame.draw.polygon(mask, (255, 255, 255), points)
                
                # ストライプをマスクで切り抜き
                striped.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                rect = striped.get_rect(center=(x_pos, y_pos))
                screen.blit(striped, rect)
                
                # カラフルな星を降らせる
                star_rain_count = 15
                for i in range(star_rain_count):
                    # 各星の位置（時間とインデックスで異なる）
                    fall_time = (time.time() * 80 + i * 20) % (HEIGHT + 100)
                    star_x = (i * 79) % WIDTH  # 疑似ランダムなX位置
                    star_y = fall_time - 50
                    
                    if 0 <= star_y <= HEIGHT:
                        # 星ごとに異なる色相
                        star_hue_offset = (star_hue + i * 24) % 360
                        star_rgb = colorsys.hsv_to_rgb(star_hue_offset / 360.0, 1.0, 1.0)
                        star_color = (int(star_rgb[0] * 255), int(star_rgb[1] * 255), int(star_rgb[2] * 255))
                        
                        # 小さな星を描画
                        star_points = []
                        small_star_size = 8
                        for j in range(10):
                            angle = (j / 10) * math.pi * 2 - math.pi / 2 + (fall_time * 0.05)
                            radius = small_star_size if j % 2 == 0 else small_star_size * 0.4
                            px = star_x + math.cos(angle) * radius
                            py = star_y + math.sin(angle) * radius
                            star_points.append((px, py))
                        pygame.draw.polygon(screen, star_color, star_points)
    
    title_font = jp_font(50)
    if true_ending_achieved:
        title = title_font.render("★ フルコンプ達成 ★", True, (255, 255, 100))
    else:
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
            # 虹の星（最上位：星ボスを装備なし・phase1から通しでクリア）
            if level_cleared_rainbow_star and len(level_cleared_rainbow_star) > i and level_cleared_rainbow_star[i]:
                # 虹色の星：複数の色を重ねてレインボーエフェクト
                import time
                hue_offset = (time.time() * 100) % 360  # 時間で色相を変化
                colors = []
                for j in range(3):
                    hue = (hue_offset + j * 120) % 360
                    import colorsys
                    rgb = colorsys.hsv_to_rgb(hue / 360.0, 1.0, 1.0)
                    colors.append((int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255)))
                
                # 3つの星を少しずつずらして重ねる
                for j, color in enumerate(colors):
                    star = text_surface("★", 38 + j * 2, color)
                    star.set_alpha(120 + j * 20)
                    screen.blit(star, (x + label.get_width() + 8 - j, y - j))
            # 装備なしクリアの場合は豪華な星を表示
            elif level_cleared_no_equipment and len(level_cleared_no_equipment) > i and level_cleared_no_equipment[i]:
                # 豪華な星：グラデーション効果を持つ金色
                star_base = text_surface("★", 38, (218, 165, 32))  # 深みのある金色
                star_glow = text_surface("★", 44, (255, 215, 100))  # 明るい金色
                # 輝きエフェクト（半透明で重ねる）
                star_glow.set_alpha(80)
                screen.blit(star_glow, (x + label.get_width() + 7, y - 3))
                screen.blit(star_base, (x + label.get_width() + 10, y))
            else:
                # 通常の星：白色
                star = text_surface("★", 38, (255, 255, 255))
                screen.blit(star, (x + label.get_width() + 10, y))
    # 操作説明を2行に分けて表示
    info1 = text_surface("↑↓: 選択  Enter: 開始  T: タイトル", 20, WHITE)
    info2 = text_surface("E: 装備  S: セーブ  L: ロード", 20, WHITE)
    screen.blit(info1, (WIDTH // 2 - info1.get_width() // 2, HEIGHT - 70))
    screen.blit(info2, (WIDTH // 2 - info2.get_width() // 2, HEIGHT - 45))


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
    menu_text = text_surface("1: メニュー   2: リトライ   T: タイトル   3: 終了", 24, WHITE)
    menu_rect = menu_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30))
    screen.blit(menu_text, menu_rect)


def draw_save_load_menu(screen, selected_slot, save_info_1, save_info_2, mode='load'):
    """セーブ・ロード画面を描画
    
    Args:
        screen: 描画先サーフェス
        selected_slot: 選択中のスロット (1 or 2)
        save_info_1: スロット1のセーブ情報 (None if empty)
        save_info_2: スロット2のセーブ情報 (None if empty)
        mode: 'load' or 'save'
    """
    screen.fill((0, 0, 0))
    title_font = jp_font(50)
    title_text = "ロード" if mode == 'load' else "セーブ"
    title = title_font.render(title_text, True, WHITE)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 60))
    
    # スロット表示
    slot_font = jp_font(38)
    info_font = jp_font(24)
    
    for slot_num in (1, 2):
        save_info = save_info_1 if slot_num == 1 else save_info_2
        y_pos = 180 + (slot_num - 1) * 120
        
        # スロット番号
        color = WHITE if selected_slot == slot_num else (120, 120, 120)
        slot_text = slot_font.render(f"スロット {slot_num}", True, color)
        screen.blit(slot_text, (WIDTH // 2 - slot_text.get_width() // 2, y_pos))
        
        # セーブ情報
        if save_info:
            levels_text = f"クリア済み: {save_info['levels_cleared']}/{save_info['total_levels']}"
            levels_surf = info_font.render(levels_text, True, (200, 200, 200))
            screen.blit(levels_surf, (WIDTH // 2 - levels_surf.get_width() // 2, y_pos + 45))
            
            # アンロック情報（短縮表記でコンパクトに）
            unlocks = []
            if save_info['unlocked_homing']:
                unlocks.append("H")  # ホーミング
            if save_info['unlocked_spread']:
                unlocks.append("S")  # 拡散
            if save_info['unlocked_dash']:
                unlocks.append("D")  # ダッシュ
            if save_info['unlocked_leaf_shield']:
                unlocks.append("L")  # リーフ
            if save_info['unlocked_hp_boost']:
                unlocks.append("HP+")
            
            if unlocks:
                unlock_text = "解放: " + ", ".join(unlocks)
                unlock_surf = info_font.render(unlock_text, True, (150, 150, 255))
                screen.blit(unlock_surf, (WIDTH // 2 - unlock_surf.get_width() // 2, y_pos + 70))
        else:
            empty_text = info_font.render("空きスロット", True, (100, 100, 100))
            screen.blit(empty_text, (WIDTH // 2 - empty_text.get_width() // 2, y_pos + 45))
    
    # 操作説明
    help_font = jp_font(22)
    if mode == 'load':
        help_text = "↑↓: 選択   Enter: ロード   D: 削除   ESC: 戻る"
    else:
        help_text = "↑↓: 選択   Enter: セーブ   ESC: 戻る"
    help_surf = help_font.render(help_text, True, WHITE)
    screen.blit(help_surf, (WIDTH // 2 - help_surf.get_width() // 2, HEIGHT - 60))


def draw_save_confirm_dialog(screen, slot_num):
    """上書き確認ダイアログを描画
    
    Args:
        screen: 描画先サーフェス
        slot_num: 上書き対象のスロット番号
    """
    # 半透明の黒い背景
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(180)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))
    
    # 確認メッセージ
    dialog_font = jp_font(32)
    confirm_text = dialog_font.render(f"スロット {slot_num} を上書きしますか?", True, WHITE)
    screen.blit(confirm_text, (WIDTH // 2 - confirm_text.get_width() // 2, HEIGHT // 2 - 40))
    
    # 選択肢
    option_font = jp_font(26)
    yes_text = option_font.render("Enter: はい   ESC: いいえ", True, (200, 200, 200))
    screen.blit(yes_text, (WIDTH // 2 - yes_text.get_width() // 2, HEIGHT // 2 + 20))


def draw_equipment_menu(screen, selected_index, equipment_enabled, unlocked_homing, 
                        unlocked_leaf_shield, unlocked_spread, unlocked_dash, unlocked_hp_boost):
    """アイテム装備画面を描画
    
    Args:
        screen: 描画先サーフェス
        selected_index: 選択中のアイテムインデックス
        equipment_enabled: 各アイテムの有効/無効設定
        unlocked_*: 各アイテムのアンロック状態
    """
    screen.fill((0, 0, 0))
    
    # タイトル
    title_font = jp_font(50)
    title = title_font.render("アイテム装備", True, WHITE)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 40))
    
    # アイテムリスト
    items = [
        {'key': 'homing', 'name': 'ホーミング弾', 'unlocked': unlocked_homing},
        {'key': 'leaf_shield', 'name': 'リーフシールド', 'unlocked': unlocked_leaf_shield},
        {'key': 'spread', 'name': '拡散弾(3WAY)', 'unlocked': unlocked_spread},
        {'key': 'dash', 'name': '緊急回避', 'unlocked': unlocked_dash},
        {'key': 'hp_boost', 'name': '体力増加', 'unlocked': unlocked_hp_boost}
    ]
    
    item_font = jp_font(32)
    status_font = jp_font(28)
    base_y = 140
    line_h = 70
    
    for i, item in enumerate(items):
        y = base_y + i * line_h
        
        # 選択カーソル
        if i == selected_index:
            cursor = "▶ "
            cursor_surf = item_font.render(cursor, True, (255, 255, 100))
            screen.blit(cursor_surf, (80, y))
        
        # アイテム名
        if item['unlocked']:
            color = WHITE
            name_text = item['name']
        else:
            color = (80, 80, 80)
            name_text = "???"
        
        name_surf = item_font.render(name_text, True, color)
        screen.blit(name_surf, (130, y))
        
        # 装備状態
        if item['unlocked']:
            if equipment_enabled[item['key']]:
                status = "ON"
                status_color = (100, 255, 100)
            else:
                status = "OFF"
                status_color = (200, 100, 100)
            
            status_surf = status_font.render(status, True, status_color)
            screen.blit(status_surf, (WIDTH - 150, y + 5))
    
    # 操作説明
    help_font = jp_font(22)
    help_text = "↑↓: 選択   Enter/Space: 切替   ESC: 戻る"
    help_surf = help_font.render(help_text, True, WHITE)
    screen.blit(help_surf, (WIDTH // 2 - help_surf.get_width() // 2, HEIGHT - 60))


def draw_pause_menu(screen, selected_index):
    """ポーズ画面を描画
    
    Args:
        screen: 描画先サーフェス
        selected_index: 選択中のメニューインデックス (0: 続ける, 1: メニューに戻る)
    """
    # 半透明の黒い背景（背景が透けて見える）
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(150)  # 透明度を下げて背景をより透けさせる
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))
    
    # タイトル
    title_font = jp_font(60)
    title = title_font.render("ポーズ", True, WHITE)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 80))
    
    # ポーズボタンの説明
    pause_info_font = jp_font(24)
    pause_info = pause_info_font.render("(ESC または P でポーズ)", True, (200, 200, 200))
    screen.blit(pause_info, (WIDTH // 2 - pause_info.get_width() // 2, 150))
    
    # メニュー項目
    menu_items = ["続ける", "メニューに戻る"]
    item_font = jp_font(40)
    base_y = 260
    line_h = 80
    
    for i, item in enumerate(menu_items):
        y = base_y + i * line_h
        
        # 選択カーソル
        if i == selected_index:
            color = (255, 255, 100)
            cursor = "▶ "
            cursor_surf = item_font.render(cursor, True, color)
            screen.blit(cursor_surf, (WIDTH // 2 - 150, y))
        else:
            color = (180, 180, 180)
        
        item_surf = item_font.render(item, True, color)
        screen.blit(item_surf, (WIDTH // 2 - item_surf.get_width() // 2, y))
    
    # 操作説明
    help_font = jp_font(22)
    help_text = "↑↓: 選択   Enter: 決定   ESC/P: ポーズ解除"
    help_surf = help_font.render(help_text, True, (255, 255, 255))
    screen.blit(help_surf, (WIDTH // 2 - help_surf.get_width() // 2, HEIGHT - 60))

