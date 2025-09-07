import pygame
import sys
import random
import math
EXPLOSION_DURATION = 30  # 爆発表示時間
BOSS_EXPLOSION_DURATION = 60  # 派手な爆発演出
PLAYER_INVINCIBLE_DURATION = 120  # 2秒間無敵
BOSS_ATTACK_INTERVAL = 180  # 3秒ごとに攻撃

pygame.init()

WIDTH, HEIGHT = 480, 640
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("シューティングゲーム")

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (180, 180, 180)
RED = (255, 0, 0)

# ボス選択メニュー
boss_list = [
    {"name": "Boss A", "radius": 60, "hp": 35, "color": RED},
    {"name": "蛇", "radius": 70, "hp": 80, "color": (128, 0, 128)},  # ボス2（紫）
    {"name": "楕円ボス", "radius": 50, "hp": 50, "color": (255, 165, 0)}  # 楕円ボス（オレンジ）
]
selected_boss = 0

# レベル選択メニュー
level_list = [
    {"level": 10, "boss": None},
    {"level": 1, "boss": boss_list[0]},
    {"level": 2, "boss": boss_list[1]},  # レベル2にボス2を割り当て
    {"level": 3, "boss": boss_list[2]},
    {"level": 4, "boss": None},
    {"level": 5, "boss": None},
    {"level": 6, "boss": None},
    {"level": 7, "boss": None},
    {"level": 8, "boss": None},
    {"level": 9, "boss": None},
]
selected_level = 1
menu_mode = True

# 星マーク管理
level_cleared = [False] * 10


