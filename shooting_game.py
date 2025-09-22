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
from fonts import jp_font
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
except Exception:
    _game_window = None
    _window_shake_timer = 0
    _window_shake_intensity = 0
    _window_base_pos = (0, 0)
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
                        boss_radius = boss_info["radius"]
                        boss_hp = boss_info["hp"]
                        boss_color = boss_info["color"]
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
                            # 三日月形ボスは第1形態: 攻撃と回避AIを無効化
                            boss_info['new_attack_enabled'] = False
                            boss_info['dodge_ai'] = False
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
        # 完了
        retry = False
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
        # 重複ブロック削除跡（不要なインデント混入を除去）

    # --- 通常プレイ時の入力処理／移動／射撃／ダッシュ ---
    frame_count += 1
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
            # ダッシュ（左右キーの二度押し）
            if event.key == pygame.K_LEFT:
                if attempt_dash(dash_state, 'left', frame_count, player, has_dash, WIDTH):
                    player_invincible = True  # ダッシュ発動時は無敵付与
            if event.key == pygame.K_RIGHT:
                if attempt_dash(dash_state, 'right', frame_count, player, has_dash, WIDTH):
                    player_invincible = True

    # 押下状態取得（移動・連射）
    keys = pygame.key.get_pressed()
    dx = (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * player_speed
    dy = (keys[pygame.K_DOWN] - keys[pygame.K_UP]) * player_speed
    player.x = max(0, min(WIDTH - player.width, player.x + dx))
    player.y = max(0, min(HEIGHT - player.height, player.y + dy))

    # 連射（Z or SPACE）
    if fire_cooldown > 0:
        fire_cooldown -= 1
    if keys[pygame.K_z] or keys[pygame.K_SPACE]:
        if fire_cooldown <= 0:
            spawn_player_bullets(bullets, player, bullet_type, bullet_speed)
            fire_cooldown = 8

    # ダッシュタイマー更新（UI同期）
    if 'dash_state' in globals():
        update_dash_timers(dash_state)
        dash_cooldown = dash_state.get('cooldown', 0)
        dash_active = dash_state.get('active', False)

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
        elif btype == "spread":
            color = BULLET_COLOR_SPREAD
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
            # 三日月形（外円 - 内円）を Surface 合成で描画
            outer_r = boss_radius
            inner_r = int(boss_radius * 0.75)
            offset = int(boss_radius * 0.45)  # 内円のオフセットで細さ調整
            cres = pygame.Surface((outer_r*2+2, outer_r*2+2), pygame.SRCALPHA)
            pygame.draw.circle(cres, boss_color, (outer_r+1, outer_r+1), outer_r)
            # 内円は透明で塗りつぶして欠けを作る（左へオフセット）
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

    # ウィンドウシェイク更新
    if _game_window and _window_shake_timer > 0:
        _window_shake_timer -= 1
        progress = 1 - (_window_shake_timer / float(WINDOW_SHAKE_DURATION))
        # ease-out 強め + ランダム揺れ合成
        decay = (1 - progress)**0.4
        jitter_phase = pygame.time.get_ticks()
        ox = int((_window_shake_intensity * decay) * math.sin(jitter_phase*0.09) + random.randint(-3,3))
        oy = int((_window_shake_intensity * decay) * math.cos(jitter_phase*0.11) + random.randint(-3,3))
        _game_window.position = (_window_base_pos[0] + ox, _window_base_pos[1] + oy)
    elif _game_window and _window_shake_timer == 0 and _game_window.position != _window_base_pos:
        _game_window.position = _window_base_pos
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
    # 敵側特殊弾 (crescent / mini_hito) 追加処理 & life 減衰
    new_enemy = []
    for b in bullets:
        subtype = b.get('subtype')
        if subtype in ('crescent','mini_hito'):
            # life カウント
            if 'life' in b:
                b['life'] -= 1
                if b['life'] <= 0:
                    continue
            # 移動 (vx, vy 既に反映済みだが homing なし単純)
            b['rect'].x += int(b.get('vx',0))
            b['rect'].y += int(b.get('vy',0))
            # 画面外で除去
            if b['rect'].right < 0 or b['rect'].left > WIDTH or b['rect'].bottom < 0 or b['rect'].top > HEIGHT:
                continue
            new_enemy.append(b)
        else:
            new_enemy.append(b)
    bullets = new_enemy

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
                # 三日月形ボス: 外円内 かつ 内円外 をヒット領域とする
                bx = bullet["rect"].centerx
                by = bullet["rect"].centery
                dx = bx - boss_x
                dy = by - boss_y
                r2 = dx*dx + dy*dy
                if boss_info.get('name') == '三日月形ボス':
                    outer_r = boss_radius
                    inner_r = int(boss_radius * 0.75)
                    offset = int(boss_radius * 0.45)
                    # 内円中心はボス中心から左に offset
                    ix = boss_x - offset
                    iy = boss_y
                    inside_outer = r2 <= outer_r*outer_r
                    inside_inner = (bx - ix)**2 + (by - iy)**2 <= inner_r*inner_r
                    if inside_outer and not inside_inner:
                        boss_hp -= bullet.get("power", 1.0)
                        boss_explosion_pos.append((bx, by))
                        if boss_hp <= 0:
                            boss_alive = False
                            boss_explosion_timer = 0
                            explosion_pos = (boss_x, boss_y)
                        damage = True
                else:
                    if r2 < boss_radius*boss_radius:
                        boss_hp -= bullet.get("power", 1.0)
                        boss_explosion_pos.append((bx, by))
                        if boss_hp <= 0:
                            boss_alive = False
                            boss_explosion_timer = 0
                            explosion_pos = (boss_x, boss_y)
                        damage = True
            else:
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
            # ここに三日月形/楕円ボスの移動ロジックを追加
            if boss_info and boss_info["name"] == "三日月形ボス":
                # --- 基本左右移動（往復） ---
                if 'move_dir' not in boss_info:
                    boss_info['move_dir'] = 1
                boss_x += boss_info['move_dir'] * boss_speed
                margin = 40
                if boss_x < boss_radius + margin:
                    boss_x = boss_radius + margin
                    boss_info['move_dir'] = 1
                elif boss_x > WIDTH - boss_radius - margin:
                    boss_x = WIDTH - boss_radius - margin
                    boss_info['move_dir'] = -1

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

            # 共有ステート更新 (初期化漏れガード)
            if 'beam_shared_state' not in boss_info:
                boss_info['beam_shared_state'] = 'idle'
            if 'beam_shared_timer' not in boss_info:
                boss_info['beam_shared_timer'] = 0
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
            if shared == 'idle' and boss_info.get('beam_shared_timer',0) >= OVAL_BEAM_INTERVAL:
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
                if boss_info.get('beam_shared_timer',0) >= boss_info['left_beam']['cooldown']:
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
                boss_info['core_gap_target'] = OVAL_CORE_GAP_TARGET
                boss_info['core_cycle_interval'] = OVAL_CORE_CYCLE_INTERVAL
                boss_info['core_firing_duration'] = OVAL_CORE_FIRING_DURATION
                boss_info['core_open_hold'] = OVAL_CORE_OPEN_HOLD
            cs = boss_info['core_state']
            boss_info['core_timer'] += 1
            gap = boss_info.get('core_gap',0)
            # 状態遷移
            if cs == 'closed':
                if boss_info['core_timer'] >= boss_info['core_cycle_interval']:
                    boss_info['core_state'] = 'opening'
                    boss_info['core_timer'] = 0
            elif cs == 'opening':
                gap += OVAL_CORE_GAP_STEP
                if gap >= boss_info['core_gap_target']:
                    gap = boss_info['core_gap_target']
                    boss_info['core_state'] = 'firing'
                    boss_info['core_timer'] = 0
                boss_info['core_gap'] = gap
            elif cs == 'firing':
                # 一定間隔で拡散弾リング
                if boss_info['core_timer'] % 12 == 1:  # 12 も後で定数化候補
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
                gap -= OVAL_CORE_GAP_STEP
                if gap <= 0:
                    gap = 0
                    boss_info['core_state'] = 'closed'
                    boss_info['core_timer'] = 0
                boss_info['core_gap'] = gap
            # gap を保持
            boss_info['core_gap'] = gap

            # （オリジンへの補正戻しなし＝回転しつつ周期的に狙う）

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
            # プレイヤー中心が三日月領域に入ったらダメージ
            bx = player.centerx; by = player.centery
            dx = bx - boss_x; dy = by - boss_y
            r2 = dx*dx + dy*dy
            outer_r = boss_radius
            inner_r = int(boss_radius * 0.75)
            offset = int(boss_radius * 0.45)
            ix = boss_x - offset; iy = boss_y
            inside_outer = r2 <= (outer_r + max(player.width, player.height)//2)**2
            inside_inner = (bx - ix)**2 + (by - iy)**2 <= (inner_r - max(player.width, player.height)//2)**2
            if inside_outer and not inside_inner:
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

    


