import sys, random, math, subprocess

# --- Auto-install required packages (pygame) at startup ---
def _ensure_pygame(min_ver=(2, 5, 0)):
    try:
        import pygame as _pg
        ver = getattr(getattr(_pg, 'version', None), 'vernum', None)
        if not isinstance(ver, tuple):
            ver = (0, 0, 0)
        if ver < min_ver:
            raise ImportError(f"pygame too old: {ver} < {min_ver}")
        return
    except Exception:
        print("[setup] pygame が見つからないか古いので、インストール/更新します (pygame>=%d.%d.%d)..." % min_ver)
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", f"pygame>={min_ver[0]}.{min_ver[1]}.{min_ver[2]}"])
        except Exception as e:
            print("[setup] 自動インストールに失敗しました。インターネット接続や権限を確認し、以下を実行してください:\n  python3 -m pip install 'pygame>=%d.%d.%d'" % min_ver)
            raise
_ensure_pygame()
import pygame
from constants import (
    WIDTH, HEIGHT,
    EXPLOSION_DURATION, BOSS_EXPLOSION_DURATION, PLAYER_INVINCIBLE_DURATION,
    OVAL_CORE_RADIUS, OVAL_CORE_GAP_HIT_THRESHOLD, OVAL_CORE_NO_REFLECT_WHEN_OPEN,
    OVAL_CORE_GAP_TARGET, OVAL_CORE_CYCLE_INTERVAL, OVAL_CORE_FIRING_DURATION,
    OVAL_CORE_OPEN_HOLD, OVAL_CORE_GAP_STEP,
    OVAL_BEAM_INTERVAL,
    WHITE, BLACK, GRAY, RED,
    BULLET_COLOR_NORMAL, BULLET_COLOR_HOMING, BULLET_COLOR_ENEMY, BULLET_COLOR_REFLECT,
    BULLET_COLOR_SPREAD,
    boss_list, level_list,
    BOUNCE_BOSS_SPEED, BOUNCE_BOSS_RING_COUNT, BOUNCE_BOSS_NO_PATTERN_BOTTOM_MARGIN,
    BOUNCE_BOSS_SQUISH_DURATION, BOUNCE_BOSS_ANGLE_JITTER_DEG,
    BOUNCE_BOSS_SHRINK_STEP, BOUNCE_BOSS_SPEED_STEP,
    WINDOW_SHAKE_DURATION, WINDOW_SHAKE_INTENSITY
)

# dash_state が存在しない環境でも NameError を避ける初期値
if 'dash_state' not in globals():
    dash_state = {'invincible_timer': 0, 'active': False}
from constants import (
    DASH_COOLDOWN_FRAMES, DASH_INVINCIBLE_FRAMES, DASH_DISTANCE,
    DASH_DOUBLE_TAP_WINDOW, DASH_ICON_SEGMENTS
)
from fonts import jp_font, text_surface
from gameplay import spawn_player_bullets, move_player_bullets, update_dash_timers, attempt_dash

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("シューティングゲーム")
try:
    from pygame._sdl2 import Window
    _game_window = Window.from_display_module()
    _window_shake_timer = 0
    _window_shake_intensity = 0
    _window_base_pos = _game_window.position
    # Crescent boss low-HP window warp state
    _window_warp_active = False
    _window_warp_timer = 0
    _window_warp_index = 0
    _window_warp_interval = 180  # about 3 seconds at 60fps
    _window_warp_vertices = []   # relative offsets from base position
except Exception:
    _game_window = None
    _window_shake_timer = 0
    _window_shake_intensity = 0
    _window_base_pos = (0, 0)
    _window_warp_active = False
    _window_warp_timer = 0
    _window_warp_index = 0
    _window_warp_interval = 180
    _window_warp_vertices = []
selected_level = 1  # 1..MAX_LEVEL を使用
menu_mode = True
level_cleared = [False]*7  # 0..6

from ui import draw_menu, draw_end_menu

# （この下にゲームループ）

# --------- Utility: split ellipse drawing (for oval boss core opening) ---------
def draw_split_ellipse(surface, center_x, center_y, radius, gap, color):
    """Draw a vertical ellipse split into two half-ellipses separated by gap.
    radius: width of original ellipse; height is radius*2 (existing design)."""
    width = radius
    height = radius * 2
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, color, (0, 0, width, height))
    half_w = width // 2
    left_half = surf.subsurface((0, 0, half_w, height))
    right_half = surf.subsurface((half_w, 0, width - half_w, height))
    top = center_y - height // 2
    left_x = center_x - width // 2 - gap // 2
    right_x = center_x - width // 2 + half_w + gap // 2
    surface.blit(left_half, (left_x, top))
    surface.blit(right_half, (right_x, top))

# --------- Utility: draw 5-pointed star ---------
def draw_star(surface, center, outer_radius, color, inner_radius=None, rotation_deg=-90):
    """Draw a filled 5-pointed star.
    center: (x,y), outer_radius: outer radius in px, inner_radius: optional (default=outer*0.5)
    rotation_deg: rotation in degrees (default -90 so that a tip faces up).
    """
    cx, cy = center
    if inner_radius is None:
        inner_radius = outer_radius * 0.5
    pts = []
    rot = math.radians(rotation_deg)
    for i in range(10):
        ang = rot + (math.pi/5) * i  # 36° step
        r = outer_radius if (i % 2 == 0) else inner_radius
        x = cx + r * math.cos(ang)
        y = cy + r * math.sin(ang)
        pts.append((x, y))
    pygame.draw.polygon(surface, color, pts)

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
CONTROLS_HINT_FRAMES = 120  # 自機の矢印ヒント表示フレーム数（約2秒）
controls_hint_timer = 0
controls_hint_mode = 'normal'  # 'normal' | 'invert'
controls_inverted = False      # 第二形態で操作反転
wasd_hint_timer = 0            # 第三形態のWASD用ヒント表示タイマー
player2 = None                 # 第三形態で追加される2P（WASD操作）

# 交互操作反転用（形態変化は廃止）
INVERT_TOGGLE_PERIOD_FRAMES = 300  # 約5秒ごとに切替（60fps想定）
invert_cycle_timer = 0