def draw_menu():
    screen.fill(BLACK)
    font = pygame.font.SysFont(None, 60)
    title = font.render("LEVEL SELECT", True, WHITE)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 60))
    font2 = pygame.font.SysFont(None, 40)
    # レベル10（最上部、赤色）
    level10_color = RED if selected_level == 0 else (180, 50, 50)
    level10 = font2.render("LEVEL 10", True, level10_color)
    x10 = WIDTH // 2 - level10.get_width() // 2
    y10 = 130
    screen.blit(level10, (x10, y10))
    if level_cleared[0]:
        star = font2.render("★", True, (255, 215, 0))
        screen.blit(star, (x10 + level10.get_width() + 10, y10))
    # レベル9〜1（下から上に並べる）
    for i in range(9, 0, -1):
        color = WHITE if selected_level == i else GRAY
        level_text = font2.render(f"LEVEL {i}", True, color)
        y = 180 + (9 - i) * 45
        x = WIDTH // 2 - level_text.get_width() // 2
        screen.blit(level_text, (x, y))
        if level_cleared[i]:
            star = font2.render("★", True, (255, 215, 0))
            screen.blit(star, (x + level_text.get_width() + 10, y))
    # 操作方法説明
    font3 = pygame.font.SysFont(None, 24)
    op1 = font3.render("[Arrow keys] Select Level", True, WHITE)
    op2 = font3.render("[Enter] Confirm", True, WHITE)
    screen.blit(op1, (WIDTH // 2 - op1.get_width() // 2, HEIGHT - 70))
    screen.blit(op2, (WIDTH // 2 - op2.get_width() // 2, HEIGHT - 40))
    pygame.display.flip()


def draw_end_menu(result, reward_text=None):
    screen.fill(BLACK)
    font = pygame.font.SysFont(None, 60)
    if result == "win":
        text = font.render("GAME CLEAR!", True, (0, 255, 0))
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 80))
        screen.blit(text, text_rect)
    else:
        text = font.render("GAME OVER", True, RED)
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60))
        screen.blit(text, text_rect)
    if reward_text:
        font_reward = pygame.font.SysFont(None, 32)
        reward = font_reward.render(reward_text, True, (0, 255, 0))
        reward_rect = reward.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 30))
        screen.blit(reward, reward_rect)
    font2 = pygame.font.SysFont(None, 40)
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
                        has_homing = False
                        bullet_type = "normal"  # normal or homing
                        has_leaf_shield = False
                        leaf_angle = 0.0
                        boss_x = WIDTH // 2
                        boss_y = 60
                        boss_alive = True
                        boss_speed = 4
                        boss_dir = 1
                        boss_state = "track"
                        if boss_info and boss_info["name"] == "楕円ボス":
                            boss_origin_x = boss_x
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
        font = pygame.font.SysFont(None, 50)
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
    boss_attack_timer = 0
    boss_origin_x = boss_x
    boss_origin_y = boss_y
    boss_hp = boss_info["hp"] if boss_info else 35
    retry = False
    continue
    if not boss_alive and boss_explosion_timer == 1:
        # ボス1を倒した場合のみ報酬
        if boss_info and boss_info["name"] == "Boss A":
            has_homing = True
            bullet_type = "normal"
        # ボス2（蛇）討伐報酬：リーフシールド
        if boss_info and boss_info["name"] == "蛇":
            has_leaf_shield = True

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
    bullets = [b for b in bullets if b["rect"].bottom > 0]

    # 弾とボスの当たり判定（整理後）
    if boss_alive and boss_info:
        cleaned_bullets = []
        for bullet in bullets:
            hit_or_reflected = False
            # 楕円ボス: 反射判定のみ（ダメージは与えない）
            if boss_info["name"] == "楕円ボス":
                cx, cy = boss_x, boss_y
                # 中央縦楕円
                if ((bullet["rect"].centerx - cx)**2)/(30**2) + ((bullet["rect"].centery - cy)**2)/(50**2) < 1:
                    bullet["reflect"] = True
                    bullet["vy"] = abs(bullet.get("vy", -7))
                    bullet["vx"] = random.randint(-3, 3)
                    hit_or_reflected = True
                else:
                    # 左右小楕円
                    for ox in (-60, 60):
                        ex = boss_x + ox - (20 if ox>0 else -20)
                        ey = boss_y
                        if ((bullet["rect"].centerx - ex)**2)/(20**2) + ((bullet["rect"].centery - ey)**2)/(30**2) < 1:
                            bullet["reflect"] = True
                            bullet["vy"] = abs(bullet.get("vy", -7))
                            bullet["vx"] = random.randint(-3, 3)
                            hit_or_reflected = True
                            break
            elif boss_info["name"] == "蛇":
                # 本体（正方形）はダメージ対象
                main_size = int(boss_radius * 1.2)
                main_rect = pygame.Rect(boss_x - main_size//2, boss_y - main_size//2, main_size, main_size)
                if main_rect.colliderect(bullet["rect"]):
                    boss_hp -= bullet.get("power", 1.0)
                    boss_explosion_pos.append((bullet["rect"].centerx, bullet["rect"].centery))
                    if boss_hp <= 0:
                        boss_alive = False
                        boss_explosion_timer = 0
                        explosion_pos = (boss_x, boss_y)
                    hit_or_reflected = True  # 弾削除
                else:
                    # 回転体節は反射
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
                            hit_or_reflected = True
                            break
            else:
                # 通常ボス: 円形判定（半径 boss_radius）
                dx = bullet["rect"].centerx - boss_x
                dy = bullet["rect"].centery - boss_y
                if dx*dx + dy*dy < boss_radius*boss_radius:
                    boss_hp -= bullet.get("power", 1.0)
                    boss_explosion_pos.append((bullet["rect"].centerx, bullet["rect"].centery))
                    if boss_hp <= 0:
                        boss_alive = False
                        boss_explosion_timer = 0
                        explosion_pos = (boss_x, boss_y)
                    hit_or_reflected = True
            # 処理後の弾リスト再構築（反射した弾は残し、ヒットした弾は除去）
            if not hit_or_reflected or bullet.get("reflect"):
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
         # ここに楕円ボスの移動ロジックを追加
        if boss_info and boss_info["name"] == "楕円ボス":
            if 'move_dir' not in boss_info:
                boss_info['move_dir'] = 1
            boss_x += boss_info['move_dir'] * boss_speed
            # 楕円ボスの移動ロジック（毎フレーム必ず実行）
            if boss_info and boss_info["name"] == "楕円ボス":
                if 'move_dir' not in boss_info:
                    boss_info['move_dir'] = 1
                boss_x += boss_info['move_dir'] * boss_speed
                if boss_x < boss_radius + 40:
                    boss_x = boss_radius + 40
                    boss_info['move_dir'] = 1
                elif boss_x > WIDTH - boss_radius - 40:
                    boss_x = WIDTH - boss_radius - 40
                    boss_info['move_dir'] = -1
                # 左右ビーム攻撃用の状態管理
                if 'beam_left_timer' not in boss_info:
                    boss_info['beam_left_timer'] = 0
                    boss_info['beam_left_active'] = False
                    boss_info['beam_left_target'] = None
                    boss_info['beam_left_delay'] = 0
                if 'beam_right_timer' not in boss_info:
                    boss_info['beam_right_timer'] = 0
                    boss_info['beam_right_active'] = False
                    boss_info['beam_right_target'] = None
                    boss_info['beam_right_delay'] = 0
                # 左ビーム攻撃（120フレームごとに座標記録、30フレーム遅延後発射、60フレーム表示）
                boss_info['beam_left_timer'] += 1
                if not boss_info['beam_left_active'] and boss_info['beam_left_timer'] > 120:
                    boss_info['beam_left_active'] = True
                    boss_info['beam_left_timer'] = 0
                    boss_info['beam_left_target'] = (player.centerx, player.centery)
                    boss_info['beam_left_delay'] = 0
                if boss_info['beam_left_active']:
                    boss_info['beam_left_delay'] += 1
                    if boss_info['beam_left_delay'] == 30:
                        boss_info['beam_left_show'] = True
                        boss_info['beam_left_show_timer'] = 0
                    if boss_info.get('beam_left_show'):
                        boss_info['beam_left_show_timer'] += 1
                        if boss_info['beam_left_show_timer'] > 60:
                            boss_info['beam_left_active'] = False
                            boss_info['beam_left_delay'] = 0
                            boss_info['beam_left_show'] = False
                # 右ビーム攻撃（180フレームごとに座標記録、30フレーム遅延後発射、60フレーム表示）
                boss_info['beam_right_timer'] += 1
                if not boss_info['beam_right_active'] and boss_info['beam_right_timer'] > 180:
                    boss_info['beam_right_active'] = True
                    boss_info['beam_right_timer'] = 0
                    boss_info['beam_right_target'] = (player.centerx, player.centery)
                    boss_info['beam_right_delay'] = 0
                if boss_info['beam_right_active']:
                    boss_info['beam_right_delay'] += 1
                    if boss_info['beam_right_delay'] == 30:
                        boss_info['beam_right_show'] = True
                        boss_info['beam_right_show_timer'] = 0
                    if boss_info.get('beam_right_show'):
                        boss_info['beam_right_show_timer'] += 1
                        if boss_info['beam_right_show_timer'] > 60:
                            boss_info['beam_right_active'] = False
                            boss_info['beam_right_delay'] = 0
                            boss_info['beam_right_show'] = False
                if boss_x > boss_origin_x:
                    boss_x -= 8
                    if boss_x < boss_origin_x:
                        boss_x = boss_origin_x
                elif boss_x < boss_origin_x:
                    boss_x += 8
                    if boss_x > boss_origin_x:
                        boss_x = boss_origin_x

    # プレイヤーとボスの当たり判定
    if boss_alive and not player_invincible:
        # 跳ね返り弾のみプレイヤー判定
        for bullet in bullets:
            if bullet.get("reflect", False):
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
        if result == "win" and boss_info and boss_info["name"] == "Boss A" and not level_cleared[selected_level]:
            reward_text = "Homing bullet unlocked!"
        # 星マーク
        if result == "win":
            level_cleared[selected_level] = True
        # 爆発表示（最後の爆発）
        for i in range(EXPLOSION_DURATION):
            screen.fill(BLACK)
            if explosion_pos:
                pygame.draw.circle(screen, RED, explosion_pos, 30)
            if result == "win":
                font = pygame.font.SysFont(None, 60)
                text = font.render("GAME CLEAR!", True, (0,255,0))
                text_rect = text.get_rect(center=(WIDTH//2, HEIGHT//2-80))
                screen.blit(text, text_rect)
            else:
                font = pygame.font.SysFont(None, 60)
                text = font.render("GAME OVER", True, RED)
                text_rect = text.get_rect(center=(WIDTH//2, HEIGHT//2-60))
                screen.blit(text, text_rect)
            if reward_text:
                font_reward = pygame.font.SysFont(None, 32)
                reward = font_reward.render(reward_text, True, (0,255,0))
                reward_rect = reward.get_rect(center=(WIDTH//2, HEIGHT//2-30))
                screen.blit(reward, reward_rect)
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
            leaf_angle += 0.03  # ゆっくり回転
            for i in range(2):
                angle = leaf_angle + math.pi * i
                leaf_radius = 40
                leaf_x = player.centerx + leaf_radius * math.cos(angle)
                leaf_y = player.centery + leaf_radius * math.sin(angle)
                pygame.draw.ellipse(screen, (0,200,0), (leaf_x-12, leaf_y-8, 24, 16))
    for bullet in bullets:
        # boss_beamは弾として描画しない
        if bullet["type"] != "boss_beam":
            color = WHITE if bullet["type"] == "normal" else (0,255,0)
            pygame.draw.rect(screen, color, bullet["rect"])

    # 楕円ボスのビーム（太い線）を描画
    if boss_alive and boss_info and boss_info["name"] == "楕円ボス":
        # 左ビーム
        if boss_info.get('beam_left_show') and boss_info.get('beam_left_target'):
            lx = boss_x - 60 + 20
            ly = boss_y
            tx, ty = boss_info['beam_left_target']
            pygame.draw.line(screen, (0,255,255), (lx, ly), (tx, ty), 12)
        # 右ビーム
        if boss_info.get('beam_right_show') and boss_info.get('beam_right_target'):
            rx = boss_x + 60 - 20
            ry = boss_y
            tx, ty = boss_info['beam_right_target']
            pygame.draw.line(screen, (0,255,255), (rx, ry), (tx, ty), 12)
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
            # 本体（大きい正方形）
            snake_color = (128, 0, 128)  # 紫色で明示
            if boss_alive:
                for bullet in bullets:
                    if boss_info:
                        # 楕円ボスの場合は中央・左右楕円で弾を反射
                        if boss_info["name"] == "楕円ボス":
                            cx, cy = boss_x, boss_y
                            if ((bullet["rect"].centerx - cx)**2) / (30**2) + ((bullet["rect"].centery - cy)**2) / (50**2) < 1:
                                bullet["reflect"] = True
                                bullet["vy"] = abs(bullet.get("vy", -7))
                                bullet["vx"] = random.randint(-3, 3)
                                continue
                            lx, ly = boss_x - 60 + 20, boss_y
                            if ((bullet["rect"].centerx - lx)**2) / (20**2) + ((bullet["rect"].centery - ly)**2) / (30**2) < 1:
                                bullet["reflect"] = True
                                bullet["vy"] = abs(bullet.get("vy", -7))
                                bullet["vx"] = random.randint(-3, 3)
                                continue
                            rx, ry = boss_x + 60 - 20, boss_y
                            if ((bullet["rect"].centerx - rx)**2) / (20**2) + ((bullet["rect"].centery - ry)**2) / (30**2) < 1:
                                bullet["reflect"] = True
                                bullet["vy"] = abs(bullet.get("vy", -7))
                                bullet["vx"] = random.randint(-3, 3)
                                continue
                        # 蛇ボスの場合は本体・体節で判定
                        elif boss_info["name"] == "蛇":
                            main_size = boss_radius * 1.2
                            main_rect = pygame.Rect(boss_x - int(main_size)//2, boss_y - int(main_size)//2, int(main_size), int(main_size))
                            if main_rect.colliderect(bullet["rect"]):
                                boss_hp -= bullet.get("power", 1.0)
                                boss_explosion_pos.append((bullet["rect"].centerx, bullet["rect"].centery))
                                bullets.remove(bullet)
                                if boss_hp <= 0:
                                    boss_alive = False
                                    boss_explosion_timer = 0
                                    explosion_pos = (boss_x, boss_y)
                                break
                            ROTATE_SEGMENTS_NUM = 5
                            ROTATE_RADIUS = boss_radius + 30
                            rotate_angle_local = globals().get("rotate_angle", 0.0)
                            for i in range(ROTATE_SEGMENTS_NUM):
                                angle = rotate_angle_local + (2 * math.pi * i / ROTATE_SEGMENTS_NUM)
                                seg_x = boss_x + ROTATE_RADIUS * math.cos(angle)
                                seg_y = boss_y + ROTATE_RADIUS * math.sin(angle)
                                seg_rect = pygame.Rect(int(seg_x-20), int(seg_y-20), 40, 40)
                                if seg_rect.colliderect(bullet["rect"]):
                                    bullet["reflect"] = True
                                    bullet["vy"] = abs(bullet.get("vy", -7))
                                    bullet["vx"] = random.randint(-3, 3)
                                    break
                        # 通常ボス
                        else:
                            dx = bullet["rect"].centerx - boss_x
                            dy = bullet["rect"].centery - boss_y
                            if dx*dx + dy*dy < boss_radius**2:
                                boss_hp -= bullet.get("power", 1.0)
                                boss_explosion_pos.append((bullet["rect"].centerx, bullet["rect"].centery))
                                bullets.remove(bullet)
                                if boss_hp <= 0:
                                    boss_alive = False
                                    boss_explosion_timer = 0
                                    explosion_pos = (boss_x, boss_y)
                                break
                        dist = max(1, (dx**2 + dy**2)**0.5)
                        vx = int(8 * dx / dist)
                        vy = int(8 * dy / dist)
                        bullets.append({
                            "rect": pygame.Rect(int(rx)-4, int(ry)-4, 8, 8),
                            "type": "boss_beam",
                            "power": 1.0,
                            "vx": vx,
                            "vy": vy,
                            "reflect": False
                        })
                    if boss_info['beam_right_timer'] > 60:
                        boss_info['beam_right_active'] = False
                        boss_info['beam_right_timer'] = 0
            rotate_angle_local = globals().get("rotate_angle", 0.0)
            for i in range(ROTATE_SEGMENTS_NUM):
                angle = rotate_angle_local + (2 * math.pi * i / ROTATE_SEGMENTS_NUM)
                seg_x = boss_x + ROTATE_RADIUS * math.cos(angle)
                seg_y = boss_y + ROTATE_RADIUS * math.sin(angle)
                seg_rect = pygame.Rect(int(seg_x-20), int(seg_y-20), 40, 40)
                pygame.draw.rect(screen, (180, 0, 180), seg_rect)
        elif boss_info and boss_info["name"] == "楕円ボス":
            # 本体（縦楕円）
            main_rect = pygame.Rect(boss_x - boss_radius//2, boss_y - boss_radius, boss_radius, boss_radius*2)
            pygame.draw.ellipse(screen, boss_color, main_rect)
            # 左右の小楕円
            small_w, small_h = boss_radius//2, boss_radius*2//3
            left_rect = pygame.Rect(boss_x - boss_radius - small_w//2, boss_y - small_h//2, small_w, small_h)
            right_rect = pygame.Rect(boss_x + boss_radius - small_w//2, boss_y - small_h//2, small_w, small_h)
            pygame.draw.ellipse(screen, (0,255,0), left_rect)
            pygame.draw.ellipse(screen, (0,255,0), right_rect)
        # ボスへの小爆発
        for pos in boss_explosion_pos:
            pygame.draw.circle(screen, (255,255,0), pos, 15)
        # 小爆発は一瞬だけ表示
        if boss_explosion_pos:
            boss_explosion_pos = []
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
        font = pygame.font.SysFont(None, 60)
        text = font.render("GAME CLEAR!", True, (0,255,0))
        text_rect = text.get_rect(center=(WIDTH//2, HEIGHT//2))
        screen.blit(text, text_rect)
        pygame.display.flip()
        pygame.time.wait(2000)
        # リトライ待ち
        font = pygame.font.SysFont(None, 40)
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
    font = pygame.font.SysFont(None, 30)
    lives_text = f"Lives: {player_lives}"
    text_surf = font.render(lives_text, True, WHITE)
    text_rect = text_surf.get_rect(bottomright=(WIDTH-10, HEIGHT-10))
    screen.blit(text_surf, text_rect)
    # 弾種表示
    font = pygame.font.SysFont(None, 24)
    if has_homing:
        bullet_text = f"Bullet: {'Homing' if bullet_type == 'homing' else 'Normal'} (V to switch)"
        text_surf = font.render(bullet_text, True, (0,255,0) if bullet_type == "homing" else WHITE)
        screen.blit(text_surf, (20, HEIGHT-40))

    pygame.display.flip()
    clock.tick(60)


