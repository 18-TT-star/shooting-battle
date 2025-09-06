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
    {"name": "Boss B", "radius": 60, "hp": 60, "color": (0, 0, 255)},
    {"name": "Boss C", "radius": 30, "hp": 20, "color": (0, 255, 0)},
    {"name": "蛇", "radius": 70, "hp": 80, "color": (128, 0, 128)}  # ボス2（紫）
]
selected_boss = 0

# レベル選択メニュー
level_list = [
    {"level": 10, "boss": None},
    {"level": 1, "boss": boss_list[0]},
    {"level": 2, "boss": boss_list[3]},  # レベル2にボス2を割り当て
    {"level": 3, "boss": None},
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
while True:
    if menu_mode:
        draw_menu()
        for event in pygame.event.get():
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
                        boss_x = WIDTH // 2
                        boss_y = 60
                        boss_alive = True
                        boss_speed = 4
                        boss_dir = 1
                        boss_state = "track"
                        boss_attack_timer = 0
                        boss_origin_x = boss_x
                        boss_origin_y = boss_y
                        player_lives = 3
                        player_invincible = False
                        player_invincible_timer = 0
                        explosion_timer = 0
                        explosion_pos = None
                        bullets = []
                        boss_explosion_timer = 0
                        boss_explosion_pos = []
                        retry = False
                        player = pygame.Rect(
    WIDTH // 2 - 15, HEIGHT - 40, 30, 15)
                        player_speed = 5
                        bullet_speed = 7
                        menu_mode = False
                        waiting_for_space = True
        continue

    if waiting_for_space:
        screen.fill(BLACK)
        font = pygame.font.SysFont(None, 50)
        text = font.render("Press SPACE to start!", True, WHITE)
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(text, text_rect)
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    # 弾にvelocity情報を追加（初期は上方向）
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
        # 初期化
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
        boss_hp = 35
        retry = False

    # ボス撃破時の報酬
    if not boss_alive and boss_explosion_timer == 1:
        # ボス1を倒した場合のみ報酬
        if boss_info and boss_info["name"] == "Boss A":
            has_homing = True
            bullet_type = "normal"

    # 弾発射
    for event in pygame.event.get():
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

    # 弾とボスの当たり判定
    if boss_alive:
        for bullet in bullets:
            # 蛇ボス（名前: "蛇"）の特殊判定
            if boss_info and boss_info["name"] == "蛇":
                import math
                import random
                main_size = boss_radius * 0.8
                main_rect = pygame.Rect(
    boss_x - int(main_size) // 2,
    boss_y - int(main_size) // 2,
    int(main_size),
     int(main_size))
                # 大きい四角形に当たった場合は反射
                if main_rect.colliderect(bullet["rect"]):
                    bullet["vy"] = int(bullet_speed * 0.7)
                    bullet["vx"] = int(
                        bullet_speed * random.uniform(-0.7, 0.7))
                    bullet["reflect"] = True
                    if bullet["rect"].top > HEIGHT or bullet["rect"].left < 0 or bullet["rect"].right > WIDTH:
                        bullets.remove(bullet)
                    continue
                # 体節（小さい四角形）に当たった場合のみダメージ
                small_size = boss_radius // 2
                hit = False
                for seg in snake_segments:
                    snake_shrink_path = []
                    if seg_rect.colliderect(bullet["rect"]):
                        boss_hp -= bullet["power"]
                        boss_explosion_pos.append(
    (bullet["rect"].centerx, bullet["rect"].centery))
                        bullets.remove(bullet)
                        hit = True
                        if boss_hp <= 0:
                            boss_alive = False
                            boss_explosion_timer = 0
                        break
                if hit:
                    break
            else:
                dx = bullet["rect"].centerx - boss_x
                dy = bullet["rect"].centery - boss_y
                if dx * dx + dy * dy < boss_radius * boss_radius:
                    boss_hp -= bullet["power"]
                    boss_explosion_pos.append(
    (bullet["rect"].centerx, bullet["rect"].centery))
                    bullets.remove(bullet)
                    if boss_hp <= 0:
                        boss_alive = False
                        boss_explosion_timer = 0
                    break
    # ボス撃破後の爆発演出
    if not boss_alive and boss_explosion_timer < BOSS_EXPLOSION_DURATION:
        boss_explosion_timer += 1

    # ボスキャラの攻撃パターン
    if boss_alive:
        boss_attack_timer += 1
        # 蛇ボスの状態管理
        if boss_info and boss_info["name"] == "蛇":
            # 攻撃サイクル管理
            snake_attack_timer += 1
            # 攻撃終了後3秒待機
            if snake_state == "normal" and snake_attack_timer > 180:
                snake_state = "grow"
                snake_attack_timer = 0
                snake_segments = []
                snake_tail_pos = None
                snake_target_edge = None
                snake_attack_y = None
                snake_cross_progress = 0
                boss_origin_x = boss_x
                boss_origin_y = 20
            # 通常時はプレイヤー追尾
            if snake_state == "normal":
                if boss_x < player.centerx:
                    boss_x += boss_speed
                    if boss_x > player.centerx:
                        boss_x = player.centerx
                elif boss_x > player.centerx:
                    boss_x -= boss_speed
                    if boss_x < player.centerx:
                        boss_x = player.centerx
                boss_x = max(boss_radius, min(WIDTH - boss_radius, boss_x))
                # しっぽはサイン波でくねくね
                # くねくね描画用snake_segmentsのみ生成（shrink用リストは上書きしない）
                main_size = boss_radius * 0.8
                small_size = boss_radius // 2
                base_x, base_y = boss_x, boss_y - main_size // 2 + 30
                snake_segments = []
                for i in range(1, 6):
                    wave = math.sin(pygame.time.get_ticks() / 200.0 + i) * (10 + i * 3)
                    seg_x = base_x + wave
                    seg_y = base_y - i * (small_size + 8)
                    snake_segments.append([seg_x, seg_y])
            elif snake_state == "shrink":
                # 収縮: snake_shrink_pathに沿って本体が戻る
                global snake_shrink_index
                # 戻る速度調整用カウンタ
                global shrink_speed_counter
                if 'shrink_speed_counter' not in globals():
                    shrink_speed_counter = 0
                if snake_shrink_path and snake_shrink_index < len(snake_shrink_path):
                    boss_x, boss_y = snake_shrink_path[-(snake_shrink_index+1)]
                    shrink_speed_counter += 1
                    if 'shrink_interval' not in globals():
                        shrink_interval = max(1, int(120 / len(snake_shrink_path)))
                    if shrink_speed_counter >= shrink_interval:
                        snake_shrink_index += 1
                        shrink_speed_counter = 0
                else:
                    # しっぽ端まで戻ったら通常状態へ
                    boss_x = boss_origin_x
                    boss_y = boss_origin_y
                    snake_state = "normal"
                    snake_attack_timer = 0
                    boss_state = "up"
                    shrink_speed_counter = 0
        # grow: しっぽ端固定、本体が端まで移動し体節生成
            elif snake_state == "grow":
                # grow開始時のみ体節生成
                if not snake_segments:
                    snake_tail_pos = [boss_x, boss_y]
                    snake_segments.append(snake_tail_pos)
                    if player.centerx < WIDTH // 2:
                        snake_target_edge = boss_radius
                    else:
                        snake_target_edge = WIDTH - boss_radius
                    snake_attack_y = boss_y
                    snake_shrink_path = [snake_tail_pos[:]]
                # 本体は端座標に完全到達するまで移動
                if boss_x < snake_target_edge:
                    boss_x += boss_speed
                    if boss_x > snake_target_edge:
                        boss_x = snake_target_edge
                elif boss_x > snake_target_edge:
                    boss_x -= boss_speed
                    if boss_x < snake_target_edge:
                        boss_x = snake_target_edge
                boss_y = snake_attack_y
                # しっぽ端から本体まで体節が連なるように線形補間
                snake_segments = [snake_tail_pos[:]]
                steps = max(2, min(5, 8))
                for i in range(1, steps + 1):
                    t = i / steps
                    seg_x = snake_tail_pos[0] + (boss_x - snake_tail_pos[0]) * t
                    seg_y = snake_attack_y + (boss_y - snake_attack_y) * t
                    snake_segments.append([seg_x, seg_y])
                    snake_shrink_path.append([seg_x, seg_y])
                if boss_x == snake_target_edge:
                    snake_state = "edge_move"
            # edge_move: 端に沿ってプレイヤーのy座標まで移動
            elif snake_state == "edge_move":
                # y座標がプレイヤーに到達するまで移動
                if boss_y < player.centery:
                    boss_y += boss_speed
                    if boss_y > player.centery:
                        boss_y = player.centery
                elif boss_y > player.centery:
                    boss_y -= boss_speed
                    if boss_y < player.centery:
                        boss_y = player.centery
                # x座標は端に固定
                boss_x = snake_target_edge
                # 毎フレーム体節座標を追加（前回追加座標と十分離れている場合のみ）
                min_dist = 18
                if not snake_segments:
                    snake_segments.append([snake_tail_pos[0], snake_tail_pos[1]])
                last_seg = snake_segments[-1]
                # x方向（端まで）
                if abs(last_seg[0] - boss_x) > min_dist or abs(last_seg[1] - boss_y) > min_dist:
                    snake_segments.append([boss_x, boss_y])
                if boss_y == player.centery:
                    snake_state = "cross"
                    snake_cross_progress = 0
            # cross: 端から反対側へ向かって移動（4分の3程度進む）
            elif snake_state == "cross":
                cross_target_x = WIDTH - boss_radius if snake_target_edge == boss_radius else boss_radius
                cross_distance = abs(cross_target_x - boss_x)
                cross_step = boss_speed
                if boss_x < cross_target_x:
                    boss_x += cross_step
                    if boss_x > cross_target_x:
                        boss_x = cross_target_x
                elif boss_x > cross_target_x:
                    boss_x -= cross_step
                    if boss_x < cross_target_x:
                        boss_x = cross_target_x
                # 毎フレーム体節座標を追加（前回追加座標と十分離れている場合のみ）
                min_dist = 18
                if not snake_segments:
                    snake_segments.append([boss_x, boss_y])
                last_seg = snake_segments[-1]
                if abs(last_seg[0] - boss_x) > min_dist or abs(last_seg[1] - boss_y) > min_dist:
                    snake_segments.append([boss_x, boss_y])
                # 4分の3進んだら収縮
                snake_cross_progress += cross_step
                if snake_cross_progress > cross_distance * 0.9:
                    print(f"[DEBUG] shrink開始: snake_shrink_pathの長さ={len(snake_segments)}")
                    # shrink開始時に体節座標リストを保存
                    snake_shrink_path = list(snake_segments)
                    snake_state = "shrink"
                    snake_shrink_timer = 0
                    snake_shrink_index = 0
                    shrink_speed_counter = 0
                # 完全に元の位置に戻ったら通常状態へ
                if boss_x == cross_target_x:
                    snake_state = "normal"
                    snake_attack_timer = 0
                    boss_state = "up"
        else:
            # 通常ボスの移動ロジック
            if boss_state == "track":
                # 追尾
                if boss_attack_timer >= BOSS_ATTACK_INTERVAL:
                    boss_state = "up"
                    boss_attack_timer = 0
                    boss_origin_x = boss_x
                    boss_origin_y = boss_y
                else:
                    if boss_x < player.centerx:
                        boss_x += boss_speed
                        if boss_x > player.centerx:
                            boss_x = player.centerx
                    elif boss_x > player.centerx:
                        boss_x -= boss_speed
                        if boss_x < player.centerx:
                            boss_x = player.centerx
                    boss_x = max(boss_radius, min(WIDTH - boss_radius, boss_x))
            elif boss_state == "up":
                # 少し上に移動
                boss_y -= 6
                if boss_y <= 20:
                    boss_y = 20
                    boss_state = "dive"
                    boss_dive_follow_frames = 20  # 20フレームだけ追尾
                    boss_dive_frame = 0
                    # 蛇ボスの場合はここでsnake_stateをnormalに戻す
                    if boss_info and boss_info["name"] == "蛇":
                        snake_state = "normal"
            elif boss_state == "dive":
                # dive中は最初の20フレームだけ追尾
                if 'boss_dive_frame' in locals() and boss_dive_frame < boss_dive_follow_frames:
                    if boss_x < player.centerx:
                        boss_x += boss_speed // 2
                        if boss_x > player.centerx:
                            boss_x = player.centerx
                    elif boss_x > player.centerx:
                        boss_x -= boss_speed // 2
                        if boss_x < player.centerx:
                            boss_x = player.centerx
                    boss_x = max(boss_radius, min(WIDTH - boss_radius, boss_x))
                    boss_dive_frame += 1
                boss_y += 16
                # プレイヤーのy座標付近まで降りる
                if boss_y >= player.centery:
                    boss_state = "return"
                    if 'boss_dive_frame' in locals():
                        del boss_dive_frame
                        del boss_dive_follow_frames
            elif boss_state == "return":
                # 元の位置に戻る
                if boss_y > boss_origin_y:
                    boss_y -= 8
                    if boss_y < boss_origin_y:
                        boss_y = boss_origin_y
                else:
                    boss_y = boss_origin_y
                    boss_state = "track"
                    boss_attack_timer = 0
                # x座標も元の位置に戻す
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
    for bullet in bullets:
        color = WHITE if bullet["type"] == "normal" else (0,255,0)
        pygame.draw.rect(screen, color, bullet["rect"])
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
        # 蛇ボス: 体節描画
        elif boss_info and boss_info["name"] == "蛇":
            main_size = boss_radius * 0.8
            main_rect = pygame.Rect(boss_x - int(main_size)//2, boss_y - int(main_size)//2, int(main_size), int(main_size))
            pygame.draw.rect(screen, boss_color, main_rect)
            small_size = boss_radius // 2
            # 体節（小さい四角形）描画
            for seg in snake_segments:
                seg_rect = pygame.Rect(seg[0] - small_size//2, seg[1] - small_size//2, small_size, small_size)
                pygame.draw.rect(screen, boss_color, seg_rect)
        else:
            pygame.draw.circle(screen, boss_color, (boss_x, boss_y), boss_radius)
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