# 蛇ボス用変数（未使用セクション保持）
snake_segments = []
snake_tail_fixed = False
snake_state = "normal"
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
bullet_type = "normal"
has_leaf_shield = False
leaf_angle = 0.0
has_spread = False
boss_attack_timer = 0
unlocked_homing = False
unlocked_leaf_shield = False
unlocked_spread = False
unlocked_dash = False
reward_granted = False
frame_count = 0  # フレームカウンタ（ダッシュ二度押し判定などに使用）
fire_cooldown = 0  # 連射クールダウン（フレーム）
while True:
    events = pygame.event.get()
    if menu_mode:
        draw_menu(screen, selected_level, level_cleared)
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected_level += 1
                    if selected_level > 6:
                        selected_level = 1
                if event.key == pygame.K_DOWN:
                    selected_level -= 1
                    if selected_level < 1:
                        selected_level = 6
                if event.key == pygame.K_RETURN:
                    boss_info = level_list[selected_level]["boss"]
                    if boss_info:
                        # ヒントタイマー初期化（持ち越し防止）
                        controls_hint_timer = 0
                        controls_hint_mode = 'normal'
                        controls_inverted = False
                        invert_cycle_timer = 0  # 反転周期タイマーをリセット
                        boss_radius = boss_info["radius"]
                        boss_hp = boss_info["hp"]
                        boss_color = boss_info["color"]
                        # 三日月の第一形態カラーを保持
                        if boss_info and boss_info.get("name") == "三日月形ボス":
                            boss_info['color_phase1'] = boss_color
                            boss_info['const_segments'] = []  # 星座線分（TTLつき）
                        retry = False
                        waiting_for_space = False
                        has_homing = unlocked_homing
                        has_leaf_shield = unlocked_leaf_shield
                        has_spread = unlocked_spread
                        has_dash = unlocked_dash
                        bullet_type = "normal"
                        reward_granted = False
                        leaf_angle = 0.0
                        boss_x = WIDTH // 2
                        boss_y = 60
                        boss_alive = True
                        boss_speed = 4
                        boss_dir = 1
                        boss_state = "track"
                        # ダッシュ状態初期化（統一）
                        dash_state = {
                            'cooldown': 0,
                            'invincible_timer': 0,
                            'active': False,
                            'last_tap': {'left': -9999, 'right': -9999},
                        }
                        if boss_info and boss_info["name"] == "バウンドボス":
                            boss_info['bounce_vx'] = 0
                            boss_info['bounce_vy'] = 0
                            boss_info['bounce_started'] = False
                            boss_info['bounce_last_side'] = None
                            # 楕円の向き: ビーム中以外はプレイヤー方向に向ける（下先端が追尾）
                            for side in ('left','right'):
                                key = f'{side}_angle'
                                if key not in boss_info:
                                    boss_info[key] = math.pi/2  # 下向き初期（下=+Y）
                                # firing 状態中は角度固定（予告/発射の向き維持）
                                beam = boss_info.get(f'{side}_beam')
                                if not (boss_info.get('core_state') == 'firing' and beam and beam.get('state') in ('telegraph','firing')):
                                    cx, cy = ((boss_x - boss_radius), boss_y) if side=='left' else ((boss_x + boss_radius), boss_y)
                                    theta = math.atan2(player.centery - cy, player.centerx - cx)
                                    boss_info[key] = theta
                            boss_info['bounce_cool'] = 0
                            boss_info['squish_timer'] = 0
                            boss_info['squish_state'] = 'normal'
                            boss_info['base_radius'] = boss_radius
                            boss_info['base_speed'] = BOUNCE_BOSS_SPEED
                            boss_info['hp_last_segment'] = boss_hp
                            boss_info['initial_hp'] = boss_hp
                            boss_info['first_drop'] = True
                        # 旧ダッシュUI用変数は毎フレーム dash_state から同期する
                        dash_cooldown = 0
                        dash_invincible_timer = 0
                        dash_last_tap = dash_state['last_tap']
                        dash_active = False
                        if boss_info["name"] == "Boss A":
                            boss_info['stomp_state'] = 'idle'
                            boss_info['stomp_timer'] = 0
                            boss_info['stomp_target_y'] = None
                            boss_info['home_y'] = boss_y
                            boss_info['stomp_interval'] = 120
                            boss_info['last_stomp_frame'] = 0
                            boss_info['stomp_grace'] = 180
                        if boss_info["name"] == "蛇":
                            boss_info['snake_stomp_state'] = 'idle'
                            boss_info['snake_stomp_timer'] = 0
                            boss_info['snake_stomp_target_y'] = None
                            boss_info['snake_home_y'] = boss_y
                            boss_info['snake_stomp_interval'] = 150
                            boss_info['snake_last_stomp_frame'] = 0
                            boss_info['snake_stomp_grace'] = 210
                        if boss_info and boss_info["name"] == "楕円ボス":
                            boss_origin_x = boss_x
                            if 'core_state' not in boss_info:
                                boss_info['core_state'] = 'closed'
                                boss_info['core_timer'] = 0
                                boss_info['core_cycle_interval'] = OVAL_CORE_CYCLE_INTERVAL
                                boss_info['core_firing_duration'] = OVAL_CORE_FIRING_DURATION
                                boss_info['core_open_hold'] = OVAL_CORE_OPEN_HOLD
                                boss_info['core_gap'] = 0
                                boss_info['core_gap_target'] = OVAL_CORE_GAP_TARGET
                        if boss_info and boss_info["name"] == "三日月形ボス":
                            # 三日月形ボスは第1形態で開始。第二形態関連を完全初期化
                            boss_info['new_attack_enabled'] = False
                            boss_info['dodge_ai'] = False
                            boss_info['phase'] = 1
                            boss_info['phase_grace'] = 0
                            boss_info['phase2_hp'] = max(25, int(boss_hp * 0.7))
                            boss_info['phase3_hp'] = max(12, int(boss_hp * 0.35))
                            boss_info['initial_hp'] = boss_hp
                            # パターン管理の初期化
                            boss_info['patt_state'] = 'idle'
                            boss_info['patt_timer'] = 0
                            boss_info['patt_cd'] = 0
                            boss_info['last_patt'] = None
                            # 第二形態 横レーザーの初期化
                            boss_info['hline_state'] = 'idle'
                            boss_info['hline_timer'] = 0
                            boss_info['hline_cd'] = 0
                            boss_info['hline_y'] = HEIGHT//2
                            boss_info['hline_thick'] = 36
                            boss_info['hline_pending_y'] = None
                            # 第三形態 分裂ボスの初期化（未分裂状態）
                            boss_info['phase3_split'] = False
                            boss_info['parts'] = []
                        player_lives = 3
                        player_invincible = False
                        player_invincible_timer = 0
                        explosion_timer = 0
                        explosion_pos = None
                        bullets = []
                        boss_explosion_timer = 0
                        boss_explosion_pos = []
                        boss_attack_timer = 0
                        player = pygame.Rect(WIDTH // 2 - 15, HEIGHT - 40, 30, 15)
                        player_speed = 5
                        bullet_speed = 7
                        fire_cooldown = 0
                        waiting_for_space = True
                        menu_mode = False
                        # ウィンドウワープ初期化
                        _window_warp_active = False
                        _window_warp_timer = 0
                        _window_warp_index = 0
                        _window_warp_vertices = []
                        # 第三形態用の2P関連を初期化
                        player2 = None
                        wasd_hint_timer = 0
        continue
    # 早期リトライ処理（勝敗判定より先に完全初期化）
    if retry:
        # プレイヤー/一般状態
        player_lives = 3
        player_invincible = False
        player_invincible_timer = 0
        explosion_timer = 0
        explosion_pos = None
        bullets = []
        fire_cooldown = 0
        frame_count = 0
        leaf_angle = 0.0
        bullet_type = "normal"
        # 画面状態
        waiting_for_space = False
        menu_mode = False
        # 第三形態用の2P関連を初期化
        player2 = None
        wasd_hint_timer = 0
        # ボス状態
        boss_info = level_list[selected_level]["boss"] if 'level_list' in globals() else boss_info
        boss_radius = boss_info["radius"] if boss_info else boss_radius
        boss_color = boss_info["color"] if boss_info else boss_color
        boss_alive = True
        boss_x = WIDTH // 2
        boss_y = 60
        boss_state = "track"
        boss_speed = 4
        boss_dir = 1
        boss_attack_timer = 0
        boss_explosion_timer = 0
        boss_explosion_pos = []
        boss_origin_x = boss_x
        boss_origin_y = boss_y
        boss_hp = boss_info["hp"] if boss_info else 35
        # プレイヤー座標リセット
        player = pygame.Rect(WIDTH // 2 - 15, HEIGHT - 40, 30, 15)
        player_speed = 5
        bullet_speed = 7
        controls_inverted = False
        invert_cycle_timer = 0
        controls_hint_mode = 'normal'
        # 三日月形ボスの形態/第二形態用ステートを初期化（持ち越し防止）
        if boss_info and boss_info.get("name") == "三日月形ボス":
            boss_info['phase'] = 1
            boss_info['phase_grace'] = 0
            boss_info['phase2_hp'] = max(25, int(boss_hp * 0.7))
            boss_info['new_attack_enabled'] = False
            boss_info['dodge_ai'] = False
            boss_info['patt_state'] = 'idle'
            boss_info['patt_timer'] = 0
            boss_info['patt_cd'] = 0
            boss_info['last_patt'] = None
            boss_info['hline_state'] = 'idle'
            boss_info['hline_timer'] = 0
            boss_info['hline_cd'] = 0
            boss_info['hline_y'] = HEIGHT//2
            boss_info['hline_thick'] = 36
            boss_info['hline_pending_y'] = None
            boss_info['phase3_split'] = False
            boss_info['parts'] = []
            boss_info['const_segments'] = []
        # ダッシュ状態を再初期化
        dash_state = {
            'cooldown': 0,
            'invincible_timer': 0,
            'active': False,
            'last_tap': {'left': -9999, 'right': -9999},
        }
        dash_cooldown = 0
        dash_invincible_timer = 0
        dash_last_tap = dash_state['last_tap']
        dash_active = False
        # ウィンドウワープ初期化（リトライ時）
        _window_warp_active = False
        _window_warp_timer = 0
        _window_warp_index = 0
        _window_warp_vertices = []
        # ボス個別初期化
        if boss_info and boss_info["name"] == "Boss A":
            boss_info['stomp_state'] = 'idle'
            boss_info['stomp_timer'] = 0
            boss_info['stomp_target_y'] = None
            boss_info['home_y'] = boss_y
            boss_info['stomp_interval'] = 120
            boss_info['last_stomp_frame'] = 0
            boss_info['stomp_grace'] = 180
        # 完了
        retry = False
        # リトライ開始直後の矢印ヒント表示（L5ボス限定）
        controls_hint_timer = CONTROLS_HINT_FRAMES if (boss_info and boss_info.get("name") == "三日月形ボス") else 0
        # このフレームはスキップして次フレームから通常進行
        continue
    if waiting_for_space:
        screen.fill(BLACK)
        font = jp_font(42)
        text = font.render("Press SPACE to start!", True, WHITE)
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(text, text_rect)
        pygame.display.flip()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                bullets.append({
                    "rect": pygame.Rect(player.centerx - 3, player.top - 6, 6, 12),
                    "type": bullet_type,
                    "power": 1.0 if bullet_type == "normal" else 0.5,
                    "vx": 0,
                    "vy": -bullet_speed
                })
                waiting_for_space = False
                controls_hint_timer = CONTROLS_HINT_FRAMES if (boss_info and boss_info.get("name") == "三日月形ボス") else 0
                if controls_hint_timer > 0:
                    controls_hint_mode = 'normal'
                # 第三形態では2Pのヒントも開始
                if boss_info and boss_info.get('name') == '三日月形ボス' and boss_info.get('phase',1) == 3:
                    wasd_hint_timer = CONTROLS_HINT_FRAMES
        continue
    if waiting_for_space:
        screen.fill(BLACK)
        font = jp_font(42)
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
                    controls_hint_timer = CONTROLS_HINT_FRAMES if (boss_info and boss_info.get("name") == "三日月形ボス") else 0
                    if controls_hint_timer > 0:
                        controls_hint_mode = 'normal'
                    controls_hint_timer = CONTROLS_HINT_FRAMES
        # 重複ブロック削除跡（不要なインデント混入を除去）

    # --- 通常プレイ時の入力処理／移動／射撃／ダッシュ ---
    frame_count += 1
    # 形態変化を廃止: 操作反転は「三日月形ボス戦」限定で一定周期トグル
    if boss_info and boss_info.get('name') == '三日月形ボス':
        invert_cycle_timer = (invert_cycle_timer + 1) % INVERT_TOGGLE_PERIOD_FRAMES
        if invert_cycle_timer == 0:
            controls_inverted = not controls_inverted
            controls_hint_mode = 'invert' if controls_inverted else 'normal'
            # 反転中はボス色を紫、通常は第1形態色（またはデフォルト）
            if controls_inverted:
                boss_color = (180, 80, 255)
            else:
                boss_color = boss_info.get('color_phase1', boss_info.get('color', (255,220,0)))
    else:
        # 三日月形ボス以外では常に通常操作に戻す（持ち越し防止）
        if controls_inverted:
            controls_inverted = False
            controls_hint_mode = 'normal'
    # イベント処理（終了・武器切替・ダッシュ）
    for event in events:
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        if event.type == pygame.KEYDOWN:
            # ESC / Q で即終了
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                pygame.quit(); sys.exit()
            # 武器切替（V）
            if event.key == pygame.K_v:
                available = ["normal"]
                if has_homing:
                    available.append("homing")
                if has_spread:
                    available.append("spread")
                try:
                    i = available.index(bullet_type)
                    bullet_type = available[(i+1) % len(available)]
                except ValueError:
                    bullet_type = available[0]
            # ダッシュ（左右キーの二度押し）: 反転中は左右を入れ替える
            if event.key == pygame.K_LEFT:
                dir_key = 'right' if controls_inverted else 'left'
                if attempt_dash(dash_state, dir_key, frame_count, player, has_dash, WIDTH):
                    player_invincible = True  # ダッシュ発動時は無敵付与
            if event.key == pygame.K_RIGHT:
                dir_key = 'left' if controls_inverted else 'right'
                if attempt_dash(dash_state, dir_key, frame_count, player, has_dash, WIDTH):
                    player_invincible = True

    # 押下状態取得（移動・連射）
    keys = pygame.key.get_pressed()
    dx = (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * player_speed
    dy = (keys[pygame.K_DOWN] - keys[pygame.K_UP]) * player_speed
    if controls_inverted:
        dx, dy = -dx, -dy
    # 分割なし: 画面全域で移動
    player.x = max(0, min(WIDTH - player.width, player.x + dx))
    player.y = max(0, min(HEIGHT - player.height, player.y + dy))

    # 2P移動なし（単体モード）

    # 連射（Z or SPACE）
    if fire_cooldown > 0:
        fire_cooldown -= 1
    if keys[pygame.K_z] or keys[pygame.K_SPACE]:
        if fire_cooldown <= 0:
            # P1発射
            spawn_player_bullets(bullets, player, bullet_type, bullet_speed)
            # 2P同時発射は無効（単体モード）
            fire_cooldown = 8

    # ダッシュタイマー更新（UI同期）
    if 'dash_state' in globals():
        update_dash_timers(dash_state)
        dash_cooldown = dash_state.get('cooldown', 0)
        dash_active = dash_state.get('active', False)

    # プレイヤーとボスの当たり判定
    if boss_alive and not player_invincible:
        # 三日月形ボス 第二形態 横レーザーの当たり判定（発射中のみ）
        if boss_info and boss_info.get('name') == '三日月形ボス' and boss_info.get('phase',1) == 2:
            if boss_info.get('hline_state') == 'firing':
                y = boss_info.get('hline_y', HEIGHT//2)
                half = max(1, boss_info.get('hline_thick', 26)//2)
                # プレイヤー矩形と横帯の交差判定
                if (y - half) <= player.bottom and (y + half) >= player.top:
                    player_lives -= 1
                    player_invincible = True
                    player_invincible_timer = 0
                    explosion_timer = 0
                    explosion_pos = (player.centerx, player.centery)
                    # プレイヤーを初期位置に戻す
                    player.x = WIDTH//2 - 15
                    player.y = HEIGHT - 40
        # 楕円ボス ビームの当たり判定（発射中のみ）
        if boss_info and boss_info.get('name') == '楕円ボス':
            for side in ('left','right'):
                beam = boss_info.get(f'{side}_beam')
                if not beam: continue
                if beam.get('state') != 'firing':
                    continue
                # 太さ14のビーム線分と矩形の交差（近傍距離）
                (ox, oy) = beam.get('origin', (boss_x, boss_y))
                (tx, ty) = beam.get('target', (boss_x, boss_y))
                # 端点からプレイヤー矩形中心への線分距離で近似
                px, py = player.centerx, player.centery
                vx, vy = tx-ox, ty-oy
                if vx*vx + vy*vy == 0:
                    continue
                t = max(0, min(1, ((px-ox)*vx + (py-oy)*vy)/(vx*vx + vy*vy)))
                cx = ox + vx*t; cy = oy + vy*t
                dist2 = (px-cx)**2 + (py-cy)**2
                thick = 14
                if dist2 <= (thick//2 + max(player.width, player.height)//2)**2:
                    player_lives -= 1
                    player_invincible = True
                    player_invincible_timer = 0
                    explosion_timer = 0
                    explosion_pos = (player.centerx, player.centery)
                    player.x = WIDTH//2 - 15
                    player.y = HEIGHT - 40
        # 跳ね返り弾のみプレイヤー判定
        for bullet in bullets:
            if (bullet.get("reflect", False) or bullet.get("type") == "enemy") and not bullet.get('harmless'):
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
        # 第三形態: 2P への敵弾/反射弾の当たり判定
        if boss_info and boss_info.get('name') == '三日月形ボス' and boss_info.get('phase',1) == 3 and player2:
            for bullet in bullets:
                if (bullet.get("reflect", False) or bullet.get("type") == "enemy") and not bullet.get('harmless'):
                    if player2.colliderect(bullet["rect"]):
                        player_lives -= 1
                        player_invincible = True
                        player_invincible_timer = 0
                        explosion_timer = 0
                        explosion_pos = (player2.centerx, player2.centery)
                        # 2Pも初期位置へ
                        player2.x = WIDTH//2 - 80
                        player2.y = HEIGHT - 40
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

        # 星座線分への接触（太線近傍）
        if boss_info and boss_info.get('name') == '三日月形ボス':
            segs = boss_info.get('const_segments', [])
            if segs:
                px, py = player.centerx, player.centery
                for s in segs:
                    if s.get('state') == 'tele':
                        continue
                    (ax, ay) = s['a']; (bx, by) = s['b']
                    vx, vy = bx-ax, by-ay
                    if vx*vx + vy*vy <= 0:
                        continue
                    t = max(0, min(1, ((px-ax)*vx + (py-ay)*vy)/(vx*vx + vy*vy)))
                    cx = ax + vx*t; cy = ay + vy*t
                    dist2 = (px-cx)**2 + (py-cy)**2
                    thick = max(3, s.get('thick', 6))
                    if dist2 <= (thick+6)**2:  # やや広めに
                        player_lives -= 1
                        player_invincible = True
                        player_invincible_timer = 0
                        explosion_timer = 0
                        explosion_pos = (player.centerx, player.centery)
                        player.x = WIDTH//2 - 15
                        player.y = HEIGHT - 40
                        break

    # 無敵時間管理
    if player_invincible:
        player_invincible_timer += 1
    if player_invincible_timer >= PLAYER_INVINCIBLE_DURATION and (globals().get('dash_state') or {'invincible_timer':0})['invincible_timer'] <= 0:
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
            elif boss_info["name"] == "楕円ボス":
                reward_text = "拡散弾(3WAY) 解放! Vで切替 威力0.5x3 敵弾相殺"
            elif boss_info["name"] == "バウンドボス":
                reward_text = "緊急回避(ダッシュ) 解放! ←← / →→ で瞬間移動&無敵"
        # 報酬アンロック（セッション内持続）
        if result == "win" and boss_info:
            if boss_info["name"] == "Boss A":
                unlocked_homing = True
            elif boss_info["name"] == "蛇":
                unlocked_leaf_shield = True
            elif boss_info["name"] == "楕円ボス":
                unlocked_spread = True
            elif boss_info["name"] == "バウンドボス":
                unlocked_dash = True
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
            draw_end_menu(screen, result, reward_text)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_t:
                        if boss_alive:
                            # 即時爆発デバッグ: HP を 0 にし爆発シーケンスへ
                            boss_hp = 0
                            boss_alive = False
                            boss_explosion_timer = 0
                            explosion_pos = (boss_x, boss_y)
                    # メニューへ戻る（1 / テンキー1）
                    if event.key in (pygame.K_1, pygame.K_KP_1):
                        menu_mode = True
                        break
                    # リトライ（2 / テンキー2 / Enter / R）
                    if event.key in (pygame.K_2, pygame.K_KP_2, pygame.K_RETURN, pygame.K_r):
                        retry = True
                        break
                    # 終了（3 / テンキー3 / ESC）
                    if event.key in (pygame.K_3, pygame.K_KP_3, pygame.K_ESCAPE):
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
    # 分割演出は廃止（形態なし）
    # プレイヤー（無敵時は半透明）
    if not player_invincible or (player_invincible_timer//10)%2 == 0:
        pygame.draw.rect(screen, WHITE, player)
    # 2P描画なし（単体モード）
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
        elif btype == "spread":
            color = BULLET_COLOR_SPREAD
        else:
            color = WHITE
        # 三日月形ボス専用: 星形弾描画
        if bullet.get('shape') == 'star':
            star_color = bullet.get('color', color)
            cx, cy = bullet["rect"].center
            radius = max(bullet["rect"].width, bullet["rect"].height) // 2
            draw_star(screen, (cx, cy), radius, star_color)
        else:
            pygame.draw.rect(screen, color, bullet["rect"])

    # ステージ開始直後だけ自機の周囲に矢印ヒントを表示（L5: 三日月形ボス限定）
    if (boss_alive and boss_info and boss_info.get("name") == "三日月形ボス") and controls_hint_timer > 0:
        controls_hint_timer -= 1
        # フェード用アルファ（イージングで少し滑らかに）
        t = controls_hint_timer / float(CONTROLS_HINT_FRAMES)
        alpha = max(0, min(220, int(220 * t)))
        # 自機中心基準の小さな矢印（上下左右）
        surf_w = player.width + 80
        surf_h = player.height + 80
        asurf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        cx, cy = surf_w // 2, surf_h // 2
        base_gap = max(player.width, player.height) // 2 + 22
        pulse = 3 * math.sin(pygame.time.get_ticks() * 0.02)
        gap = base_gap + pulse
        size = 10  # 三角矢印のサイズ
        col = (255, 255, 255, alpha)
        invert = (controls_hint_mode == 'invert')
        # 逆矢印: 向きを反転
        if not invert:
            up = [(cx, cy - gap - size), (cx - size, cy - gap + size), (cx + size, cy - gap + size)]
            dn = [(cx, cy + gap + size), (cx - size, cy + gap - size), (cx + size, cy + gap - size)]
            lf = [(cx - gap - size, cy), (cx - gap + size, cy - size), (cx - gap + size, cy + size)]
            rt = [(cx + gap + size, cy), (cx + gap - size, cy - size), (cx + gap - size, cy + size)]
        else:
            # 上下左右の向きを逆に
            up = [(cx, cy + gap + size), (cx - size, cy + gap - size), (cx + size, cy + gap - size)]
            dn = [(cx, cy - gap - size), (cx - size, cy - gap + size), (cx + size, cy - gap + size)]
            lf = [(cx + gap + size, cy), (cx + gap - size, cy - size), (cx + gap - size, cy + size)]
            rt = [(cx - gap - size, cy), (cx - gap + size, cy - size), (cx - gap + size, cy + size)]
        for tri in (up, dn, lf, rt):
            pygame.draw.polygon(asurf, col, tri)
        screen.blit(asurf, (player.centerx - cx, player.centery - cy))

    # 第三形態: WASD用ヒント（2Pの周囲にW/A/S/Dを対応方向に表示）
    if (boss_alive and boss_info and boss_info.get('name') == '三日月形ボス' and boss_info.get('phase',1) == 3) and wasd_hint_timer > 0 and player2:
        wasd_hint_timer -= 1
        t2 = wasd_hint_timer / float(CONTROLS_HINT_FRAMES)
        alpha2 = max(0, min(220, int(220 * t2)))
        surf_w2 = player2.width + 100
        surf_h2 = player2.height + 100
        wsurf = pygame.Surface((surf_w2, surf_h2), pygame.SRCALPHA)
        cx2, cy2 = surf_w2 // 2, surf_h2 // 2
        base_gap2 = max(player2.width, player2.height) // 2 + 28
        pulse2 = 3 * math.sin(pygame.time.get_ticks() * 0.02)
        gap2 = base_gap2 + pulse2
        col2 = (255, 255, 255, alpha2)
        font2 = jp_font(16)
        # 上W
        w = font2.render('W', True, (255,255,255))
        wsurf.blit(w, w.get_rect(center=(cx2, cy2 - gap2)))
        # 下S
        s = font2.render('S', True, (255,255,255))
        wsurf.blit(s, s.get_rect(center=(cx2, cy2 + gap2)))
        # 左A
        a = font2.render('A', True, (255,255,255))
        wsurf.blit(a, a.get_rect(center=(cx2 - gap2, cy2)))
        # 右D
        d = font2.render('D', True, (255,255,255))
        wsurf.blit(d, d.get_rect(center=(cx2 + gap2, cy2)))
        screen.blit(wsurf, (player2.centerx - cx2, player2.centery - cy2))

    # 操作反転中はボス横に ⇔ を表示
    if boss_alive and boss_info and boss_info.get('name') == '三日月形ボス' and controls_inverted:
        sym_font = jp_font(28)
        sym = sym_font.render("⇔", True, (200, 160, 255))
        srect = sym.get_rect(midleft=(boss_x + boss_radius + 10, boss_y))
        screen.blit(sym, srect)

    # 三日月形ボスの星座線分（予告→有効）の描画
    if boss_alive and boss_info and boss_info.get('name') == '三日月形ボス':
        segs = boss_info.get('const_segments', [])
        if segs:
            # TTL を減衰しつつ描画
            new_segs = []
            for s in segs:
                # 状態: tele(予告) -> active(有効)
                state = s.get('state', 'active')
                if state == 'tele':
                    s['tele_ttl'] = s.get('tele_ttl', 30) - 1
                    # 点滅（2フレームおき）で予告
                    if (pygame.time.get_ticks() // 100) % 2 == 0:
                        pygame.draw.line(screen, (220,200,255), s['a'], s['b'], s.get('thick', 6))
                    # 端点の丸
                    pygame.draw.circle(screen, (220,200,255), (int(s['a'][0]), int(s['a'][1])), max(2, s.get('thick',6)//2))
                    pygame.draw.circle(screen, (220,200,255), (int(s['b'][0]), int(s['b'][1])), max(2, s.get('thick',6)//2))
                    if s['tele_ttl'] <= 0:
                        s['state'] = 'active'
                        s['ttl'] = s.get('active_ttl', 180)
                else:
                    s['ttl'] = s.get('ttl', 180) - 1
                    if s['ttl'] <= 0:
                        continue
                    a = s['a']; b = s['b']
                    thick = max(2, int(s.get('thick', 6)))
                    col = (180, 160, 255)
                    pygame.draw.line(screen, col, a, b, thick)
                    pygame.draw.circle(screen, col, (int(a[0]), int(a[1])), max(2, thick//2))
                    pygame.draw.circle(screen, col, (int(b[0]), int(b[1])), max(2, thick//2))
                new_segs.append(s)
            boss_info['const_segments'] = new_segs

    # 楕円ボス 新ビーム描画
    if boss_alive and boss_info and boss_info["name"] == "楕円ボス":
        for side in ('left','right'):
            beam = boss_info.get(f'{side}_beam')
            if not beam: continue
            ox, oy = beam.get('origin', (boss_x, boss_y))
            if 'target' in beam:
                tx, ty = beam['target']
            else:
                # 角度から暫定ターゲット（表示/衝突用）
                ang = beam.get('angle', -math.pi/2)
                tx = int(ox + math.cos(ang) * 1200)
                ty = int(oy + math.sin(ang) * 1200)
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
        # レーザー演出は廃止（形態なし）
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
            # 定義前参照の回避用にローカル既定値を設定
            ROTATE_SEGMENTS_NUM = 5
            ROTATE_RADIUS = boss_radius + 30
            for i in range(ROTATE_SEGMENTS_NUM):
                angle = rotate_angle_local + (2 * math.pi * i / ROTATE_SEGMENTS_NUM)
                seg_x = boss_x + ROTATE_RADIUS * math.cos(angle)
                seg_y = boss_y + ROTATE_RADIUS * math.sin(angle)
                seg_rect = pygame.Rect(int(seg_x-20), int(seg_y-20), 40, 40)
                pygame.draw.rect(screen, (180, 0, 180), seg_rect)
        elif boss_info and boss_info["name"] == "楕円ボス":
            # 旧本体描画は分割描画セクションで済んでいるためここでは小楕円のみ可動表示（緑）。
            # 各小楕円は角度 boss_info['left_angle'/'right_angle'] に合わせて下先端がプレイヤーを向く。
            small_w, small_h = boss_radius//2, boss_radius*2//3
            for side in ('left','right'):
                cx = boss_x - boss_radius if side=='left' else boss_x + boss_radius
                cy = boss_y
                ang = boss_info.get(f'{side}_angle', -math.pi/2)
                # 回転楕円の簡易描画: 軸は回転させず、下先端方向に小さな三角で向きを示す
                rect = pygame.Rect(int(cx - small_w//2), int(cy - small_h//2), small_w, small_h)
                pygame.draw.ellipse(screen, (0,200,0), rect)
                tipx = cx + (-math.sin(ang)) * (small_h/2)
                tipy = cy + ( math.cos(ang)) * (small_h/2)
                # 向きマーカー（小さなライン）
                pygame.draw.line(screen, (0,255,0), (cx, cy), (int(tipx), int(tipy)), 3)
        elif boss_info and boss_info["name"] == "バウンドボス":
            # 潰れ演出: squish_state中は縦に潰し・横に拡げる
            if boss_info.get('squish_state') == 'squish':
                t = boss_info.get('squish_timer',0)
                ratio = 1 - (t / max(1, BOUNCE_BOSS_SQUISH_DURATION))
                # 直前のバウンド面を推定: 速度ベクトルの符号から反射面を判断（速度成分の絶対値大きい軸）
                vx = boss_info.get('bounce_vx',0)
                vy = boss_info.get('bounce_vy',0)
                horizontal_hit = abs(vy) > abs(vx)  # 上下反射後は縦速度が大, 左右反射後は横速度が大
                if horizontal_hit:
                    # 上下バウンド: 従来（縦潰れ）
                    squash = 0.45 + 0.55 * ratio
                    stretch = 1.0 + (1 - ratio) * 0.5
                else:
                    # 左右バウンド: 横潰れ / 縦伸び
                    stretch = 0.45 + 0.55 * ratio  # 横縮小
                    squash = 1.0 + (1 - ratio) * 0.5  # 縦拡張
                w = int(boss_radius * 2 * stretch)
                h = int(boss_radius * 2 * squash)
                rect = pygame.Rect(0,0,w,h)
                rect.center = (int(boss_x), int(boss_y))
                pygame.draw.ellipse(screen, boss_color, rect)
            else:
                pygame.draw.circle(screen, boss_color, (int(boss_x), int(boss_y)), boss_radius)
        elif boss_info and boss_info["name"] == "三日月形ボス":
            # 単体三日月描画
            outer_r = boss_radius
            inner_r = int(boss_radius * 0.75)
            offset = int(boss_radius * 0.45)  # 内円のオフセットで細さ調整
            cres = pygame.Surface((outer_r*2+2, outer_r*2+2), pygame.SRCALPHA)
            pygame.draw.circle(cres, boss_color, (outer_r+1, outer_r+1), outer_r)
            pygame.draw.circle(cres, (0,0,0,0), (outer_r+1 - offset, outer_r+1), inner_r)
            screen.blit(cres, (int(boss_x-outer_r-1), int(boss_y-outer_r-1)))
        # ボスへの小爆発
        for pos in boss_explosion_pos:
            pygame.draw.circle(screen, (255,255,0), pos, 15)
        # 小爆発は一瞬だけ表示
        if boss_explosion_pos:
            boss_explosion_pos = []
    # デバッグヒント表示
    # デバッグヒント(削除済み)
    # ボス撃破後の派手な爆発
    if not boss_alive and boss_explosion_timer < BOSS_EXPLOSION_DURATION:
        for i in range(12):
            angle = i * 30
            x = int(boss_x + boss_radius * 1.5 * math.cos(math.radians(angle)))
            y = int(boss_y + boss_radius * 1.5 * math.sin(math.radians(angle)))
            pygame.draw.circle(screen, (255, 100, 0), (x, y), 40)
        pygame.draw.circle(screen, (255,255,0), (boss_x, boss_y), 60)
    # クリア表示の重複ルートは削除（上のエンドメニューで統一）

    # 残機表示（画面右下）
    font = jp_font(26)
    lives_text = f"Lives: {player_lives}"
    text_surf = font.render(lives_text, True, WHITE)
    text_rect = text_surf.get_rect(bottomright=(WIDTH-10, HEIGHT-10))
    screen.blit(text_surf, text_rect)
    # 弾種表示
    font = jp_font(20)
    # 武器アイコン表示（解放済みのもののみ）
    weapon_icons = []  # (label, color, active)
    weapon_icons.append(("N", BULLET_COLOR_NORMAL, bullet_type == "normal"))
    if has_homing:
        weapon_icons.append(("H", BULLET_COLOR_HOMING, bullet_type == "homing"))
    if has_spread:
        weapon_icons.append(("S", BULLET_COLOR_SPREAD, bullet_type == "spread"))
    icon_size = 22
    pad = 6
    base_x = 20
    base_y = HEIGHT - 50
    for i,(lbl,col,active) in enumerate(weapon_icons):
        x = base_x + i*(icon_size+pad)
        rect = pygame.Rect(x, base_y, icon_size, icon_size)
        pygame.draw.rect(screen, col, rect, 0 if active else 2)
        if not active:
            pygame.draw.rect(screen, WHITE, rect, 2)
        f2 = jp_font(18)
        ts = f2.render(lbl, True, BLACK if active else col)
        ts_rect = ts.get_rect(center=rect.center)
        screen.blit(ts, ts_rect)
    hint_font = jp_font(18)
    hint = hint_font.render("V:切替", True, WHITE)
    screen.blit(hint, (base_x, base_y - 18))

    # （L5用デバッグHUDはユーザー要望により削除）

    # ダッシュクールダウン表示
    if 'has_dash' in globals() and has_dash:
        # 円形メーター (右下ライフの左側)
        cx = WIDTH - 80
        cy = HEIGHT - 70
        radius = 24
        # 外枠
        pygame.draw.circle(screen, (200,200,200), (cx, cy), radius, 2)
        # クール残割合
        if dash_cooldown > 0:
            ratio = dash_cooldown / DASH_COOLDOWN_FRAMES
            # 12分割(アイコンの足=セグメント)埋め
            segs = DASH_ICON_SEGMENTS
            filled = int(segs * ratio + 0.999)
            for i in range(filled):
                ang0 = (2*math.pi * i / segs) - math.pi/2
                ang1 = (2*math.pi * (i+1) / segs) - math.pi/2
                inner = radius - 8
                pts = [
                    (cx + inner * math.cos(ang0), cy + inner * math.sin(ang0)),
                    (cx + radius * math.cos(ang0), cy + radius * math.sin(ang0)),
                    (cx + radius * math.cos(ang1), cy + radius * math.sin(ang1)),
                    (cx + inner * math.cos(ang1), cy + inner * math.sin(ang1)),
                ]
                pygame.draw.polygon(screen, (120,180,255), pts)
        else:
            # READY 表示
            font_ready = jp_font(18)
            txt = font_ready.render("DASH", True, (120,200,255))
            rect = txt.get_rect(center=(cx, cy))
            screen.blit(txt, rect)
        # 発動中ハイライトリング
        if dash_active:
            pygame.draw.circle(screen, (0,255,255), (cx, cy), radius+2, 2)

    pygame.display.flip()
    clock.tick(60)

    # ウィンドウ ワープ/シェイク更新（ワープ優先）
    if _game_window:
        # ワープ発動条件（三日月形ボスのHPが1/3以下）
        if boss_info and boss_alive and boss_info.get('name') == '三日月形ボス':
            try:
                max_hp_for_warp = int(boss_info.get('initial_hp', boss_info.get('hp', 0)))
            except Exception:
                max_hp_for_warp = boss_hp
            threshold = max(1, max_hp_for_warp // 3) if max_hp_for_warp else max(1, int((boss_info.get('hp', 1))/3))
            if boss_hp <= threshold:
                if not _window_warp_active:
                    _window_warp_active = True
                    _window_warp_timer = 0
                    _window_warp_index = 0
                    # 五芒星の外側5頂点（基準: 上向き）を半径Rで配置
                    R = 140
                    pts = []
                    for i in range(5):
                        ang = math.radians(-90 + 72*i)
                        dx = int(R * math.cos(ang))
                        dy = int(R * math.sin(ang))
                        pts.append((dx, dy))
                    order = [0, 2, 4, 1, 3]  # 星の結び順
                    _window_warp_vertices = [pts[i] for i in order]
                    # 初回は即ジャンプ
                    ox, oy = _window_warp_vertices[_window_warp_index]
                    _game_window.position = (_window_base_pos[0] + ox, _window_base_pos[1] + oy)
                else:
                    _window_warp_timer += 1
                    if _window_warp_timer >= _window_warp_interval:
                        _window_warp_timer = 0
                        _window_warp_index = (_window_warp_index + 1) % max(1, len(_window_warp_vertices) or 1)
            else:
                if _window_warp_active:
                    _window_warp_active = False
                    _window_warp_timer = 0
                    _window_warp_index = 0
                    _window_warp_vertices = []
                    if _game_window.position != _window_base_pos:
                        _game_window.position = _window_base_pos
        else:
            # 対象外: ワープ解除
            if _window_warp_active:
                _window_warp_active = False
                _window_warp_timer = 0
                _window_warp_index = 0
                _window_warp_vertices = []
                if _game_window.position != _window_base_pos:
                    _game_window.position = _window_base_pos

        # 目標位置決定（ワープ中はその頂点、そうでなければシェイク/ベース）
        desired_pos = _window_base_pos
        if _window_warp_active and _window_warp_vertices:
            ox, oy = _window_warp_vertices[_window_warp_index]
            desired_pos = (_window_base_pos[0] + ox, _window_base_pos[1] + oy)
        elif _window_shake_timer > 0:
            _window_shake_timer -= 1
            progress = 1 - (_window_shake_timer / float(WINDOW_SHAKE_DURATION))
            decay = (1 - progress)**0.4
            jitter_phase = pygame.time.get_ticks()
            ox = int((_window_shake_intensity * decay) * math.sin(jitter_phase*0.09) + random.randint(-3,3))
            oy = int((_window_shake_intensity * decay) * math.cos(jitter_phase*0.11) + random.randint(-3,3))
            desired_pos = (_window_base_pos[0] + ox, _window_base_pos[1] + oy)
        if _game_window.position != desired_pos:
            _game_window.position = desired_pos
    if waiting_for_space:
        screen.fill(BLACK)
        font = jp_font(42)
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
                    controls_hint_timer = CONTROLS_HINT_FRAMES if (boss_info and boss_info.get("name") == "三日月形ボス") else 0
                    if controls_hint_timer > 0:
                        controls_hint_mode = 'normal'
    if retry:
        # プレイヤー/一般状態
        player_lives = 3
        player_invincible = False
        player_invincible_timer = 0
        explosion_timer = 0
        explosion_pos = None
        bullets = []
        fire_cooldown = 0
        frame_count = 0
        leaf_angle = 0.0
        bullet_type = "normal"
        # 画面状態
        waiting_for_space = False
        menu_mode = False
        # ボス状態
        boss_alive = True
        boss_x = WIDTH // 2
        boss_y = 60
        boss_state = "track"
        boss_speed = 4
        boss_dir = 1
        boss_attack_timer = 0
        boss_explosion_timer = 0
        boss_explosion_pos = []
        boss_origin_x = boss_x
        boss_origin_y = boss_y
        boss_hp = boss_info["hp"] if boss_info else 35
        # プレイヤー座標リセット
        player = pygame.Rect(WIDTH // 2 - 15, HEIGHT - 40, 30, 15)
        player_speed = 5
        bullet_speed = 7
        controls_inverted = False
        invert_cycle_timer = 0
        # ダッシュ状態を再初期化
        dash_state = {
            'cooldown': 0,
            'invincible_timer': 0,
            'active': False,
            'last_tap': {'left': -9999, 'right': -9999},
        }
        dash_cooldown = 0
        dash_invincible_timer = 0
        dash_last_tap = dash_state['last_tap']
        dash_active = False
        # ボス個別初期化
        if boss_info and boss_info["name"] == "Boss A":
            boss_info['stomp_state'] = 'idle'
            boss_info['stomp_timer'] = 0
            boss_info['stomp_target_y'] = None
            boss_info['home_y'] = boss_y
            boss_info['stomp_interval'] = 120
            boss_info['last_stomp_frame'] = 0
            boss_info['stomp_grace'] = 180
    # 三日月形ボス特別セクタ当たり/斬撃判定削除
        # リトライフラグを下ろして次フレームへ（このフレームは描画スキップ）
        retry = False
        continue
    # dash_state 参照を安全化（未定義でも OK に）
    if 'dash_state' in globals():
        dash_invincible_timer = dash_state.get('invincible_timer', 0)
        dash_active = dash_state.get('active', False)
    else:
        dash_invincible_timer = 0
        dash_active = False

    # 弾の移動
    move_player_bullets(bullets, bullet_speed, boss_alive, (boss_x, boss_y))
    # 敵弾の移動（汎用: type=='enemy'）と特殊弾（crescent/mini_hito）
    moved = []
    spawn_extras = []
    for b in bullets:
        subtype = b.get('subtype')
        btype = b.get('type')
        if btype == 'enemy' or subtype in ('crescent','mini_hito'):
            # life 減衰
            if 'life' in b:
                b['life'] -= 1
                if b['life'] <= 0:
                    # スターバースト（大）: 寿命で5方向に分裂
                    if b.get('subtype') == 'star_burst_big' and not b.get('exploded'):
                        base = b.get('burst_base_angle', 0.0)
                        speed = b.get('burst_speed', 4.2)
                        cx, cy = b['rect'].center
                        for i in range(5):
                            ang = base + (2*math.pi*i/5)
                            vx = speed*math.cos(ang); vy = speed*math.sin(ang)
                            spawn_extras.append({
                                'rect': pygame.Rect(int(cx-5), int(cy-5), 10, 10),
                                'type': 'enemy', 'vx': vx, 'vy': vy, 'power': 1.0,
                                'life': 220, 'fx': float(cx-5), 'fy': float(cy-5),
                                'shape': 'star', 'color': (255,230,0)
                            })
                        b['exploded'] = True
                    # 寿命尽きたので削除
                    continue
            # 速度適用
            move_mode = b.get('move')
            if move_mode == 'sine':
                # ベース速度に対し、垂直な横揺れ成分を付与
                b['t'] = b.get('t', 0.0) + b.get('freq', 0.2)
                bvx = b.get('base_vx', b.get('vx', 0.0))
                bvy = b.get('base_vy', b.get('vy', 0.0))
                speed = math.hypot(bvx, bvy) or 1.0
                # 垂直単位ベクトル
                nx = -bvy / speed
                ny = bvx / speed
                amp = b.get('amp', 2.0)
                offset = amp * math.sin(b['t'])
                # 基本移動 + 横揺れ
                fx = b.get('fx', float(b['rect'].x)) + bvx + nx * offset
                fy = b.get('fy', float(b['rect'].y)) + bvy + ny * offset
                b['fx'], b['fy'] = fx, fy
                b['rect'].x = int(fx)
                b['rect'].y = int(fy)
            elif move_mode == 'orbit':
                # 原点 around に沿って角度 ang で半径 r を増やしつつ回転、一定以上で解放
                ang = b.get('ang', 0.0) + b.get('ang_vel', 0.08)
                r = b.get('radius', 20.0) + b.get('rad_speed', 0.35)
                ox, oy = b.get('orbit_origin', (float(b['rect'].centerx), float(b['rect'].centery)))
                x = ox + r * math.cos(ang)
                y = oy + r * math.sin(ang)
                b['ang'] = ang; b['radius'] = r
                b['rect'].center = (int(x), int(y))
                b['fx'], b['fy'] = x-6, y-6
                # リリース
                rel_r = b.get('release_radius', None)
                if rel_r is not None and r >= rel_r:
                    speed = b.get('release_speed', 4.0)
                    b['move'] = None
                    b['vx'] = speed * math.cos(ang)
                    b['vy'] = speed * math.sin(ang)
            else:
                b['rect'].x += int(b.get('vx', 0))
                b['rect'].y += int(b.get('vy', 0))

            # 落下着弾（スター・フォール）: 地面で8方向に分裂
            if b.get('subtype') == 'star_fall' and b['rect'].bottom >= HEIGHT - 2 and not b.get('exploded'):
                cx, cy = b['rect'].center
                speed = 4.2
                for i in range(8):
                    ang = i * (math.pi/4)
                    vx = speed * math.cos(ang); vy = speed * math.sin(ang)
                    spawn_extras.append({
                        'rect': pygame.Rect(int(cx-4), int(cy-4), 8, 8),
                        'type':'enemy', 'vx': vx, 'vy': vy, 'life': 180,
                        'shape':'star', 'color': (255,230,0), 'power': 1.0
                    })
                b['exploded'] = True
                # 元弾は消滅
                continue
            # 画面外なら除去
            if b['rect'].right < -20 or b['rect'].left > WIDTH + 20 or b['rect'].bottom < -20 or b['rect'].top > HEIGHT + 20:
                continue
            moved.append(b)
        else:
            moved.append(b)
    bullets = moved + spawn_extras

    # 弾とボスの当たり判定（多重ヒット防止版）
    # 拡散弾: 敵弾( enemy ) と接触した場合双方消滅（ボス判定前）
    if any(b.get("type") == "spread" for b in bullets):
        survivors = []
        enemy_bullets = []
        spread_bullets = []
        for b in bullets:
            t = b.get("type")
            if t == "enemy":
                enemy_bullets.append(b)
            elif t == "spread":
                spread_bullets.append(b)
            else:
                survivors.append(b)
        # 相殺判定（O(n*m) だが弾数少なので十分）
        removed_enemy = set()
        removed_spread = set()
        for si, sb in enumerate(spread_bullets):
            for ei, eb in enumerate(enemy_bullets):
                if ei in removed_enemy:
                    continue
                if sb["rect"].colliderect(eb["rect"]):
                    removed_enemy.add(ei)
                    removed_spread.add(si)
        new_list = survivors
        for ei, eb in enumerate(enemy_bullets):
            if ei not in removed_enemy:
                new_list.append(eb)
        for si, sb in enumerate(spread_bullets):
            if si not in removed_spread:
                new_list.append(sb)
        bullets = new_list

    if boss_alive and boss_info:
        cleaned_bullets = []
        for bullet in bullets:
            if bullet.get("type") in ("enemy", "boss_beam"):
                cleaned_bullets.append(bullet)
                continue
            damage = False
            # 楕円ボス: コア開放時は反射せず、楕円本体にもダメージ可
            if boss_info["name"] == "楕円ボス":
                core_state = boss_info.get('core_state','closed')
                gap = boss_info.get('core_gap',0)
                cx, cy = boss_x, boss_y
                central_open = (core_state in ('opening','firing','open_hold') and gap > OVAL_CORE_GAP_HIT_THRESHOLD)
                # コア開放中 & 弾がコア円内ならダメージ
                if central_open:
                    if (bullet["rect"].centerx - cx)**2 + (bullet["rect"].centery - cy)**2 < OVAL_CORE_RADIUS**2:
                        boss_hp -= bullet.get("power", 1.0)
                        boss_explosion_pos.append((bullet["rect"].centerx, bullet["rect"].centery))
                        # 第二形態移行判定
                        if boss_info and boss_info.get('name') == '三日月形ボス' and boss_info.get('phase',1) == 1 and boss_hp <= boss_info.get('phase2_hp', 20):
                            boss_info['phase'] = 2
                            boss_info['phase_grace'] = 60
                            controls_inverted = True
                            controls_hint_mode = 'invert'
                            controls_hint_timer = CONTROLS_HINT_FRAMES
                            boss_color = (180, 80, 255)
                            # 第二形態開始: 横レーザー初弾は必ず自機Yに照準
                            margin = 40
                            y0 = max(margin, min(HEIGHT - margin, player.centery))
                            # すぐに撃たず、グレース後に予告開始
                            boss_info['hline_pending_y'] = y0
                            boss_info['hline_state'] = 'idle'
                            boss_info['hline_timer'] = 0
                            boss_info['hline_cd'] = 0
                            boss_info.setdefault('hline_thick', 36)
                        # 第三形態移行: 第二形態中にHPが更に減少した場合
                        elif boss_info and boss_info.get('name') == '三日月形ボス' and boss_info.get('phase',1) == 2 and boss_hp <= boss_info.get('phase3_hp', max(12, int((boss_info.get('hp', 50))*0.35))):
                            boss_info['phase'] = 3
                            boss_info['phase_grace'] = 60
                            # 色は黄色に戻す
                            boss_color = boss_info.get('color_phase1', (255, 220, 0))
                            # 操作反転を解除
                            controls_inverted = False
                            controls_hint_mode = 'normal'
                            # レーザーを停止
                            boss_info['hline_state'] = 'idle'
                            boss_info['hline_timer'] = 0
                            boss_info['hline_cd'] = 0
                            # 分裂ボス初期化
                            pr = int(boss_radius * 0.8)
                            half_hp = max(1, int(math.ceil(boss_hp / 2)))
                            boss_info['parts'] = [
                                {'x': WIDTH//4, 'y': boss_y, 'dir': 1,  'face': 'right', 'r': pr, 'hp': half_hp, 'alive': True},
                                {'x': (WIDTH*3)//4, 'y': boss_y, 'dir': -1, 'face': 'left',  'r': pr, 'hp': boss_hp - half_hp, 'alive': True},
                            ]
                            boss_info['phase3_split'] = True
                            # 2P生成（WASD操作）。第3形態では2P=左側、P1=右側
                            if not player2:
                                player2 = pygame.Rect(WIDTH//2 - 80, HEIGHT - 40, 30, 15)
                            # ヒント: 矢印側（既存のcontrols_hint_timer）とWASD側（wasd_hint_timer）を起動
                            controls_hint_timer = CONTROLS_HINT_FRAMES
                            wasd_hint_timer = CONTROLS_HINT_FRAMES
                        if boss_hp <= 0:
                            boss_alive = False
                            boss_explosion_timer = 0
                            explosion_pos = (boss_x, boss_y)
                        damage = True
                if not damage:
                    # 反射/ダメージ領域の幾何（中央楕円 + 左右楕円）
                    R = boss_radius
                    central_a = int(R * 0.6)
                    central_b = int(R * 1.0)
                    side_a = int(R * 0.4)
                    side_b = int(R * 0.6)
                    side_offset = int(R * 1.2)

                    def inside_central(px, py):
                        return ((px - cx)**2)/(central_a**2) + ((py - cy)**2)/(central_b**2) < 1

                    def inside_side(px, py):
                        for ox in (-side_offset, side_offset):
                            ex = boss_x + ox - (side_a if ox>0 else -side_a)
                            ey = boss_y
                            if ((px - ex)**2)/(side_a**2) + ((py - ey)**2)/(side_b**2) < 1:
                                return True
                        return False

                    bx, by = bullet["rect"].centerx, bullet["rect"].centery
                    if central_open:
                        # コア開放中: 反射しない。楕円本体に当たればダメージ。
                        if inside_central(bx, by) or inside_side(bx, by):
                            boss_hp -= bullet.get("power", 1.0)
                            boss_explosion_pos.append((bx, by))
                            if boss_hp <= 0:
                                boss_alive = False
                                boss_explosion_timer = 0
                                explosion_pos = (boss_x, boss_y)
                            damage = True
                        # 当たっていなければそのまま通過（何もしない）
                    else:
                        # コア閉鎖中: 従来通り反射
                        reflected_here = inside_central(bx, by) or inside_side(bx, by)
                        if reflected_here:
                            bullet["reflect"] = True
                            if bullet.get("type") == "homing":
                                bullet["type"] = "normal"
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
                            if bullet.get("type") == "homing":
                                bullet["type"] = "normal"
                            bullet["vy"] = abs(bullet.get("vy", -7))
                            bullet["vx"] = random.randint(-3, 3)
                            break
                if not damage:
                    cleaned_bullets.append(bullet)
                continue
            # 通常ボス
            bx = bullet["rect"].centerx
            by = bullet["rect"].centery
            if boss_info.get('name') == '三日月形ボス':
                    # 三日月（第3形態は左右分裂）
                    if boss_info.get('phase',1) == 3 and boss_info.get('phase3_split') and boss_info.get('parts'):
                        any_hit = False
                        for p in boss_info['parts']:
                            if not p.get('alive', True):
                                continue
                            px, py = p['x'], p['y']
                            pr = p.get('r', int(boss_radius*0.8))
                            inner_r = int(pr * 0.75)
                            offset = int(pr * 0.45)
                            ix = px - offset if p.get('face') == 'right' else px + offset
                            dx = bx - px; dy = by - py
                            r2 = dx*dx + dy*dy
                            inside_outer = r2 <= pr*pr
                            inside_inner = (bx - ix)**2 + (by - py)**2 <= inner_r*inner_r
                            if inside_outer and not inside_inner:
                                p['hp'] = p.get('hp', 5) - bullet.get('power', 1.0)
                                boss_explosion_pos.append((bx, by))
                                any_hit = True
                                if p['hp'] <= 0:
                                    p['alive'] = False
                        if any_hit:
                            if not any(pp.get('alive', True) for pp in boss_info['parts']):
                                boss_alive = False
                                boss_explosion_timer = 0
                                explosion_pos = (WIDTH//2, int(sum(pp.get('y', boss_y) for pp in boss_info['parts'])/max(1,len(boss_info['parts']))))
                            damage = True
                    else:
                        dx = bx - boss_x; dy = by - boss_y
                        r2 = dx*dx + dy*dy
                        outer_r = boss_radius
                        inner_r = int(boss_radius * 0.75)
                        offset = int(boss_radius * 0.45)
                        ix = boss_x - offset
                        inside_outer = r2 <= outer_r*outer_r
                        inside_inner = (bx - ix)**2 + (by - boss_y)**2 <= inner_r*inner_r
                        if inside_outer and not inside_inner:
                            boss_hp -= bullet.get("power", 1.0)
                            boss_explosion_pos.append((bx, by))
                            # 形態遷移は廃止（ダメージ処理のみ）
                            if boss_hp <= 0:
                                boss_alive = False
                                boss_explosion_timer = 0
                                explosion_pos = (boss_x, boss_y)
                            damage = True
            else:
                    # その他の丸ボス
                    dx = bx - boss_x; dy = by - boss_y
                    r2 = dx*dx + dy*dy
                    if r2 < boss_radius*boss_radius:
                        boss_hp -= bullet.get("power", 1.0)
                        boss_explosion_pos.append((bx, by))
                        if boss_hp <= 0:
                            boss_alive = False
                            boss_explosion_timer = 0
                            explosion_pos = (boss_x, boss_y)
                        damage = True
            
                    # バウンドボス: HP5ごと縮小 & 速度上昇
                    if boss_info and boss_info.get("name") == "バウンドボス" and boss_hp > 0:
                        # 基準HPとの差異で段数計算 (初期HPからの減少量)
                        initial_hp = boss_info.get('initial_hp') or boss_info.setdefault('initial_hp', boss_info['hp'])
                        reduced = initial_hp - boss_hp
                        new_stage = int(reduced // 5)
                        if new_stage != boss_info.get('shrink_stage', 0):
                            boss_info['shrink_stage'] = new_stage
                            # 半径縮小 (割合減少)
                            boss_radius = int(boss_info['base_radius'] * (1 - BOUNCE_BOSS_SHRINK_STEP * new_stage))
                            boss_radius = max(25, boss_radius)
                            # 速度再計算（方向保持）
                            speed_now = boss_info['base_speed'] * (1 + BOUNCE_BOSS_SPEED_STEP * new_stage)
                            vx = boss_info.get('bounce_vx',0)
                            vy = boss_info.get('bounce_vy',0)
                            cur_speed = math.hypot(vx, vy) or 1
                            scale = speed_now / cur_speed
                            boss_info['bounce_vx'] = vx * scale
                            boss_info['bounce_vy'] = vy * scale
            if not damage:
                cleaned_bullets.append(bullet)
        bullets = cleaned_bullets
    # ボス撃破後の爆発演出
    if not boss_alive and boss_explosion_timer < BOSS_EXPLOSION_DURATION:
        boss_explosion_timer += 1
    # ボスキャラの攻撃パターン
    if boss_alive:
        boss_attack_timer += 1
        # 楕円ボス: 水平往復移動 + コア開閉サイクル
        if boss_info and boss_info.get("name") == "楕円ボス":
            # 左右往復（端で折り返し）
            margin = 40
            if 'move_dir' not in boss_info:
                boss_info['move_dir'] = 1
            boss_x += boss_info['move_dir'] * boss_speed
            if boss_x < boss_radius + margin:
                boss_x = boss_radius + margin
                boss_info['move_dir'] = 1
            elif boss_x > WIDTH - boss_radius - margin:
                boss_x = WIDTH - boss_radius - margin
                boss_info['move_dir'] = -1
            # コア開閉（シンプル周期）
            cs = boss_info.get('core_state','closed')
            boss_info['core_timer'] = boss_info.get('core_timer',0) + 1
            gap = boss_info.get('core_gap', 0)
            gap_target = boss_info.get('core_gap_target', OVAL_CORE_GAP_TARGET)
            gap_step = max(1, boss_info.get('core_gap_step', OVAL_CORE_GAP_STEP))
            cycle = boss_info.get('core_cycle_interval', OVAL_CORE_CYCLE_INTERVAL)
            fire_dur = boss_info.get('core_firing_duration', OVAL_CORE_FIRING_DURATION)
            open_hold = boss_info.get('core_open_hold', OVAL_CORE_OPEN_HOLD)
            # 状態遷移
            if cs == 'closed':
                if boss_info['core_timer'] >= cycle:
                    boss_info['core_state'] = 'opening'
                    boss_info['core_timer'] = 0
            elif cs == 'opening':
                gap = min(gap_target, gap + gap_step)
                boss_info['core_gap'] = gap
                if gap >= gap_target:
                    boss_info['core_state'] = 'open_hold'
                    boss_info['core_timer'] = 0
                    # コアが開いた瞬間にリング弾を一斉発射
                    ring_n = 10
                    spd = 3.8
                    for i in range(ring_n):
                        ang = 2*math.pi*i/ring_n
                        vx = spd*math.cos(ang); vy = spd*math.sin(ang)
                        bullets.append({'rect': pygame.Rect(int(boss_x-4), int(boss_y-4), 8, 8),
                                        'type':'enemy','vx':vx,'vy':vy,'life':240,'power':1.0})
            elif cs == 'open_hold':
                if boss_info['core_timer'] >= open_hold:
                    boss_info['core_state'] = 'firing'
                    boss_info['core_timer'] = 0
                    # 両側からビーム予告開始（方向は固定／下先端から発射）
                    small_h = boss_radius*2//3
                    for side in ('left','right'):
                        cx, cy = ((boss_x - boss_radius), boss_y) if side=='left' else ((boss_x + boss_radius), boss_y)
                        # プレイヤー方向に「下先端(0,+1)」が向く角度 ang（固定）。
                        theta = math.atan2(player.centery - cy, player.centerx - cx)
                        ang = theta
                        boss_info[f'{side}_beam'] = {
                            'state':'telegraph',
                            'timer': 0,
                            'angle': ang
                        }
            elif cs == 'firing':
                # ビームタイミング更新（テレグラフ中も firing ステート継続）
                finished = True
                for side in ('left','right'):
                    beam = boss_info.get(f'{side}_beam')
                    if not beam:
                        continue
                    beam['timer'] = beam.get('timer',0) + 1
                    # 下先端を角度 ang で固定。origin は毎フレーム位置のみ更新（角度は固定）。
                    small_h = boss_radius*2//3
                    cx, cy = ((boss_x - boss_radius), boss_y) if side=='left' else ((boss_x + boss_radius), boss_y)
                    ang = beam.get('angle', 0.0)
                    ox = cx + (-math.sin(ang)) * (small_h/2)
                    oy = cy + ( math.cos(ang)) * (small_h/2)
                    beam['origin'] = (int(ox), int(oy))
                    if beam['state'] == 'telegraph':
                        # 予告は固定（ターゲットは初回のみ算出）
                        if 'target' not in beam:
                            dirx = math.cos(ang)
                            diry = math.sin(ang)
                            tx = int(ox + dirx * 1200)
                            ty = int(oy + diry * 1200)
                            beam['target'] = (tx, ty)
                        if beam['timer'] >= 30:
                            beam['state'] = 'firing'
                            beam['timer'] = 0
                        # いずれにせよ終了ではない
                        finished = False
                    elif beam['state'] == 'firing':
                        if beam['timer'] < fire_dur:
                            finished = False
                # firing期間が終わったら閉じる
                if finished:
                    boss_info['core_state'] = 'closing'
                    boss_info['core_timer'] = 0
                    # ビーム終了
                    boss_info['left_beam'] = None
                    boss_info['right_beam'] = None
                else:
                    # firing中は追加の狙い弾は出さない（ユーザー指定）。リング弾は開いた瞬間のみ。
                    pass
            elif cs == 'closing':
                gap = max(0, gap - gap_step)
                boss_info['core_gap'] = gap
                if gap <= 0:
                    boss_info['core_state'] = 'closed'
                    boss_info['core_timer'] = 0
            # 三日月形ボス以外の処理はここまで
        # 三日月形ボス: 左右往復移動（攻撃/回避AIなし）
        if boss_info and boss_info.get("name") == "三日月形ボス":
            margin = 40
            if boss_info.get('phase',1) == 3 and boss_info.get('phase3_split') and boss_info.get('parts'):
                # 分裂ボス: 各半面で往復
                for p in boss_info['parts']:
                    if not p.get('alive', True):
                        continue
                    pr = p.get('r', int(boss_radius*0.8))
                    p['x'] += p.get('dir',1) * boss_speed
                    if p['x'] < (pr + margin):
                        p['x'] = pr + margin
                        p['dir'] = 1
                    # 半面境界
                    if p.get('face') == 'right':
                        # 左側パートの右端は中央手前まで
                        max_x = (WIDTH//2) - margin - pr
                        if p['x'] > max_x:
                            p['x'] = max_x
                            p['dir'] = -1
                    else:
                        # 右側パートの左端は中央より
                        min_x = (WIDTH//2) + margin + pr
                        if p['x'] < min_x:
                            p['x'] = min_x
                            p['dir'] = 1
                        if p['x'] > WIDTH - pr - margin:
                            p['x'] = WIDTH - pr - margin
                            p['dir'] = -1
                # 単体ボス位置は代表値として中央寄りに維持
                boss_x = WIDTH//2
            else:
                if 'move_dir' not in boss_info:
                    boss_info['move_dir'] = 1
                boss_x += boss_info['move_dir'] * boss_speed
                if boss_x < boss_radius + margin:
                    boss_x = boss_radius + margin
                    boss_info['move_dir'] = 1
                elif boss_x > WIDTH - boss_radius - margin:
                    boss_x = WIDTH - boss_radius - margin
                    boss_info['move_dir'] = -1
            # 第1/第2形態: パターン制御
            bi = boss_info
            bi.setdefault('patt_state', 'idle')
            bi.setdefault('patt_timer', 0)
            bi.setdefault('patt_cd', 0)
            bi.setdefault('last_patt', None)
            # 第二形態: 横レーザー用の状態を初期化
            if bi.get('phase', 1) == 2:
                bi.setdefault('hline_state', 'idle')      # idle -> telegraph -> firing -> cooldown
                bi.setdefault('hline_timer', 0)
                bi.setdefault('hline_y', HEIGHT//2)
                bi.setdefault('hline_thick', 36)          # 太さ（ピクセル）
                bi.setdefault('hline_telegraph', 45)      # 予告時間
                bi.setdefault('hline_firing', 60)         # 発射時間
                bi.setdefault('hline_cooldown', 90)       # クールダウン
            # 形態移行直後のグレース（攻撃停止）
            if bi.get('phase_grace', 0) > 0:
                bi['phase_grace'] -= 1
                bi['patt_state'] = 'idle'
                bi['patt_timer'] = 0
            else:
                # グレース明けで第二形態にpending初弾があれば予告開始
                if bi.get('phase',1) == 2 and bi.get('hline_pending_y') is not None and bi.get('hline_state') == 'idle':
                    bi['hline_y'] = bi['hline_pending_y']
                    bi['hline_pending_y'] = None
                    bi['hline_state'] = 'telegraph'
                    bi['hline_timer'] = 0
                bi['patt_timer'] += 1
            if bi['patt_state'] == 'idle' and bi.get('phase_grace',0) == 0:
                # 連続アイドルの監視（フェイルセーフ）
                bi['idle_guard'] = bi.get('idle_guard', 0) + 1
                if bi['patt_cd'] > 0:
                    bi['patt_cd'] -= 1
                # クールダウン終了 or 長時間アイドル時は強制的にパターン開始
                if bi['patt_cd'] <= 0 or bi['idle_guard'] > 240:
                    # 新しい星パターン（直前と重複しにくく）
                    pats = ['star_spread5', 'starfield_spin', 'star_burst', 'constellation', 'star_curtain']
                    if bi.get('last_patt') in pats and len(pats) > 1:
                        pats.remove(bi['last_patt'])
                    choice = random.choice(pats) if pats else 'star_spread5'
                    bi['patt_choice'] = choice
                    bi['patt_state'] = 'run'
                    bi['patt_timer'] = 0
                    bi['idle_guard'] = 0
            elif bi['patt_state'] == 'run':
                t = bi['patt_timer']
                ch = bi.get('patt_choice')
                # 発射起点（分裂モード時は各パート、通常は本体）
                origins = []
                if bi.get('phase',1) == 3 and bi.get('phase3_split') and bi.get('parts'):
                    for p in bi['parts']:
                        if p.get('alive', True):
                            origins.append(p)
                else:
                    origins.append({'x': boss_x, 'y': boss_y, 'face':'right', 'r': boss_radius})

                # 1) 拡散シューティングスター
                if ch == 'star_spread5':
                    if t in (1, 10, 20):
                        speed = 8.0
                        base = -math.pi/2 + (t*0.08)
                        for org in origins:
                            for i in range(5):
                                ang = base + 2*math.pi*i/5
                                vx = speed*math.cos(ang); vy = speed*math.sin(ang)
                                bullets.append({'rect': pygame.Rect(int(org['x']-6), int(org['y']-6), 12, 12),
                                                'type':'enemy','vx':vx,'vy':vy,'power':1.0,'life':360,
                                                'fx': float(org['x']-6), 'fy': float(org['y']-6),
                                                'shape':'star','color': (255,230,0), 'trail_ttl': 10})
                    if t > 28:
                        bi['patt_state']='idle'; bi['patt_timer']=0; bi['patt_cd']=50; bi['last_patt']=ch

                # 2) 回転スターフィールド（軌道→解放）
                elif ch == 'starfield_spin':
                    if t in (1,):
                        for org in origins:
                            ring_n = 10
                            for i in range(ring_n):
                                ang = 2*math.pi*i/ring_n
                                bullets.append({'rect': pygame.Rect(int(org['x']-6), int(org['y']-6), 12, 12),
                                                'type':'enemy','move':'orbit','orbit_origin': (org['x'], org['y']),
                                                'ang': ang, 'ang_vel': 0.08, 'radius': 20.0, 'rad_speed': 0.45,
                                                'release_radius': 200.0, 'release_speed': 4.3,
                                                'power':1.0,'life':480,'shape':'star','color': (255,230,0), 'trail_ttl': 16})
                    if t > 90:
                        bi['patt_state']='idle'; bi['patt_timer']=0; bi['patt_cd']=65; bi['last_patt']=ch

                # 3) （削除済み）

                # 4) 星連弾（スターバースト）
                elif ch == 'star_burst':
                    if t in (1, 30):
                        for org in origins:
                            dxp = player.centerx - org['x']; dyp = player.centery - org['y']
                            base = math.atan2(dyp, dxp)
                            bullets.append({'rect': pygame.Rect(int(org['x']-8), int(org['y']-8), 16, 16), 'type':'enemy',
                                            'vx': 3.0*math.cos(base), 'vy': 3.0*math.sin(base), 'power': 1.0,
                                            'life': 40, 'shape':'star', 'color': (255,230,0), 'subtype':'star_burst_big',
                                            'burst_base_angle': base})
                    if t > 70:
                        bi['patt_state']='idle'; bi['patt_timer']=0; bi['patt_cd']=60; bi['last_patt']=ch

                # 5) 星座攻撃（コンステレーション）
                elif ch == 'constellation':
                    bi.setdefault('const_segments', [])
                    if t in (1,):
                        nodes = []
                        for org in origins:
                            for i in range(6):
                                ang = random.random()*2*math.pi
                                r = random.uniform(20, boss_radius+40)
                                sx = org['x'] + r*math.cos(ang)
                                sy = org['y'] + r*math.sin(ang)
                                vx = 0.6*math.cos(ang+math.pi/2)
                                vy = 0.6*math.sin(ang+math.pi/2)
                                bullets.append({'rect': pygame.Rect(int(sx-6), int(sy-6), 12, 12), 'type':'enemy',
                                                'vx': vx, 'vy': vy, 'life': 300, 'power':1.0,
                                                'shape':'star','color': (255,230,0), 'harmless': True})
                                nodes.append((sx, sy))
                        for _ in range(5):
                            if len(nodes) >= 2:
                                a = random.choice(nodes); b = random.choice(nodes)
                                if a != b:
                                    bi['const_segments'].append({'a': a, 'b': b, 'state': 'tele', 'tele_ttl': 30, 'active_ttl': 180, 'thick': 6})
                    if t > 60:
                        bi['patt_state']='idle'; bi['patt_timer']=0; bi['patt_cd']=75; bi['last_patt']=ch

                # 6) スターカーテン（斜めに流れる星弾）
                elif ch == 'star_curtain':
                    if t % 3 == 1 and t <= 90:
                        side = random.choice(['L','R'])
                        if side == 'L':
                            x = random.randint(-20, WIDTH//3)
                            y = -10
                            vx = random.uniform(1.5, 3.0)
                        else:
                            x = random.randint((WIDTH*2)//3, WIDTH+20)
                            y = -10
                            vx = random.uniform(-3.0, -1.5)
                        vy = random.uniform(4.0, 6.0)
                        bullets.append({'rect': pygame.Rect(int(x-6), int(y-6), 12, 12), 'type':'enemy',
                                        'vx': vx, 'vy': vy, 'life': 360, 'power':1.0,
                                        'shape':'star','color': (255,230,0), 'trail_ttl': 14})
                    if t > 110:
                        bi['patt_state']='idle'; bi['patt_timer']=0; bi['patt_cd']=70; bi['last_patt']=ch
            # 第二形態: 横レーザー 状態遷移（独立進行）※ 第三形態では無効
            if bi.get('phase', 1) == 2:
                st = bi.get('hline_state', 'idle')
                # グレース中はレーザーを進行させない
                if bi.get('phase_grace',0) > 0:
                    pass
                else:
                    bi['hline_timer'] = bi.get('hline_timer', 0) + 1
                if bi['patt_state'] == 'idle' and bi.get('phase_grace',0) == 0:
                    # クールダウン中は待機
                    if bi.get('hline_cd', 0) > 0:
                        bi['hline_cd'] -= 1
                        # 次のパターンを選ぶかは別ロジックに任せる（ここではレーザーのCDのみ管理）
                        if bi.get('phase_grace',0) == 0:
                            if random.random() < 0.02:
                                margin = 40
                                bi['hline_y'] = random.randint(margin, HEIGHT - margin)
                                bi['hline_state'] = 'telegraph'
                                bi['hline_timer'] = 0
                elif st == 'telegraph':
                    if bi.get('phase_grace',0) == 0 and bi['hline_timer'] >= bi['hline_telegraph']:
                        bi['hline_state'] = 'firing'
                        bi['hline_timer'] = 0
                elif st == 'firing':
                    if bi.get('phase_grace',0) == 0 and bi['hline_timer'] >= bi['hline_firing']:
                        bi['hline_state'] = 'cooldown'
                        bi['hline_timer'] = 0
                        bi['hline_cd'] = bi['hline_cooldown']
                elif st == 'cooldown':
                    if bi.get('hline_cd', 0) > 0:
                        bi['hline_cd'] -= 1
                    else:
                        bi['hline_state'] = 'idle'
                        bi['hline_timer'] = 0
            
        # 三日月形ボス 新攻撃ステート（第1形態: 今は無効化）
        if boss_info and boss_info.get('name') == '三日月形ボス':
            bi = boss_info
            if 'attack_state' not in bi:
                bi['attack_state'] = 'idle'
                bi['attack_timer'] = 0
                bi['attack_cooldowns'] = {'dive':180,'iai':200,'crescent':240,'hito':320}
                now = -9999
                bi['attack_last_used'] = {k:now for k in bi['attack_cooldowns']}
                bi['telegraphs'] = []
                bi.setdefault('active_slashes', [])
                bi['sword_detached'] = False
                bi['sword_projectile'] = None
                bi['attack_history'] = []
                # 第1形態: 三日月状（中心角狭め、外周沿い接触）
                bi.setdefault('tri_base_angle', -math.pi/2)
                bi.setdefault('tri_angle_span', math.radians(120))
                bi['dive_params'] = {'prep':25,'drop_speed':12,'slash_ttl':14,'recover':40}
                bi['iai_params'] = {'charge':55,'beam_ttl':8}
                bi['crescent_params'] = {'charge':50,'waves':1,'count':3,'speed':7,'spread_angle':math.radians(40)}
                bi['hito_params'] = {'throw_speed':10,'throw_time':50,'split_count':6,'mini_speed':5,'return_speed':9}
                bi['cooldown_time'] = 50
                # 攻撃は今は無効化
                bi['new_attack_enabled'] = False
            # TTL update for slashes（攻撃無効でも安全にTTLだけ減衰）
            new_sl = []
            for sl in bi.get('active_slashes', []):
                sl['ttl'] -= 1
                if sl['ttl'] > 0:
                    new_sl.append(sl)
            bi['active_slashes'] = new_sl
            if bi.get('new_attack_enabled'):
                bi['attack_timer'] += 1
                state = bi['attack_state']
                t = bi['attack_timer']
                frame = boss_attack_timer
                # State machine (same logic as before but centralized)
                if state == 'idle':
                    if t > 90:
                        bi['attack_state'] = 'select'; bi['attack_timer'] = 0
                elif state == 'select':
                    cd = bi['attack_cooldowns']; last = bi['attack_last_used']
                    opts = [o for o in cd if frame - last.get(o,-9999) >= cd[o]]
                    if not opts:
                        bi['attack_state'] = 'idle'; bi['attack_timer'] = 0
                    else:
                        hist = bi['attack_history'][-2:]
                        prefer = [o for o in opts if o not in hist] or opts
                        choice = random.choice(prefer)
                        bi['attack_history'].append(choice)
                        bi['attack_choice'] = choice
                        if choice == 'dive':
                            bi['attack_state'] = 'dive_prep'
                        elif choice == 'iai':
                            bi['attack_state'] = 'iai_charge'
                        elif choice == 'crescent':
                            bi['attack_state'] = 'crescent_charge'; bi['telegraphs'].append({'type':'crescent_charge','ttl':bi['crescent_params']['charge']})
                        elif choice == 'hito':
                            bi['attack_state'] = 'hito_throw'; bi['telegraphs'].append({'type':'hito_throw','ttl':20})
                        bi['attack_timer'] = 0
                        if choice == 'dive':
                            target_y = player.centery - (boss_radius + 30)
                            target_y = max(90, min(target_y, HEIGHT - boss_radius - 80))
                            bi['dive_target_y_new'] = target_y
                            bi['telegraphs'].append({'type':'dive_prep','ttl':bi['dive_params']['prep']})
                elif state == 'dive_prep':
                    prep = bi['dive_params']['prep']
                    if t == 1: bi['dive_home_y'] = bi.get('dive_home_y', boss_y)
                    if t < prep: boss_y -= 1.8
                    else: bi['attack_state']='dive_drop'; bi['attack_timer']=0
                elif state == 'dive_drop':
                    target_y = bi.get('dive_target_y_new', boss_y)
                    speed_y = max(4, int(bi['dive_params']['drop_speed']*0.55))
                    if boss_y < target_y:
                        boss_y += speed_y
                        if boss_y > target_y: boss_y = target_y
                    dxp = player.centerx - boss_x
                    boss_x += max(-4, min(4, dxp*0.12))
                    if abs(boss_y - target_y) < 4:
                        slash_rect = pygame.Rect(int(boss_x-150//2), int(boss_y), 150, 120)
                        bi['active_slashes'].append({'type':'dive','rect':slash_rect,'ttl':bi['dive_params']['slash_ttl']})
                        bi['attack_state']='dive_slash'; bi['attack_timer']=0
                elif state == 'dive_slash':
                    if t > bi['dive_params']['slash_ttl'] + 6:
                        bi['attack_state']='dive_recover'; bi['attack_timer']=0
                elif state == 'dive_recover':
                    home_y = bi.get('dive_home_y', boss_y)
                    dist = boss_y - home_y
                    if dist>0:
                        asc = 2.6 if dist>90 else 2.2 if dist>60 else 1.8 if dist>30 else 1.2
                        boss_y -= asc
                        if boss_y < home_y: boss_y = home_y
                    if abs(boss_y-home_y)<=0.5 and t> int(bi['dive_params']['recover']*0.4):
                        bi['attack_last_used']['dive']=frame; bi['attack_state']='cooldown'; bi['attack_timer']=0
                elif state == 'iai_charge':
                    charge = bi['iai_params']['charge']
                    if t==1: bi['telegraphs'].append({'type':'iai_charge','ttl':charge})
                    if t>=charge:
                        beam_y = boss_y + boss_radius//3
                        beam_thick = 16
                        beam_rect = pygame.Rect(0, int(beam_y - beam_thick//2), WIDTH, beam_thick)
                        bi['active_slashes'].append({'type':'iai','rect':beam_rect,'ttl':bi['iai_params']['beam_ttl']})
                        bi['attack_state']='iai_slash'; bi['attack_timer']=0
                elif state == 'iai_slash':
                    if t > bi['iai_params']['beam_ttl'] + 6:
                        bi['attack_last_used']['iai']=frame; bi['attack_state']='cooldown'; bi['attack_timer']=0
                elif state == 'crescent_charge':
                    charge = bi['crescent_params']['charge']
                    if t == 1:
                        bi['telegraphs'].append({'type':'crescent_charge','ttl':charge})
                    if t >= charge:
                        waves = bi['crescent_params']['waves']
                        count = bi['crescent_params']['count']
                        spread = bi['crescent_params']['spread_angle']
                        speed = bi['crescent_params']['speed']
                        dxp = player.centerx - boss_x
                        dyp = player.centery - boss_y
                        base_angle = math.atan2(dyp, dxp)
                        for w in range(waves):
                            for i in range(count):
                                ang = base_angle if count == 1 else (base_angle - spread/2 + spread * (i/(count-1)))
                                vx = math.cos(ang) * speed
                                vy = math.sin(ang) * speed
                                rect = pygame.Rect(int(boss_x-6), int(boss_y-6),12,12)
                                bullets.append({'rect':rect,'type':'enemy','subtype':'crescent','vx':vx,'vy':vy,'life':220})
                        bi['attack_state']='crescent_fire'
                        bi['attack_timer']=0
                    else:
                        prog = min(1.0, t/float(charge))
                        # シンプルな引き( -0.6rad ) から 0 へ近づくカーブ
                        bi['sword_angle_offset'] = -0.6 * (0.5 - 0.5*math.cos(math.pi*prog))
                elif state == 'crescent_fire':
                    if t>20:
                        bi['attack_last_used']['crescent']=frame; bi['attack_state']='cooldown'; bi['attack_timer']=0
                elif state == 'hito_throw':
                    # (重複旧コード削除済み) hito_throw のロジックは後段統合版を使用
                    pass
                    wind_total = 30
                    if t <= wind_total:
                        prog = t/float(wind_total)
                        if prog < 0.4:
                            p = prog/0.4
                            bi['sword_angle_offset'] = -0.85 * (0.5 - 0.5*math.cos(math.pi*p))
                        elif prog < 0.7:
                            p = (prog-0.4)/0.3
                            bi['sword_angle_offset'] = -0.85 + ( -0.45 + 0.85 ) * p
                        else:
                            p = (prog-0.7)/0.3
                            bi['sword_angle_offset'] = -0.45 + ( -0.15 + 0.45 ) * (0.5 - 0.5*math.cos(math.pi*p))
                    if t == wind_total+1 and not bi['sword_detached']:
                        bi['sword_detached']=True
                        dxp=player.centerx-boss_x; dyp=player.centery-boss_y; dist=math.hypot(dxp,dyp) or 1
                        spd=bi['hito_params']['throw_speed']; vx=spd*dxp/dist; vy=spd*dyp/dist
                        bi['sword_projectile']={'phase':'out','x':boss_x,'y':boss_y,'vx':vx,'vy':vy,'life':bi['hito_params']['throw_time']}
        # 三日月形ボス: 弾回避AI（今は無効。True のときのみ作動）
        if boss_info and boss_info.get("name") == "三日月形ボス" and boss_info.get('dodge_ai', False):
            bi = boss_info
            # クールダウンタイマー
            bi['dodge_timer'] = bi.get('dodge_timer',0) + 1
            # 既存ターゲットへの移動
            target_x = bi.get('dodge_target_x')
            need_new_target = False
            if target_x is None or boss_attack_timer > bi.get('dodge_active_until', -1):
                need_new_target = True
            elif abs(target_x - boss_x) < 4:
                # 目標付近に来たら停止判定
                need_new_target = True
            # 弾脅威スキャン（再ターゲット可能なら）
            if need_new_target and bi['dodge_timer'] >= bi.get('dodge_retarget_grace',8):
                earliest_time = None
                threat_x = None
                predict_frames = bi.get('dodge_predict_frames',160)
                min_time = bi.get('dodge_min_time',12)
                # プレイヤー弾のみ対象 (type 未設定=普通弾想定、敵弾は除外)
                for b in bullets:
                    if b.get('type') in ('enemy','boss_beam'):  # 敵側弾は無視
                        continue
                    vx_b = b.get('vx',0)
                    vy_b = b.get('vy', -7)
                    # 下向き弾(負vy_b)のみ対象 (プレイヤー弾が上向きの場合は条件反転: ここではvy<0をプレイヤー弾と想定)
                    if vy_b >= 0:
                        continue
                    # 何フレーム後に弾YがボスY帯( boss_y +/- boss_radius ) に到達するか
                    # y(t) = y0 + vy*t  (vy<0) -> 到達 t = (boss_y - b.centerY)/vy_b
                    by = b['rect'].centery
                    t_hit = (boss_y - by) / vy_b if vy_b != 0 else None
                    if not t_hit or t_hit < 0 or t_hit > predict_frames:
                        continue
                    if t_hit < min_time:
                        continue
                    # その時点のX予測
                    bx = b['rect'].centerx + vx_b * t_hit
                    # ボスXとの距離が半径以内であれば脅威
                    if abs(bx - boss_x) <= boss_radius * 0.9:
                        if earliest_time is None or t_hit < earliest_time:
                            earliest_time = t_hit
                            threat_x = bx
                if threat_x is not None:
                    # 回避方向決定（左右余白比較）
                    padding = bi.get('dodge_padding',70)
                    left_space = (boss_x - padding) - (boss_radius)
                    right_space = (WIDTH - boss_x - padding) - (boss_radius)
                    dir_choice = -1 if right_space > left_space else 1  # 空きの広い方へ逃げる（逆方向にする）
                    # ただし脅威位置相対で調整: 脅威が左なら右へ
                    if threat_x < boss_x:
                        dir_choice = 1
                    else:
                        dir_choice = -1
                    # 連続同方向が続く場合少しランダム補正
                    if dir_choice == bi.get('dodge_last_dir',0):
                        if random.random() < 0.25:
                            dir_choice *= -1
                    bi['dodge_last_dir'] = dir_choice
                    # 目標X設定（境界内）
                    target_x = boss_x + dir_choice * (boss_radius + bi.get('dodge_padding',70))
                    target_x = max(boss_radius+20, min(WIDTH - boss_radius - 20, target_x))
                    bi['dodge_target_x'] = target_x
                    bi['dodge_active_until'] = boss_attack_timer + bi.get('dodge_cooldown',25)
                    bi['dodge_timer'] = 0
                else:
                    # 脅威なし
                    bi['dodge_target_x'] = None
            # 移動適用
            speed = bi.get('dodge_speed',6.0)
            if target_x is not None:
                dx = target_x - boss_x
                step = max(-speed, min(speed, dx))
                boss_x += step
            else:
                # ドリフト（中央へ戻る）
                center_x = WIDTH//2
                drift = bi.get('dodge_drift_speed',1.2)
                if abs(center_x - boss_x) > 3:
                    boss_x += drift if center_x > boss_x else -drift
            # 攻撃ステートマシン
            if not bi.get('new_attack_enabled'):
                # --- Legacy fan_state system (disabled when new_attack_enabled=True) ---
                if 'fan_state' not in bi:
                    bi['fan_state'] = 'idle'
                    bi['fan_state_timer'] = 0
                    bi['fan_attack_cool'] = 120
                    bi['fan_last_attack_frame'] = -9999
                    bi['fan_next_type'] = 'dive'
                    bi['active_slashes'] = []
                # TTL update
                new_sl = []
                for sl in bi.get('active_slashes', []):
                    sl['ttl'] -= 1
                    if sl['ttl'] > 0:
                        new_sl.append(sl)
                bi['active_slashes'] = new_sl
                state = bi['fan_state']
                bi['fan_state_timer'] += 1
                time_since_last = boss_attack_timer - bi.get('fan_last_attack_frame', -9999)
                can_attack = (time_since_last >= bi.get('fan_attack_cool',120))
                if state == 'idle' and can_attack:
                    atk = bi.get('fan_next_type','dive')
                    if atk == 'dive':
                        bi['fan_state'] = 'dive_prep'
                        bi['fan_state_timer'] = 0
                        bi['fan_next_type'] = 'iai'
                        target_y = player.centery - (boss_radius + 30)
                        target_y = max(90, min(target_y, HEIGHT - boss_radius - 80))
                        bi['dive_target_y'] = target_y
                    else:
                        bi['fan_state'] = 'iai_charge'
                        bi['fan_state_timer'] = 0
                        bi['fan_next_type'] = 'dive'
                state = bi['fan_state']
                if state == 'dive_prep':
                    if bi['fan_state_timer'] < 12:
                        boss_y -= 2
                    else:
                        bi['fan_state'] = 'dive_move'
                        bi['fan_state_timer'] = 0
                elif state == 'dive_move':
                    target_y = bi.get('dive_target_y', boss_y)
                    speed_y = 10
                    if boss_y < target_y:
                        boss_y += speed_y
                        if boss_y > target_y:
                            boss_y = target_y
                    dxp = player.centerx - boss_x
                    boss_x += max(-6, min(6, dxp*0.15))
                    if abs(boss_y - target_y) < 3:
                        bi['fan_state'] = 'dive_swing'
                        bi['fan_state_timer'] = 0
                        sw_w = 140
                        sw_h = 110
                        slash_rect = pygame.Rect(int(boss_x - sw_w//2), int(boss_y), sw_w, sw_h)
                        bi['active_slashes'].append({'type':'dive','rect':slash_rect,'ttl':14})
                        bi['fan_last_attack_frame'] = boss_attack_timer
                elif state == 'dive_swing':
                    if bi['fan_state_timer'] > 18:
                        bi['fan_state'] = 'dive_recover'
                        bi['fan_state_timer'] = 0
                elif state == 'dive_recover':
                    boss_y -= 3
                    if bi['fan_state_timer'] > 25:
                        bi['fan_state'] = 'idle'
                        bi['fan_state_timer'] = 0
                elif state == 'iai_charge':
                    charge_dur = 50
                    if bi['fan_state_timer'] == charge_dur:
                        bi['fan_state'] = 'iai_release'
                        bi['fan_state_timer'] = 0
                        beam_y = boss_y + boss_radius//3
                        beam_thick = 16
                        beam_rect = pygame.Rect(0, int(beam_y - beam_thick//2), WIDTH, beam_thick)
                        bi['active_slashes'].append({'type':'iai','rect':beam_rect,'ttl':6})
                        bi['fan_last_attack_frame'] = boss_attack_timer
                elif state == 'iai_release':
                    if bi['fan_state_timer'] > 8:
                        bi['fan_state'] = 'iai_recover'
                        bi['fan_state_timer'] = 0
                elif state == 'iai_recover':
                    if boss_y > 110:
                        boss_y -= 2
                    if bi['fan_state_timer'] > 40:
                        bi['fan_state'] = 'idle'
                        bi['fan_state_timer'] = 0
        
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

        # バウンドボス: 直進突撃→バウンド運動
        if boss_info and boss_info["name"] == "バウンドボス":
            r = boss_radius
            # 潰れ演出中
            if boss_info.get('squish_state') == 'squish':
                boss_info['squish_timer'] += 1
                # 一定フレーム経過で復帰（移動再開）
                if boss_info['squish_timer'] >= BOUNCE_BOSS_SQUISH_DURATION:
                    boss_info['squish_state'] = 'normal'
                    boss_info['squish_timer'] = 0
                # 潰れ中は移動しない
            else:
                # 初回発射方向決定
                if not boss_info.get('bounce_started'):
                    # 初回は真下へ落下(速度はYのみ)
                    boss_info['bounce_vx'] = 0
                    boss_info['bounce_vy'] = BOUNCE_BOSS_SPEED
                    boss_info['bounce_started'] = True
                boss_x += boss_info['bounce_vx']
                boss_y += boss_info['bounce_vy']
                bounced = None
                # 画面端衝突判定
                if boss_x - r < 0:
                    boss_x = r
                    boss_info['bounce_vx'] *= -1
                    bounced = 'left'
                elif boss_x + r > WIDTH:
                    boss_x = WIDTH - r
                    boss_info['bounce_vx'] *= -1
                    bounced = 'right'
                if boss_y - r < 0 and not boss_info.get('first_drop'):
                    boss_y = r
                    boss_info['bounce_vy'] *= -1
                    bounced = 'top'
                elif boss_y + r > HEIGHT:
                    boss_y = HEIGHT - r
                    if boss_info.get('first_drop'):
                        # 初回底面到達: 方向をランダム斜めに変換し first_drop 終了
                        boss_info['first_drop'] = False
                        base_ang = math.radians(random.choice([120, 150, 210, 240]))  # 上向き4方向
                        speed = math.hypot(boss_info['bounce_vx'], boss_info['bounce_vy']) or BOUNCE_BOSS_SPEED
                        boss_info['bounce_vx'] = speed * math.cos(base_ang)
                        boss_info['bounce_vy'] = speed * math.sin(base_ang)
                        bounced = 'bottom'  # ここでは弾幕無し（仕様通り）
                    else:
                        boss_info['bounce_vy'] *= -1
                        bounced = 'bottom'
                if bounced:
                    # 反射角にランダムばらつき
                    speed = math.hypot(boss_info['bounce_vx'], boss_info['bounce_vy'])
                    ang = math.atan2(boss_info['bounce_vy'], boss_info['bounce_vx'])
                    # 1次ジッター + 追加で微小再ジッター
                    jitter = math.radians(random.uniform(-BOUNCE_BOSS_ANGLE_JITTER_DEG, BOUNCE_BOSS_ANGLE_JITTER_DEG))
                    ang += jitter
                    ang += math.radians(random.uniform(-12, 12)) * 0.4
                    nvx = speed * math.cos(ang)
                    nvy = speed * math.sin(ang)
                    # 垂直成分が極端に小さくなりすぎるとゲームが水平往復になるので最小比率を確保
                    min_vert = 0.25 * speed
                    if abs(nvy) < min_vert:
                        nvy = min_vert if nvy >= 0 else -min_vert
                        # 水平成分再計算して速度維持
                        horiz = math.sqrt(max(speed**2 - nvy**2, 0.1))
                        nvx = horiz if nvx >= 0 else -horiz
                    boss_info['bounce_vx'] = nvx
                    boss_info['bounce_vy'] = nvy
                    # 潰れ状態遷移 & 弾幕生成（下端以外）
                    if bounced != 'bottom':
                        # first_drop解除前は弾を出さない（落下演出中）
                        if not boss_info.get('first_drop') and boss_attack_timer - boss_info.get('bounce_cool', 0) >= 4:
                            cx, cy = boss_x, boss_y
                            for i in range(BOUNCE_BOSS_RING_COUNT):
                                bang = 2*math.pi*i/BOUNCE_BOSS_RING_COUNT
                                bspeed = 4
                                vx = int(bspeed * math.cos(bang))
                                vy = int(bspeed * math.sin(bang))
                                bullets.append({
                                    'rect': pygame.Rect(int(cx-4), int(cy-4), 8, 8),
                                    'type': 'enemy',
                                    'power': 1.0,
                                    'vx': vx,
                                    'vy': vy
                                })
                            boss_info['bounce_cool'] = boss_attack_timer
                    # 全方向バウンドでウィンドウシェイク（下端は既に弾幕無しだが揺れは発生）
                    if bounced and _game_window:
                        _window_shake_timer = WINDOW_SHAKE_DURATION
                        _window_shake_intensity = WINDOW_SHAKE_INTENSITY
                    boss_info['squish_state'] = 'squish'
                    boss_info['squish_timer'] = 0

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
        if boss_info and boss_info.get("name") == "三日月形ボス":
            def hit_crescent_point(px, py, cx, cy, r, face, pad=0):
                inner_r = int(r * 0.75)
                offset = int(r * 0.45)
                ix = cx - offset if face == 'right' else cx + offset
                dx = px - cx; dy = py - cy
                inside_outer = dx*dx + dy*dy <= (r + pad)**2
                inside_inner = (px - ix)**2 + (py - cy)**2 <= max(0, inner_r - pad)**2
                return inside_outer and not inside_inner
            # P1
            if boss_info.get('phase',1) == 3 and boss_info.get('phase3_split') and boss_info.get('parts'):
                for p in boss_info['parts']:
                    if not p.get('alive', True):
                        continue
                    if hit_crescent_point(player.centerx, player.centery, p['x'], p['y'], p.get('r', int(boss_radius*0.8)), p.get('face','right'), max(player.width, player.height)//2):
                        player_lives -= 1
                        player_invincible = True
                        player_invincible_timer = 0
                        explosion_timer = 0
                        explosion_pos = (player.centerx, player.centery)
                        player.x = WIDTH//2 - 15
                        player.y = HEIGHT - 40
                        break
                # P2 も接触判定
                if player2:
                    for p in boss_info['parts']:
                        if not p.get('alive', True):
                            continue
                        if hit_crescent_point(player2.centerx, player2.centery, p['x'], p['y'], p.get('r', int(boss_radius*0.8)), p.get('face','right' if p['x'] < WIDTH//2 else 'left'), max(player2.width, player2.height)//2):
                            player_lives -= 1
                            player_invincible = True
                            player_invincible_timer = 0
                            explosion_timer = 0
                            explosion_pos = (player2.centerx, player2.centery)
                            player2.x = WIDTH//2 + 40
                            player2.y = HEIGHT - 40
                            break
            else:
                bx = player.centerx; by = player.centery
                if hit_crescent_point(bx, by, boss_x, boss_y, boss_radius, 'right', max(player.width, player.height)//2):
                    player_lives -= 1
                    player_invincible = True
                    player_invincible_timer = 0
                    explosion_timer = 0
                    explosion_pos = (player.centerx, player.centery)
                    player.x = WIDTH//2 - 15
                    player.y = HEIGHT - 40
            # 追加: 斬撃当たり判定
            for sl in boss_info.get('active_slashes', []):
                if sl['rect'].colliderect(player):
                    player_lives -= 1
                    player_invincible = True
                    player_invincible_timer = 0
                    explosion_timer = 0
                    explosion_pos = (player.centerx, player.centery)
                    player.x = WIDTH//2 - 15
                    player.y = HEIGHT - 40
        else:
            # 三日月形ボスでない通常ボス接触判定
            dx = player.centerx - boss_x
            dy = player.centery - boss_y
            if dx*dx + dy*dy < (boss_radius + max(player.width, player.height)//2)**2:
                player_lives -= 1
                player_invincible = True
                player_invincible_timer = 0
                explosion_timer = 0
                explosion_pos = (player.centerx, player.centery)
                player.x = WIDTH//2 - 15
                player.y = HEIGHT - 40

    # 無敵時間管理
    if player_invincible:
        player_invincible_timer += 1
    if player_invincible_timer >= PLAYER_INVINCIBLE_DURATION and (globals().get('dash_state') or {'invincible_timer':0})['invincible_timer'] <= 0:
            player_invincible = False

    # 爆発表示管理
    if explosion_timer < EXPLOSION_DURATION and explosion_pos:
        explosion_timer += 1

    


