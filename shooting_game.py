import pygame
import sys
import random
import math

# ================== 定数 ==================
EXPLOSION_DURATION = 30        # 小爆発表示
BOSS_EXPLOSION_DURATION = 60   # ボス撃破時派手演出
PLAYER_INVINCIBLE_DURATION = 120
BOSS_ATTACK_INTERVAL = 180
# 楕円ボス コア調整（当てやすさ緩和用）
OVAL_CORE_RADIUS = 28          # 弱点赤丸半径 (旧18→24→28)
OVAL_CORE_GAP_HIT_THRESHOLD = 3  # gap この値超えでコア当たり判定開始 (旧5相当)
OVAL_CORE_NO_REFLECT_WHEN_OPEN = True  # 開放中は中央縦楕円で弾を反射しない

pygame.init()
WIDTH, HEIGHT = 480, 640
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("シューティングゲーム")

# ================== 色 ==================
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY  = (120, 120, 120)
RED   = (255, 0, 0)

# 弾カラー（視認性向上）
BULLET_COLOR_NORMAL  = WHITE
BULLET_COLOR_HOMING  = (50, 200, 255)   # シアン寄り
BULLET_COLOR_ENEMY   = (255, 120, 40)   # オレンジ
BULLET_COLOR_REFLECT = (255, 255, 0)    # 反射中: 黄

# 楕円ボス ビーム同時発射用定数
OVAL_BEAM_INTERVAL = 170   # 両側同時に telegraph へ移行するまでの待機フレーム

# ================== 日本語フォント対応 ==================
JP_FONT_CANDIDATES = [
    "NotoSansCJKJP", "Noto Sans CJK JP", "notosanscjkjp", "notosansjp",
    "SourceHanSansJP", "sourcehansansjp", "ipagothic", "ipamgothic",
    "TakaoPGothic", "VL PGothic", "meiryo", "msgothic", "Yu Gothic", "yugothic", "sansserif"
]
_JP_FONT_PATH = None
for name in JP_FONT_CANDIDATES:
    try:
        p = pygame.font.match_font(name)
    except Exception:
        p = None
    if p:
        _JP_FONT_PATH = p
        break
_font_cache = {}
def jp_font(size: int):
    f = _font_cache.get(size)
    if f:
        return f
    if _JP_FONT_PATH:
        f = pygame.font.Font(_JP_FONT_PATH, size)
    else:
        f = pygame.font.SysFont(None, size)
    _font_cache[size] = f
    return f

# ================== ボス / レベル定義 ==================
boss_list = [
    {"name": "Boss A", "radius": 60, "hp": 35, "color": RED},
    {"name": "蛇", "radius": 70, "hp": 40, "color": (128, 0, 128)},
    # 楕円ボス大型化 radius 50 -> 70
    {"name": "楕円ボス", "radius": 70, "hp": 10, "color": (255, 165, 0)}
]

level_list = [
    {"level": 10, "boss": None},
    {"level": 1, "boss": boss_list[0]},
    {"level": 2, "boss": boss_list[1]},
    {"level": 3, "boss": boss_list[2]},
    {"level": 4, "boss": None},
    {"level": 5, "boss": None},
    {"level": 6, "boss": None},
    {"level": 7, "boss": None},
    {"level": 8, "boss": None},
    {"level": 9, "boss": None},
]
selected_level = 1  # 0 が level10, 1..9 が level1..9
menu_mode = True
level_cleared = [False]*10

