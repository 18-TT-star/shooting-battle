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
    {"name": "Boss C", "radius": 30, "hp": 20, "color": (0, 255, 0)}
]
selected_boss = 0
menu_mode = True

def draw_menu():
    screen.fill(BLACK)
    font = pygame.font.SysFont(None, 60)
    title = font.render("BOSS SELECT", True, WHITE)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
    font2 = pygame.font.SysFont(None, 40)
    for i, boss in enumerate(boss_list):
        color = boss["color"] if i == selected_boss else GRAY
        text = font2.render(boss["name"], True, color)
        x = WIDTH//2 - text.get_width()//2
        y = 220 + i*60
        screen.blit(text, (x, y))
    font3 = pygame.font.SysFont(None, 30)
    info = font3.render("Use ↑↓ to select, Enter to start", True, WHITE)
    screen.blit(info, (WIDTH//2 - info.get_width()//2, HEIGHT-80))
    pygame.display.flip()

# ゲームループ
clock = pygame.time.Clock()

retry = False
while True:
    if menu_mode:
        draw_menu()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected_boss = (selected_boss - 1) % len(boss_list)
                if event.key == pygame.K_DOWN:
                    selected_boss = (selected_boss + 1) % len(boss_list)
                if event.key == pygame.K_RETURN:
                    # 選択したボスでゲーム開始
                    boss_radius = boss_list[selected_boss]["radius"]
                    boss_hp = boss_list[selected_boss]["hp"]
                    boss_color = boss_list[selected_boss]["color"]
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
                    # プレイヤー初期化
                    player = pygame.Rect(WIDTH//2 - 15, HEIGHT - 40, 30, 15)
                    player_speed = 5
                    bullet_speed = 7
                    menu_mode = False
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

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        # 弾発射
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                bullets.append(pygame.Rect(player.centerx - 3, player.top - 6, 6, 12))

    # 自機移動
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT] and player.left > 0:
        player.x -= player_speed
    if keys[pygame.K_RIGHT] and player.right < screen.get_width():
        player.x += player_speed

    # 弾の移動
    for bullet in bullets:
        bullet.y -= bullet_speed
    bullets = [b for b in bullets if b.bottom > 0]

    # 弾とボスの当たり判定（耐久力35）
    if boss_alive:
        for bullet in bullets:
            dx = bullet.centerx - boss_x
            dy = bullet.centery - boss_y
            if dx*dx + dy*dy < boss_radius*boss_radius:
                boss_hp -= 1
                boss_explosion_pos.append((bullet.centerx, bullet.centery))  # 小爆発位置
                if bullet in bullets:
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
                boss_state = "dive"
        elif boss_state == "dive":
            # 急降下
            boss_y += 16
            # プレイヤーのy座標付近まで降りる
            if boss_y >= player.centery:
                boss_state = "return"
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

    # ゲームオーバー判定
    if player_lives <= 0:
        # 爆発表示（最後の爆発）
        for i in range(EXPLOSION_DURATION):
            screen.fill(BLACK)
            if explosion_pos:
                pygame.draw.circle(screen, RED, explosion_pos, 30)
            font = pygame.font.SysFont(None, 60)
            text = font.render("GAME OVER", True, RED)
            text_rect = text.get_rect(center=(WIDTH//2, HEIGHT//2))
            screen.blit(text, text_rect)
            pygame.display.flip()
            pygame.time.wait(20)
        pygame.time.wait(1500)
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

    # 描画
    screen.fill(BLACK)
    # 爆発表示
    if explosion_timer < EXPLOSION_DURATION and explosion_pos:
        pygame.draw.circle(screen, RED, explosion_pos, 30)
    # プレイヤー（無敵時は半透明）
    if not player_invincible or (player_invincible_timer//10)%2 == 0:
        pygame.draw.rect(screen, WHITE, player)
    for bullet in bullets:
        pygame.draw.rect(screen, WHITE, bullet)
    # ボスキャラ
    if boss_alive:
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

    pygame.display.flip()
    clock.tick(60)


