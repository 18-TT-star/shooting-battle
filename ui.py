# ui.py
# メニュー / リザルト / 汎用テキスト描画
import pygame
from fonts import jp_font, text_surface
from constants import WIDTH, HEIGHT, WHITE, RED

def draw_title_screen(screen, frame_count):
    """タイトル画面を描画"""
    screen.fill((5, 5, 20))  # 暗い青背景
    
    # タイトルを特殊フォント（大きく）で表示
    title_size = 52  # さらに小さくしてウィンドウに収める
    title_font = jp_font(title_size)
    
    # ゲームタイトル
    title_text = "Bob's Big Adventure"
    title_surf = title_font.render(title_text, True, (255, 215, 0))  # ゴールド色
    
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


def draw_menu(screen, selected_level, level_cleared, level_cleared_no_equipment=None):
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
            # 装備なしクリアの場合は豪華な星を表示
            if level_cleared_no_equipment and len(level_cleared_no_equipment) > i and level_cleared_no_equipment[i]:
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
    info = text_surface("↑↓: 選択  Enter: 開始  E: 装備  S: セーブ  L: ロード", 20, WHITE)
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