def draw_menu():
    screen.fill(BLACK)
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
    # levels 9..1
    # 行間を少し詰めて下部の説明文と重ならないようにする
    for i in range(9,0,-1):
        color = WHITE if selected_level == i else GRAY
        lvl_text = font2.render(f"LEVEL {i}", True, color)
        # 45 -> 42 に変更し全体を上に詰める
        y = 180 + (9 - i) * 42
        x = WIDTH//2 - lvl_text.get_width()//2
        screen.blit(lvl_text, (x, y))
        if level_cleared[i]:
            star = font2.render("★", True, (255,215,0))
            screen.blit(star, (x + lvl_text.get_width() + 10, y))
    # 下部説明（1行に統合して視認性向上）
    font3 = pygame.font.SysFont(None, 20)
    info = font3.render("←→:Select  Enter:Start   ★=Cleared", True, WHITE)
    screen.blit(info, (WIDTH//2 - info.get_width()//2, HEIGHT - 46))
    pygame.display.flip()

# （この下にゲームループ）

# --------- Utility: split ellipse drawing (for oval boss core opening) ---------
def draw_split_ellipse(surface, center_x, center_y, radius, gap, color):
    """Draw a vertical ellipse split into two half-ellipses separated by gap.
    radius: width of original ellipse; height is radius*2 (existing design)."""
    width = radius
    height = radius * 2
    # Create full ellipse surface with alpha
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, color, (0, 0, width, height))
    half_w = width // 2
    # Left half
    left_half = surf.subsurface((0, 0, half_w, height))
    right_half = surf.subsurface((half_w, 0, width - half_w, height))
    # Positions (gap splits outward)
    top = center_y - height // 2
    left_x = center_x - width // 2 - gap // 2
    right_x = center_x - width // 2 + half_w + gap // 2
    surface.blit(left_half, (left_x, top))
    surface.blit(right_half, (right_x, top))

def draw_end_menu(result, reward_text=None):
    screen.fill(BLACK)
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
        # 簡易改行: 幅がはみ出す場合はスペース区切りで複数行化
        def split_reward(text):
            parts = text.split(' ')
            lines = []
            cur = ''
            for p in parts:
                test = (cur + ' ' + p).strip()
                w, _ = font_reward.size(test)
                if w > WIDTH - 40 and cur:
                    lines.append(cur)
                    cur = p
                else:
                    cur = test
            if cur:
                lines.append(cur)
            return lines
        lines = split_reward(reward_text)
        # 複数行の高さ調整（中央付近に収める）
        line_h = font_reward.get_linesize()
        total_h = line_h * len(lines)
        # GAME CLEAR との重なり回避のため少し下へオフセット(+20)
        start_y = (HEIGHT // 2 - 10) - total_h // 2 + line_h // 2
        for i, line in enumerate(lines):
            surf = font_reward.render(line, True, (0,255,0))
            rect = surf.get_rect(center=(WIDTH//2, start_y + i*line_h))
            screen.blit(surf, rect)
    font2 = jp_font(30)
    menu_text = font2.render("1: Menu   2: Retry   3: Quit", True, WHITE)
    menu_rect = menu_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30))
    screen.blit(menu_text, menu_rect)
    pygame.display.flip()


# ゲームループ

clock = pygame.time.Clock()
edge_move_flag = None
cross_flag = None

# プレイヤー初期化
player = pygame.Rect(WIDTH // 2 - 15, HEIGHT - 40, 30, 30)
player_speed = 7
player_lives = 3
explosion_timer = 0
explosion_pos = None
bullet_speed = 10

# 蛇ボス用変数
snake_segments = []  # 小さい正方形の座標リスト
snake_tail_fixed = False
snake_state = "normal"  # normal, grow, edge_move, cross, shrink
snake_attack_timer = 0
snake_grow_timer = 0
snake_shrink_timer = 0
snake_tail_pos = None
snake_target_edge = None
snake_attack_y = None
snake_cross_progress = 0

retry = False
waiting_for_space = False
# 報酬・弾種管理
has_homing = False
bullet_type = "normal"  # normal or homing
has_leaf_shield = False
leaf_angle = 0.0
# ボス攻撃タイマー（グローバル宣言）
boss_attack_timer = 0
# 報酬持ち越しフラグ
unlocked_homing = False
unlocked_leaf_shield = False
while True:
    events = pygame.event.get()
    if menu_mode:
        draw_menu()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected_level = (selected_level + 1) % 10
                if event.key == pygame.K_DOWN:
                    selected_level = (selected_level - 1) % 10
                if event.key == pygame.K_RETURN:
                    # レベル選択でボスがいる場合のみ開始
                    boss_info = level_list[selected_level]["boss"]
                    if boss_info:
                        boss_radius = boss_info["radius"]
                        boss_hp = boss_info["hp"]
                        boss_color = boss_info["color"]
                        retry = False
                        waiting_for_space = False
                        # 報酬・弾種管理
                        has_homing = unlocked_homing
                        has_leaf_shield = unlocked_leaf_shield
                        bullet_type = "normal"  # 常に通常から
                        leaf_angle = 0.0
                        boss_x = WIDTH // 2
                        boss_y = 60
                        boss_alive = True
                        boss_speed = 4
                        boss_dir = 1
                        boss_state = "track"
                        # Boss A 踏み潰し攻撃用初期化
                        if boss_info["name"] == "Boss A":
                            boss_info['stomp_state'] = 'idle'  # idle, descending, pause, ascending, cooldown
                            boss_info['stomp_timer'] = 0
                            boss_info['stomp_target_y'] = None
                            boss_info['home_y'] = boss_y
                            boss_info['stomp_interval'] = 120  # 通常間隔
                            boss_info['last_stomp_frame'] = 0   # 開始直後に即発動しないため現在値
                            boss_info['stomp_grace'] = 180      # 最初の猶予(約3秒)
                        if boss_info["name"] == "蛇":
                            boss_info['snake_stomp_state'] = 'idle'
                            boss_info['snake_stomp_timer'] = 0
                            boss_info['snake_stomp_target_y'] = None
                            boss_info['snake_home_y'] = boss_y
                            boss_info['snake_stomp_interval'] = 150  # Boss2 は少し遅め開始
                            boss_info['snake_last_stomp_frame'] = 0
                            boss_info['snake_stomp_grace'] = 210  # 3.5秒猶予
                        if boss_info and boss_info["name"] == "楕円ボス":
                            boss_origin_x = boss_x
                            if 'core_state' not in boss_info:
                                boss_info['core_state'] = 'closed'
                                boss_info['core_timer'] = 0
                                boss_info['core_cycle_interval'] = 240
                                boss_info['core_firing_duration'] = 60
                                boss_info['core_open_hold'] = 120  # 開放維持を長く
                                boss_info['core_gap'] = 0
                                boss_info['core_gap_target'] = 40
                        player_lives = 3
                        player_invincible = False
                        player_invincible_timer = 0
                        explosion_timer = 0
                        explosion_pos = None
                        bullets = []
                        boss_explosion_timer = 0
                        boss_explosion_pos = []
                        boss_attack_timer = 0
                        retry = False
                        player = pygame.Rect(WIDTH // 2 - 15, HEIGHT - 40, 30, 15)
                        player_speed = 5
                        bullet_speed = 7
                        waiting_for_space = True
                        menu_mode = False
        continue
    if waiting_for_space:
        screen.fill(BLACK)
        font = pygame.font.SysFont(None, 42)
        text = font.render("Press SPACE to start!", True, WHITE)
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(text, text_rect)
        pygame.display.flip()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    bullets.append({
                        "rect": pygame.Rect(player.centerx - 3, player.top - 6, 6, 12),
                        "type": bullet_type,
                        "power": 1.0 if bullet_type == "normal" else 0.5,
                        "vx": 0,
                        "vy": -bullet_speed
                    })
                    waiting_for_space = False
        continue
    if retry:
        player_lives = 3
        player_invincible = False
        player_invincible_timer = 0
        explosion_timer = 0
        explosion_pos = None
        bullets = []

        boss_alive = True
        boss_x = WIDTH // 2
        boss_y = 60
        boss_state = "track"
        boss_speed = 4
        boss_dir = 1
        boss_attack_timer = 0
        boss_origin_x = boss_x
        boss_origin_y = boss_y
        boss_hp = boss_info["hp"] if boss_info else 35
        if boss_info and boss_info["name"] == "Boss A":
            boss_info['stomp_state'] = 'idle'
            boss_info['stomp_timer'] = 0
            boss_info['stomp_target_y'] = None
            boss_info['home_y'] = boss_y
            boss_info['stomp_interval'] = 120
            boss_info['last_stomp_frame'] = 0
            boss_info['stomp_grace'] = 180
        if boss_info and boss_info["name"] == "蛇":
            boss_info['snake_stomp_state'] = 'idle'
            boss_info['snake_stomp_timer'] = 0
            boss_info['snake_stomp_target_y'] = None
            boss_info['snake_home_y'] = boss_y
            boss_info['snake_stomp_interval'] = 150
            boss_info['snake_last_stomp_frame'] = 0
            boss_info['snake_stomp_grace'] = 210
        retry = False
    if not boss_alive and boss_explosion_timer == 1:
        # ボス1を倒した場合のみ報酬
        if boss_info and boss_info["name"] == "Boss A":
            has_homing = True
            unlocked_homing = True
            bullet_type = "normal"
        # ボス2（蛇）討伐報酬：リーフシールド
        if boss_info and boss_info["name"] == "蛇":
            has_leaf_shield = True
            unlocked_leaf_shield = True

    # 弾発射
    for event in events:
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if bullet_type == "normal":
                    bullets.append({"rect": pygame.Rect(
                        player.centerx - 3, player.top - 6, 6, 12), "type": "normal", "power": 1.0})
                elif bullet_type == "homing":
                    bullets.append({"rect": pygame.Rect(
                        player.centerx - 3, player.top - 6, 6, 12), "type": "homing", "power": 0.5})
            # 全ボス共通: テスト用即撃破キー
            if event.key == pygame.K_t and boss_alive and boss_info:
                boss_hp = 0
            if event.key == pygame.K_v and has_homing:
                bullet_type = "homing" if bullet_type == "normal" else "normal"

    # 自機移動
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT] and player.left > 0:
        player.x -= player_speed
    if keys[pygame.K_RIGHT] and player.right < screen.get_width():
        player.x += player_speed

    # 弾の移動
    for bullet in bullets:
        # velocityベースで移動
        if bullet["type"] == "homing" and boss_alive:
            dx = boss_x - bullet["rect"].centerx
            dy = boss_y - bullet["rect"].centery
            dist = max(1, (dx**2 + dy**2)**0.5)
            bullet["vx"] = int(6 * dx / dist)
            bullet["vy"] = int(6 * dy / dist)
        bullet["rect"].x += bullet.get("vx", 0)
        bullet["rect"].y += bullet.get("vy", -bullet_speed)
    # 上に抜けた自機弾と下に抜けた敵弾を除去
    bullets = [b for b in bullets if b["rect"].bottom > 0 and b["rect"].top < HEIGHT]

    # 弾とボスの当たり判定（多重ヒット防止版）
    if boss_alive and boss_info:
        cleaned_bullets = []
        for bullet in bullets:
            if bullet.get("type") in ("enemy", "boss_beam"):
                cleaned_bullets.append(bullet)
                continue
            damage = False
            # 楕円ボス: コア開放時のみ弱点ダメージ, それ以外は反射
            if boss_info["name"] == "楕円ボス":
                core_state = boss_info.get('core_state','closed')
                gap = boss_info.get('core_gap',0)
                cx, cy = boss_x, boss_y
                # コア開放中 & 弾がコア円内ならダメージ
                if core_state in ('opening','firing','open_hold') and gap > OVAL_CORE_GAP_HIT_THRESHOLD:
                    if (bullet["rect"].centerx - cx)**2 + (bullet["rect"].centery - cy)**2 < OVAL_CORE_RADIUS**2:
                        boss_hp -= bullet.get("power", 1.0)
                        boss_explosion_pos.append((bullet["rect"].centerx, bullet["rect"].centery))
                        if boss_hp <= 0:
                            boss_alive = False
                            boss_explosion_timer = 0
                            explosion_pos = (boss_x, boss_y)
                        damage = True
                if not damage:
                    central_open = (core_state in ('opening','firing','open_hold') and gap > OVAL_CORE_GAP_HIT_THRESHOLD)
                    if central_open:
                        # 開放中は本体を完全スルー（反射無効）
                        pass
                    else:
                        # Boss radius に応じて反射領域をスケール
                        R = boss_radius  # 70 想定（可変対応）
                        central_a = int(R * 0.6)   # 旧: 30 (R=50)
                        central_b = int(R * 1.0)   # 旧: 50 (R=50)
                        side_a = int(R * 0.4)      # 旧: 20 (R=50)
                        side_b = int(R * 0.6)      # 旧: 30 (R=50)
                        side_offset = int(R * 1.2) # 旧: 60 (R=50)
                        reflected_here = False
                        if ((bullet["rect"].centerx - cx)**2)/(central_a**2) + ((bullet["rect"].centery - cy)**2)/(central_b**2) < 1:
                            reflected_here = True
                        else:
                            for ox in (-side_offset, side_offset):
                                ex = boss_x + ox - (side_a if ox>0 else -side_a)
                                ey = boss_y
                                if ((bullet["rect"].centerx - ex)**2)/(side_a**2) + ((bullet["rect"].centery - ey)**2)/(side_b**2) < 1:
                                    reflected_here = True
                                    break
                        if reflected_here:
                            bullet["reflect"] = True
                            bullet["vy"] = abs(bullet.get("vy", -7))
                            bullet["vx"] = random.randint(-3, 3)
                if not damage:
                    cleaned_bullets.append(bullet)
                continue
            if boss_info["name"] == "蛇":
                main_size = int(boss_radius * 1.2)
                main_rect = pygame.Rect(boss_x - main_size//2, boss_y - main_size//2, main_size, main_size)
                if main_rect.colliderect(bullet["rect"]):
                    boss_hp -= bullet.get("power", 1.0)
                    boss_explosion_pos.append((bullet["rect"].centerx, bullet["rect"].centery))
                    if boss_hp <= 0:
                        boss_alive = False
                        boss_explosion_timer = 0
                        explosion_pos = (boss_x, boss_y)
                    damage = True  # ダメージ弾は消す
                else:
                    ROTATE_SEGMENTS_NUM = 5
                    ROTATE_RADIUS = boss_radius + 30
                    rotate_angle_local = globals().get("rotate_angle", 0.0)
                    for i in range(ROTATE_SEGMENTS_NUM):
                        angle = rotate_angle_local + (2*math.pi*i/ROTATE_SEGMENTS_NUM)
                        sx = boss_x + ROTATE_RADIUS * math.cos(angle)
                        sy = boss_y + ROTATE_RADIUS * math.sin(angle)
                        seg_rect = pygame.Rect(int(sx-20), int(sy-20), 40, 40)
                        if seg_rect.colliderect(bullet["rect"]):
                            bullet["reflect"] = True
                            bullet["vy"] = abs(bullet.get("vy", -7))
                            bullet["vx"] = random.randint(-3, 3)
                            break
                if not damage:
                    cleaned_bullets.append(bullet)
                continue
            # 通常ボス
            dx = bullet["rect"].centerx - boss_x
            dy = bullet["rect"].centery - boss_y
            if dx*dx + dy*dy < boss_radius*boss_radius:
                boss_hp -= bullet.get("power", 1.0)
                boss_explosion_pos.append((bullet["rect"].centerx, bullet["rect"].centery))
                if boss_hp <= 0:
                    boss_alive = False
                    boss_explosion_timer = 0
                    explosion_pos = (boss_x, boss_y)
                damage = True
            if not damage:
                cleaned_bullets.append(bullet)
        bullets = cleaned_bullets
    # ボス撃破後の爆発演出
    if not boss_alive and boss_explosion_timer < BOSS_EXPLOSION_DURATION:
        boss_explosion_timer += 1
    # ボスキャラの攻撃パターン
    if boss_alive:
        boss_attack_timer += 1
        
        # 新・回転型ボス
        ROTATE_SEGMENTS_NUM = 5
        ROTATE_RADIUS = boss_radius + 30
        ROTATE_SPEED = 0.03
        if 'rotate_angle' not in globals():
            rotate_angle = 0.0
        rotate_angle += ROTATE_SPEED
        # Boss A: 横移動＋攻撃パターン
        if boss_info and boss_info["name"] == "Boss A":
            # 踏み潰し攻撃状態遷移
            if 'stomp_state' not in boss_info:
                boss_info['stomp_state'] = 'idle'   # idle -> prelift -> descending -> pause -> ascending -> cooldown
                boss_info['stomp_timer'] = 0
                boss_info['stomp_target_y'] = None
                boss_info['home_y'] = boss_y
                boss_info['stomp_interval'] = 120  # 約2秒
                boss_info['last_stomp_frame'] = 0   # 初回即発動防止
                boss_info['stomp_grace'] = 180      # 初回猶予フレーム
            else:
                # 既存辞書に欠けている場合の安全補填
                boss_info.setdefault('last_stomp_frame', -9999)
                boss_info.setdefault('stomp_interval', 120)
                boss_info.setdefault('stomp_grace', 180)
            state = boss_info['stomp_state']
            # 共通: idle / cooldown 中はX追従
            TRACK_SPEED = 6
            if state in ('idle', 'cooldown'):
                dx_track = player.centerx - boss_x
                if abs(dx_track) > TRACK_SPEED:
                    boss_x += TRACK_SPEED if dx_track > 0 else -TRACK_SPEED
                else:
                    boss_x = player.centerx
            # 状態遷移
            if state == 'idle':
                # 一定間隔後、プレイヤーとのX差が小さければ予備動作へ
                if boss_attack_timer >= boss_info.get('stomp_grace',0) and \
                   boss_attack_timer - boss_info['last_stomp_frame'] >= boss_info['stomp_interval'] and \
                   abs(player.centerx - boss_x) < boss_radius * 1.8:
                    boss_info['stomp_state'] = 'prelift'
                    boss_info['stomp_timer'] = 0
            elif state == 'prelift':
                # 上に少し持ち上がる（予備動作）
                boss_info['stomp_timer'] += 1
                lift_amount = 12
                target_up = boss_info['home_y'] - lift_amount
                if boss_y > target_up:
                    boss_y -= 7  # 予備上昇さらに加速
                if boss_info['stomp_timer'] > 10:  # 10F後に下降開始
                    boss_info['stomp_state'] = 'descending'
                    # プレイヤー直上まで踏み込む（中心がプレイヤーの少し上に来るよう調整）
                    target_center = player.centery - (boss_radius - 10)
                    target_center = min(target_center, HEIGHT - boss_radius - 20)
                    target_center = max(target_center, boss_info.get('home_y', 60) + 80)
                    boss_info['stomp_target_y'] = target_center
            elif state == 'descending':
                # 動的にプレイヤーを追尾して更に深く潜る余地（プレイヤーが下がったら更新）
                dynamic_target = player.centery - (boss_radius - 10)
                dynamic_target = min(dynamic_target, HEIGHT - boss_radius - 20)
                if dynamic_target > boss_info.get('stomp_target_y', dynamic_target):
                    boss_info['stomp_target_y'] = dynamic_target
                boss_y += 22  # 下降さらに加速
                if boss_info['stomp_target_y'] is not None and boss_y >= boss_info['stomp_target_y']:
                    boss_y = boss_info['stomp_target_y']
                    boss_info['stomp_state'] = 'pause'
                    boss_info['stomp_timer'] = 0
            elif state == 'pause':
                boss_info['stomp_timer'] += 1  # 溜め短縮
                if boss_info['stomp_timer'] > 8:
                    boss_info['stomp_state'] = 'ascending'
            elif state == 'ascending':
                boss_y -= 12  # 上昇さらに加速
                if boss_y <= boss_info.get('home_y', 60):
                    boss_y = boss_info.get('home_y', 60)
                    boss_info['stomp_state'] = 'cooldown'
                    boss_info['stomp_timer'] = 0
                    boss_info['last_stomp_frame'] = boss_attack_timer
            elif state == 'cooldown':
                boss_info['stomp_timer'] += 1  # クールダウン短縮
                if boss_info['stomp_timer'] > 30:
                    boss_info['stomp_state'] = 'idle'
            # 弾幕なし
        # Boss2 蛇: Boss1 と似た踏み潰し＋X追従（回転体節を保持）
        if boss_info and boss_info["name"] == "蛇":
            # 初期セットアップ（不足分補填）
            if 'snake_stomp_state' not in boss_info:
                boss_info['snake_stomp_state'] = 'idle'
                boss_info['snake_stomp_timer'] = 0
                boss_info['snake_stomp_target_y'] = None
                boss_info['snake_home_y'] = boss_y
                boss_info['snake_stomp_interval'] = 150
                boss_info['snake_last_stomp_frame'] = 0
                boss_info['snake_stomp_grace'] = 210
            else:
                boss_info.setdefault('snake_last_stomp_frame', 0)
                boss_info.setdefault('snake_stomp_interval', 150)
                boss_info.setdefault('snake_stomp_grace', 210)
            s_state = boss_info['snake_stomp_state']
            TRACK_SPEED2 = 5
            if s_state in ('idle','cooldown'):
                dx_track = player.centerx - boss_x
                if abs(dx_track) > TRACK_SPEED2:
                    boss_x += TRACK_SPEED2 if dx_track > 0 else -TRACK_SPEED2
                else:
                    boss_x = player.centerx
            if s_state == 'idle':
                if boss_attack_timer >= boss_info['snake_stomp_grace'] and \
                   boss_attack_timer - boss_info['snake_last_stomp_frame'] >= boss_info['snake_stomp_interval'] and \
                   abs(player.centerx - boss_x) < boss_radius * 2.0:
                    boss_info['snake_stomp_state'] = 'prelift'
                    boss_info['snake_stomp_timer'] = 0
            elif s_state == 'prelift':
                boss_info['snake_stomp_timer'] += 1
                lift_amount = 16
                target_up = boss_info['snake_home_y'] - lift_amount
                if boss_y > target_up:
                    boss_y -= 6
                if boss_info['snake_stomp_timer'] > 8:
                    boss_info['snake_stomp_state'] = 'descending'
                    target_center = player.centery - (boss_radius - 6)
                    target_center = min(target_center, HEIGHT - boss_radius - 30)
                    target_center = max(target_center, boss_info.get('snake_home_y', 60) + 90)
                    boss_info['snake_stomp_target_y'] = target_center
            elif s_state == 'descending':
                dyn_target = player.centery - (boss_radius - 6)
                dyn_target = min(dyn_target, HEIGHT - boss_radius - 30)
                if dyn_target > boss_info.get('snake_stomp_target_y', dyn_target):
                    boss_info['snake_stomp_target_y'] = dyn_target
                boss_y += 18
                if boss_info['snake_stomp_target_y'] is not None and boss_y >= boss_info['snake_stomp_target_y']:
                    boss_y = boss_info['snake_stomp_target_y']
                    boss_info['snake_stomp_state'] = 'pause'
                    boss_info['snake_stomp_timer'] = 0
            elif s_state == 'pause':
                boss_info['snake_stomp_timer'] += 1
                if boss_info['snake_stomp_timer'] > 6:
                    boss_info['snake_stomp_state'] = 'ascending'
            elif s_state == 'ascending':
                boss_y -= 11
                if boss_y <= boss_info.get('snake_home_y', 60):
                    boss_y = boss_info.get('snake_home_y', 60)
                    boss_info['snake_stomp_state'] = 'cooldown'
                    boss_info['snake_stomp_timer'] = 0
                    boss_info['snake_last_stomp_frame'] = boss_attack_timer
            elif s_state == 'cooldown':
                boss_info['snake_stomp_timer'] += 1
                if boss_info['snake_stomp_timer'] > 40:
                    boss_info['snake_stomp_state'] = 'idle'
            # （弾幕なし、既存反射ギミックのみ）
         # ここに楕円ボスの移動ロジックを追加
        if boss_info and boss_info["name"] == "楕円ボス":
            # --- 基本左右移動 ---
            if 'move_dir' not in boss_info:
                boss_info['move_dir'] = 1
            boss_x += boss_info['move_dir'] * boss_speed
            if boss_x < boss_radius + 40:
                boss_x = boss_radius + 40
                boss_info['move_dir'] = 1
            elif boss_x > WIDTH - boss_radius - 40:
                boss_x = WIDTH - boss_radius - 40
                boss_info['move_dir'] = -1

            # --- 小楕円の向き（プレイヤー追尾 + 発射時ロック） ---
            boss_info.setdefault('left_angle', 0.0)
            boss_info.setdefault('right_angle', math.pi)

            # --- ビーム状態管理（左右同期版） ---
            # 共有ステート: idle -> telegraph -> firing -> cooldown
            if 'beam_shared_state' not in boss_info:
                boss_info['beam_shared_state'] = 'idle'
                boss_info['beam_shared_timer'] = 0
            if 'left_beam' not in boss_info:
                boss_info['left_beam'] = {'state':'idle','timer':0,'telegraph':30,'firing':55,'cooldown':70,'target':None,'origin':None}
            if 'right_beam' not in boss_info:
                boss_info['right_beam'] = {'state':'idle','timer':0,'telegraph':30,'firing':55,'cooldown':70,'target':None,'origin':None}

            small_w = boss_radius//2
            small_h = boss_radius*2//3
            left_center = (boss_x - boss_radius, boss_y)
            right_center = (boss_x + boss_radius, boss_y)

            # 共有ステート更新
            boss_info['beam_shared_timer'] += 1
            shared = boss_info['beam_shared_state']
            # 角度更新（idle/cooldown のみ追尾）
            for side, center in (('left', left_center), ('right', right_center)):
                angle_key = 'left_angle' if side=='left' else 'right_angle'
                if shared in ('idle','cooldown'):
                    dxp = player.centerx - center[0]
                    dyp = player.centery - center[1]
                    boss_info[angle_key] = math.atan2(dyp, dxp)
            # 状態遷移 (共有)
            if shared == 'idle' and boss_info['beam_shared_timer'] >= OVAL_BEAM_INTERVAL:
                # 双方ターゲット確定
                for side, center in (('left', left_center), ('right', right_center)):
                    beam = boss_info[f'{side}_beam']
                    beam['target'] = (player.centerx, player.centery)
                    dx = beam['target'][0] - center[0]
                    dy = beam['target'][1] - center[1]
                    boss_info['left_angle' if side=='left' else 'right_angle'] = math.atan2(dy, dx)
                    beam['timer'] = 0
                    beam['state'] = 'telegraph'
                boss_info['beam_shared_state'] = 'telegraph'
                boss_info['beam_shared_timer'] = 0
            elif shared == 'telegraph':
                # telegraph 長は left_beam の telegraph 値使用（同じ設定）
                if boss_info['left_beam']['timer'] >= boss_info['left_beam']['telegraph']:
                    for side in ('left','right'):
                        b = boss_info[f'{side}_beam']
                        b['state'] = 'firing'
                        b['timer'] = 0
                    boss_info['beam_shared_state'] = 'firing'
            elif shared == 'firing':
                # ダメージ判定 & firing 終了
                for side, center in (('left', left_center), ('right', right_center)):
                    beam = boss_info[f'{side}_beam']
                    if beam.get('origin') and beam.get('target') and not player_invincible:
                        px, py = player.centerx, player.centery
                        ox, oy = beam['origin']
                        tx, ty = beam['target']
                        vx, vy = tx-ox, ty-oy
                        if vx*vx + vy*vy > 0:
                            t = max(0, min(1, ((px-ox)*vx + (py-oy)*vy)/(vx*vx+vy*vy)))
                            cx = ox + vx*t
                            cy = oy + vy*t
                            if (px-cx)**2 + (py-cy)**2 < 14*14:
                                player_lives -= 1
                                player_invincible = True
                                player_invincible_timer = 0
                                explosion_timer = 0
                                explosion_pos = (player.centerx, player.centery)
                                player.x = WIDTH//2 - 15
                                player.y = HEIGHT - 40
                if boss_info['left_beam']['timer'] >= boss_info['left_beam']['firing']:
                    for side in ('left','right'):
                        b = boss_info[f'{side}_beam']
                        b['state'] = 'cooldown'
                        b['timer'] = 0
                    boss_info['beam_shared_state'] = 'cooldown'
                    boss_info['beam_shared_timer'] = 0
            elif shared == 'cooldown':
                if boss_info['beam_shared_timer'] >= boss_info['left_beam']['cooldown']:
                    boss_info['beam_shared_state'] = 'idle'
                    boss_info['beam_shared_timer'] = 0
            # 個別タイマー加算 & origin 更新
            for side, center in (('left', left_center), ('right', right_center)):
                beam = boss_info[f'{side}_beam']
                beam['timer'] += 1
                ang = boss_info['left_angle' if side=='left' else 'right_angle']
                tip_x = center[0] + (small_w//2) * math.cos(ang)
                tip_y = center[1] + (small_w//2) * math.sin(ang)
                if beam['state'] in ('telegraph','firing'):
                    beam['origin'] = (tip_x, tip_y)

            # --- コア開閉＆拡散弾 ---
            # ステートが無い場合安全初期化
            if 'core_state' not in boss_info:
                boss_info['core_state'] = 'closed'
                boss_info['core_timer'] = 0
                boss_info['core_gap'] = 0
                boss_info['core_gap_target'] = 40
                boss_info['core_cycle_interval'] = 240
                boss_info['core_firing_duration'] = 60
                boss_info['core_open_hold'] = 50
            cs = boss_info['core_state']
            boss_info['core_timer'] += 1
            gap = boss_info.get('core_gap',0)
            # 状態遷移
            if cs == 'closed':
                if boss_info['core_timer'] >= boss_info['core_cycle_interval']:
                    boss_info['core_state'] = 'opening'
                    boss_info['core_timer'] = 0
            elif cs == 'opening':
                gap += 4
                if gap >= boss_info['core_gap_target']:
                    gap = boss_info['core_gap_target']
                    boss_info['core_state'] = 'firing'
                    boss_info['core_timer'] = 0
                boss_info['core_gap'] = gap
            elif cs == 'firing':
                # 一定間隔で拡散弾リング
                if boss_info['core_timer'] % 12 == 1:
                    core_cx, core_cy = boss_x, boss_y
                    RING_NUM = 10
                    speed = 4
                    for i in range(RING_NUM):
                        ang = 2*math.pi*i/RING_NUM + (boss_info['core_timer']//12)*0.3
                        vx = int(speed * math.cos(ang))
                        vy = int(speed * math.sin(ang))
                        bullets.append({
                            'rect': pygame.Rect(core_cx-4, core_cy-4, 8, 8),
                            'type': 'enemy',
                            'power': 1.0,
                            'vx': vx,
                            'vy': vy
                        })
                if boss_info['core_timer'] >= boss_info['core_firing_duration']:
                    boss_info['core_state'] = 'open_hold'
                    boss_info['core_timer'] = 0
            elif cs == 'open_hold':
                if boss_info['core_timer'] >= boss_info['core_open_hold']:
                    boss_info['core_state'] = 'closing'
                    boss_info['core_timer'] = 0
            elif cs == 'closing':
                gap -= 4
                if gap <= 0:
                    gap = 0
                    boss_info['core_state'] = 'closed'
                    boss_info['core_timer'] = 0
                boss_info['core_gap'] = gap
            # gap を保持
            boss_info['core_gap'] = gap

            # （オリジンへの補正戻しなし＝回転しつつ周期的に狙う）

    # プレイヤーとボスの当たり判定
    if boss_alive and not player_invincible:
        # 跳ね返り弾のみプレイヤー判定
        for bullet in bullets:
            if bullet.get("reflect", False) or bullet.get("type") == "enemy":
                if player.colliderect(bullet["rect"]):
                    player_lives -= 1
                    player_invincible = True
                    player_invincible_timer = 0
                    explosion_timer = 0
                    explosion_pos = (player.centerx, player.centery)
                    # プレイヤーを初期位置に戻す
                    player.x = WIDTH//2 - 15
                    player.y = HEIGHT - 40
                    bullets.remove(bullet)
                    break
        # 通常のボス接触判定
        dx = player.centerx - boss_x
        dy = player.centery - boss_y
        if dx*dx + dy*dy < (boss_radius + max(player.width, player.height)//2)**2:
            player_lives -= 1
            player_invincible = True
            player_invincible_timer = 0
            explosion_timer = 0
            explosion_pos = (player.centerx, player.centery)
            # プレイヤーを初期位置に戻す
            player.x = WIDTH//2 - 15
            player.y = HEIGHT - 40

    # 無敵時間管理
    if player_invincible:
        player_invincible_timer += 1
        if player_invincible_timer >= PLAYER_INVINCIBLE_DURATION:
            player_invincible = False

    # 爆発表示管理
    if explosion_timer < EXPLOSION_DURATION and explosion_pos:
        explosion_timer += 1

    # ゲームオーバー・クリア判定
    if player_lives <= 0 or (not boss_alive and boss_explosion_timer >= BOSS_EXPLOSION_DURATION):
        result = "win" if not boss_alive else "lose"
        reward_text = None
        # 報酬文
        if result == "win" and boss_info and not level_cleared[selected_level]:
            if boss_info["name"] == "Boss A":
                reward_text = "ホーミング弾解放! V切替 威力0.5/追尾"
            elif boss_info["name"] == "蛇":
                reward_text = "リーフシールド獲得! 自機周囲で敵/弾を防ぐ"
        # 星マーク
        if result == "win":
            level_cleared[selected_level] = True
        # 爆発表示（最後の爆発）
        for i in range(EXPLOSION_DURATION):
            screen.fill(BLACK)
            if explosion_pos:
                pygame.draw.circle(screen, RED, explosion_pos, 30)
            if result == "win":
                font = jp_font(50)
                text = font.render("GAME CLEAR!", True, (0,255,0))
                text_rect = text.get_rect(center=(WIDTH//2, HEIGHT//2-80))
                screen.blit(text, text_rect)
            else:
                font = jp_font(50)
                text = font.render("GAME OVER", True, RED)
                text_rect = text.get_rect(center=(WIDTH//2, HEIGHT//2-60))
                screen.blit(text, text_rect)
            if reward_text:
                font_reward = jp_font(26)
                def split_reward(text):
                    parts = text.split(' ')
                    lines = []
                    cur = ''
                    for p in parts:
                        test = (cur + ' ' + p).strip()
                        w, _ = font_reward.size(test)
                        if w > WIDTH - 40 and cur:
                            lines.append(cur)
                            cur = p
                        else:
                            cur = test
                    if cur:
                        lines.append(cur)
                    return lines
                lines = split_reward(reward_text)
                line_h = font_reward.get_linesize()
                total_h = line_h * len(lines)
                # 爆発演出中も同様に下へずらす
                start_y = (HEIGHT // 2 - 10) - total_h // 2 + line_h // 2
                for li, line in enumerate(lines):
                    surf = font_reward.render(line, True, (0,255,0))
                    rect = surf.get_rect(center=(WIDTH//2, start_y + li*line_h))
                    screen.blit(surf, rect)
            pygame.display.flip()
            pygame.time.wait(20)
        pygame.time.wait(1000)
        # 選択メニュー
        while True:
            draw_end_menu(result, reward_text)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        menu_mode = True
                        break
                    if event.key == pygame.K_2:
                        retry = True
                        break
                    if event.key == pygame.K_3:
                        pygame.quit()
                        sys.exit()
            if menu_mode or retry:
                break
        continue

    # 描画
    screen.fill(BLACK)
    # 爆発表示
    if explosion_timer < EXPLOSION_DURATION and explosion_pos:
        pygame.draw.circle(screen, RED, explosion_pos, 30)
    # プレイヤー（無敵時は半透明）
    if not player_invincible or (player_invincible_timer//10)%2 == 0:
        pygame.draw.rect(screen, WHITE, player)
        # リーフシールド描画
        if has_leaf_shield:
            # 回転をさらに遅くして存在感を抑える
            leaf_angle += 0.015
            leaf_hit_boxes = []
            for i in range(2):
                angle = leaf_angle + math.pi * i
                leaf_radius = 40
                leaf_x = player.centerx + leaf_radius * math.cos(angle)
                leaf_y = player.centery + leaf_radius * math.sin(angle)
                r = pygame.Rect(leaf_x-14, leaf_y-10, 28, 20)
                leaf_hit_boxes.append(r)
                pygame.draw.ellipse(screen, (0,200,0), r)
            # シールドで敵弾/反射弾を弾く（削除）
            filtered = []
            for b in bullets:
                if (b.get("reflect") or b.get("type") == "enemy") and any(r.colliderect(b["rect"]) for r in leaf_hit_boxes):
                    # 葉に当たった弾は消す
                    continue
                filtered.append(b)
            bullets = filtered
    for bullet in bullets:
        if bullet["type"] == "boss_beam":
            continue
        btype = bullet.get("type")
        if bullet.get("reflect"):
            color = BULLET_COLOR_REFLECT
        elif btype == "normal":
            color = BULLET_COLOR_NORMAL
        elif btype == "homing":
            color = BULLET_COLOR_HOMING
        elif btype == "enemy":
            color = BULLET_COLOR_ENEMY
        else:
            color = WHITE
        pygame.draw.rect(screen, color, bullet["rect"])

    # 楕円ボス 新ビーム描画
    if boss_alive and boss_info and boss_info["name"] == "楕円ボス":
        for side in ('left','right'):
            beam = boss_info.get(f'{side}_beam')
            if not beam: continue
            if not beam.get('origin') or not beam.get('target'): continue
            ox, oy = beam['origin']
            tx, ty = beam['target']
            if beam['state'] == 'telegraph':
                # 点滅赤予告（フレームごとに表示/非表示）
                if (beam['timer'] // 5) % 2 == 0:
                    pygame.draw.line(screen, (255,60,60), (ox, oy), (tx, ty), 4)
            elif beam['state'] == 'firing':
                pygame.draw.line(screen, (0,255,255), (ox, oy), (tx, ty), 14)
        # コア開閉描画（gap に応じて半楕円が左右へ割れる）
        gap = boss_info.get('core_gap', 0)
        # 新ヘルパーで半楕円分割を実現（gap=0 でもそのまま一体表示）
        draw_split_ellipse(screen, boss_x, boss_y, boss_radius, gap, boss_color)
        # 開いている間コア表示
        if boss_info.get('core_state') in ('opening','firing','open_hold'):
            pygame.draw.circle(screen, (255,80,80), (boss_x, boss_y), OVAL_CORE_RADIUS)
    # ボスキャラ
    if boss_alive:
        # Boss A: 台形
        if boss_info and boss_info["name"] == "Boss A":
            top_width = boss_radius
            bottom_width = boss_radius * 2
            height = boss_radius * 1.5
            points = [
                (boss_x - top_width//2, boss_y - int(height//2)),
                (boss_x + top_width//2, boss_y - int(height//2)),
                (boss_x + bottom_width//2, boss_y + int(height//2)),
                (boss_x - bottom_width//2, boss_y + int(height//2)),
            ]
            pygame.draw.polygon(screen, boss_color, points)
        elif boss_info and boss_info["name"] == "蛇":
            # 衝突判定は既にロジック上部で処理済みなのでここでは描画のみ
            main_size = int(boss_radius * 1.2)
            main_rect = pygame.Rect(boss_x - main_size//2, boss_y - main_size//2, main_size, main_size)
            pygame.draw.rect(screen, (128, 0, 128), main_rect)
            rotate_angle_local = globals().get("rotate_angle", 0.0)
            for i in range(ROTATE_SEGMENTS_NUM):
                angle = rotate_angle_local + (2 * math.pi * i / ROTATE_SEGMENTS_NUM)
                seg_x = boss_x + ROTATE_RADIUS * math.cos(angle)
                seg_y = boss_y + ROTATE_RADIUS * math.sin(angle)
                seg_rect = pygame.Rect(int(seg_x-20), int(seg_y-20), 40, 40)
                pygame.draw.rect(screen, (180, 0, 180), seg_rect)
        elif boss_info and boss_info["name"] == "楕円ボス":
            # 旧本体描画は分割描画セクションで済んでいるためここでは小楕円のみ可動表示（緑）
            small_w, small_h = boss_radius//2, boss_radius*2//3
            left_rect = pygame.Rect(boss_x - boss_radius - small_w//2, boss_y - small_h//2, small_w, small_h)
            right_rect = pygame.Rect(boss_x + boss_radius - small_w//2, boss_y - small_h//2, small_w, small_h)
            pygame.draw.ellipse(screen, (0,200,0), left_rect)
            pygame.draw.ellipse(screen, (0,200,0), right_rect)
        # ボスへの小爆発
        for pos in boss_explosion_pos:
            pygame.draw.circle(screen, (255,255,0), pos, 15)
        # 小爆発は一瞬だけ表示
        if boss_explosion_pos:
            boss_explosion_pos = []
    # デバッグヒント表示
    dbg_font = pygame.font.SysFont(None, 18)
    hint = dbg_font.render("T: ボス即撃破(テスト)", True, (100,180,255))
    screen.blit(hint, (10, HEIGHT-22))
    # ボス撃破後の派手な爆発
    if not boss_alive and boss_explosion_timer < BOSS_EXPLOSION_DURATION:
        for i in range(12):
            angle = i * 30
            x = int(boss_x + boss_radius * 1.5 * math.cos(math.radians(angle)))
            y = int(boss_y + boss_radius * 1.5 * math.sin(math.radians(angle)))
            pygame.draw.circle(screen, (255, 100, 0), (x, y), 40)
        pygame.draw.circle(screen, (255,255,0), (boss_x, boss_y), 60)
    # ゲームクリア表示
    if not boss_alive and boss_explosion_timer >= BOSS_EXPLOSION_DURATION:
        font = pygame.font.SysFont(None, 50)
        text = font.render("GAME CLEAR!", True, (0,255,0))
        text_rect = text.get_rect(center=(WIDTH//2, HEIGHT//2))
        screen.blit(text, text_rect)
        pygame.display.flip()
        pygame.time.wait(2000)
        # リトライ待ち
        font = pygame.font.SysFont(None, 32)
        text = font.render("Press Enter to Retry", True, WHITE)
        text_rect = text.get_rect(center=(WIDTH//2, HEIGHT//2+60))
        screen.blit(text, text_rect)
        pygame.display.flip()
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        retry = True
                        waiting = False
            pygame.time.wait(50)
        continue

    # 残機表示（画面右下）
    font = pygame.font.SysFont(None, 26)
    lives_text = f"Lives: {player_lives}"
    text_surf = font.render(lives_text, True, WHITE)
    text_rect = text_surf.get_rect(bottomright=(WIDTH-10, HEIGHT-10))
    screen.blit(text_surf, text_rect)
    # 弾種表示
    font = pygame.font.SysFont(None, 20)
    if has_homing:
        bullet_text = f"Bullet: {'Homing' if bullet_type == 'homing' else 'Normal'} (V to switch)"
        text_surf = font.render(bullet_text, True, (0,255,0) if bullet_type == "homing" else WHITE)
        screen.blit(text_surf, (20, HEIGHT-40))

    pygame.display.flip()
    clock.tick(60)


