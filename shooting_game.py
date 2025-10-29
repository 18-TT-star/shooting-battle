import sys, random, math, subprocess, copy, colorsys

# --- Auto-install required packages (pygame) at startup ---
try:
    import pygame
except ImportError:  # Install pygame automatically if missing
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame>=2.0.0"])
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
    boss_list, level_list, MAX_LEVEL,
    BOUNCE_BOSS_SPEED, BOUNCE_BOSS_RING_COUNT, BOUNCE_BOSS_NO_PATTERN_BOTTOM_MARGIN,
    BOUNCE_BOSS_SQUISH_DURATION, BOUNCE_BOSS_ANGLE_JITTER_DEG,
    BOUNCE_BOSS_SHRINK_STEP, BOUNCE_BOSS_SPEED_STEP,
    WINDOW_SHAKE_DURATION, WINDOW_SHAKE_INTENSITY,
    DASH_COOLDOWN_FRAMES, DASH_INVINCIBLE_FRAMES, DASH_DISTANCE,
    DASH_DOUBLE_TAP_WINDOW, DASH_ICON_SEGMENTS
)
from fonts import jp_font, text_surface
from gameplay import spawn_player_bullets, move_player_bullets, update_dash_timers, attempt_dash
from music import init_audio, play_enemy_hit, play_reflect, play_boss_clear_music, stop_music, play_shape_transform, play_bgm, fade_out_bgm, play_menu_beep, get_current_bgm

pygame.init()
if not pygame.font.get_init():
    pygame.font.init()

init_audio()
play_bgm()  # BGMをループ再生開始

DISPLAY_FLAGS = pygame.DOUBLEBUF  # RESIZABLEを削除してウィンドウサイズ固定
display_surface = pygame.display.set_mode((WIDTH, HEIGHT), DISPLAY_FLAGS)
screen = pygame.Surface((WIDTH, HEIGHT)).convert()
pygame.display.set_caption("Bob's Big Adventure")
is_fullscreen = False
fullscreen_unlocked = False  # フルスクリーン機能のアンロック状態
_border_starfield_cache = {}


def set_display_mode(fullscreen: bool):
    """Toggle between fullscreen and windowed modes while preserving surfaces."""
    global display_surface, is_fullscreen, fullscreen_unlocked
    # フルスクリーンがアンロックされていない場合は何もしない
    if fullscreen and not fullscreen_unlocked:
        return
    if fullscreen and not is_fullscreen:
        try:
            pygame.display.quit()
            pygame.display.init()
            display_surface = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.DOUBLEBUF)
            is_fullscreen = True
        except Exception:
            pygame.display.quit()
            pygame.display.init()
            display_surface = pygame.display.set_mode((WIDTH, HEIGHT), DISPLAY_FLAGS)
            is_fullscreen = False
    elif not fullscreen and is_fullscreen:
        pygame.display.quit()
        pygame.display.init()
        display_surface = pygame.display.set_mode((WIDTH, HEIGHT), DISPLAY_FLAGS)
        is_fullscreen = False
    else:
        flags = pygame.FULLSCREEN | pygame.DOUBLEBUF if fullscreen else DISPLAY_FLAGS
        display_surface = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        is_fullscreen = fullscreen
    pygame.display.set_caption("Bob's Big Adventure")


def get_border_starfield(width, height):
    """Return a cached starfield surface for letterboxed borders."""
    if width <= 0 or height <= 0:
        return None
    key = (int(width), int(height))
    cached = _border_starfield_cache.get(key)
    if cached:
        return cached
    surface = pygame.Surface(key)
    surface.fill((0, 0, 0))
    star_count = max(8, (key[0] * key[1]) // 1600)
    for _ in range(star_count):
        x = random.randrange(0, key[0])
        y = random.randrange(0, key[1])
        shade = random.randint(180, 255)
        surface.set_at((x, y), (shade, shade, shade))
    _border_starfield_cache[key] = surface
    return surface


def present_frame():
    if display_surface and display_surface is not screen:
        display_width, display_height = display_surface.get_size()
        scale = min(display_width / float(WIDTH), display_height / float(HEIGHT or 1))
        scaled_width = max(1, int(WIDTH * scale))
        scaled_height = max(1, int(HEIGHT * scale))
        scaled_surface = pygame.transform.smoothscale(screen, (scaled_width, scaled_height))
        offset_x = (display_width - scaled_width) // 2
        offset_y = (display_height - scaled_height) // 2
        display_surface.fill((0, 0, 0))
        if offset_x > 0:
            border_surface = get_border_starfield(offset_x, display_height)
            if border_surface:
                display_surface.blit(border_surface, (0, 0))
                display_surface.blit(border_surface, (display_width - offset_x, 0))
        if offset_y > 0:
            top_border = get_border_starfield(display_width, offset_y)
            bottom_border = get_border_starfield(display_width, offset_y)
            if top_border:
                display_surface.blit(top_border, (0, 0))
            if bottom_border:
                display_surface.blit(bottom_border, (0, display_height - offset_y))
        display_surface.blit(scaled_surface, (offset_x, offset_y))
        pygame.display.flip()
    else:
        pygame.display.flip()


try:
    from pygame._sdl2.video import Window as SDLWindow
except ImportError:  # SDL2 window manipulation is optional
    SDLWindow = None

_game_window = None
_window_base_pos = (0, 0)
if SDLWindow:
    try:
        _game_window = SDLWindow.from_display_module()
    except Exception:
        _game_window = None
if _game_window:
    try:
        _window_base_pos = _game_window.position
    except Exception:
        _window_base_pos = (0, 0)

_window_shake_timer = 0
_window_shake_intensity = 0
_window_warp_active = False
_window_warp_timer = 0
_window_warp_index = 0
_window_warp_interval = 150
_window_warp_vertices = []

# 三日月形ボス用 星座トレイル演出の調整値
BOSS5_TRAIL_INTERVAL_FRAMES = 28
BOSS5_TRAIL_TTL_RANGE = (70, 120)
BOSS5_TRAIL_MAX_PATTERNS = 20
BOSS5_TRAIL_RADIUS_RANGE = (24, 58)
BOSS5_TRAIL_EXTRA_LINK_CHANCE = 0.45
BOSS5_TRAIL_SPAWN_LIMIT = 1

# dash_state が存在しない環境でも NameError を避ける初期値
if 'dash_state' not in globals():
    dash_state = {'invincible_timer': 0, 'active': False}


def reset_boss_hazards_after_player_hit(boss_state):
    """Remove lingering boss-specific hazards when the player respawns."""
    if not boss_state:
        return
    if boss_state.get('name') == '赤バツボス':
        falls = boss_state.get('cross_falls')
        if falls:
            falls.clear()
        if boss_state.get('cross_wall_attack'):
            boss_state['cross_wall_attack'] = None
        state = boss_state.get('cross_phase2_state')
        beams = boss_state.get('cross_phase2_moon_beams')
        moons = boss_state.get('cross_phase2_moons')
        if state in ('moon_intro', 'moon_attack', 'moon_cleanup'):
            # プレイヤー被弾後も月レーザーを継続するためクリアしない
            pass
        starfield = boss_state.get('cross_phase3_starfield')
        if starfield:
            starfield.clear()
        background = boss_state.get('cross_phase3_background')
        if background:
            background.clear()
        boss_state['cross_phase3_overlay_alpha'] = 0
        boss_state['cross_phase3_wave_clock'] = 0
        boss_state['star_rain_active'] = False
    if boss_state.get('name') == '三日月形ボス':
        trails = boss_state.get('trail_constellations')
        if trails:
            trails.clear()
        boss_state['trail_spawn_timer'] = 0
        lasers = boss_state.get('side_lasers')
        if lasers:
            lasers.clear()
        boss_state['patt_state'] = 'idle'
        boss_state['patt_timer'] = 0
        boss_state['patt_cd'] = 0
        boss_state.pop('patt_choice', None)
    boss_state['idle_guard'] = 0
selected_level = 1  # 1..MAX_LEVEL を使用
title_mode = True  # タイトル画面モード
menu_mode = False  # レベル選択モード（タイトル後に移行）
level_cleared = [False]*7  # 0..6
boss6_phase2_checkpoint = False  # ボス6のphase2チェックポイント（リトライ用）

from ui import draw_menu, draw_end_menu, draw_title_screen

# （この下にゲームループ）

# --------- Utility: split ellipse drawing (for oval boss core opening) ---------
def draw_split_ellipse(surface, center_x, center_y, radius, gap, color):
    """Draw a vertical ellipse that opens sideways by separating left/right halves."""
    width = max(4, int(radius * 1.25))
    height = max(6, int(radius * 2.0))
    base = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(base, color, (0, 0, width, height))
    half_w = width // 2
    left_half = base.subsurface((0, 0, half_w, height))
    right_half = base.subsurface((half_w, 0, width - half_w, height))
    gap_offset = max(0, gap // 2)
    left_rect = left_half.get_rect(midright=(center_x - gap_offset, center_y))
    right_rect = right_half.get_rect(midleft=(center_x + gap_offset, center_y))
    surface.blit(left_half, left_rect)
    surface.blit(right_half, right_rect)

# --------- Staff roll & ending sequences ---------
STAFF_ROLL_ENTRIES = [
    ("ディレクター", "T.T"),
    ("ゲームデザイン", "T.T"),
    ("プログラミング", "No T.T"),
    ("サウンド", "No T.T"),
    ("グラフィック", "No T.T"),
    ("Special Thanks", "T.T")
]

BOSS_PORTRAITS = [
    {'shape': 'trapezoid', 'color': (255, 110, 110)},
    {'shape': 'core_cluster', 'color': (150, 80, 200)},
    {'shape': 'triple_oval', 'color': (255, 170, 80)},
    {'shape': 'bounce', 'color': (255, 200, 80)},
    {'shape': 'crescent', 'color': (200, 240, 255)},
    {'shape': 'cross', 'color': (255, 90, 90)},
    {'shape': 'rainbow_star', 'color': (255, 220, 120)}
]

def _draw_portrait_icon(surface, info):
    w, h = surface.get_size()
    cx, cy = w // 2, int(h * 0.44)
    color = info.get('color', (255, 255, 255))
    shape = info.get('shape', 'trapezoid')
    if shape == 'trapezoid':
        top_w = int(w * 0.45)
        bottom_w = int(w * 0.75)
        height = int(h * 0.5)
        top_y = cy - height // 2
        points = [
            (cx - top_w // 2, top_y),
            (cx + top_w // 2, top_y),
            (cx + bottom_w // 2, top_y + height),
            (cx - bottom_w // 2, top_y + height)
        ]
        pygame.draw.polygon(surface, color, points)
    elif shape == 'orb_chain':
        orb_r = max(6, int(min(w, h) * 0.18))
        spacing = orb_r * 1.5
        for i in range(-2, 3):
            oy = cy + int(i * spacing)
            pygame.draw.circle(surface, color, (cx, oy), orb_r)
        core = pygame.Rect(0, 0, orb_r * 3, orb_r * 3)
        core.center = (cx, cy)
        pygame.draw.ellipse(surface, (255, 200, 255), core)
    elif shape == 'core_cluster':
        base = pygame.Rect(0, 0, int(w * 0.55), int(h * 0.55))
        base.center = (cx, cy)
        pygame.draw.rect(surface, color, base, border_radius=14)
        small = max(8, int(min(w, h) * 0.18))
        offsets = [(-small * 1.6, -small * 1.6), (small * 1.6, -small * 1.6),
                   (-small * 1.6, small * 1.6), (small * 1.6, small * 1.6), (0, 0)]
        for ox, oy in offsets:
            rect = pygame.Rect(0, 0, small * 1.2, small * 1.2)
            rect.center = (cx + int(ox), cy + int(oy))
            pygame.draw.rect(surface, (200, 120, 240), rect, border_radius=6)
    elif shape == 'triple_oval':
        center_rect = pygame.Rect(0, 0, int(w * 0.38), int(h * 0.7))
        center_rect.center = (cx, cy)
        pygame.draw.ellipse(surface, (255, 160, 80), center_rect)
        side_rect = center_rect.inflate(-center_rect.width * 0.35, -center_rect.height * 0.15)
        side_rect.width = int(side_rect.width * 0.75)
        side_rect.height = int(side_rect.height * 0.9)
        left_rect = side_rect.copy(); left_rect.center = (cx - int(center_rect.width * 0.9), cy)
        right_rect = side_rect.copy(); right_rect.center = (cx + int(center_rect.width * 0.9), cy)
        for rect in (left_rect, right_rect):
            pygame.draw.ellipse(surface, (90, 200, 120), rect)
    elif shape == 'bounce':
        radius = int(min(w, h) * 0.32)
        pygame.draw.circle(surface, color, (cx, cy), radius)
        mask = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(mask, (0, 0, 0, 0), (radius, radius), radius)
        pygame.draw.circle(mask, (0, 0, 0, 255), (radius + radius // 2, radius), radius)
        surface.blit(mask, (cx - radius, cy - radius), special_flags=pygame.BLEND_RGBA_SUB)
    elif shape == 'cross':
        arm_w = int(w * 0.2)
        size = int(min(w, h) * 0.55)
        vert = pygame.Rect(0, 0, arm_w, size)
        vert.center = (cx, cy)
        pygame.draw.rect(surface, color, vert)
        horiz = pygame.Rect(0, 0, size, arm_w)
        horiz.center = (cx, cy)
        pygame.draw.rect(surface, color, horiz)
    elif shape == 'rainbow_star':
        size = int(min(w, h) * 0.9)
        striped = pygame.Surface((size, size), pygame.SRCALPHA)
        spectrum = [
            (255, 80, 80),
            (255, 150, 60),
            (255, 220, 90),
            (120, 240, 120),
            (100, 190, 255),
            (170, 120, 250)
        ]
        stripe_w = max(2, size // (len(spectrum) * 2))
        x = 0
        color_index = 0
        while x < size:
            col = spectrum[color_index % len(spectrum)]
            pygame.draw.rect(striped, col, (x, 0, stripe_w, size))
            x += stripe_w
            color_index += 1
        mask = pygame.Surface((size, size), pygame.SRCALPHA)
        inner_radius = int(size * 0.25)
        draw_star(mask, (size // 2, size // 2), size // 2, (255, 255, 255), inner_radius=inner_radius, rotation_deg=-90)
        striped.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        rect = striped.get_rect(center=(cx, cy))
        surface.blit(striped, rect)
        pts = []
        rot = math.radians(-90)
        outer_r = size // 2
        inner_r = inner_radius
        for i in range(10):
            ang = rot + (math.pi / 5) * i
            radius = outer_r if i % 2 == 0 else inner_r
            px = rect.centerx + radius * math.cos(ang)
            py = rect.centery + radius * math.sin(ang)
            pts.append((px, py))
        pygame.draw.lines(surface, (255, 255, 255), True, pts, 2)


def render_boss_portraits(surface, alpha=255):
    if not BOSS_PORTRAITS:
        return
    count = len(BOSS_PORTRAITS)
    portrait_w = 90
    portrait_h = 110
    gap = 16
    portraits_per_row = 4
    row_gap = portrait_h + 30
    for idx, info in enumerate(BOSS_PORTRAITS):
        psurf = pygame.Surface((portrait_w, portrait_h), pygame.SRCALPHA)
        _draw_portrait_icon(psurf, info)
        psurf.set_alpha(alpha)
        row = idx // portraits_per_row
        col = idx % portraits_per_row
        remaining = count - row * portraits_per_row
        cols_this_row = min(remaining, portraits_per_row)
        row_width = cols_this_row * portrait_w + gap * max(0, cols_this_row - 1)
        start_x = int((WIDTH - row_width) / 2)
        dest_x = start_x + col * (portrait_w + gap)
        base_y = HEIGHT // 2 + 40 + row * row_gap
        dest_y = base_y
        surface.blit(psurf, (dest_x, dest_y))


ENDING_SCENES = [
    ("あなたはなんてものに", 200),
    ("時間を費やしているんですか", 240),
    ("これよりもやるべきものが", 220),
    ("残っているだろうに", 220),
    ("それはともかく", 210),
    ("THANK YOU FOR PLAYING!", 300)
]

def _handle_common_events(skip_keys=None):
    skip_keys = skip_keys or {pygame.K_SPACE, pygame.K_RETURN, pygame.K_z, pygame.K_x, pygame.K_ESCAPE}
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN and event.key in skip_keys:
            return True
    return False

def play_staff_roll():
    clock = pygame.time.Clock()
    title_font = jp_font(42)
    role_font = jp_font(28)
    name_font = jp_font(36)
    title_surf = title_font.render("スタッフロール", True, (255, 255, 255))
    entry_surfaces = []
    for role, name in STAFF_ROLL_ENTRIES:
        role_surf = role_font.render(role, True, (200, 200, 220))
        name_surf = name_font.render(name, True, (255, 255, 255))
        entry_surfaces.append((role_surf, name_surf))
    spacing = 90
    base_y = HEIGHT + 80
    total_height = spacing * len(entry_surfaces) + 160
    scroll_y = base_y
    skip = False
    while scroll_y > -total_height and not skip:
        skip = _handle_common_events()
        screen.fill(BLACK)
        title_rect = title_surf.get_rect(center=(WIDTH // 2, int(scroll_y - 120)))
        screen.blit(title_surf, title_rect)
        for idx, (role_surf, name_surf) in enumerate(entry_surfaces):
            y = scroll_y + idx * spacing
            role_rect = role_surf.get_rect(center=(WIDTH // 2, int(y)))
            name_rect = name_surf.get_rect(center=(WIDTH // 2, int(y + 36)))
            screen.blit(role_surf, role_rect)
            screen.blit(name_surf, name_rect)
        scroll_y -= 1.6
        present_frame()
        clock.tick(60)
    pygame.event.pump()

def play_ending_sequence():
    clock = pygame.time.Clock()
    message_font = jp_font(40)
    skip = False
    for text, duration in ENDING_SCENES:
        timer = 0
        text_surface = message_font.render(text, True, (255, 255, 255))
        while timer < duration and not skip:
            skip = _handle_common_events()
            screen.fill(BLACK)
            if duration >= 120:
                fade_frames = 60
                if timer < fade_frames:
                    alpha = int(255 * (timer / float(fade_frames)))
                elif timer > duration - fade_frames:
                    alpha = int(255 * max(0.0, (duration - timer) / float(fade_frames)))
                else:
                    alpha = 255
            else:
                alpha = 255
            text_surface.set_alpha(alpha)
            rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            screen.blit(text_surface, rect)
            if text == "THANK YOU FOR PLAYING!":
                render_boss_portraits(screen, alpha)
            present_frame()
            clock.tick(60)
            timer += 1
        if skip:
            break
    pygame.event.pump()

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


def draw_player_ship(surface, rect, fill_color, outline_color):
    """Render a simple ship silhouette for a player rectangle."""
    nose = (rect.centerx, rect.top)
    left = (rect.left, rect.bottom)
    right = (rect.right, rect.bottom)
    tail = (rect.centerx, rect.bottom - max(4, rect.height // 3))
    points = (nose, left, tail, right)
    pygame.draw.polygon(surface, fill_color, points)
    pygame.draw.lines(surface, outline_color, True, points, 2)
    engine = pygame.Rect(0, 0, max(4, rect.width // 3), max(4, rect.height // 3))
    engine.center = (rect.centerx, rect.bottom - rect.height // 6)
    pygame.draw.rect(surface, outline_color, engine, width=0)


def _rgb(color):
    if not color:
        return (255, 255, 255)
    if len(color) >= 3:
        return int(color[0]), int(color[1]), int(color[2])
    return (int(color[0]),) * 3


def _tint(color, lighten=0.0):
    base = _rgb(color)
    if lighten <= 0:
        return base
    return tuple(min(255, int(c + (255 - c) * lighten)) for c in base)


def _shade(color, factor=1.0):
    base = _rgb(color)
    return tuple(max(0, min(255, int(c * factor))) for c in base)


def draw_bullet(surface, bullet):
    rect = bullet.get('rect')
    if not rect:
        return
    cx, cy = rect.center
    color = bullet.get('color')
    if color is None:
        if bullet.get('reflect'):
            color = BULLET_COLOR_REFLECT
        else:
            btype = bullet.get('type')
            if btype == 'homing':
                color = BULLET_COLOR_HOMING
            elif btype == 'spread':
                color = BULLET_COLOR_SPREAD
            elif btype == 'normal':
                color = BULLET_COLOR_NORMAL
            else:
                color = BULLET_COLOR_ENEMY
    color = _rgb(color)
    shape = bullet.get('shape')
    if bullet.get('trail_ttl'):
        glow_radius = max(rect.width, rect.height)
        if glow_radius > 0:
            glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surface, (*color, 90), (glow_radius, glow_radius), glow_radius)
            surface.blit(glow_surface, glow_surface.get_rect(center=(int(cx), int(cy))))
    if shape == 'star':
        outer = max(6, int(max(rect.width, rect.height) * 0.6))
        inner = max(3, int(outer * 0.5))
        spin = (pygame.time.get_ticks() * 0.2) % 360
        draw_star(surface, (cx, cy), outer, color, inner_radius=inner, rotation_deg=spin)
        pygame.draw.circle(surface, _tint(color, 0.35), (int(cx), int(cy)), max(2, inner // 3))
    elif shape == 'orb':
        radius = max(rect.width, rect.height) // 2
        radius = max(5, radius)
        pygame.draw.circle(surface, color, (int(cx), int(cy)), radius)
        highlight = _tint(color, 0.4)
        pygame.draw.circle(surface, highlight, (int(cx + radius * 0.25), int(cy - radius * 0.25)), max(2, radius // 2))
    else:
        pygame.draw.rect(surface, color, rect)
        if bullet.get('reflect'):
            pygame.draw.rect(surface, _tint(color, 0.4), rect, 2)


def draw_leaf_orb(surface, center, radius, angle_rad, base_color=(80, 255, 120)):
    cx, cy = center
    _ = angle_rad  # Provided for future orientation tweaks; orbit uses diagonal lock now
    glow_radius = max(6, int(radius * 1.6))
    if glow_radius > 0:
        glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surface, (*_rgb(base_color), 70), (glow_radius, glow_radius), glow_radius)
        surface.blit(glow_surface, glow_surface.get_rect(center=(int(cx), int(cy))))
    length = max(6, int(radius * 2.8))
    width = max(4, int(radius * 1.5))
    leaf_surface = pygame.Surface((length, width), pygame.SRCALPHA)
    main_rect = pygame.Rect(0, 0, length, width)
    pygame.draw.ellipse(leaf_surface, _rgb(base_color), main_rect)
    inner_rect = main_rect.inflate(-max(2, length // 4), -max(2, width // 3))
    if inner_rect.width > 0 and inner_rect.height > 0:
        pygame.draw.ellipse(leaf_surface, _tint(base_color, 0.25), inner_rect)
    vein_color = _shade(base_color, 0.35)
    pygame.draw.line(leaf_surface, vein_color, (length // 5, width // 2), (length - 4, width // 2), max(1, width // 7))
    pygame.draw.line(leaf_surface, vein_color, (length // 2, width // 2), (int(length * 0.82), int(width * 0.32)), max(1, width // 12))
    pygame.draw.line(leaf_surface, vein_color, (length // 2, width // 2), (int(length * 0.82), int(width * 0.68)), max(1, width // 12))
    scaled = pygame.transform.smoothscale(leaf_surface, (max(2, int(length * 1.05)), max(2, int(width * 1.05))))
    rotation = -45.0
    rotated = pygame.transform.rotate(scaled, rotation)
    surface.blit(rotated, rotated.get_rect(center=(int(cx), int(cy))))


def _build_boss5_constellation_pattern(center):
    cx, cy = center
    node_count = random.randint(3, 4)
    points = []
    min_radius, max_radius = BOSS5_TRAIL_RADIUS_RANGE
    for _ in range(node_count):
        ang = random.random() * 2 * math.pi
        dist = random.uniform(min_radius * 0.4, max_radius)
        px = cx + math.cos(ang) * dist
        py = cy + math.sin(ang) * dist
        px = max(6, min(WIDTH - 6, px))
        py = max(6, min(HEIGHT - 6, py))
        points.append({'pos': (px, py), 'size': random.randint(2, 4)})
    if not points:
        return None
    order = list(range(len(points)))
    random.shuffle(order)
    segments = []
    for idx in range(len(order) - 1):
        a = points[order[idx]]['pos']
        b = points[order[idx + 1]]['pos']
        segments.append({'a': a, 'b': b, 'width': random.randint(1, 2)})
    if len(points) >= 4 and random.random() < BOSS5_TRAIL_EXTRA_LINK_CHANCE:
        pa, pb = random.sample(points, 2)
        segments.append({'a': pa['pos'], 'b': pb['pos'], 'width': 1})
    ttl = random.randint(*BOSS5_TRAIL_TTL_RANGE)
    return {'points': points, 'segments': segments, 'ttl': ttl, 'max_ttl': ttl}


def update_boss5_path_constellations(boss_info, anchors, spawn_enabled):
    if not boss_info:
        return
    trails = boss_info.setdefault('trail_constellations', [])
    timer = boss_info.get('trail_spawn_timer', 0)
    if spawn_enabled and anchors:
        timer += 1
        interval = max(4, int(boss_info.get('trail_interval', BOSS5_TRAIL_INTERVAL_FRAMES)))
        if timer >= interval:
            timer = 0
            shuffled = list(anchors)
            random.shuffle(shuffled)
            limit = max(1, int(boss_info.get('trail_spawn_limit', BOSS5_TRAIL_SPAWN_LIMIT)))
            for center in shuffled[:limit]:
                pattern = _build_boss5_constellation_pattern(center)
                if pattern:
                    trails.append(pattern)
    else:
        timer = 0 if not spawn_enabled else timer
    max_patterns = max(1, int(boss_info.get('trail_max_patterns', BOSS5_TRAIL_MAX_PATTERNS)))
    new_trails = []
    for pattern in trails[-max_patterns:]:
        pattern['ttl'] -= 1
        if pattern['ttl'] > 0:
            new_trails.append(pattern)
    boss_info['trail_constellations'] = new_trails
    boss_info['trail_spawn_timer'] = timer


def draw_boss5_path_constellations(surface, boss_info):
    trails = boss_info.get('trail_constellations') if boss_info else None
    if not trails:
        return
    for pattern in trails:
        ttl = pattern.get('ttl', 0)
        max_ttl = max(1, pattern.get('max_ttl', 1))
        ratio = max(0.0, min(1.0, ttl / float(max_ttl)))
        line_strength = int(120 + 100 * ratio)
        line_color = (line_strength, line_strength, 255)
        for seg in pattern.get('segments', []):
            ax, ay = seg.get('a', (0, 0))
            bx, by = seg.get('b', (0, 0))
            width = max(1, int(seg.get('width', 1)))
            pygame.draw.line(surface, line_color, (int(ax), int(ay)), (int(bx), int(by)), width)
        outer_color = (255, 245, 210)
        inner_color = (255, 255, 255)
        for node in pattern.get('points', []):
            px, py = node.get('pos', (0, 0))
            radius = max(1, int(node.get('size', 3)))
            pygame.draw.circle(surface, outer_color, (int(px), int(py)), radius)
            inner_radius = max(1, radius - 1)
            pygame.draw.circle(surface, inner_color, (int(px), int(py)), inner_radius)


def update_boss5_side_lasers(boss_info, boss_position, parts=None):
    if not boss_info:
        return
    lasers = boss_info.setdefault('side_lasers', [])
    parts = parts or []
    position = boss_position or (0, 0)
    new_lasers = []
    for laser in lasers:
        state = laser.get('state', 'charge')
        timer = laser.get('timer', 0) + 1
        laser['timer'] = timer
        charge_time = laser.get('charge_time', 36)
        fire_time = laser.get('fire_time', 70)
        fade_time = laser.get('fade_time', 24)
        part_ref = laser.get('part_ref')
        alive_part = None
        if part_ref and part_ref in parts and part_ref.get('alive', True):
            alive_part = part_ref
        origin = laser.get('origin_static')
        if alive_part:
            origin = (alive_part.get('x', position[0]), alive_part.get('y', position[1]))
        elif origin is None:
            origin = position
        laser['origin'] = origin
        direction = laser.get('direction', 'left')
        if direction == 'left':
            target = (WIDTH * 0.12, HEIGHT + 60)
        else:
            target = (WIDTH * 0.88, HEIGHT + 60)
        laser['target'] = target
        base_width = laser.get('width', 32)
        if state == 'charge':
            if timer >= charge_time:
                laser['state'] = 'fire'
                laser['timer'] = 0
                timer = 0
            pulse = 0.4 + 0.4 * math.sin(pygame.time.get_ticks() / 140.0)
            current_width = max(4, int(base_width * pulse * 0.5))
        elif state == 'fire':
            if timer >= fire_time:
                laser['state'] = 'fade'
                laser['timer'] = 0
                timer = 0
            current_width = base_width
        else:  # fade
            if timer >= fade_time:
                continue
            remaining = max(0.0, 1.0 - (timer / float(max(1, fade_time))))
            current_width = max(4, int(base_width * remaining))
        laser['render_width'] = current_width
        new_lasers.append(laser)
    boss_info['side_lasers'] = new_lasers


def draw_boss5_side_lasers(surface, boss_info):
    lasers = boss_info.get('side_lasers') if boss_info else None
    if not lasers:
        return
    for laser in lasers:
        origin = laser.get('origin')
        target = laser.get('target')
        state = laser.get('state')
        width = max(2, int(laser.get('render_width', laser.get('width', 30))))
        if not origin or not target:
            continue
        beam_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        if state == 'charge':
            color = (255, 220, 160, 90)
        elif state == 'fire':
            color = (255, 240, 200, 190)
        else:
            fade_ratio = max(0.1, width / float(laser.get('width', width) or 1))
            alpha = int(160 * fade_ratio)
            color = (255, 200, 150, alpha)
        pygame.draw.line(beam_surface, color, (int(origin[0]), int(origin[1])), (int(target[0]), int(target[1])), width)
        surface.blit(beam_surface, (0, 0))

# 新・星降り弾幕フェーズ
def update_star_rain_phase(boss_state, player_rect, bullets):
    """大量の星が斜めに降ってくるフェーズ。Trueで終了。"""
    if not boss_state:
        return False
    timer = boss_state.setdefault('star_rain_timer', 0)
    phase_duration = 600
    interval = max(1, boss_state.get('star_rain_interval', 8))
    batch = max(1, boss_state.get('star_rain_batch', 12))
    # 画面上部から斜めに星を降らせる
    if timer % interval == 0:
        fullscreen_mode = boss_state.get('cross_phase_mode') == 'fullscreen_starstorm'
        for _ in range(batch):
            x = random.randint(0, WIDTH)
            if fullscreen_mode:
                speed = random.uniform(3.8, 6.2)
            else:
                speed = random.uniform(6.5, 10.5)
            angle = random.uniform(math.radians(70), math.radians(110))
            vx = speed * math.cos(angle)
            vy = speed * math.sin(angle)
            size = random.randint(12, 20)
            rect = pygame.Rect(int(x), -size, size, size)
            bullets.append({
                'rect': rect,
                'type': 'enemy',
                'vx': vx,
                'vy': vy,
                'power': 1.0,
                'shape': 'star',
                'color': (255, 230, 0),
                'life': 420,
            })
    boss_state['star_rain_timer'] = timer + 1
    # 終了条件
    if timer > phase_duration:
        boss_state['star_rain_timer'] = 0
        return True
    return False


def distance_point_to_segment(px, py, ax, ay, bx, by):
    vx = bx - ax
    vy = by - ay
    denom = vx * vx + vy * vy
    if denom <= 1e-6:
        dx = px - ax
        dy = py - ay
        return math.hypot(dx, dy), ax, ay
    t = ((px - ax) * vx + (py - ay) * vy) / denom
    t = max(0.0, min(1.0, t))
    cx = ax + vx * t
    cy = ay + vy * t
    return math.hypot(px - cx, py - cy), cx, cy


def build_rainbow_star_surface(outer_radius, color_sequence=None):
    """Create a vibrant rainbow star surface centered on origin."""
    outer_radius = max(outer_radius, 12)
    size = int(outer_radius * 2) + 12
    center = (size // 2, size // 2)

    if color_sequence is None:
        color_sequence = [
            (255, 0, 0),        # red
            (255, 127, 0),      # orange
            (255, 255, 0),      # yellow
            (0, 255, 0),        # green
            (0, 0, 255),        # blue
            (75, 0, 130),       # indigo
            (148, 0, 211),      # violet
        ]
    else:
        # Normalize provided colors to keep saturation high
        normalized = []
        for r, g, b in color_sequence:
            h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            s = min(1.0, max(0.8, s * 1.1))
            v = min(1.0, max(0.85, v * 1.05))
            nr, ng, nb = colorsys.hsv_to_rgb(h, s, v)
            normalized.append((int(nr * 255), int(ng * 255), int(nb * 255)))
        color_sequence = normalized

    # --- Build diagonally striped rainbow base ---
    big_size = int(size * 1.8)
    stripe_surface = pygame.Surface((big_size, big_size), pygame.SRCALPHA)
    repeats_per_sequence = 12
    stripe_width = max(2, int(math.ceil(big_size / max(1, len(color_sequence) * repeats_per_sequence))))
    x = -big_size
    color_index = 0
    while x < big_size * 2:
        rgb = color_sequence[color_index % len(color_sequence)]
        rect = pygame.Rect(x, 0, stripe_width, big_size)
        stripe_surface.fill((*rgb, 255), rect)
        x += stripe_width
        color_index += 1
    rotated_stripes = pygame.transform.rotate(stripe_surface, -32)
    rainbow_surface = pygame.Surface((size, size), pygame.SRCALPHA)
    rainbow_surface.blit(rotated_stripes, rotated_stripes.get_rect(center=center))

    # --- Mask stripes with star silhouette ---
    mask = pygame.Surface((size, size), pygame.SRCALPHA)
    draw_star(mask, center, outer_radius, (255, 255, 255, 255), inner_radius=outer_radius * 0.45)
    rainbow_surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    color_core = rainbow_surface.copy()

    # --- Outline for crisp edges ---
    outline = pygame.Surface((size, size), pygame.SRCALPHA)
    pts = []
    rot = math.radians(-90)
    inner_r = outer_radius * 0.45
    for i in range(10):
        ang = rot + (math.pi / 5) * i
        radius = outer_radius if i % 2 == 0 else inner_r
        px = center[0] + radius * math.cos(ang)
        py = center[1] + radius * math.sin(ang)
        pts.append((px, py))
    pygame.draw.polygon(outline, (30, 30, 30, 190), pts, width=max(2, int(outer_radius * 0.08)))
    rainbow_surface.blit(outline, (0, 0))

    # --- Inner highlights ---
    inner_star = pygame.Surface((size, size), pygame.SRCALPHA)
    draw_star(inner_star, center, outer_radius * 0.32, (255, 255, 255, 140), inner_radius=outer_radius * 0.14)
    rainbow_surface.blit(inner_star, (0, 0))

    # Soft glow derived from the colored star to avoid bleaching hues
    blur_scale = max(8, int(size * 0.62))
    glow = pygame.transform.smoothscale(color_core, (blur_scale, blur_scale))
    glow = pygame.transform.smoothscale(glow, (size, size))
    glow.set_alpha(120)
    rainbow_surface.blit(glow, (0, 0))

    return rainbow_surface


def build_rainbow_disc_surface(radius, color_sequence=None):
    """Create a vivid rainbow disc surface used during 赤バツボス phase2 transformation."""
    radius = max(radius, 10)
    size = int(radius * 2) + 12
    center = (size // 2, size // 2)

    if color_sequence is None:
        color_sequence = [
            (255, 0, 0),
            (255, 127, 0),
            (255, 255, 0),
            (0, 255, 0),
            (0, 0, 255),
            (75, 0, 130),
            (148, 0, 211),
        ]

    big_size = int(size * 1.6)
    stripe_surface = pygame.Surface((big_size, big_size), pygame.SRCALPHA)
    repeats_per_sequence = 10
    stripe_width = max(2, int(math.ceil(big_size / max(1, len(color_sequence) * repeats_per_sequence))))
    x = -big_size
    color_index = 0
    while x < big_size * 2:
        rgb = color_sequence[color_index % len(color_sequence)]
        rect = pygame.Rect(x, 0, stripe_width, big_size)
        stripe_surface.fill((*rgb, 255), rect)
        x += stripe_width
        color_index += 1

    rotated_stripes = pygame.transform.rotate(stripe_surface, -28)
    disc_surface = pygame.Surface((size, size), pygame.SRCALPHA)
    disc_surface.blit(rotated_stripes, rotated_stripes.get_rect(center=center))

    mask = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), center, radius)
    disc_surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    outline_width = max(2, int(radius * 0.12))
    pygame.draw.circle(disc_surface, (30, 30, 30, 200), center, radius, outline_width)

    inner_radius = int(radius * 0.45)
    glow_core = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(glow_core, (255, 255, 255, 120), center, inner_radius)
    disc_surface.blit(glow_core, (0, 0))

    blur_scale = max(8, int(size * 0.5))
    glow = pygame.transform.smoothscale(disc_surface, (blur_scale, blur_scale))
    glow = pygame.transform.smoothscale(glow, (size, size))
    glow.set_alpha(110)
    disc_surface.blit(glow, (0, 0))

    return disc_surface


def build_rainbow_trapezoid_surface(width, height, color_sequence=None):
    """Create a rainbow trapezoid surface reminiscent of Boss1's attack aura."""
    width = max(40, int(width))
    height = max(30, int(height))
    top_width = int(width * 0.55)
    base_width = width
    size = (base_width + 20, height + 20)
    surface = pygame.Surface(size, pygame.SRCALPHA)
    cx, cy = size[0] // 2, size[1] // 2

    if color_sequence is None:
        color_sequence = [
            (255, 0, 0),
            (255, 120, 0),
            (255, 230, 40),
            (40, 220, 120),
            (60, 140, 255),
            (170, 70, 250)
        ]

    stripe_surface = pygame.Surface((size[0] * 2, size[1] * 2), pygame.SRCALPHA)
    stripe_width = max(4, int(stripe_surface.get_width() / (len(color_sequence) * 10)))
    x = -stripe_surface.get_width()
    idx = 0
    while x < stripe_surface.get_width() * 2:
        color = color_sequence[idx % len(color_sequence)]
        stripe_surface.fill((*color, 255), pygame.Rect(x, 0, stripe_width, stripe_surface.get_height()))
        x += stripe_width
        idx += 1

    stripes = pygame.transform.rotate(stripe_surface, -18)
    surface.blit(stripes, stripes.get_rect(center=(cx, cy)))

    half_base = base_width / 2
    half_top = top_width / 2
    top_y = cy - height / 2
    bottom_y = cy + height / 2
    vertices = [
        (cx - half_top, top_y),
        (cx + half_top, top_y),
        (cx + half_base, bottom_y),
        (cx - half_base, bottom_y)
    ]

    mask = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), vertices)
    surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    outline_width = max(2, int(height * 0.08))
    pygame.draw.polygon(surface, (40, 40, 40, 200), vertices, width=outline_width)

    inner = pygame.Surface(size, pygame.SRCALPHA)
    inner_vertices = [
        (cx - half_top * 0.8, top_y + height * 0.15),
        (cx + half_top * 0.8, top_y + height * 0.15),
        (cx + half_base * 0.78, bottom_y - height * 0.12),
        (cx - half_base * 0.78, bottom_y - height * 0.12)
    ]
    pygame.draw.polygon(inner, (255, 255, 255, 120), inner_vertices)
    surface.blit(inner, (0, 0))

    glow = pygame.transform.smoothscale(surface, (int(size[0] * 0.45), int(size[1] * 0.45)))
    glow = pygame.transform.smoothscale(glow, size)
    glow.set_alpha(90)
    surface.blit(glow, (0, 0))

    return surface


def build_rainbow_ellipse_surface(width, height, color_sequence=None):
    width = max(40, int(width))
    height = max(40, int(height))
    surf = pygame.Surface((width + 20, height + 20), pygame.SRCALPHA)
    cx = surf.get_width() // 2
    cy = surf.get_height() // 2
    if color_sequence is None:
        color_sequence = [
            (255, 90, 90),
            (255, 170, 80),
            (255, 250, 120),
            (80, 255, 150),
            (90, 180, 255),
            (190, 90, 255)
        ]
    stripe = pygame.Surface((surf.get_width() * 2, surf.get_height() * 2), pygame.SRCALPHA)
    stripe_w = max(4, int(stripe.get_width() / (len(color_sequence) * 9)))
    x = -stripe.get_width()
    idx = 0
    while x < stripe.get_width() * 2:
        color = color_sequence[idx % len(color_sequence)]
        stripe.fill((*color, 255), pygame.Rect(x, 0, stripe_w, stripe.get_height()))
        x += stripe_w
        idx += 1
    rotated = pygame.transform.rotate(stripe, -22)
    surf.blit(rotated, rotated.get_rect(center=(cx, cy)))
    mask = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    rect = pygame.Rect(cx - width // 2, cy - height // 2, width, height)
    pygame.draw.ellipse(mask, (255, 255, 255, 255), rect)
    surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    outline = max(2, int(min(width, height) * 0.08))
    pygame.draw.ellipse(surf, (40, 40, 40, 210), rect, outline)
    glow = pygame.transform.smoothscale(surf, (int(surf.get_width() * 0.45), int(surf.get_height() * 0.45)))
    glow = pygame.transform.smoothscale(glow, surf.get_size())
    glow.set_alpha(80)
    surf.blit(glow, (0, 0))
    return surf


def build_orbit_moon_surface(radius, color=(255, 240, 200)):
    radius = max(12, int(radius))
    size = radius * 2 + 12
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    center = (size // 2, size // 2)
    base_col = (225, 225, 215)
    pygame.draw.circle(surf, base_col, center, radius)
    shade = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(shade, (40, 40, 40, 90), (center[0] - int(radius * 0.25), center[1] + int(radius * 0.2)), radius)
    surf.blit(shade, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
    glow = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(glow, (255, 255, 255, 130), (center[0] + int(radius * 0.25), center[1] - int(radius * 0.3)), int(radius * 0.7))
    surf.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    crater_layer = pygame.Surface((size, size), pygame.SRCALPHA)
    crater_specs = [
        (0.25, -0.15, 0.32, 180),
        (-0.35, 0.25, 0.26, 160),
        (0.05, 0.35, 0.18, 140),
        (-0.12, -0.38, 0.22, 120)
    ]
    for ox, oy, scale, alpha in crater_specs:
        cx = center[0] + int(radius * ox)
        cy = center[1] + int(radius * oy)
        r = max(2, int(radius * scale))
        pygame.draw.circle(crater_layer, (150, 150, 150, alpha), (cx, cy), r)
        inner = max(1, r - max(1, r // 3))
        pygame.draw.circle(crater_layer, (230, 230, 230, alpha), (cx - int(r * 0.2), cy - int(r * 0.15)), inner)
    surf.blit(crater_layer, (0, 0))
    return surf

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
has_dash = False
boss_attack_timer = 0
unlocked_homing = False
unlocked_leaf_shield = False
unlocked_spread = False
unlocked_dash = False
unlocked_hp_boost = False
reward_granted = False
leaf_orb_positions = []
frame_count = 0  # フレームカウンタ（ダッシュ二度押し判定などに使用）
fire_cooldown = 0  # 連射クールダウン（フレーム）
debug_infinite_hp = False
boss_music_played = False
while True:
    events = pygame.event.get()
    
    # タイトル画面モード
    if title_mode:
        # BGMをデフォルトに戻す
        if get_current_bgm() != "picopiconostalgie":
            play_bgm("picopiconostalgie", volume=0.4)
        # phase2チェックポイントをリセット
        boss6_phase2_checkpoint = False
        draw_title_screen(screen, frame_count)
        present_frame()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                # いずれかのキーでメニューへ
                title_mode = False
                menu_mode = True
                play_menu_beep()
        frame_count += 1
        continue
    
    if menu_mode:
        # BGMをデフォルトに戻す
        if get_current_bgm() != "picopiconostalgie":
            play_bgm("picopiconostalgie", volume=0.4)
        # phase2チェックポイントをリセット
        boss6_phase2_checkpoint = False
        # BGMは継続再生（stop_music()を削除）
        boss_music_played = False
        draw_menu(screen, selected_level, level_cleared)
        present_frame()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected_level += 1
                    if selected_level > 6:
                        selected_level = 1
                    play_menu_beep()  # メニュー移動音
                if event.key == pygame.K_DOWN:
                    selected_level -= 1
                    if selected_level < 1:
                        selected_level = 6
                    play_menu_beep()  # メニュー移動音
                if event.key == pygame.K_i:
                    unlocked_homing = True
                    unlocked_leaf_shield = True
                    unlocked_spread = True
                    unlocked_dash = True
                    unlocked_hp_boost = True
                    has_homing = True
                    has_leaf_shield = True
                    has_spread = True
                    has_dash = True
                    player_lives = max(player_lives, 5)
                if event.key == pygame.K_h:
                    debug_infinite_hp = not debug_infinite_hp
                    if debug_infinite_hp:
                        player_lives = max(player_lives, 5 if unlocked_hp_boost else 3)
                if event.key == pygame.K_RETURN:
                    boss_template = level_list[selected_level]["boss"]
                    boss_info = copy.deepcopy(boss_template) if boss_template else None
                    if boss_info:
                        if is_fullscreen:
                            set_display_mode(False)
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
                            boss_info['trail_constellations'] = []
                            boss_info['trail_spawn_timer'] = 0
                            boss_info['side_lasers'] = []
                        retry = False
                        waiting_for_space = False
                        boss_music_played = False
                        has_homing = unlocked_homing
                        has_leaf_shield = unlocked_leaf_shield
                        has_spread = unlocked_spread
                        has_dash = unlocked_dash
                        # 残機は報酬アンロックで5に増加（デフォルト3）
                        player_lives = 5 if unlocked_hp_boost else 3
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
                                if not (boss_info.get('beam_state') in ('telegraph','firing') and beam and beam.get('state') in ('telegraph','firing')):
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
                        if boss_info["name"] == "赤バツボス":
                            boss_y = 140
                            boss_info['cross_phase'] = 0.0
                            boss_info['cross_angle'] = 0.0
                            boss_info['cross_phase_speed'] = 0.015
                            boss_info['cross_spin_speed'] = 0.05
                            boss_info['cross_orbit'] = 80
                            boss_info['cross_bob'] = 28
                            boss_info['cross_base_y'] = boss_y
                            boss_info['cross_falls'] = []
                            boss_info['cross_attack_timer'] = 0
                            boss_info['cross_attack_cooldown'] = 150
                            boss_info['cross_wall_attack'] = None
                            boss_info['cross_last_pattern'] = None
                            boss_info['cross_transition_effects'] = []
                            boss_info['cross_phase_mode'] = 'phase1'
                            base_hp = boss_info.get('hp', 180)
                            boss_info['cross_phase1_hp'] = base_hp
                            boss_info['cross_phase2_hp'] = max(base_hp + 60, int(base_hp * 1.2))
                            boss_info['cross_active_hp_max'] = base_hp
                            boss_info['cross_transition_timer'] = 0
                            boss_info['cross_phase2_intro_timer'] = 0
                            boss_info['cross_blackout_alpha'] = 0
                            boss_info['cross_phase2_started'] = False
                            boss_info['cross_star_state'] = 'cross'
                            boss_info['cross_star_progress'] = 0.0
                            boss_info['cross_star_rotation'] = 0.0
                            boss_info['cross_star_spin_speed'] = 1.6
                            boss_info['cross_star_transition_speed'] = 0.02
                            boss_info['cross_star_surface'] = None
                            boss_info['cross_star_surface_radius'] = 0
                            boss_info['cross_phase2_settings_applied'] = False
                            boss_info['cross_phase3_triggered'] = False
                            boss_info['cross_phase3_state'] = 'dormant'
                            boss_info['cross_phase3_timer'] = 0
                            boss_info['cross_phase3_starfield'] = []
                            boss_info['cross_phase3_background'] = []
                            boss_info['cross_phase3_overlay_alpha'] = 0
                            boss_info['cross_phase3_invincible'] = False
                            boss_info['star_rain_active'] = False
                            boss_info['cross_phase2_fullscreen_done'] = False
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
                            # 楕円ボスのコア/ビーム/角度を毎回リセット（持ち越し防止）
                            boss_info['core_state'] = 'closed'
                            boss_info['core_timer'] = 0
                            boss_info['core_cycle_interval'] = OVAL_CORE_CYCLE_INTERVAL
                            boss_info['core_firing_duration'] = OVAL_CORE_FIRING_DURATION
                            boss_info['core_open_hold'] = OVAL_CORE_OPEN_HOLD
                            boss_info['core_gap'] = 0
                            boss_info['core_gap_target'] = OVAL_CORE_GAP_TARGET
                            # ビーム状態リセット
                            boss_info['left_beam'] = None
                            boss_info['right_beam'] = None
                            boss_info['beam_state'] = 'idle'
                            boss_info['beam_timer'] = 0
                            # 初手は撃たないため初期クールダウンを与える
                            boss_info['beam_cd'] = 180
                            boss_info['beam_focus'] = None
                            # 小楕円（左右）の向きを初期化（下向き）
                            boss_info['left_angle'] = math.pi/2
                            boss_info['right_angle'] = math.pi/2
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
                            boss_info['trail_constellations'] = []
                            boss_info['trail_spawn_timer'] = 0
                            boss_info['side_lasers'] = []
                        # 残機は報酬アンロックで5に増加（デフォルト3）
                        player_lives = 5 if unlocked_hp_boost else 3
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
        if is_fullscreen:
            set_display_mode(False)
        # BGMは継続再生（stop_music()を削除）
        # プレイヤー/一般状態
        # 残機は報酬アンロックで5に増加（デフォルト3）
        player_lives = 5 if unlocked_hp_boost else 3
        player_invincible = False
        player_invincible_timer = 0
        explosion_timer = 0
        explosion_pos = None
        bullets = []
        fire_cooldown = 0
        frame_count = 0
        leaf_angle = 0.0
        bullet_type = "normal"
        boss_music_played = False
        # 画面状態
        waiting_for_space = False
        menu_mode = False
        # 第三形態用の2P関連を初期化
        player2 = None
        wasd_hint_timer = 0
        # ボス状態
        if 'level_list' in globals():
            boss_template = level_list[selected_level]["boss"]
            boss_info = copy.deepcopy(boss_template) if boss_template else None
        else:
            boss_info = boss_info
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
        # 楕円ボスのビーム/コア/角度は必ずリセット（リトライ時の持ち越し防止）
        if boss_info and boss_info.get('name') == '楕円ボス':
            boss_info['left_beam'] = None
            boss_origin_y = boss_y
            boss_info['right_beam'] = None
            boss_info['beam_state'] = 'idle'
            boss_info['beam_timer'] = 0
            # 初手ビーム防止のためリトライ時も初期CDを設定
            boss_info['beam_cd'] = 180
            boss_info['beam_focus'] = None
            boss_info['core_state'] = 'closed'
            boss_info['core_timer'] = 0
            boss_info['core_gap'] = 0
            boss_info['left_angle'] = math.pi/2
            boss_info['right_angle'] = math.pi/2
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
            boss_info['trail_constellations'] = []
            boss_info['trail_spawn_timer'] = 0
            boss_info['side_lasers'] = []
        if boss_info and boss_info.get("name") == "赤バツボス":
            boss_y = 140
            boss_origin_y = boss_y
            boss_info['cross_phase'] = 0.0
            boss_info['cross_angle'] = 0.0
            boss_info['cross_phase_speed'] = 0.015
            boss_info['cross_spin_speed'] = 0.05
            boss_info['cross_orbit'] = 80
            boss_info['cross_bob'] = 28
            boss_info['cross_base_y'] = boss_y
            boss_info['cross_falls'] = []
            boss_info['cross_attack_timer'] = 0
            boss_info['cross_attack_cooldown'] = 150
            boss_info['cross_wall_attack'] = None
            boss_info['cross_last_pattern'] = None
            boss_info['cross_transition_effects'] = []
            # チェックポイントがあればphase2から開始
            if boss6_phase2_checkpoint:
                boss_info['cross_phase_mode'] = 'phase2'
                boss_info['cross_phase2_started'] = True
            else:
                boss_info['cross_phase_mode'] = 'phase1'
            base_hp = boss_info.get('hp', 180)
            boss_info['cross_phase1_hp'] = base_hp
            boss_info['cross_phase2_hp'] = max(base_hp + 60, int(base_hp * 1.2))
            if boss6_phase2_checkpoint:
                # phase2から開始する場合、HPをphase2の値に設定
                boss_hp = boss_info['cross_phase2_hp']
                boss_info['hp'] = boss_hp
            boss_info['cross_active_hp_max'] = base_hp
            boss_info['cross_transition_timer'] = 0
            boss_info['cross_phase2_intro_timer'] = 0
            boss_info['cross_blackout_alpha'] = 0
            boss_info['cross_phase2_started'] = False
            boss_info['cross_star_state'] = 'cross'
            boss_info['cross_star_progress'] = 0.0
            boss_info['cross_star_rotation'] = 0.0
            boss_info['cross_star_spin_speed'] = 1.6
            boss_info['cross_star_transition_speed'] = 0.02
            boss_info['cross_star_surface'] = None
            boss_info['cross_star_surface_radius'] = 0
            boss_info['cross_phase2_settings_applied'] = False
            boss_info['cross_phase2_fullscreen_done'] = False
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
        present_frame()
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
                if event.type == pygame.KEYDOWN and event.key == pygame.K_i:
                    unlocked_homing = True
                    unlocked_leaf_shield = True
                    unlocked_spread = True
                    unlocked_dash = True
                    unlocked_hp_boost = True
                    has_homing = True
                    has_leaf_shield = True
                    has_spread = True
                    has_dash = True
                    player_lives = max(player_lives, 5)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_h:
                    debug_infinite_hp = not debug_infinite_hp
                    if debug_infinite_hp:
                        player_lives = max(player_lives, 5 if unlocked_hp_boost else 3)
        continue
    if waiting_for_space:
        screen.fill(BLACK)
        font = jp_font(42)
        text = font.render("Press SPACE to start!", True, WHITE)
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(text, text_rect)
        present_frame()
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
            if event.key == pygame.K_i:
                unlocked_homing = True
                unlocked_leaf_shield = True
                unlocked_spread = True
                unlocked_dash = True
                unlocked_hp_boost = True
                has_homing = True
                has_leaf_shield = True
                has_spread = True
                has_dash = True
                player_lives = max(player_lives, 5)
            if event.key == pygame.K_h:
                debug_infinite_hp = not debug_infinite_hp
                if debug_infinite_hp:
                    player_lives = max(player_lives, 5 if unlocked_hp_boost else 3)
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
            # デバッグ: T でボス即撃破
            if event.key == pygame.K_t and boss_alive:
                if boss_info and boss_info.get('name') == '赤バツボス':
                    cross_mode = boss_info.get('cross_phase_mode', 'phase1')
                    if cross_mode == 'phase1':
                        boss_info['cross_phase1_hp'] = 0
                        boss_info['cross_phase_mode'] = 'transition_explosion'
                        boss_info['cross_transition_timer'] = 0
                        boss_info['cross_phase2_intro_timer'] = 0
                        boss_info['cross_blackout_alpha'] = 0
                        boss_info['cross_phase2_started'] = False
                        boss_info['cross_phase2_settings_applied'] = False
                        boss_info['cross_star_state'] = 'transition'
                        boss_info['cross_star_progress'] = 0.0
                        boss_info['cross_star_rotation'] = 0.0
                        boss_info['cross_attack_timer'] = 0
                        boss_info['cross_wall_attack'] = None
                        boss_info['cross_falls'] = []
                        boss_info['cross_last_pattern'] = None
                        phase2_hp = boss_info.get('cross_phase2_hp')
                        if not phase2_hp:
                            phase2_hp = boss_info.get('hp', boss_hp)
                        boss_info['cross_phase2_hp'] = phase2_hp
                        boss_info['cross_active_hp_max'] = max(1, phase2_hp)
                        boss_info['hp'] = phase2_hp
                        boss_hp = phase2_hp
                    else:
                        boss_info['cross_phase2_hp'] = 0
                        boss_info['hp'] = 0
                        boss_hp = 0
                        boss_alive = False
                        boss_explosion_timer = 0
                        explosion_pos = (boss_x, boss_y)
                else:
                    boss_hp = 0
                    boss_alive = False
                    boss_explosion_timer = 0
                    explosion_pos = (boss_x, boss_y)
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
                    if not debug_infinite_hp:
                        player_lives -= 1
                    player_invincible = True
                    player_invincible_timer = 0
                    explosion_timer = 0
                    explosion_pos = (player.centerx, player.centery)
                    reset_boss_hazards_after_player_hit(boss_info)
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
                    if not debug_infinite_hp:
                        player_lives -= 1
                    player_invincible = True
                    player_invincible_timer = 0
                    explosion_timer = 0
                    explosion_pos = (player.centerx, player.centery)
                    # ビームで被弾したフレームは他の衝突判定をスキップ（多重減少防止）
                    break
        # 赤バツボスの落下パーツとの当たり判定
        if boss_info and boss_info.get('name') == '赤バツボス':
            for fall in list(boss_info.get('cross_falls', [])):
                rect = fall.get('rect')
                if rect:
                    shrink_w = int(rect.width * 0.4)
                    shrink_h = int(rect.height * 0.3)
                    if shrink_w >= rect.width:
                        shrink_w = rect.width - 2
                    if shrink_h >= rect.height:
                        shrink_h = rect.height - 2
                    # 槍の当たり判定を視覚より小さくする
                    hit_rect = rect.inflate(-shrink_w, -shrink_h) if rect.width > 2 and rect.height > 2 else rect
                    if hit_rect.width <= 0 or hit_rect.height <= 0:
                        hit_rect = rect
                else:
                    hit_rect = None
                if hit_rect and hit_rect.colliderect(player):
                    if not debug_infinite_hp:
                        player_lives -= 1
                    player_invincible = True
                    player_invincible_timer = 0
                    explosion_timer = 0
                    explosion_pos = (player.centerx, player.centery)
                    boss_info['cross_falls'].remove(fall)
                    reset_boss_hazards_after_player_hit(boss_info)
                    break
            if not player_invincible:
                wall_attack = boss_info.get('cross_wall_attack')
                if wall_attack and wall_attack.get('state') in ('advance', 'hold', 'retract'):
                    for spear in wall_attack.get('spears', []):
                        rect = spear.get('rect')
                        if rect and rect.colliderect(player):
                            if not debug_infinite_hp:
                                player_lives -= 1
                            player_invincible = True
                            player_invincible_timer = 0
                            explosion_timer = 0
                            explosion_pos = (player.centerx, player.centery)
                            boss_info['cross_wall_attack'] = None
                            reset_boss_hazards_after_player_hit(boss_info)
                            break

        # 被弾後はこのフレームの他の衝突をスキップ
        if player_invincible:
            pass
        else:
            # 跳ね返り弾のみプレイヤー判定
            for bullet in bullets:
                if (bullet.get("reflect", False) or bullet.get("type") == "enemy") and not bullet.get('harmless'):
                    if player.colliderect(bullet["rect"]):
                        if not debug_infinite_hp:
                            player_lives -= 1
                        player_invincible = True
                        player_invincible_timer = 0
                        explosion_timer = 0
                        explosion_pos = (player.centerx, player.centery)
                        reset_boss_hazards_after_player_hit(boss_info)
                        bullets.remove(bullet)
                        break
        # 第三形態: 2P への敵弾/反射弾の当たり判定（被弾していなければ）
        if not player_invincible and boss_info and boss_info.get('name') == '三日月形ボス' and boss_info.get('phase',1) == 3 and player2:
            for bullet in bullets:
                if (bullet.get("reflect", False) or bullet.get("type") == "enemy") and not bullet.get('harmless'):
                    if player2.colliderect(bullet["rect"]):
                        if not debug_infinite_hp:
                            player_lives -= 1
                        player_invincible = True
                        player_invincible_timer = 0
                        explosion_timer = 0
                        explosion_pos = (player2.centerx, player2.centery)
                        # 2Pも初期位置へ
                        player2.x = WIDTH//2 - 80
                        player2.y = HEIGHT - 40
                        reset_boss_hazards_after_player_hit(boss_info)
                        bullets.remove(bullet)
                        break
        # 通常のボス接触判定（被弾していなければ）
        if not player_invincible:
            dx = player.centerx - boss_x
            dy = player.centery - boss_y
            if dx*dx + dy*dy < (boss_radius + max(player.width, player.height)//2)**2:
                if not debug_infinite_hp:
                    player_lives -= 1
                player_invincible = True
                player_invincible_timer = 0
                explosion_timer = 0
                explosion_pos = (player.centerx, player.centery)
                reset_boss_hazards_after_player_hit(boss_info)

        if boss_info and boss_info.get('name') == '三日月形ボス':
            update_boss5_side_lasers(boss_info, (boss_x, boss_y), boss_info.get('parts') if boss_info.get('phase3_split') else None)

        # 星座線分への接触（太線近傍）
        if not player_invincible and boss_info and boss_info.get('name') == '三日月形ボス':
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
                        if not debug_infinite_hp:
                            player_lives -= 1
                        player_invincible = True
                        player_invincible_timer = 0
                        explosion_timer = 0
                        explosion_pos = (player.centerx, player.centery)
                        reset_boss_hazards_after_player_hit(boss_info)
                        break

        # 側面レーザーとの接触判定
        lasers = boss_info.get('side_lasers', []) if boss_info and boss_info.get('name') == '三日月形ボス' else []
        if lasers and not player_invincible:
            px, py = player.centerx, player.centery
            for laser in lasers:
                state = laser.get('state')
                if state != 'fire':
                    continue
                origin = laser.get('origin')
                target = laser.get('target')
                if not origin or not target:
                    continue
                width = max(6, int(laser.get('render_width', laser.get('width', 30))))
                ax, ay = origin
                bx, by = target
                vx, vy = bx - ax, by - ay
                denom = vx * vx + vy * vy
                if denom <= 0:
                    continue
                t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / denom))
                cx = ax + vx * t
                cy = ay + vy * t
                if (px - cx)**2 + (py - cy)**2 <= (width / 2 + 8)**2:
                    if not debug_infinite_hp:
                        player_lives -= 1
                    player_invincible = True
                    player_invincible_timer = 0
                    explosion_timer = 0
                    explosion_pos = (player.centerx, player.centery)
                    reset_boss_hazards_after_player_hit(boss_info)
                    break

        if lasers and not player_invincible and boss_info and boss_info.get('phase', 1) == 3 and boss_info.get('phase3_split') and player2:
            px2, py2 = player2.centerx, player2.centery
            for laser in lasers:
                state = laser.get('state')
                if state != 'fire':
                    continue
                origin = laser.get('origin')
                target = laser.get('target')
                if not origin or not target:
                    continue
                width = max(6, int(laser.get('render_width', laser.get('width', 30))))
                ax, ay = origin
                bx, by = target
                vx, vy = bx - ax, by - ay
                denom = vx * vx + vy * vy
                if denom <= 0:
                    continue
                t = max(0.0, min(1.0, ((px2 - ax) * vx + (py2 - ay) * vy) / denom))
                cx = ax + vx * t
                cy = ay + vy * t
                if (px2 - cx)**2 + (py2 - cy)**2 <= (width / 2 + 8)**2:
                    if not debug_infinite_hp:
                        player_lives -= 1
                    player_invincible = True
                    player_invincible_timer = 0
                    explosion_timer = 0
                    explosion_pos = (player2.centerx, player2.centery)
                    player2.x = WIDTH//2 - 80
                    player2.y = HEIGHT - 40
                    reset_boss_hazards_after_player_hit(boss_info)
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
            elif boss_info["name"] == "三日月形ボス":
                reward_text = "体力増加! 次回から残機が5に"
            elif boss_info["name"] == "赤バツボス":
                reward_text = None
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
            elif boss_info["name"] == "三日月形ボス":
                unlocked_hp_boost = True
            elif boss_info["name"] == "赤バツボス":
                pass
        # 星マーク
        if result == "win":
            level_cleared[selected_level] = True
        # 爆発表示（最後の爆発）
        for i in range(EXPLOSION_DURATION):
            screen.fill(BLACK)
            if explosion_pos:
                # プレイヤー被弾爆発エフェクト（ゲームオーバー画面でも同様）
                progress = i / EXPLOSION_DURATION  # 0.0 ~ 1.0
                for wave_i in range(3):
                    wave_progress = max(0.0, min(1.0, progress - wave_i * 0.15))
                    if wave_progress > 0:
                        radius = int(15 + wave_progress * 35)
                        alpha = int(255 * (1.0 - wave_progress))
                        red_val = max(100, 255 - int(wave_progress * 155))
                        color = (red_val, 0, 0)
                        
                        circle_surf = pygame.Surface((radius * 2 + 10, radius * 2 + 10), pygame.SRCALPHA)
                        pygame.draw.circle(circle_surf, (*color, alpha), 
                                         (radius + 5, radius + 5), radius, max(2, int(6 - wave_progress * 4)))
                        inner_alpha = int(alpha * 0.3)
                        pygame.draw.circle(circle_surf, (*color, inner_alpha), 
                                         (radius + 5, radius + 5), max(1, radius - 3))
                        screen.blit(circle_surf, 
                                  (explosion_pos[0] - radius - 5, explosion_pos[1] - radius - 5))
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
            present_frame()
            pygame.time.wait(20)
        pygame.time.wait(1000)
        if result == "win" and boss_info and boss_info.get('name') == '赤バツボス':
            play_staff_roll()
            play_ending_sequence()
            pygame.event.clear()
        # 選択メニュー
        while True:
            draw_end_menu(screen, result, reward_text)
            present_frame()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_t:
                        # タイトルへ戻る
                        if is_fullscreen:
                            set_display_mode(False)
                        title_mode = True
                        menu_mode = False
                        break
                    # メニューへ戻る（1 / テンキー1）
                    if event.key in (pygame.K_1, pygame.K_KP_1):
                        if is_fullscreen:
                            set_display_mode(False)
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
            if menu_mode or retry or title_mode:
                break
        continue

    # 描画
    screen.fill(BLACK)
    if boss_info and boss_info.get('name') == '三日月形ボス':
        spawn_allowed = boss_alive and not waiting_for_space
        anchors = []
        if spawn_allowed:
            if boss_info.get('phase', 1) == 3 and boss_info.get('phase3_split') and boss_info.get('parts'):
                anchors = [(p.get('x', boss_x), p.get('y', boss_y)) for p in boss_info['parts'] if p.get('alive', True)]
                if not anchors:
                    anchors = [(boss_x, boss_y)]
            else:
                anchors = [(boss_x, boss_y)]
        update_boss5_path_constellations(boss_info, anchors, spawn_allowed)
        draw_boss5_path_constellations(screen, boss_info)
        draw_boss5_side_lasers(screen, boss_info)
    if boss_info and boss_info.get('name') == '赤バツボス' and boss_alive:
        cross_mode = boss_info.get('cross_phase_mode', 'phase1')
        if cross_mode != 'phase1':
            initial_hp = boss_info.get('initial_hp') or boss_info.setdefault('initial_hp', boss_hp)
            threshold = 0.25 * initial_hp if initial_hp else 0
            if threshold and boss_hp <= threshold:
                update_star_rain_phase(boss_info, player, bullets)

    # 星座線分・ヒント演出撤去

    # 楕円ボス 新ビーム描画
    if boss_alive and boss_info and boss_info["name"] == "楕円ボス":
        for side in ('left','right'):
            beam = boss_info.get(f'{side}_beam')
            if not beam: continue
            ox, oy = beam.get('origin', (boss_x, boss_y))
            if 'target' in beam:
                tx, ty = beam['target']
            else:
                # 角度から暫定ターゲット（表示/衝突用）: 下先端方向に伸ばす
                ang = beam.get('angle', -math.pi/2)
                rot = ang - math.pi/2
                dirx = -math.sin(rot)
                diry =  math.cos(rot)
                tx = int(ox + dirx * 1200)
                ty = int(oy + diry * 1200)
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
            # 各小楕円は角度 boss_info['left_angle'/'right_angle'] に合わせて回転させる（下先端がプレイヤーを向く）。
            small_w, small_h = boss_radius//2, boss_radius*2//3
            for side in ('left','right'):
                cx = boss_x - boss_radius if side=='left' else boss_x + boss_radius
                cy = boss_y
                ang = boss_info.get(f'{side}_angle', -math.pi/2)
                # 回転楕円の描画（Surfaceを回して中心にブリット）
                esurf = pygame.Surface((small_w, small_h), pygame.SRCALPHA)
                pygame.draw.ellipse(esurf, (0,200,0), (0, 0, small_w, small_h))
                deg = math.degrees(ang) - 90.0
                rsurf = pygame.transform.rotate(esurf, deg)
                rrect = rsurf.get_rect(center=(int(cx), int(cy)))
                screen.blit(rsurf, rrect)
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
        elif boss_info and boss_info["name"] == "赤バツボス":
            cross_mode = boss_info.get('cross_phase_mode', 'phase1')
            star_state = boss_info.get('cross_star_state', 'cross')
            progress = boss_info.get('cross_star_progress', 0.0)
            eased = progress ** 0.6 if progress > 0 else 0.0
            if star_state == 'star' or cross_mode in ('transition_explosion', 'transition_blackout', 'phase2_intro', 'phase2'):
                eased = 1.0
            cross_alpha = 255 if star_state == 'cross' and cross_mode == 'phase1' else int(max(0, min(255, 255 * (1.0 - eased))))
            if cross_mode != 'phase1':
                cross_alpha = 0
            star_alpha = 0
            if star_state == 'circle':
                charge_ratio = max(0.0, min(1.0, boss_info.get('cross_phase2_charge_ratio', 1.0)))
                star_alpha = int(max(120, min(255, 255 * charge_ratio)))
            elif star_state == 'trapezoid':
                charge_ratio = max(0.0, min(1.0, boss_info.get('cross_phase2_charge_ratio', 1.0)))
                star_alpha = int(max(150, min(255, 235 * (0.6 + charge_ratio * 0.6))))
            elif star_state in ('transition', 'star') or cross_mode != 'phase1':
                star_alpha = 255 if cross_mode != 'phase1' else int(max(0, min(255, 255 * eased)))

            size = boss_radius * 2 + 40
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            center = size // 2
            arm = boss_radius + 10
            thickness = max(12, boss_radius // 3)
            color = boss_color
            pygame.draw.line(surf, color, (center - arm, center - arm), (center + arm, center + arm), thickness)
            pygame.draw.line(surf, color, (center - arm, center + arm), (center + arm, center - arm), thickness)
            pygame.draw.circle(surf, (255, 180, 180, 180), (center, center), thickness//2)
            angle_deg = math.degrees(boss_info.get('cross_angle', 0.0)) % 360
            if cross_alpha > 0:
                rotated_cross = pygame.transform.rotate(surf, angle_deg)
                cross_rect = rotated_cross.get_rect(center=(int(boss_x), int(boss_y)))
                if cross_alpha < 255:
                    rotated_cross.set_alpha(cross_alpha)
                screen.blit(rotated_cross, cross_rect)

            squish_rendered = False
            squish = boss_info.get('cross_phase2_bounce_squish')
            if squish and boss_info.get('cross_phase2_state') == 'bounce' and star_state == 'circle' and star_alpha > 0:
                timer = squish.get('timer', 0)
                duration = max(1, squish.get('duration', 16))
                axis = squish.get('axis', 'both')
                ratio = max(0.0, min(1.0, 1.0 - (timer / float(duration))))
                base_radius = boss_info.get('cross_phase2_disc_radius') or (boss_radius + 24)
                disc_surface = boss_info.get('cross_phase2_disc_surface')
                if disc_surface is None or disc_surface.get_width() <= 0 or disc_surface.get_height() <= 0:
                    disc_surface = build_rainbow_disc_surface(base_radius)
                    boss_info['cross_phase2_disc_surface'] = disc_surface
                    boss_info['cross_phase2_disc_radius'] = base_radius
                if disc_surface:
                    width, height = disc_surface.get_size()
                    if axis == 'x':
                        stretch_x = 1.0 + (1.0 - ratio) * 0.45
                        stretch_y = 0.55 + 0.45 * ratio
                    elif axis == 'y':
                        stretch_x = 0.55 + 0.45 * ratio
                        stretch_y = 1.0 + (1.0 - ratio) * 0.45
                    else:
                        stretch_x = 0.85 + 0.15 * ratio
                        stretch_y = 0.85 + 0.15 * ratio
                    scaled_w = max(8, int(width * stretch_x))
                    scaled_h = max(8, int(height * stretch_y))
                    scaled_surface = pygame.transform.smoothscale(disc_surface, (scaled_w, scaled_h))
                    spin = boss_info.get('cross_phase2_disc_spin', 0.0)
                    rotated = pygame.transform.rotate(scaled_surface, spin)
                    if star_alpha < 255:
                        rotated.set_alpha(star_alpha)
                    rect = rotated.get_rect(center=(int(boss_x), int(boss_y)))
                    screen.blit(rotated, rect)
                    squish_rendered = True

            if star_alpha > 0 and not squish_rendered:
                render_surface = None
                if star_state in ('circle', 'ellipse'):
                    base_radius = boss_info.get('cross_phase2_disc_radius') or (boss_radius + 24)
                    disc_surface = boss_info.get('cross_phase2_disc_surface')
                    if disc_surface is None or disc_surface.get_width() <= 0 or disc_surface.get_height() <= 0:
                        disc_surface = build_rainbow_disc_surface(base_radius)
                        boss_info['cross_phase2_disc_surface'] = disc_surface
                        boss_info['cross_phase2_disc_radius'] = base_radius
                    if disc_surface:
                        if star_state == 'ellipse':
                            scale = boss_info.get('cross_phase2_ellipse_scale')
                            if not scale or scale[0] >= scale[1]:
                                scale = (0.75, 1.3)
                                boss_info['cross_phase2_ellipse_scale'] = scale
                            width = max(4, int(disc_surface.get_width() * scale[0]))
                            height = max(4, int(disc_surface.get_height() * scale[1]))
                            render_surface = pygame.transform.smoothscale(disc_surface, (width, height))
                        else:
                            render_surface = disc_surface
                elif star_state == 'trapezoid':
                    dims = boss_info.get('cross_phase2_trapezoid_dims')
                    if not dims:
                        dims = (boss_radius * 2 + 60, boss_radius + 80)
                        boss_info['cross_phase2_trapezoid_dims'] = dims
                    trap_surface = boss_info.get('cross_phase2_trapezoid_surface')
                    if trap_surface is None or trap_surface.get_width() <= 0 or trap_surface.get_height() <= 0:
                        trap_surface = build_rainbow_trapezoid_surface(*dims)
                        boss_info['cross_phase2_trapezoid_surface'] = trap_surface
                    render_surface = trap_surface
                else:
                    base_radius = boss_info.get('cross_phase2_star_radius_cached') or (boss_radius + 40)
                    star_surface = boss_info.get('cross_phase2_star_surface')
                    cached_radius = boss_info.get('cross_phase2_star_radius_cached')
                    if star_surface is None or cached_radius != base_radius or star_surface.get_width() <= 0 or star_surface.get_height() <= 0:
                        star_surface = build_rainbow_star_surface(base_radius)
                        boss_info['cross_phase2_star_surface'] = star_surface
                        boss_info['cross_phase2_star_radius_cached'] = base_radius
                    render_surface = star_surface

                if render_surface:
                    if star_state in ('star', 'transition'):
                        rotation = boss_info.get('cross_star_rotation', 0.0)
                        render_surface = pygame.transform.rotate(render_surface, rotation)
                    if star_alpha < 255:
                        temp_surface = render_surface.copy()
                        temp_surface.set_alpha(star_alpha)
                        render_surface = temp_surface
                    rect = render_surface.get_rect(center=(int(boss_x), int(boss_y)))
                    screen.blit(render_surface, rect)

            moon_beams = boss_info.get('cross_phase2_moon_beams', [])
            if moon_beams:
                for beam in moon_beams:
                    origin = beam.get('origin')
                    target = beam.get('target')
                    if not origin or not target:
                        continue
                    ox, oy = origin
                    tx, ty = target
                    state = beam.get('state')
                    width = beam.get('width', 10)
                    if state == 'warning':
                        color = (255, 160, 120)
                        line_w = max(2, width // 4)
                    elif state == 'telegraph':
                        color = (255, 230, 150)
                        line_w = max(2, width // 3)
                    else:
                        color = (170, 230, 255)
                        line_w = max(4, width)
                    pygame.draw.line(screen, color, (int(ox), int(oy)), (int(tx), int(ty)), line_w)
                    if state == 'warning':
                        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 70.0)
                        warn_tip = pygame.Surface((line_w * 4, line_w * 4), pygame.SRCALPHA)
                        pygame.draw.circle(warn_tip, (255, 200, 160, int(140 * pulse)), (line_w * 2, line_w * 2), max(2, line_w))
                        warn_tip_rect = warn_tip.get_rect(center=(int(tx), int(ty)))
                        screen.blit(warn_tip, warn_tip_rect)
                    elif state == 'firing':
                        tip = (int(tx), int(ty))
                        pygame.draw.circle(screen, (255, 255, 255), tip, max(3, line_w // 2))
            moons = boss_info.get('cross_phase2_moons', [])
            if moons:
                base_surface = None
                cached_radius = boss_info.get('cross_phase2_moon_surface_radius')
                if cached_radius != moons[0].get('radius', 18) or boss_info.get('cross_phase2_moon_surface') is None:
                    base_surface = build_orbit_moon_surface(moons[0].get('radius', 18))
                    boss_info['cross_phase2_moon_surface'] = base_surface
                    boss_info['cross_phase2_moon_surface_radius'] = moons[0].get('radius', 18)
                else:
                    base_surface = boss_info.get('cross_phase2_moon_surface')
                for moon in moons:
                    mx = moon.get('x', boss_x)
                    my = moon.get('y', boss_y)
                    radius = moon.get('radius', 18)
                    if base_surface and radius != boss_info.get('cross_phase2_moon_surface_radius'):
                        base_surface = build_orbit_moon_surface(radius)
                        boss_info['cross_phase2_moon_surface'] = base_surface
                        boss_info['cross_phase2_moon_surface_radius'] = radius
                    surface = boss_info.get('cross_phase2_moon_surface')
                    if not surface:
                        continue
                    angle = math.degrees(math.atan2(my - boss_y, mx - boss_x)) - 90
                    rotated = pygame.transform.rotate(surface, angle)
                    rect = rotated.get_rect(center=(int(mx), int(my)))
                    screen.blit(rotated, rect)

            if cross_mode in ('phase1', 'phase2'):
                for fall in boss_info.get('cross_falls', []):
                    fall_rect = fall.get('rect')
                    fall_surface = fall.get('surface')
                    if fall_surface is not None and fall_rect is not None:
                        screen.blit(fall_surface, fall_rect)
                wall_attack = boss_info.get('cross_wall_attack')
                if wall_attack:
                    state = wall_attack.get('state')
                    tele_surface = None
                    if state == 'telegraph':
                        tele_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                        lane_sample = {}
                        for spear in wall_attack.get('spears', []):
                            lane = spear.get('lane')
                            if lane not in lane_sample:
                                lane_sample[lane] = spear
                        for spear in lane_sample.values():
                            base_color = (255, 110, 110, 120)
                            surface_ref = spear.get('surface')
                            surf_height = surface_ref.get_height() if surface_ref else (spear.get('rect').height if spear.get('rect') else 0)
                            if surf_height <= 0:
                                continue
                            top = int(spear['y'] - surf_height / 2)
                            left_rect = pygame.Rect(0, top, 70, surf_height)
                            right_rect = pygame.Rect(WIDTH - 70, top, 70, surf_height)
                            tele_surface.fill(base_color, left_rect)
                            tele_surface.fill(base_color, right_rect)
                    if state in ('advance', 'hold', 'retract'):
                        for spear in wall_attack.get('spears', []):
                            rect_spear = spear.get('rect')
                            surf_spear = spear.get('surface')
                            if rect_spear and surf_spear:
                                screen.blit(surf_spear, rect_spear)
                    else:
                        for spear in wall_attack.get('spears', []):
                            rect_spear = spear.get('rect')
                            surf_spear = spear.get('surface')
                            if rect_spear and surf_spear:
                                screen.blit(surf_spear, rect_spear)
                    if tele_surface is not None:
                        screen.blit(tele_surface, (0, 0))

            for fx in boss_info.get('cross_transition_effects', []):
                ttl = fx.get('ttl', 0)
                max_ttl = max(1, fx.get('max_ttl', ttl if ttl > 0 else 1))
                ratio = max(0.0, min(1.0, ttl / max_ttl))
                alpha = int(255 * ratio)
                radius = int(max(6, fx.get('radius', 14)))
                if alpha <= 0 or radius <= 0:
                    continue
                effect_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(effect_surface, (255, 210, 120, alpha), (radius, radius), radius)
                pygame.draw.circle(effect_surface, (255, 255, 255, min(255, alpha + 40)), (radius, radius), max(2, radius // 3), 2)
                effect_rect = effect_surface.get_rect(center=(int(fx.get('x', boss_x)), int(fx.get('y', boss_y))))
                screen.blit(effect_surface, effect_rect)
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
    # ブラックアウト演出撤去
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

    # 弾描画
    for bullet in bullets:
        draw_bullet(screen, bullet)

    # プレイヤー・シールド描画（無敵時は点滅）
    dash_inv_timer = dash_state.get('invincible_timer', 0) if 'dash_state' in globals() else 0
    should_draw_primary = True
    if player_invincible and dash_inv_timer <= 0:
        should_draw_primary = (player_invincible_timer // 6) % 2 == 0
    if should_draw_primary:
        draw_player_ship(screen, player, WHITE, (40, 40, 40))
    if player2:
        draw_player_ship(screen, player2, BULLET_COLOR_HOMING, (30, 60, 90))
    if leaf_orb_positions:
        for orb in leaf_orb_positions:
            draw_leaf_orb(screen, (orb['x'], orb['y']), orb['radius'], orb.get('angle', 0.0))
    
    # プレイヤー被弾時の爆発エフェクト（赤い円が拡大しながらフェードアウト）
    if explosion_timer < EXPLOSION_DURATION and explosion_pos:
        progress = explosion_timer / EXPLOSION_DURATION  # 0.0 ~ 1.0
        # 複数の円を描画して波紋効果
        for i in range(3):
            # 各円のタイミングをずらす
            wave_progress = max(0.0, min(1.0, progress - i * 0.15))
            if wave_progress > 0:
                # 半径は時間経過で拡大（15 → 50ピクセル）
                radius = int(15 + wave_progress * 35)
                # 透明度は時間経過で減少（255 → 0）
                alpha = int(255 * (1.0 - wave_progress))
                # 赤色の濃淡も変化させる
                red_val = max(100, 255 - int(wave_progress * 155))
                color = (red_val, 0, 0)
                
                # 半透明円を描画するためのサーフェス作成
                circle_surf = pygame.Surface((radius * 2 + 10, radius * 2 + 10), pygame.SRCALPHA)
                # 外側の円（太い輪郭）
                pygame.draw.circle(circle_surf, (*color, alpha), 
                                 (radius + 5, radius + 5), radius, max(2, int(6 - wave_progress * 4)))
                # 内側の薄い塗りつぶし
                inner_alpha = int(alpha * 0.3)
                pygame.draw.circle(circle_surf, (*color, inner_alpha), 
                                 (radius + 5, radius + 5), max(1, radius - 3))
                
                # 画面に描画
                screen.blit(circle_surf, 
                          (explosion_pos[0] - radius - 5, explosion_pos[1] - radius - 5))

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
    if has_leaf_shield:
        shield_color = (80, 255, 120)
        weapon_icons.append(("L", shield_color, True))
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

    present_frame()
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
                    # 第二形態はより大きく動かす
                    R = 220 if boss_info.get('phase',1) == 2 else 140
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
                    # 第二形態は移動間隔を短縮
                    interval = 90 if boss_info.get('phase',1) == 2 else _window_warp_interval
                    if _window_warp_timer >= interval:
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
        present_frame()
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
            elif move_mode == 'spiral':
                center = b.get('center')
                if not center:
                    cx, cy = b['rect'].center
                    center = [float(cx), float(cy)]
                angle = b.get('angle', 0.0) + b.get('spin_speed', 0.14)
                radius = b.get('radius', 14.0) + b.get('radius_speed', 0.32)
                forward = b.get('forward_speed', 2.4)
                drift_x = b.get('drift_x', 0.0)
                center[0] += drift_x
                center[1] += forward
                max_radius = b.get('max_radius', 120.0)
                if radius > max_radius:
                    radius = max_radius
                x = center[0] + math.cos(angle) * radius
                y = center[1] + math.sin(angle) * radius
                b['center'] = center
                b['angle'] = angle
                b['radius'] = radius
                b['rect'].center = (int(x), int(y))
                b['fx'], b['fy'] = x - b['rect'].width / 2.0, y - b['rect'].height / 2.0
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
            elif move_mode == 'spiral':
                center = b.get('center')
                if center is None:
                    center = [float(b['rect'].centerx), float(b['rect'].centery)]
                else:
                    center = [float(center[0]), float(center[1])]
                spin_speed = b.get('spin_speed', 0.18)
                radius_speed = b.get('radius_speed', 0.35)
                forward_speed = b.get('forward_speed', 2.5)
                angle = b.get('angle', 0.0) + spin_speed
                radius = max(4.0, b.get('radius', 12.0) + radius_speed)
                center[1] += forward_speed
                x = center[0] + radius * math.cos(angle)
                y = center[1] + radius * math.sin(angle)
                b['center'] = center
                b['angle'] = angle
                b['radius'] = radius
                rect = b.get('rect')
                if rect:
                    rect.center = (int(x), int(y))
                b['fx'] = x - rect.width / 2 if rect else x
                b['fy'] = y - rect.height / 2 if rect else y
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

    # リーフシールド: 自機周囲に回転する防御オーブ
    active_leaf_orbs = []
    if has_leaf_shield:
        leaf_angle = (leaf_angle + 0.08) % (2*math.pi)
        orb_count = 4
        shield_radius = max(32, player.width // 2 + 20)
        orb_radius = 10
        for i in range(orb_count):
            ang = leaf_angle + (2*math.pi * i / orb_count)
            ox = player.centerx + shield_radius * math.cos(ang)
            oy = player.centery + shield_radius * math.sin(ang)
            active_leaf_orbs.append({'x': ox, 'y': oy, 'radius': orb_radius, 'angle': ang})
        # 敵弾をブロック
        filtered_bullets = []
        for b in bullets:
            is_enemy_like = (b.get('type') == 'enemy') or b.get('reflect', False) or b.get('subtype') in ('crescent','mini_hito')
            if is_enemy_like:
                rect = b.get('rect')
                if not rect:
                    filtered_bullets.append(b)
                    continue
                bx, by = rect.center
                blocked = False
                for orb in active_leaf_orbs:
                    ox, oy, rad = orb['x'], orb['y'], orb['radius']
                    enclosing = rad + max(rect.width, rect.height) / 2
                    if (bx - ox)**2 + (by - oy)**2 <= enclosing * enclosing:
                        blocked = True
                        break
                if blocked:
                    continue
            filtered_bullets.append(b)
        bullets = filtered_bullets
    else:
        leaf_angle = 0.0
    leaf_orb_positions = active_leaf_orbs

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
                        play_enemy_hit()
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
                            play_enemy_hit()
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
                            play_reflect()
                if not damage:
                    cleaned_bullets.append(bullet)
                continue
            if boss_info["name"] == "蛇":
                main_size = int(boss_radius * 1.2)
                main_rect = pygame.Rect(boss_x - main_size//2, boss_y - main_size//2, main_size, main_size)
                if main_rect.colliderect(bullet["rect"]):
                    boss_hp -= bullet.get("power", 1.0)
                    boss_explosion_pos.append((bullet["rect"].centerx, bullet["rect"].centery))
                    play_enemy_hit()
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
                            play_reflect()
                            break
                if not damage:
                    cleaned_bullets.append(bullet)
                continue
            if boss_info["name"] == "赤バツボス":
                bx = bullet["rect"].centerx
                by = bullet["rect"].centery
                dx = bx - boss_x
                dy = by - boss_y
                if dx * dx + dy * dy < boss_radius * boss_radius:
                    cross_mode = boss_info.get('cross_phase_mode', 'phase1')
                    if cross_mode in ('transition_explosion', 'transition_blackout', 'phase2_intro'):
                        cleaned_bullets.append(bullet)
                        continue
                    if cross_mode == 'phase1':
                        current_hp = boss_info.get('cross_phase1_hp', boss_info.get('hp', 180))
                        boss_info['cross_phase1_hp'] = max(0, current_hp - bullet.get("power", 1.0))
                        boss_hp = boss_info['cross_phase1_hp']
                        boss_explosion_pos.append((bx, by))
                        play_enemy_hit()
                        if boss_hp <= 0:
                            boss_info['cross_phase_mode'] = 'transition_explosion'
                            boss_info['cross_transition_timer'] = 0
                            boss_info['cross_phase2_intro_timer'] = 0
                            boss_info['cross_blackout_alpha'] = 0
                            boss_info['cross_phase2_started'] = False
                            boss_info['cross_phase2_settings_applied'] = False
                            boss_info['cross_star_state'] = 'transition'
                            boss_info['cross_star_progress'] = 0.0
                            boss_info['cross_star_rotation'] = 0.0
                            boss_info['cross_attack_timer'] = 0
                            boss_info['cross_wall_attack'] = None
                            boss_info['cross_falls'] = []
                            boss_info['cross_last_pattern'] = None
                            boss_info['cross_active_hp_max'] = boss_info.get('cross_phase2_hp', current_hp)
                            boss_info['cross_phase2_hp'] = boss_info.get('cross_phase2_hp', current_hp)
                            boss_info['hp'] = boss_info['cross_phase2_hp']
                            boss_hp = boss_info['cross_phase2_hp']
                    elif cross_mode in ('phase2', 'phase2_intro', 'fullscreen_starstorm'):
                        if boss_info.get('cross_phase2_reflect', False):
                            bullet['reflect'] = True
                            if bullet.get('type') == 'homing':
                                bullet['type'] = 'normal'
                            speed_now = math.hypot(bullet.get('vx', 0.0), bullet.get('vy', -6.0))
                            speed_now = max(3.2, speed_now)
                            aim_ang = math.atan2(player.centery - boss_y, player.centerx - boss_x)
                            aim_ang += math.radians(random.uniform(-14, 14))
                            bullet['vx'] = speed_now * math.cos(aim_ang)
                            bullet['vy'] = speed_now * math.sin(aim_ang)
                            if bullet['vy'] <= 0:
                                bullet['vy'] = abs(bullet['vy']) + 0.6
                            play_reflect()
                            cleaned_bullets.append(bullet)
                            continue
                        phase2_hp = boss_info.get('cross_phase2_hp', boss_info.get('hp', 240))
                        phase2_hp = max(0, phase2_hp - bullet.get("power", 1.0))
                        boss_info['cross_phase2_hp'] = phase2_hp
                        boss_hp = phase2_hp
                        boss_info['hp'] = phase2_hp
                        if not boss_info.get('cross_phase2_fullscreen_done', False) and boss_info.get('cross_phase_mode') == 'phase2':
                            active_max = boss_info.get('cross_active_hp_max') or 0
                            if active_max and phase2_hp > 0 and phase2_hp <= active_max * 0.25:
                                # フルスクリーン機能をアンロック
                                fullscreen_unlocked = True
                                if not is_fullscreen:
                                    set_display_mode(True)
                                boss_info['cross_phase2_fullscreen_done'] = True
                        boss_explosion_pos.append((bx, by))
                        play_enemy_hit()
                        if boss_hp <= 0:
                            boss_alive = False
                            boss_explosion_timer = 0
                            explosion_pos = (boss_x, boss_y)
                    damage = True
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
                            if inside_outer and (not inside_inner or bullet.get('type') == 'homing'):
                                # 内円内でもホーミング弾はダメージを与える
                                p['hp'] = p.get('hp', 5) - bullet.get('power', 1.0)
                                boss_explosion_pos.append((bx, by))
                                play_enemy_hit()
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
                        if inside_outer and (not inside_inner or bullet.get('type') == 'homing'):
                            # 内円内でもホーミング弾はダメージを与える
                            boss_hp -= bullet.get("power", 1.0)
                            boss_explosion_pos.append((bx, by))
                            play_enemy_hit()
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
                        play_enemy_hit()
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
                            base_r = boss_info.get('base_radius') or boss_info.setdefault('base_radius', boss_radius)
                            boss_radius = int(base_r * (1 - BOUNCE_BOSS_SHRINK_STEP * new_stage))
                            boss_radius = max(25, boss_radius)
                            # 速度再計算（方向保持）
                            base_spd = boss_info.get('base_speed') or boss_info.setdefault('base_speed', BOUNCE_BOSS_SPEED)
                            speed_now = base_spd * (1 + BOUNCE_BOSS_SPEED_STEP * new_stage)
                            vx = boss_info.get('bounce_vx',0)
                            vy = boss_info.get('bounce_vy',0)
                            cur_speed = math.hypot(vx, vy) or 1
                            scale = speed_now / cur_speed
                            boss_info['bounce_vx'] = vx * scale
                            boss_info['bounce_vy'] = vy * scale
            if not damage:
                cleaned_bullets.append(bullet)
        bullets = cleaned_bullets
    if not boss_alive and boss_info and not boss_music_played:
        play_boss_clear_music()
        boss_music_played = True
    # ボス撃破後の爆発演出
    if not boss_alive and boss_explosion_timer < BOSS_EXPLOSION_DURATION:
        boss_explosion_timer += 1
    # ボスキャラの攻撃パターン
    if boss_alive:
        boss_attack_timer += 1
        # 楕円ボス: 水平往復移動 + コア開閉サイクル
        if boss_info and boss_info.get("name") == "楕円ボス":
            # スタート待機中はビームAIを停止（カウントしない）
            if waiting_for_space:
                boss_x += boss_info.get('move_dir', 1) * boss_speed if 'move_dir' in boss_info else 0
                # コアの開閉サイクルはそのまま/もしくは停止したいならここでreturn
                # ここではビームのみ凍結
            else:
                # 左右往復（端で折り返し）
                margin = 40
                if 'move_dir' not in boss_info:
                    boss_info['move_dir'] = 1
            # ビーム独立クールダウン（コアと独立）
                boss_info.setdefault('beam_state', 'idle')  # idle -> telegraph -> firing -> cooldown
                boss_info.setdefault('beam_timer', 0)
                boss_info.setdefault('beam_cd', 0)
            # 目標: コア1ループに約2回撃てるチンポ（短め）
                boss_info['beam_telegraph'] = 25
                boss_info['beam_firing'] = 44
                boss_info['beam_cooldown'] = 150
            # 進行
                if boss_info['beam_cd'] > 0:
                    boss_info['beam_cd'] -= 1
                state_b = boss_info.get('beam_state','idle')
                if state_b == 'idle':
                # 短めの間隔で攻撃開始（CDが0のとき）
                    if boss_info.get('beam_cd',0) <= 0:
                        # 予告開始（左右同時）
                        # 収束点（フォーカス）を固定: 予告開始時のプレイヤー位置
                        boss_info['beam_focus'] = (player.centerx, player.centery)
                        for side in ('left','right'):
                            cx, cy = ((boss_x - boss_radius), boss_y) if side=='left' else ((boss_x + boss_radius), boss_y)
                            theta = math.atan2(player.centery - cy, player.centerx - cx)
                            boss_info[f'{side}_beam'] = {'state':'telegraph','timer':0,'angle':theta}
                        boss_info['beam_state'] = 'telegraph'
                        boss_info['beam_timer'] = 0
                elif state_b == 'telegraph':
                    boss_info['beam_timer'] += 1
                    done = False
                    if boss_info['beam_timer'] >= boss_info['beam_telegraph']:
                        # 発射開始（各サイドのビームも firing に遷移）
                        boss_info['beam_state'] = 'firing'
                        boss_info['beam_timer'] = 0
                        for side in ('left','right'):
                            beam = boss_info.get(f'{side}_beam')
                            if beam:
                                beam['state'] = 'firing'
                                beam['timer'] = 0
                    # 各ビームのorigin更新とターゲット初期化
                    for side in ('left','right'):
                        beam = boss_info.get(f'{side}_beam')
                        if not beam: continue
                        beam['timer'] = beam.get('timer',0) + 1
                        small_h = boss_radius*2//3
                        cx, cy = ((boss_x - boss_radius), boss_y) if side=='left' else ((boss_x + boss_radius), boss_y)
                        ang = beam.get('angle', 0.0)
                        rot = ang - math.pi/2
                        ox = cx + (-math.sin(rot)) * (small_h/2)
                        oy = cy + ( math.cos(rot)) * (small_h/2)
                        beam['origin'] = (int(ox), int(oy))
                        focus = boss_info.get('beam_focus')
                        if focus:
                            dx = focus[0] - ox; dy = focus[1] - oy
                            l = math.hypot(dx, dy) or 1.0
                            dirx = dx / l; diry = dy / l
                            beam['target'] = (int(ox + dirx*1200), int(oy + diry*1200))
                        elif 'target' not in beam:
                            dirx = -math.sin(rot); diry = math.cos(rot)
                            beam['target'] = (int(ox + dirx*1200), int(oy + diry*1200))
                elif state_b == 'firing':
                    boss_info['beam_timer'] += 1
                    # 更新と当たりは既存の描画/衝突ロジックが参照
                    for side in ('left','right'):
                        beam = boss_info.get(f'{side}_beam')
                        if not beam: continue
                        beam['timer'] = beam.get('timer',0) + 1
                        small_h = boss_radius*2//3
                        cx, cy = ((boss_x - boss_radius), boss_y) if side=='left' else ((boss_x + boss_radius), boss_y)
                        ang = beam.get('angle', 0.0)
                        rot = ang - math.pi/2
                        ox = cx + (-math.sin(rot)) * (small_h/2)
                        oy = cy + ( math.cos(rot)) * (small_h/2)
                        beam['origin'] = (int(ox), int(oy))
                        focus = boss_info.get('beam_focus')
                        if focus:
                            dx = focus[0] - ox; dy = focus[1] - oy
                            l = math.hypot(dx, dy) or 1.0
                            dirx = dx / l; diry = dy / l
                            beam['target'] = (int(ox + dirx*1200), int(oy + diry*1200))
                    if boss_info['beam_timer'] >= boss_info['beam_firing']:
                        boss_info['beam_state'] = 'cooldown'
                        boss_info['beam_timer'] = 0
                        # ビーム終了
                        boss_info['left_beam'] = None
                        boss_info['right_beam'] = None
                        boss_info['beam_cd'] = boss_info['beam_cooldown']
                        boss_info['beam_focus'] = None
                elif state_b == 'cooldown':
                    # クールダウン経過で待機へ
                    if boss_info.get('beam_cd',0) <= 0:
                        boss_info['beam_state'] = 'idle'
                        boss_info['beam_timer'] = 0
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
                # 発射頻度を落とす: 待機を元サイクルより長めに
                if boss_info['core_timer'] >= max(1, int(cycle * 1.25)):
                    boss_info['core_state'] = 'opening'
                    boss_info['core_timer'] = 0
            elif cs == 'opening':
                gap = min(gap_target, gap + gap_step)
                boss_info['core_gap'] = gap
                if gap >= gap_target:
                    boss_info['core_state'] = 'open_hold'
                    boss_info['core_timer'] = 0
                    # コアが開いた瞬間に多層リング弾を一斉発射（層・数・速度・オフセット）
                    layers = [
                        {'n': 10, 'speed': 3.4, 'offset': 0.00},
                        {'n': 14, 'speed': 4.0, 'offset': 0.10*math.pi},
                        {'n': 18, 'speed': 4.6, 'offset': 0.20*math.pi},
                        {'n': 22, 'speed': 5.0, 'offset': 0.30*math.pi},
                        {'n': 26, 'speed': 5.4, 'offset': 0.40*math.pi},
                    ]
                    for layer in layers:
                        n = layer['n']; spd = layer['speed']; off = layer['offset']
                        for i in range(n):
                            ang = off + 2*math.pi*i/n
                            vx = spd*math.cos(ang); vy = spd*math.sin(ang)
                            bullets.append({'rect': pygame.Rect(int(boss_x-4), int(boss_y-4), 8, 8),
                                            'type':'enemy','vx':vx,'vy':vy,'life':260,'power':1.0})
            elif cs == 'open_hold':
                if boss_info['core_timer'] >= open_hold:
                    # コアはビームと無関係に閉じる
                    boss_info['core_state'] = 'closing'
                    boss_info['core_timer'] = 0
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
                    pats = ['star_spread5', 'starfield_spin', 'star_burst', 'constellation', 'star_curtain', 'spiral_swarm', 'side_beam']
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
                handled = False
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
                                bullets.append({
                                    'rect': pygame.Rect(int(org['x']-6), int(org['y']-6), 12, 12),
                                    'type': 'enemy',
                                    'vx': vx,
                                    'vy': vy,
                                    'power': 1.0,
                                    'life': 360,
                                    'shape': 'star',
                                    'color': (255, 230, 0),
                                    'trail_ttl': 12
                                })
                    if t > 60:
                        bi['patt_state'] = 'idle'
                        bi['patt_timer'] = 0
                        bi['patt_cd'] = 55
                        bi['last_patt'] = ch
                    handled = True
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
                    handled = True

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
                    handled = True

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
                    handled = True

                elif ch == 'spiral_swarm':
                    if t in (1, 36, 72):
                        for org in origins:
                            count = 6
                            base_radius = 8.0
                            for i in range(count):
                                ang = (2*math.pi*i/count) + (t * 0.07)
                                rect = pygame.Rect(int(org['x']-6), int(org['y']-6), 12, 12)
                                bullets.append({
                                    'rect': rect,
                                    'type': 'enemy',
                                    'move': 'spiral',
                                    'center': [float(org['x']), float(org['y'])],
                                    'angle': ang,
                                    'radius': base_radius + i * 2.5,
                                    'radius_speed': 0.38 + 0.02 * i,
                                    'spin_speed': 0.16 + 0.015 * i,
                                    'forward_speed': 2.2 + 0.12 * i,
                                    'life': 360,
                                    'power': 1.0,
                                    'shape': 'star',
                                    'color': (255, 230, 140),
                                    'trail_ttl': 14
                                })
                    if t > 140:
                        bi['patt_state']='idle'; bi['patt_timer']=0; bi['patt_cd']=85; bi['last_patt']=ch
                    handled = True

                elif ch == 'side_beam':
                    lasers = bi.setdefault('side_lasers', [])
                    if t in (1, 90):
                        choices = ['left', 'right']
                        random.shuffle(choices)
                        for org in origins[:2]:
                            if not choices:
                                direction = random.choice(['left', 'right'])
                            else:
                                direction = choices.pop(0)
                            part_ref = org if org in bi.get('parts', []) else None
                            lasers.append({
                                'state': 'charge',
                                'timer': 0,
                                'direction': direction,
                                'charge_time': 42,
                                'fire_time': 75,
                                'fade_time': 22,
                                'width': 34,
                                'origin_static': (org['x'], org['y']),
                                'part_ref': part_ref
                            })
                    if t > 170:
                        bi['patt_state']='idle'; bi['patt_timer']=0; bi['patt_cd']=95; bi['last_patt']=ch
                    handled = True

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
                    handled = True

                if not handled:
                    # 未知パターンや異常時はフェイルセーフでアイドルに戻す
                    if t > 200 or ch is None:
                        bi['patt_state'] = 'idle'
                        bi['patt_timer'] = 0
                        bi['patt_cd'] = 60
                        bi['last_patt'] = ch
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
        if boss_info and boss_info["name"] == "赤バツボス":
            if boss_alive:
                boss_info.setdefault('cross_phase_mode', 'phase1')
                boss_info.setdefault('cross_falls', [])
                boss_info.setdefault('cross_wall_attack', None)
                boss_info.setdefault('cross_last_pattern', None)
                boss_info.setdefault('cross_star_state', 'cross')
                boss_info.setdefault('cross_star_progress', 0.0)
                boss_info.setdefault('cross_star_rotation', 0.0)
                boss_info.setdefault('cross_star_spin_speed', 1.6)
                boss_info.setdefault('cross_star_transition_speed', 0.02)
                boss_info.setdefault('cross_star_surface', None)
                boss_info.setdefault('cross_star_surface_radius', 0)
                boss_info.setdefault('cross_transition_effects', [])
                boss_info.setdefault('cross_active_hp_max', boss_info.get('hp', 180))
                boss_info.setdefault('cross_phase2_moons', [])
                boss_info.setdefault('cross_phase2_moon_beams', [])
                boss_info.setdefault('cross_phase2_reflect', False)
                boss_info.setdefault('cross_phase2_moon_duration', 360)
                boss_info.setdefault('cross_phase2_moon_orbit_radius', boss_radius + 70)
                cross_mode = boss_info.get('cross_phase_mode', 'phase1')

                def decay_transition_effects(growth=4.0):
                    updated = []
                    for fx in boss_info.get('cross_transition_effects', []):
                        fx['ttl'] -= 1
                        fx['radius'] += fx.get('growth', growth)
                        if fx['ttl'] > 0:
                            updated.append(fx)
                    boss_info['cross_transition_effects'] = updated

                if is_fullscreen:
                    boss_info['cross_wall_attack'] = None
                    boss_info['cross_falls'] = []
                    boss_info['cross_phase2_moon_beams'] = []
                    boss_info['cross_phase2_moons'] = []
                    boss_info['cross_phase2_state'] = 'fullscreen_starstorm'
                    boss_info['cross_phase_mode'] = 'fullscreen_starstorm'
                    boss_info['cross_phase2_bounce_squish'] = None
                    boss_info['cross_transition_effects'] = []
                    boss_info['cross_star_state'] = 'star'
                    boss_info['cross_star_spin_speed'] = max(2.0, boss_info.get('cross_star_spin_speed', 2.0))
                    boss_info['cross_star_rotation'] = (boss_info.get('cross_star_rotation', 0.0) + boss_info.get('cross_star_spin_speed', 2.0)) % 360
                    boss_x = WIDTH / 2
                    boss_y = boss_info.get('cross_base_y', 120)
                    # フルスクリーン時の星弾幕密度調整
                    boss_info['star_rain_interval'] = 18
                    boss_info['star_rain_batch'] = 3
                    if not boss_info.get('star_rain_active'):
                        boss_info['star_rain_active'] = True
                        boss_info['star_rain_timer'] = 0
                    update_star_rain_phase(boss_info, player, bullets)
                elif cross_mode in ('phase1', 'phase2'):
                    decay_transition_effects(3.0)
                    boss_info.setdefault('cross_star_trigger_ratio', 0.55)
                    phase_speed = boss_info.get('cross_phase_speed', 0.015)
                    spin_speed = boss_info.get('cross_spin_speed', 0.05)
                    boss_info['cross_phase'] = boss_info.get('cross_phase', 0.0) + phase_speed
                    boss_info['cross_angle'] = boss_info.get('cross_angle', 0.0) + spin_speed
                    orbit = boss_info.get('cross_orbit', 80)
                    bob = boss_info.get('cross_bob', 28)
                    base_y = boss_info.get('cross_base_y', 120)
                    boss_x = WIDTH / 2 + math.sin(boss_info['cross_phase']) * orbit
                    boss_y = base_y + math.sin(boss_info['cross_phase'] * 1.8) * bob

                    boss_info['cross_attack_timer'] = boss_info.get('cross_attack_timer', 0) + 1

                    active_hp_max = max(1, boss_info.get('cross_active_hp_max', boss_info.get('hp', 180)))
                    current_hp = max(0, boss_hp)
                    hp_ratio = current_hp / active_hp_max
                    initial_hp = boss_info.get('initial_hp') or boss_info.setdefault('initial_hp', active_hp_max)
                    if cross_mode == 'phase1':
                        if boss_info.get('star_rain_active'):
                            boss_info['star_rain_active'] = False
                            boss_info['star_rain_timer'] = 0
                    else:
                        trigger_ratio = boss_info.get('star_rain_trigger_ratio', boss_info.get('cross_phase3_trigger_ratio', 0.25))
                        trigger_hp = initial_hp * trigger_ratio if initial_hp else 0
                        if trigger_hp and current_hp <= trigger_hp:
                            if not boss_info.get('star_rain_active'):
                                boss_info['star_rain_active'] = True
                                boss_info['star_rain_timer'] = 0
                                boss_info.setdefault('star_rain_interval', 8)
                                boss_info.setdefault('star_rain_batch', 12)
                        if boss_info.get('star_rain_active'):
                            update_star_rain_phase(boss_info, player, bullets)
                    base_cd = boss_info.get('cross_attack_cooldown', 150)
                    if cross_mode == 'phase2':
                        base_cd = max(60, int(base_cd * 0.8))
                    dynamic_cd = max(50 if cross_mode == 'phase2' else 70,
                                     int(base_cd * (0.45 + 0.55 * hp_ratio)))

                    star_state = boss_info.get('cross_star_state', 'cross')
                    if cross_mode == 'phase1':
                        # 第一形態では常に赤いクロスのまま維持する
                        boss_info['cross_star_state'] = 'cross'
                        boss_info['cross_star_progress'] = 0.0
                        star_state = 'cross'
                    else:
                        if boss_info.get('cross_star_state') != 'circle':
                            boss_info['cross_star_state'] = 'star'
                        boss_info['cross_star_progress'] = 1.0
                        star_state = boss_info.get('cross_star_state', 'star')
                        if not boss_info.get('cross_phase2_settings_applied', False):
                            boss_info['cross_phase2_settings_applied'] = True
                            boss_info['cross_phase_speed'] = boss_info.get('cross_phase_speed', 0.015) * 1.3
                            boss_info['cross_spin_speed'] = boss_info.get('cross_spin_speed', 0.05) * 1.5
                            boss_info['cross_orbit'] = int(boss_info.get('cross_orbit', 80) * 1.18)
                            boss_info['cross_bob'] = int(boss_info.get('cross_bob', 28) * 1.25)
                            boss_info['cross_attack_cooldown'] = max(60, int(boss_info.get('cross_attack_cooldown', 150) * 0.7))
                            boss_info['cross_star_spin_speed'] = max(2.6, boss_info.get('cross_star_spin_speed', 1.6) * 1.6)

                    if boss_info.get('cross_star_state') in ('transition', 'star', 'circle', 'trapezoid', 'ellipse'):
                        spin = boss_info.get('cross_star_spin_speed', 1.6)
                        boss_info['cross_star_rotation'] = (boss_info.get('cross_star_rotation', 0.0) + spin) % 360

                    max_falls = 22 if cross_mode == 'phase1' else 28
                    wall_attack = boss_info.get('cross_wall_attack')

                    if cross_mode == 'phase2':
                        boss_info['cross_wall_attack'] = None
                        state = boss_info.get('cross_phase2_state', 'idle')
                        valid_states = {
                            'idle', 'move_center', 'charge_circle', 'bounce',
                            'rise_top', 'rainbow_charge', 'rainbow_attack',
                            'fall_barrage', 'ground_barrage', 'return_center', 'reset_star',
                            'moon_intro', 'moon_attack', 'moon_cleanup'
                        }
                        if state not in valid_states:
                            state = 'idle'
                            boss_info['cross_phase2_state'] = state
                        timer = boss_info.get('cross_phase2_timer', 0)
                        pos = boss_info.get('cross_phase2_pos')
                        if not pos:
                            pos = [float(boss_x), float(boss_y)]
                            boss_info['cross_phase2_pos'] = pos
                        center_target = boss_info.get('cross_phase2_target_center', (WIDTH / 2.0, base_y))
                        boss_info['cross_falls'] = []

                        if state == 'idle':
                            boss_info['cross_phase2_pos'] = [float(boss_x), float(boss_y)]
                            boss_info['cross_phase2_timer'] = timer + 1
                            boss_info['cross_attack_timer'] = boss_info.get('cross_attack_timer', 0) + 1
                            cooldown = boss_info.get('cross_phase2_idle_cooldown', 120)
                            if boss_info['cross_attack_timer'] >= cooldown:
                                pattern = boss_info.get('cross_phase2_next_pattern', 'bounce')
                                boss_info['cross_phase2_active_pattern'] = pattern
                                boss_info['cross_phase2_timer'] = 0
                                boss_info['cross_phase2_charge_ratio'] = 0.0
                                boss_info['cross_phase2_disc_surface'] = None
                                boss_info['cross_phase2_disc_radius'] = 0
                                boss_info['cross_phase2_disc_spin'] = 0.0
                                boss_info['cross_phase2_trapezoid_surface'] = None
                                boss_info['cross_phase2_trapezoid_width'] = 0
                                boss_info['cross_phase2_trapezoid_height'] = 0
                                boss_info['cross_phase2_bounce_vel'] = [0.0, 0.0]
                                boss_info['cross_attack_timer'] = 0
                                if pattern == 'bounce':
                                    boss_info['cross_phase2_state'] = 'move_center'
                                    boss_info['cross_phase2_pos'] = [float(boss_x), float(boss_y)]
                                    boss_info['cross_phase2_target_center'] = (WIDTH / 2.0, base_y)
                                    base_goal = max(4, int(5 + (1.0 - hp_ratio) * 3))
                                    boss_info['cross_phase2_bounce_hits'] = 0
                                    boss_info['cross_phase2_bounce_goal'] = base_goal
                                    base_speed = 7.4 + (1.0 - hp_ratio) * 1.8
                                    boss_info['cross_phase2_bounce_speed'] = base_speed
                                    boss_info['cross_phase2_bounce_squish'] = None
                                    boss_info['cross_phase2_bounce_squish_duration'] = boss_info.get('cross_phase2_bounce_squish_duration', 16)
                                    boss_info['cross_phase2_bounce_timer'] = 0
                                    boss_info['cross_phase2_bounce_limit'] = max(300, int(base_goal * 60))
                                elif pattern == 'rainbow_drop':
                                    top_y = max(boss_radius + 72, 100)
                                    bottom_limit = HEIGHT - max(boss_radius + 30, 70)
                                    if bottom_limit <= top_y + 90:
                                        bottom_y = min(bottom_limit, top_y + 90)
                                    else:
                                        bottom_y = bottom_limit
                                    boss_info['cross_phase2_state'] = 'rise_top'
                                    boss_info['cross_phase2_pos'] = [float(boss_x), float(boss_y)]
                                    boss_info['cross_phase2_target_center'] = (WIDTH / 2.0, base_y)
                                    boss_info['cross_phase2_target_top'] = (WIDTH / 2.0, top_y)
                                    boss_info['cross_phase2_target_bottom'] = (WIDTH / 2.0, bottom_y)
                                    boss_info['cross_phase2_fall_speed'] = 0.0
                                    boss_info['cross_phase2_rainbow_timer'] = 0
                                    boss_info['cross_phase2_rainbow_angle'] = random.uniform(0.0, math.tau)
                                    boss_info['cross_phase2_rainbow_rings'] = 0
                                    boss_info['cross_phase2_rainbow_burst_step'] = 0
                                    boss_info['cross_phase2_ground_timer'] = 0
                                    boss_info['cross_phase2_charge_ratio'] = 0.0
                                    boss_info['cross_star_state'] = 'trapezoid'
                                    boss_info['cross_star_spin_speed'] = max(3.0, boss_info.get('cross_star_spin_speed', 2.6))
                                    # 台形に変形時の効果音（一度だけ）
                                    if boss_info.get('cross_last_transform_shape') != 'trapezoid':
                                        play_shape_transform()
                                        boss_info['cross_last_transform_shape'] = 'trapezoid'
                                    boss_info['cross_transition_effects'].append({
                                        'x': boss_x,
                                        'y': boss_y,
                                        'radius': random.uniform(boss_radius * 0.5, boss_radius * 0.9),
                                        'growth': random.uniform(3.0, 5.0),
                                        'ttl': 24,
                                        'max_ttl': 24
                                    })
                                else:
                                    boss_info['cross_phase2_state'] = 'moon_intro'
                                    boss_info['cross_phase2_pos'] = [float(boss_x), float(boss_y)]
                                    boss_info['cross_phase2_target_center'] = (WIDTH / 2.0, base_y)
                                    boss_info['cross_phase2_moons'] = []
                                    boss_info['cross_phase2_moon_beams'] = []
                                    boss_info['cross_phase2_moon_timer'] = 0
                                    boss_info['cross_phase2_moon_duration'] = 360
                                    boss_info['cross_phase2_moon_orbit_radius'] = boss_info.get('cross_phase2_moon_orbit_radius', boss_radius + 70)
                                    boss_info['cross_phase2_reflect'] = False
                                    boss_info['cross_phase2_charge_ratio'] = 0.0
                                    boss_info['cross_star_state'] = 'ellipse'
                                    boss_info['cross_phase2_ellipse_scale'] = (0.75, 1.3)
                                    # 楕円に変形時の効果音（一度だけ）
                                    if boss_info.get('cross_last_transform_shape') != 'ellipse':
                                        play_shape_transform()
                                        boss_info['cross_last_transform_shape'] = 'ellipse'
                                    boss_info['cross_phase2_moon_spin_backup'] = boss_info.get('cross_star_spin_speed', 0.0)
                                    boss_info['cross_star_spin_speed'] = 0.0
                                    boss_info['cross_phase2_disc_surface'] = None
                                    boss_info['cross_phase2_disc_radius'] = 0
                                    boss_info['cross_phase2_disc_spin'] = 0.0
                                    boss_info['cross_transition_effects'].append({
                                        'x': boss_x,
                                        'y': boss_y,
                                        'radius': random.uniform(boss_radius * 0.5, boss_radius * 0.9),
                                        'growth': random.uniform(3.0, 4.5),
                                        'ttl': 26,
                                        'max_ttl': 26
                                    })
                        elif state == 'move_center':
                            speed = 6.4
                            dx = center_target[0] - pos[0]
                            dy = center_target[1] - pos[1]
                            dist = math.hypot(dx, dy)
                            if dist <= speed:
                                pos[0], pos[1] = center_target
                                boss_info['cross_phase2_state'] = 'charge_circle'
                                boss_info['cross_phase2_timer'] = 0
                                boss_info['cross_phase2_charge_ratio'] = 0.0
                                boss_info['cross_phase2_disc_surface'] = None
                                boss_info['cross_phase2_disc_radius'] = 0
                                boss_info['cross_phase2_disc_spin'] = 0.0
                            else:
                                pos[0] += (dx / dist) * speed
                                pos[1] += (dy / dist) * speed
                                boss_info['cross_phase2_timer'] = timer + 1
                            boss_x, boss_y = pos[0], pos[1]
                            boss_info['cross_phase2_pos'] = pos
                            boss_info['cross_attack_timer'] = 0
                        elif state == 'charge_circle':
                            boss_info['cross_phase2_timer'] = timer + 1
                            charge_total = 48
                            boss_info['cross_phase2_charge_ratio'] = min(1.0, boss_info['cross_phase2_timer'] / float(charge_total))
                            if boss_info['cross_phase2_timer'] >= 14 and boss_info.get('cross_star_state') != 'circle':
                                # 丸に変形時の効果音（一度だけ）
                                if boss_info.get('cross_last_transform_shape') != 'circle':
                                    play_shape_transform()
                                    boss_info['cross_last_transform_shape'] = 'circle'
                                boss_info['cross_star_state'] = 'circle'
                                boss_info['cross_phase2_disc_surface'] = None
                                boss_info['cross_phase2_disc_radius'] = 0
                            boss_info['cross_phase2_disc_spin'] = boss_info.get('cross_phase2_disc_spin', 0.0) + 2.2
                            if boss_info['cross_phase2_timer'] % 6 == 0:
                                boss_info['cross_transition_effects'].append({
                                    'x': pos[0] + random.uniform(-12, 12),
                                    'y': pos[1] + random.uniform(-12, 12),
                                    'radius': random.uniform(boss_radius * 0.4, boss_radius * 0.8),
                                    'growth': random.uniform(3.5, 5.5),
                                    'ttl': 20,
                                    'max_ttl': 20
                                })
                            boss_x, boss_y = pos[0], pos[1]
                            if boss_info['cross_phase2_timer'] >= charge_total:
                                boss_info['cross_phase2_state'] = 'bounce'
                                boss_info['cross_phase2_timer'] = 0
                                speed = boss_info.get('cross_phase2_bounce_speed', 7.4 + (1.0 - hp_ratio) * 1.8)
                                boss_info['cross_phase2_bounce_speed'] = speed
                                angle_choices = [math.radians(a) for a in (35, 55, 125, 145, 215, 235, 305, 325)]
                                angle = random.choice(angle_choices) + math.radians(random.uniform(-8, 8))
                                vx = math.cos(angle) * speed
                                vy = math.sin(angle) * speed
                                min_vert = speed * 0.28
                                if abs(vy) < min_vert:
                                    vy = min_vert if vy >= 0 else -min_vert
                                    vx = math.copysign(math.sqrt(max(speed * speed - vy * vy, 0.1)), vx)
                                boss_info['cross_phase2_bounce_vel'] = [vx, vy]
                                boss_info['cross_phase2_bounce_timer'] = 0
                                boss_info['cross_phase2_bounce_hits'] = 0
                                boss_info['cross_phase2_bounce_squish'] = None
                                boss_info['cross_phase2_charge_ratio'] = 1.0
                                boss_info['cross_phase2_disc_spin'] = boss_info.get('cross_phase2_disc_spin', 0.0) + 1.5
                            boss_info['cross_phase2_pos'] = pos
                            boss_info['cross_attack_timer'] = 0
                        elif state == 'rise_top':
                            boss_info['cross_phase2_timer'] = timer + 1
                            target_top = boss_info.get('cross_phase2_target_top', (WIDTH / 2.0, max(boss_radius + 72, 100)))
                            speed = 7.4
                            dx = target_top[0] - pos[0]
                            dy = target_top[1] - pos[1]
                            dist = math.hypot(dx, dy)
                            if boss_info.get('cross_star_state') != 'trapezoid':
                                # 台形に変形時の効果音（一度だけ）
                                if boss_info.get('cross_last_transform_shape') != 'trapezoid':
                                    play_shape_transform()
                                    boss_info['cross_last_transform_shape'] = 'trapezoid'
                                boss_info['cross_star_state'] = 'trapezoid'
                            boss_info['cross_phase2_disc_spin'] = boss_info.get('cross_phase2_disc_spin', 0.0) + 2.6
                            if dist <= speed:
                                pos[0], pos[1] = target_top
                                boss_info['cross_phase2_state'] = 'rainbow_charge'
                                boss_info['cross_phase2_timer'] = 0
                                boss_info['cross_phase2_charge_ratio'] = 0.0
                                boss_info['cross_phase2_rainbow_timer'] = 0
                                boss_info['cross_phase2_rainbow_angle'] = boss_info.get('cross_phase2_rainbow_angle', random.uniform(0.0, math.tau))
                                boss_info['cross_transition_effects'].append({
                                    'x': pos[0],
                                    'y': pos[1],
                                    'radius': random.uniform(boss_radius * 0.5, boss_radius * 0.9),
                                    'growth': random.uniform(3.0, 4.6),
                                    'ttl': 24,
                                    'max_ttl': 24
                                })
                            elif dist > 0:
                                pos[0] += (dx / dist) * speed
                                pos[1] += (dy / dist) * speed
                                if boss_info['cross_phase2_timer'] % 6 == 0:
                                    boss_info['cross_transition_effects'].append({
                                        'x': pos[0] + random.uniform(-10, 10),
                                        'y': pos[1] + random.uniform(-10, 10),
                                        'radius': random.uniform(boss_radius * 0.35, boss_radius * 0.6),
                                        'growth': random.uniform(2.6, 4.0),
                                        'ttl': 18,
                                        'max_ttl': 18
                                    })
                            boss_x, boss_y = pos[0], pos[1]
                            boss_info['cross_star_rotation'] = (boss_info.get('cross_star_rotation', 0.0) + boss_info.get('cross_star_spin_speed', 3.0)) % 360
                            boss_info['cross_phase2_pos'] = pos
                            boss_info['cross_phase2_charge_ratio'] = min(0.6, boss_info.get('cross_phase2_charge_ratio', 0.0) + 0.015)
                            boss_info['cross_attack_timer'] = 0
                        elif state == 'rainbow_charge':
                            boss_info['cross_phase2_timer'] = timer + 1
                            boss_x, boss_y = pos[0], pos[1]
                            charge_total = 38
                            ratio = min(1.0, boss_info['cross_phase2_timer'] / float(charge_total))
                            boss_info['cross_phase2_charge_ratio'] = ratio
                            spin_boost = boss_info.get('cross_star_spin_speed', 3.2)
                            boss_info['cross_star_rotation'] = (boss_info.get('cross_star_rotation', 0.0) + spin_boost + 0.6) % 360
                            if boss_info.get('cross_star_state') != 'trapezoid':
                                # 台形に変形時の効果音（一度だけ）
                                if boss_info.get('cross_last_transform_shape') != 'trapezoid':
                                    play_shape_transform()
                                    boss_info['cross_last_transform_shape'] = 'trapezoid'
                                boss_info['cross_star_state'] = 'trapezoid'
                            boss_info['cross_phase2_disc_spin'] = boss_info.get('cross_phase2_disc_spin', 0.0) + 3.0
                            if boss_info['cross_phase2_timer'] % 5 == 0:
                                boss_info['cross_transition_effects'].append({
                                    'x': boss_x + random.uniform(-12, 12),
                                    'y': boss_y + random.uniform(-10, 10),
                                    'radius': random.uniform(boss_radius * 0.5, boss_radius * 0.95),
                                    'growth': random.uniform(3.0, 4.8),
                                    'ttl': 20,
                                    'max_ttl': 20
                                })
                            if boss_info['cross_phase2_timer'] >= charge_total:
                                boss_info['cross_phase2_state'] = 'rainbow_attack'
                                boss_info['cross_phase2_timer'] = 0
                                boss_info['cross_phase2_rainbow_timer'] = 0
                                boss_info['cross_phase2_rainbow_burst_step'] = 0
                                boss_info['cross_phase2_charge_ratio'] = 1.0
                                boss_info['cross_transition_effects'].append({
                                    'x': boss_x,
                                    'y': boss_y,
                                    'radius': random.uniform(boss_radius * 0.8, boss_radius * 1.2),
                                    'growth': random.uniform(4.5, 6.0),
                                    'ttl': 26,
                                    'max_ttl': 26
                                })
                            boss_info['cross_phase2_pos'] = pos
                            boss_info['cross_attack_timer'] = 0
                        elif state == 'rainbow_attack':
                            boss_info['cross_phase2_timer'] = timer + 1
                            attack_timer = boss_info.get('cross_phase2_rainbow_timer', 0) + 1
                            boss_info['cross_phase2_rainbow_timer'] = attack_timer
                            boss_x, boss_y = pos[0], pos[1]
                            spin_amount = boss_info.get('cross_star_spin_speed', 3.2) + 1.4
                            boss_info['cross_star_rotation'] = (boss_info.get('cross_star_rotation', 0.0) + spin_amount) % 360
                            if boss_info.get('cross_star_state') != 'trapezoid':
                                # 台形に変形時の効果音（一度だけ）
                                if boss_info.get('cross_last_transform_shape') != 'trapezoid':
                                    play_shape_transform()
                                    boss_info['cross_last_transform_shape'] = 'trapezoid'
                                boss_info['cross_star_state'] = 'trapezoid'
                            boss_info['cross_phase2_disc_spin'] = boss_info.get('cross_phase2_disc_spin', 0.0) + 3.8
                            base_angle = boss_info.get('cross_phase2_rainbow_angle', 0.0)
                            base_angle = (base_angle + math.radians(8.0)) % math.tau
                            boss_info['cross_phase2_rainbow_angle'] = base_angle
                            rainbow_colors = [
                                (255, 60, 60),
                                (255, 150, 40),
                                (255, 230, 80),
                                (60, 255, 120),
                                (80, 140, 255),
                                (150, 80, 255),
                                (255, 90, 190)
                            ]
                            if attack_timer % 8 == 0:
                                ring_count = 10 + (attack_timer // 32) % 3
                                bullet_speed = 4.8 + (attack_timer % 40) * 0.03
                                for i in range(ring_count):
                                    ang = base_angle + math.tau * (i / ring_count)
                                    color = rainbow_colors[i % len(rainbow_colors)]
                                    bullets.append({
                                        'rect': pygame.Rect(int(boss_x - 5), int(boss_y - 5), 10, 10),
                                        'type': 'enemy',
                                        'vx': bullet_speed * math.cos(ang),
                                        'vy': bullet_speed * math.sin(ang),
                                        'life': 320,
                                        'power': 1.0,
                                        'shape': 'star',
                                        'color': color
                                    })
                            if attack_timer % 8 == 0:
                                boss_info['cross_transition_effects'].append({
                                    'x': boss_x + random.uniform(-16, 16),
                                    'y': boss_y + random.uniform(-16, 12),
                                    'radius': random.uniform(boss_radius * 0.4, boss_radius * 0.95),
                                    'growth': random.uniform(4.0, 6.2),
                                    'ttl': 22,
                                    'max_ttl': 22
                                })
                            if attack_timer >= 72:
                                boss_info['cross_phase2_state'] = 'fall_barrage'
                                boss_info['cross_phase2_timer'] = 0
                                boss_info['cross_phase2_rainbow_timer'] = 0
                                boss_info['cross_phase2_fall_speed'] = 6.2
                                boss_info['cross_phase2_charge_ratio'] = 1.0
                                center_target = boss_info.get('cross_phase2_target_center', (WIDTH / 2.0, base_y))
                                if center_target:
                                    pos[1] = center_target[1]
                            boss_info['cross_phase2_pos'] = pos
                            boss_info['cross_attack_timer'] = 0
                        elif state == 'fall_barrage':
                            fall_timer = boss_info.get('cross_phase2_timer', 0) + 1
                            fall_speed = boss_info.get('cross_phase2_fall_speed', 6.2)
                            fall_speed = min(fall_speed + 0.32, 18.0)
                            boss_info['cross_phase2_fall_speed'] = fall_speed
                            pos[1] += fall_speed
                            boss_x, boss_y = pos[0], pos[1]
                            boss_info['cross_phase2_pos'] = pos
                            if fall_timer % 9 == 0:
                                drop_columns = 3
                                base_offset = boss_radius * 0.55
                                for lane in range(drop_columns):
                                    offset = (lane - (drop_columns - 1) / 2.0) * base_offset
                                    spawn_x = boss_x + offset + random.uniform(-6, 6)
                                    spawn_y = boss_y + boss_radius * 0.15
                                    vy_drop = 6.6 + random.uniform(-0.35, 0.45)
                                    vx_drop = random.uniform(-0.6, 0.6)
                                    bullets.append({
                                        'rect': pygame.Rect(int(spawn_x - 5), int(spawn_y - 5), 10, 10),
                                        'type': 'enemy',
                                        'vx': vx_drop,
                                        'vy': vy_drop,
                                        'life': 220,
                                        'power': 1.0,
                                        'shape': 'orb',
                                        'color': (170, 200, 255)
                                    })
                            boss_info['cross_phase2_timer'] = fall_timer
                            boss_info['cross_phase2_charge_ratio'] = max(0.55, boss_info.get('cross_phase2_charge_ratio', 1.0) - 0.008)
                            boss_info['cross_phase2_disc_spin'] = boss_info.get('cross_phase2_disc_spin', 0.0) + 2.4
                            if boss_info.get('cross_star_state') != 'trapezoid':
                                # 台形に変形時の効果音（一度だけ）
                                if boss_info.get('cross_last_transform_shape') != 'trapezoid':
                                    play_shape_transform()
                                    boss_info['cross_last_transform_shape'] = 'trapezoid'
                                boss_info['cross_star_state'] = 'trapezoid'
                            if boss_info['cross_phase2_timer'] % 8 == 0:
                                pass
                            if boss_info['cross_phase2_timer'] % 7 == 0:
                                boss_info['cross_transition_effects'].append({
                                    'x': boss_x + random.uniform(-14, 14),
                                    'y': boss_y + random.uniform(-6, 6),
                                    'radius': random.uniform(boss_radius * 0.36, boss_radius * 0.74),
                                    'growth': random.uniform(3.0, 4.8),
                                    'ttl': 18,
                                    'max_ttl': 18
                                })
                            bottom_target = boss_info.get('cross_phase2_target_bottom', (WIDTH / 2.0, HEIGHT - boss_radius - 6))
                            if pos[1] >= bottom_target[1]:
                                pos[1] = bottom_target[1]
                                boss_info['cross_phase2_state'] = 'ground_barrage'
                                boss_info['cross_phase2_timer'] = 0
                                boss_info['cross_phase2_ground_timer'] = 0
                                boss_info['cross_phase2_fall_speed'] = 0.0
                                boss_info['cross_phase2_charge_ratio'] = max(0.6, boss_info.get('cross_phase2_charge_ratio', 0.6))
                                boss_info['cross_transition_effects'].append({
                                    'x': boss_x,
                                    'y': pos[1],
                                    'radius': random.uniform(boss_radius * 0.6, boss_radius * 1.0),
                                    'growth': random.uniform(3.4, 5.4),
                                    'ttl': 24,
                                    'max_ttl': 24
                                })
                            boss_info['cross_attack_timer'] = 0
                        elif state == 'ground_barrage':
                            boss_info['cross_phase2_timer'] = timer + 1
                            ground_timer = boss_info.get('cross_phase2_ground_timer', 0) + 1
                            boss_info['cross_phase2_ground_timer'] = ground_timer
                            boss_x, boss_y = pos[0], pos[1]
                            bottom_target = boss_info.get('cross_phase2_target_bottom', (WIDTH / 2.0, HEIGHT - boss_radius - 6))
                            if pos[1] < bottom_target[1]:
                                pos[1] = bottom_target[1]
                                boss_y = pos[1]
                            boss_info['cross_phase2_pos'] = pos
                            boss_info['cross_phase2_charge_ratio'] = max(0.35, boss_info.get('cross_phase2_charge_ratio', 0.6) - 0.006)
                            boss_info['cross_phase2_disc_spin'] = boss_info.get('cross_phase2_disc_spin', 0.0) + 2.0
                            if boss_info.get('cross_star_state') != 'trapezoid':
                                # 台形に変形時の効果音（一度だけ）
                                if boss_info.get('cross_last_transform_shape') != 'trapezoid':
                                    play_shape_transform()
                                    boss_info['cross_last_transform_shape'] = 'trapezoid'
                                boss_info['cross_star_state'] = 'trapezoid'
                            if ground_timer % 24 == 0:
                                lanes = 2
                                top_y = boss_y - boss_radius - 10
                                for lane in range(lanes):
                                    offset = (lane - (lanes - 1) / 2.0) * (boss_radius * 0.75)
                                    spawn_x = boss_x + offset
                                    jitter = math.radians(random.uniform(-6, 6))
                                    aim_ang = math.atan2(player.centery - top_y, player.centerx - spawn_x) + jitter
                                    speed = 4.6 + random.uniform(-0.35, 0.35)
                                    bullets.append({
                                        'rect': pygame.Rect(int(spawn_x - 6), int(top_y - 6), 12, 12),
                                        'type': 'enemy',
                                        'vx': speed * math.cos(aim_ang),
                                        'vy': speed * math.sin(aim_ang),
                                        'life': 240,
                                        'power': 1.2,
                                        'shape': 'orb',
                                        'color': (170, 140, 255)
                                    })
                            if ground_timer % 15 == 0:
                                boss_info['cross_transition_effects'].append({
                                    'x': boss_x + random.uniform(-18, 18),
                                    'y': boss_y - boss_radius * 0.6,
                                    'radius': random.uniform(boss_radius * 0.4, boss_radius * 0.9),
                                    'growth': random.uniform(2.8, 4.8),
                                    'ttl': 18,
                                    'max_ttl': 18
                                })
                            hold_frames = 72
                            if ground_timer >= hold_frames:
                                boss_info['cross_phase2_state'] = 'return_center'
                                boss_info['cross_phase2_timer'] = 0
                                boss_info['cross_phase2_charge_ratio'] = max(0.5, boss_info.get('cross_phase2_charge_ratio', 0.5))
                                boss_info['cross_phase2_fall_speed'] = 0.0
                            boss_info['cross_attack_timer'] = 0
                        elif state == 'moon_intro':
                            boss_info['cross_phase2_timer'] = timer + 1
                            speed = 6.0
                            dx = center_target[0] - pos[0]
                            dy = center_target[1] - pos[1]
                            dist = math.hypot(dx, dy)
                            if dist > speed:
                                pos[0] += (dx / dist) * speed
                                pos[1] += (dy / dist) * speed
                            else:
                                pos[0], pos[1] = center_target
                            boss_x, boss_y = pos[0], pos[1]
                            boss_info['cross_phase2_pos'] = pos
                            if boss_info.get('cross_star_state') != 'ellipse':
                                # 楕円に変形時の効果音（一度だけ）
                                if boss_info.get('cross_last_transform_shape') != 'ellipse':
                                    play_shape_transform()
                                    boss_info['cross_last_transform_shape'] = 'ellipse'
                                boss_info['cross_star_state'] = 'ellipse'
                            boss_info['cross_phase2_disc_spin'] = 0.0
                            charge = min(1.0, boss_info.get('cross_phase2_charge_ratio', 0.0) + 0.02)
                            boss_info['cross_phase2_charge_ratio'] = charge
                            if dist <= speed and boss_info['cross_phase2_timer'] >= 36 and not boss_info.get('cross_phase2_moons'):
                                orbit_radius = boss_info.get('cross_phase2_moon_orbit_radius', boss_radius + 70)
                                moons = []
                                base_speed = 0.017 + (1.0 - hp_ratio) * 0.004
                                moon_radius = max(14, int(boss_radius * 0.32))
                                specs = [
                                    {'angle': 0.0, 'speed_mult': 0.95, 'fire_offset': random.randint(18, 30), 'interval_range': (40, 54)},
                                    {'angle': math.pi, 'speed_mult': 1.35, 'fire_offset': random.randint(26, 38), 'interval_range': (46, 62)}
                                ]
                                for idx, spec in enumerate(specs):
                                    interval_low, interval_high = spec['interval_range']
                                    moons.append({
                                        'angle': spec['angle'],
                                        'speed': base_speed * spec['speed_mult'],
                                        'fire_timer': spec['fire_offset'],
                                        'fire_interval': random.randint(interval_low, interval_high),
                                        'x': boss_x,
                                        'y': boss_y,
                                        'radius': moon_radius,
                                        'id': idx
                                    })
                                boss_info['cross_phase2_moons'] = moons
                                boss_info['cross_phase2_moon_beams'] = []
                                boss_info['cross_phase2_moon_timer'] = 0
                                boss_info['cross_phase2_reflect'] = True
                                boss_info['cross_phase2_state'] = 'moon_attack'
                                boss_info['cross_phase2_timer'] = 0
                                boss_info['cross_transition_effects'].append({
                                    'x': boss_x,
                                    'y': boss_y,
                                    'radius': random.uniform(boss_radius * 0.5, boss_radius * 0.95),
                                    'growth': random.uniform(3.0, 4.8),
                                    'ttl': 28,
                                    'max_ttl': 28
                                })
                        elif state == 'moon_attack':
                            attack_timer = boss_info.get('cross_phase2_timer', 0) + 1
                            boss_info['cross_phase2_timer'] = attack_timer
                            boss_x, boss_y = pos[0], pos[1]
                            boss_info['cross_phase2_pos'] = pos
                            if boss_info.get('cross_star_state') != 'ellipse':
                                # 楕円に変形時の効果音（一度だけ）
                                if boss_info.get('cross_last_transform_shape') != 'ellipse':
                                    play_shape_transform()
                                    boss_info['cross_last_transform_shape'] = 'ellipse'
                                boss_info['cross_star_state'] = 'ellipse'
                            boss_info['cross_phase2_charge_ratio'] = min(1.0, max(0.7, boss_info.get('cross_phase2_charge_ratio', 0.8) + 0.008))
                            boss_info['cross_phase2_disc_spin'] = 0.0
                            orbit_radius = boss_info.get('cross_phase2_moon_orbit_radius', boss_radius + 70)
                            moon_speed_scale = 1.0 + (1.0 - hp_ratio) * 0.18
                            moons = boss_info.get('cross_phase2_moons', [])
                            beams = list(boss_info.get('cross_phase2_moon_beams', []))
                            for idx, moon in enumerate(moons):
                                spin_speed = moon.get('speed', 0.02) * moon_speed_scale
                                moon['angle'] = (moon['angle'] + spin_speed) % math.tau
                                mx = pos[0] + math.cos(moon['angle']) * orbit_radius
                                my = pos[1] + math.sin(moon['angle']) * orbit_radius
                                moon['x'] = mx
                                moon['y'] = my
                                moon['fire_timer'] = moon.get('fire_timer', 0) - 1
                                if moon['fire_timer'] <= 0:
                                    aim = math.atan2(player.centery - my, player.centerx - mx)
                                    aim += math.radians(random.uniform(-6, 6))
                                    length = 1400.0
                                    beam = {
                                        'moon': idx,
                                        'state': 'warning',
                                        'timer': 0,
                                        'warning': 22,
                                        'telegraph': 24,
                                        'firing': 26,
                                        'width': 8,
                                        'hit_radius': 10,
                                        'angle': aim,
                                        'length': length,
                                        'origin': (mx, my),
                                        'target': (mx + math.cos(aim) * length, my + math.sin(aim) * length),
                                        'locked_target': (mx + math.cos(aim) * length, my + math.sin(aim) * length)
                                    }
                                    beams.append(beam)
                                    interval = moon.get('fire_interval', 32)
                                    moon['fire_timer'] = max(30, interval + random.randint(6, 14))
                            boss_info['cross_phase2_moons'] = moons
                            updated_beams = []
                            for beam in beams:
                                moon_idx = beam.get('moon')
                                if moon_idx is not None and 0 <= moon_idx < len(moons):
                                    mx = moons[moon_idx].get('x', pos[0])
                                    my = moons[moon_idx].get('y', pos[1])
                                    beam['origin'] = (mx, my)
                                    locked = beam.get('locked_target')
                                    if locked:
                                        beam['target'] = locked
                                        beam['angle'] = math.atan2(locked[1] - my, locked[0] - mx)
                                        beam['length'] = math.hypot(locked[0] - mx, locked[1] - my)
                                    else:
                                        angle = beam.get('angle', 0.0)
                                        length = beam.get('length', 1200.0)
                                        target = (mx + math.cos(angle) * length, my + math.sin(angle) * length)
                                        beam['target'] = target
                                        beam['locked_target'] = target
                                beam['timer'] = beam.get('timer', 0) + 1
                                if beam['state'] == 'warning':
                                    if beam['timer'] >= beam.get('warning', 14):
                                        beam['state'] = 'telegraph'
                                        beam['timer'] = 0
                                elif beam['state'] == 'telegraph':
                                    if beam['timer'] >= beam.get('telegraph', 18):
                                        beam['state'] = 'firing'
                                        beam['timer'] = 0
                                elif beam['state'] == 'firing':
                                    if beam['timer'] >= beam.get('firing', 34):
                                        continue
                                updated_beams.append(beam)
                            boss_info['cross_phase2_moon_beams'] = updated_beams
                            boss_info['cross_phase2_moon_timer'] = boss_info.get('cross_phase2_moon_timer', 0) + 1
                            if boss_info['cross_phase2_moon_timer'] % 18 == 0:
                                boss_info['cross_transition_effects'].append({
                                    'x': boss_x + random.uniform(-14, 14),
                                    'y': boss_y + random.uniform(-14, 14),
                                    'radius': random.uniform(boss_radius * 0.4, boss_radius * 0.8),
                                    'growth': random.uniform(3.2, 5.0),
                                    'ttl': 20,
                                    'max_ttl': 20
                                })
                            duration = boss_info.get('cross_phase2_moon_duration', 360)
                            if boss_info['cross_phase2_moon_timer'] >= duration:
                                boss_info['cross_phase2_state'] = 'moon_cleanup'
                                boss_info['cross_phase2_timer'] = 0
                                boss_info['cross_phase2_reflect'] = False
                        elif state == 'moon_cleanup':
                            cleanup_timer = boss_info.get('cross_phase2_timer', 0) + 1
                            boss_info['cross_phase2_timer'] = cleanup_timer
                            boss_x, boss_y = pos[0], pos[1]
                            boss_info['cross_phase2_pos'] = pos
                            if boss_info.get('cross_star_state') != 'ellipse':
                                # 楕円に変形時の効果音（一度だけ）
                                if boss_info.get('cross_last_transform_shape') != 'ellipse':
                                    play_shape_transform()
                                    boss_info['cross_last_transform_shape'] = 'ellipse'
                                boss_info['cross_star_state'] = 'ellipse'
                            boss_info['cross_phase2_disc_spin'] = 0.0
                            base_orbit = boss_info.get('cross_phase2_moon_orbit_radius', boss_radius + 70)
                            decay = max(0.0, 1.0 - cleanup_timer / 36.0)
                            orbit_radius = base_orbit * decay
                            moons = boss_info.get('cross_phase2_moons', [])
                            for moon in moons:
                                moon['angle'] = (moon['angle'] + 0.015) % math.tau
                                mx = pos[0] + math.cos(moon['angle']) * orbit_radius
                                my = pos[1] + math.sin(moon['angle']) * orbit_radius
                                moon['x'] = mx
                                moon['y'] = my
                            boss_info['cross_phase2_moons'] = moons
                            updated_beams = []
                            for beam in boss_info.get('cross_phase2_moon_beams', []):
                                moon_idx = beam.get('moon')
                                if moon_idx is not None and 0 <= moon_idx < len(moons):
                                    mx = moons[moon_idx].get('x', pos[0])
                                    my = moons[moon_idx].get('y', pos[1])
                                    beam['origin'] = (mx, my)
                                    locked = beam.get('locked_target')
                                    if locked:
                                        beam['target'] = locked
                                        beam['angle'] = math.atan2(locked[1] - my, locked[0] - mx)
                                        beam['length'] = math.hypot(locked[0] - mx, locked[1] - my)
                                    else:
                                        angle = beam.get('angle', 0.0)
                                        length = beam.get('length', 1200.0)
                                        target = (mx + math.cos(angle) * length, my + math.sin(angle) * length)
                                        beam['target'] = target
                                        beam['locked_target'] = target
                                beam['timer'] = beam.get('timer', 0) + 1
                                if beam['state'] == 'warning':
                                    if beam['timer'] >= beam.get('warning', 14):
                                        beam['state'] = 'telegraph'
                                        beam['timer'] = 0
                                elif beam['state'] == 'telegraph':
                                    if beam['timer'] >= beam.get('telegraph', 18):
                                        beam['state'] = 'firing'
                                        beam['timer'] = 0
                                elif beam['state'] == 'firing':
                                    if beam['timer'] >= beam.get('firing', 28):
                                        continue
                                updated_beams.append(beam)
                            boss_info['cross_phase2_moon_beams'] = updated_beams
                            boss_info['cross_phase2_charge_ratio'] = max(0.0, boss_info.get('cross_phase2_charge_ratio', 0.6) - 0.03)
                            if decay <= 0.05 and not updated_beams:
                                boss_info['cross_phase2_moons'] = []
                                boss_info['cross_phase2_moon_beams'] = []
                                boss_info['cross_phase2_state'] = 'return_center'
                                boss_info['cross_phase2_timer'] = 0
                                boss_info['cross_phase2_charge_ratio'] = 0.5
                                boss_info['cross_transition_effects'].append({
                                    'x': boss_x,
                                    'y': boss_y,
                                    'radius': random.uniform(boss_radius * 0.35, boss_radius * 0.6),
                                    'growth': random.uniform(2.6, 4.2),
                                    'ttl': 18,
                                    'max_ttl': 18
                                })
                        elif state == 'bounce':
                            boss_info['cross_phase2_timer'] = timer + 1
                            squish = boss_info.get('cross_phase2_bounce_squish')
                            if squish:
                                squish['timer'] = squish.get('timer', 0) + 1
                                if squish['timer'] >= squish.get('duration', 16):
                                    boss_info['cross_phase2_bounce_squish'] = None
                                else:
                                    boss_info['cross_phase2_bounce_squish'] = squish
                            bounce_timer = boss_info['cross_phase2_timer']
                            boss_info['cross_phase2_bounce_timer'] = boss_info.get('cross_phase2_bounce_timer', 0) + 1
                            bounce_lifetime = boss_info['cross_phase2_bounce_timer']
                            vx, vy = boss_info.get('cross_phase2_bounce_vel', [0.0, 0.0])
                            speed = boss_info.get('cross_phase2_bounce_speed', 7.4)
                            min_x = boss_radius + 32
                            max_x = WIDTH - boss_radius - 32
                            min_y = max(boss_radius + 48, 80)
                            max_y = HEIGHT - boss_radius - 72
                            if max_y <= min_y:
                                min_y = boss_radius + 40
                                max_y = HEIGHT - boss_radius - 40
                            if abs(vx) < 1e-3 and abs(vy) < 1e-3:
                                start_angle = random.uniform(0, math.tau)
                                vx = math.cos(start_angle) * speed
                                vy = math.sin(start_angle) * speed
                            else:
                                dir_len = math.hypot(vx, vy)
                                if dir_len > 1e-4:
                                    dir_x = vx / dir_len
                                    dir_y = vy / dir_len
                                    dist_candidates = []
                                    if dir_x > 0:
                                        dist_candidates.append((max_x - pos[0]) / max(abs(dir_x), 1e-4))
                                    elif dir_x < 0:
                                        dist_candidates.append((pos[0] - min_x) / max(abs(dir_x), 1e-4))
                                    if dir_y > 0:
                                        dist_candidates.append((max_y - pos[1]) / max(abs(dir_y), 1e-4))
                                    elif dir_y < 0:
                                        dist_candidates.append((pos[1] - min_y) / max(abs(dir_y), 1e-4))
                                    if dist_candidates:
                                        travel_frames = max(0.0, min(dist_candidates))
                                    else:
                                        travel_frames = 999.0
                                    travel_ratio = max(0.0, min(1.0, travel_frames / 160.0))
                                    base_speed = max(0.1, boss_info.get('cross_phase2_bounce_speed', speed))
                                    target_speed = base_speed * (0.68 + 0.32 * travel_ratio)
                                    current_speed = dir_len
                                    adjusted_speed = current_speed + (target_speed - current_speed) * 0.28
                                    adjusted_speed = max(0.35 * base_speed, min(adjusted_speed, 1.15 * base_speed))
                                    vx = dir_x * adjusted_speed
                                    vy = dir_y * adjusted_speed
                            pos[0] += vx
                            pos[1] += vy
                            bounce_axes = []
                            bounce_hits = boss_info.get('cross_phase2_bounce_hits', 0)
                            if pos[0] < min_x:
                                pos[0] = min_x
                                vx = abs(vx)
                                bounce_axes.append('x')
                            elif pos[0] > max_x:
                                pos[0] = max_x
                                vx = -abs(vx)
                                bounce_axes.append('x')
                            if pos[1] < min_y:
                                pos[1] = min_y
                                vy = abs(vy)
                                bounce_axes.append('y')
                            elif pos[1] > max_y:
                                pos[1] = max_y
                                vy = -abs(vy)
                                bounce_axes.append('y')
                            bounced = bool(bounce_axes)
                            if bounced:
                                current_speed = math.hypot(vx, vy)
                                if current_speed <= 0.1:
                                    current_speed = speed
                                jitter = math.radians(random.uniform(-16, 16))
                                ang = math.atan2(vy, vx) + jitter
                                vx = math.cos(ang) * current_speed
                                vy = math.sin(ang) * current_speed
                                min_vert = current_speed * 0.25
                                if abs(vy) < min_vert:
                                    vy = min_vert if vy >= 0 else -min_vert
                                    vx = math.copysign(math.sqrt(max(current_speed * current_speed - vy * vy, 0.1)), vx)
                                bounce_hits += 1
                                ring_count = 6 + int((1.0 - hp_ratio) * 3)
                                ring_speed = 3.6 + (1.0 - hp_ratio) * 1.0
                                for i in range(ring_count):
                                    ang_ring = math.tau * (i / ring_count)
                                    bullets.append({
                                        'rect': pygame.Rect(int(pos[0] - 6), int(pos[1] - 6), 12, 12),
                                        'type': 'enemy',
                                        'vx': ring_speed * math.cos(ang_ring),
                                        'vy': ring_speed * math.sin(ang_ring),
                                        'life': 240,
                                        'power': 1.0,
                                        'shape': 'star',
                                        'color': (255, 215, 130)
                                    })
                                boss_info['cross_transition_effects'].append({
                                    'x': pos[0],
                                    'y': pos[1],
                                    'radius': random.uniform(boss_radius * 0.38, boss_radius * 0.82),
                                    'growth': random.uniform(3.6, 5.8),
                                    'ttl': 18,
                                    'max_ttl': 18
                                })
                                axis_tag = 'both'
                                if bounce_axes:
                                    unique_axes = set(bounce_axes)
                                    if len(unique_axes) == 1:
                                        axis_tag = next(iter(unique_axes))
                                boss_info['cross_phase2_bounce_squish'] = {
                                    'timer': 0,
                                    'duration': boss_info.get('cross_phase2_bounce_squish_duration', 16),
                                    'axis': axis_tag
                                }
                            boss_x, boss_y = pos[0], pos[1]
                            boss_info['cross_phase2_pos'] = pos
                            boss_info['cross_phase2_bounce_vel'] = [vx, vy]
                            boss_info['cross_phase2_bounce_hits'] = bounce_hits
                            boss_info['cross_phase2_charge_ratio'] = max(0.85, boss_info.get('cross_phase2_charge_ratio', 1.0))
                            if bounce_timer % 8 == 0:
                                base_ang = math.atan2(vy, vx)
                                for spread in (-0.35, 0.35):
                                    scatter_ang = base_ang + spread + math.radians(random.uniform(-8, 8))
                                    scatter_speed = 3.6 + random.uniform(-0.4, 0.5)
                                    bullets.append({
                                        'rect': pygame.Rect(int(boss_x - 5), int(boss_y - 5), 10, 10),
                                        'type': 'enemy',
                                        'vx': scatter_speed * math.cos(scatter_ang),
                                        'vy': scatter_speed * math.sin(scatter_ang),
                                        'life': 260,
                                        'power': 1.0,
                                        'shape': 'star',
                                        'color': (255, 170, 255)
                                    })
                            if bounce_timer % 14 == 0:
                                trail_ang = math.atan2(vy, vx) + math.pi + math.radians(random.uniform(-24, 24))
                                trail_speed = 2.6 + random.uniform(-0.4, 0.4)
                                bullets.append({
                                    'rect': pygame.Rect(int(boss_x - 4), int(boss_y - 4), 8, 8),
                                    'type': 'enemy',
                                    'vx': trail_speed * math.cos(trail_ang),
                                    'vy': trail_speed * math.sin(trail_ang),
                                    'life': 200,
                                    'power': 0.8,
                                    'shape': 'star',
                                    'color': (120, 220, 255)
                                })
                            if bounce_timer % 9 == 0:
                                boss_info['cross_transition_effects'].append({
                                    'x': boss_x + random.uniform(-12, 12),
                                    'y': boss_y + random.uniform(-12, 12),
                                    'radius': random.uniform(boss_radius * 0.32, boss_radius * 0.7),
                                    'growth': random.uniform(3.0, 4.8),
                                    'ttl': 16,
                                    'max_ttl': 16
                                })
                            goal = boss_info.get('cross_phase2_bounce_goal', 6)
                            limit = boss_info.get('cross_phase2_bounce_limit', 360)
                            if bounce_hits >= goal or bounce_lifetime >= limit:
                                boss_info['cross_phase2_state'] = 'return_center'
                                boss_info['cross_phase2_timer'] = 0
                                boss_info['cross_phase2_charge_ratio'] = 1.0
                                boss_info['cross_phase2_bounce_timer'] = 0
                            boss_info['cross_attack_timer'] = 0
                        elif state == 'return_center':
                            speed = 7.2
                            dx = center_target[0] - pos[0]
                            dy = center_target[1] - pos[1]
                            dist = math.hypot(dx, dy)
                            if dist <= speed:
                                pos[0], pos[1] = center_target
                                boss_info['cross_phase2_state'] = 'reset_star'
                                boss_info['cross_phase2_timer'] = 0
                                boss_info['cross_phase2_bounce_vel'] = [0.0, 0.0]
                                boss_info['cross_phase2_bounce_timer'] = 0
                                boss_info['cross_phase2_fall_speed'] = 0.0
                                boss_info['cross_phase2_ground_timer'] = 0
                                boss_info['cross_phase2_moons'] = []
                                boss_info['cross_phase2_moon_beams'] = []
                                boss_info['cross_phase2_reflect'] = False
                                spin_restore = boss_info.pop('cross_phase2_moon_spin_backup', None)
                                if spin_restore is not None:
                                    boss_info['cross_star_spin_speed'] = max(3.2, spin_restore or 3.2)
                            else:
                                pos[0] += (dx / dist) * speed
                                pos[1] += (dy / dist) * speed
                                boss_info['cross_phase2_timer'] = timer + 1
                                boss_info['cross_phase2_bounce_vel'] = [0.0, 0.0]
                                boss_info['cross_phase2_bounce_timer'] = 0
                                boss_info['cross_phase2_fall_speed'] = 0.0
                                if boss_info.get('cross_phase2_moons'):
                                    boss_info['cross_phase2_moons'] = []
                                if boss_info.get('cross_phase2_moon_beams'):
                                    boss_info['cross_phase2_moon_beams'] = []
                                boss_info['cross_phase2_reflect'] = False
                            boss_x, boss_y = pos[0], pos[1]
                            boss_info['cross_phase2_pos'] = pos
                            boss_info['cross_phase2_disc_spin'] = boss_info.get('cross_phase2_disc_spin', 0.0) + 3.0
                            boss_info['cross_attack_timer'] = 0
                        elif state == 'reset_star':
                            boss_info['cross_phase2_timer'] = timer + 1
                            fade_frames = 26
                            ratio = max(0.0, 1.0 - boss_info['cross_phase2_timer'] / float(fade_frames))
                            boss_info['cross_phase2_charge_ratio'] = ratio
                            boss_info['cross_phase2_disc_spin'] = boss_info.get('cross_phase2_disc_spin', 0.0) + 1.8
                            boss_x, boss_y = pos[0], pos[1]
                            if boss_info['cross_phase2_timer'] >= fade_frames:
                                boss_info['cross_star_state'] = 'star'
                                boss_info['cross_phase2_state'] = 'idle'
                                boss_info['cross_phase2_timer'] = 0
                                boss_info['cross_phase2_disc_surface'] = None
                                boss_info['cross_phase2_disc_radius'] = 0
                                boss_info['cross_phase2_disc_spin'] = 0.0
                                boss_info['cross_phase2_bounce_vel'] = [0.0, 0.0]
                                boss_info['cross_phase2_bounce_hits'] = 0
                                boss_info['cross_phase2_bounce_timer'] = 0
                                boss_info['cross_phase2_fall_speed'] = 0.0
                                boss_info['cross_phase2_ground_timer'] = 0
                                boss_info['cross_phase2_rainbow_timer'] = 0
                                boss_info['cross_phase2_rainbow_burst_step'] = 0
                                boss_info['cross_phase2_trapezoid_surface'] = None
                                boss_info['cross_phase2_trapezoid_width'] = 0
                                boss_info['cross_phase2_trapezoid_height'] = 0
                                boss_info['cross_phase2_moons'] = []
                                boss_info['cross_phase2_moon_beams'] = []
                                boss_info['cross_phase2_reflect'] = False
                                spin_restore = boss_info.pop('cross_phase2_moon_spin_backup', None)
                                if spin_restore is not None:
                                    boss_info['cross_star_spin_speed'] = max(3.2, spin_restore or 3.2)
                                prev_pattern = boss_info.get('cross_phase2_active_pattern', 'bounce')
                                pattern_cycle = ['bounce', 'rainbow_drop', 'moon_orbit']
                                if prev_pattern not in pattern_cycle:
                                    prev_pattern = 'bounce'
                                idx = pattern_cycle.index(prev_pattern)
                                next_pattern = pattern_cycle[(idx + 1) % len(pattern_cycle)]
                                boss_info['cross_phase2_next_pattern'] = next_pattern
                                if next_pattern == 'bounce':
                                    next_cd = max(90, int(125 - hp_ratio * 38))
                                elif next_pattern == 'rainbow_drop':
                                    next_cd = max(120, int(150 - hp_ratio * 45))
                                else:
                                    next_cd = max(140, int(170 - hp_ratio * 52))
                                boss_info['cross_phase2_active_pattern'] = None
                                boss_info['cross_phase2_idle_cooldown'] = next_cd
                                boss_info['cross_attack_timer'] = 0
                        else:
                            boss_info['cross_phase2_state'] = 'idle'
                            boss_info['cross_phase2_timer'] = 0
                            boss_info['cross_attack_timer'] = 0

                        boss_info['cross_phase2_pos'] = [float(boss_x), float(boss_y)]
                    else:
                        if wall_attack:
                            state = wall_attack.get('state', 'telegraph')
                            wall_attack['timer'] = wall_attack.get('timer', 0) + 1
                            extend_speed = wall_attack.get('extend_speed', 14)
                            retract_speed = wall_attack.get('retract_speed', extend_speed)
                            telegraph_frames = wall_attack.get('telegraph_duration', 30)
                            hold_frames = wall_attack.get('hold_duration', 54)
                            spears = wall_attack.get('spears', [])
                            if state == 'telegraph':
                                for spear in spears:
                                    surf = spear.get('surface')
                                    if not surf:
                                        continue
                                    if spear['side'] == 'left':
                                        rect = surf.get_rect(midright=(int(spear['tip_x']), int(spear['y'])))
                                    else:
                                        rect = surf.get_rect(midleft=(int(spear['tip_x']), int(spear['y'])))
                                    spear['rect'] = rect
                                if wall_attack['timer'] >= telegraph_frames:
                                    wall_attack['state'] = 'advance'
                                    wall_attack['timer'] = 0
                            elif state == 'advance':
                                all_reached = True
                                for spear in spears:
                                    if spear['side'] == 'left':
                                        spear['tip_x'] = min(spear['tip_x'] + extend_speed, spear['tip_target'])
                                        if spear['tip_x'] < spear['tip_target'] - 0.5:
                                            all_reached = False
                                    else:
                                        spear['tip_x'] = max(spear['tip_x'] - extend_speed, spear['tip_target'])
                                        if spear['tip_x'] > spear['tip_target'] + 0.5:
                                            all_reached = False
                                    surf = spear.get('surface')
                                    if spear['side'] == 'left':
                                        rect = surf.get_rect(midright=(int(spear['tip_x']), int(spear['y'])))
                                    else:
                                        rect = surf.get_rect(midleft=(int(spear['tip_x']), int(spear['y'])))
                                    spear['rect'] = rect
                                if all_reached:
                                    wall_attack['state'] = 'hold'
                                    wall_attack['timer'] = 0
                            elif state == 'hold':
                                for spear in spears:
                                    surf = spear.get('surface')
                                    if spear['side'] == 'left':
                                        rect = surf.get_rect(midright=(int(spear['tip_x']), int(spear['y'])))
                                    else:
                                        rect = surf.get_rect(midleft=(int(spear['tip_x']), int(spear['y'])))
                                    spear['rect'] = rect
                                if wall_attack['timer'] >= hold_frames:
                                    wall_attack['state'] = 'retract'
                                    wall_attack['timer'] = 0
                            elif state == 'retract':
                                done = True
                                for spear in spears:
                                    if spear['side'] == 'left':
                                        spear['tip_x'] = max(spear['tip_x'] - retract_speed, spear['tip_start'])
                                        if spear['tip_x'] > spear['tip_start'] + 0.5:
                                            done = False
                                    else:
                                        spear['tip_x'] = min(spear['tip_x'] + retract_speed, spear['tip_start'])
                                        if spear['tip_x'] < spear['tip_start'] - 0.5:
                                            done = False
                                    surf = spear.get('surface')
                                    if spear['side'] == 'left':
                                        rect = surf.get_rect(midright=(int(spear['tip_x']), int(spear['y'])))
                                    else:
                                        rect = surf.get_rect(midleft=(int(spear['tip_x']), int(spear['y'])))
                                    spear['rect'] = rect
                                if done:
                                    boss_info['cross_wall_attack'] = None
                                    boss_info['cross_attack_timer'] = 0
                                    boss_info['cross_last_pattern'] = 'wall'

                        if not boss_info.get('cross_wall_attack') and boss_info['cross_attack_timer'] >= dynamic_cd:
                            patterns = []
                            if len(boss_info['cross_falls']) < max_falls:
                                patterns.append('falls')
                            patterns.append('wall')
                            last_pattern = boss_info.get('cross_last_pattern')
                            if len(patterns) > 1 and last_pattern in patterns:
                                alt_patterns = [p for p in patterns if p != last_pattern]
                                if alt_patterns:
                                    patterns = alt_patterns
                            choice = random.choice(patterns) if patterns else 'falls'
                            if choice == 'falls':
                                boss_info['cross_attack_timer'] = 0
                                wave_count = 5 if hp_ratio > 0.6 else 6
                                if hp_ratio < 0.45:
                                    wave_count += 1
                                if hp_ratio < 0.25:
                                    wave_count += 1

                                spear_length = max(130, int(boss_radius * 2.0))
                                spear_width = max(10, int(boss_radius * 0.22))
                                tip_length = max(28, int(spear_length * 0.28))
                                shaft_length = spear_length - tip_length
                                canvas_height = spear_width * 2
                                center_y = canvas_height / 2
                                half_shaft = spear_width / 2
                                half_canvas = canvas_height / 2.0

                                base_rect = pygame.Surface((spear_length, canvas_height), pygame.SRCALPHA)
                                spear_points = [
                                    (0, center_y - half_shaft),
                                    (shaft_length, center_y - half_shaft),
                                    (shaft_length + tip_length * 0.35, center_y - half_shaft * 0.6),
                                    (spear_length, center_y),
                                    (shaft_length + tip_length * 0.35, center_y + half_shaft * 0.6),
                                    (shaft_length, center_y + half_shaft),
                                    (0, center_y + half_shaft),
                                ]
                                spear_points_int = [(int(x), int(y)) for (x, y) in spear_points]
                                pygame.draw.polygon(base_rect, (255, 70, 70), spear_points_int)
                                pygame.draw.polygon(base_rect, (255, 170, 170), spear_points_int, width=2)
                                highlight_start = (int(shaft_length * 0.15), int(center_y))
                                highlight_end = (int(shaft_length + tip_length * 0.6), int(center_y))
                                pygame.draw.line(base_rect, (255, 200, 200, 180), highlight_start, highlight_end, max(1, spear_width // 3))
                                vertical_surface = pygame.transform.rotate(base_rect, -90)

                                player_bias = (player.centerx - boss_x) * 0.25
                                for i in range(wave_count):
                                    offset = (i - (wave_count - 1) / 2.0) * (spear_length * 0.38)
                                    spawn_x = boss_x + offset + random.uniform(-25, 25) + player_bias * 0.08
                                    spawn_x = max(30, min(WIDTH - 30, spawn_x))
                                    spawn_y = boss_y - boss_radius - 80 - random.uniform(0, 60)
                                    init_vx = 0.0
                                    init_vy = random.uniform(2.8, 4.4)
                                    gravity = random.uniform(0.26, 0.38)
                                    spin_speed = 0.0
                                    segment = {
                                        'x': spawn_x,
                                        'y': spawn_y,
                                        'vx': init_vx,
                                        'vy': init_vy,
                                        'gravity': gravity,
                                        'spin_speed': spin_speed,
                                        'spin_angle': 270,
                                        'base_surface': base_rect,
                                        'vertical_surface': vertical_surface,
                                        'surface': vertical_surface,
                                        'rect': vertical_surface.get_rect(center=(int(spawn_x), int(spawn_y))),
                                        'state': 'fall',
                                        'pause_done': False
                                    }
                                    boss_info['cross_falls'].append(segment)
                                boss_info['cross_last_pattern'] = 'falls'
                            else:
                                boss_info['cross_attack_timer'] = 0
                                lane_count = 6 if hp_ratio > 0.6 else 7
                                if hp_ratio < 0.5:
                                    lane_count += 1
                                if hp_ratio < 0.3:
                                    lane_count += 1
                                if hp_ratio < 0.15:
                                    lane_count += 1
                                lane_count = min(8, lane_count)

                                safe_half = 62 if hp_ratio > 0.7 else 56
                                if hp_ratio < 0.5:
                                    safe_half = 48
                                if hp_ratio < 0.35:
                                    safe_half = 42
                                if hp_ratio < 0.2:
                                    safe_half = 36
                                safe_half = max(34, safe_half)
                                safe_half = min(WIDTH / 2 - 55, safe_half)
                                safe_lane_half_gap = 48 if hp_ratio > 0.6 else 42
                                if hp_ratio < 0.45:
                                    safe_lane_half_gap = 38
                                if hp_ratio < 0.3:
                                    safe_lane_half_gap = 32
                                if hp_ratio < 0.18:
                                    safe_lane_half_gap = 28
                                safe_lane_half_gap = max(26, min(WIDTH / 2 - 60, safe_lane_half_gap))

                                spear_length = max(int(WIDTH * 0.36), 240)
                                spear_width = max(18, int(boss_radius * 0.3))
                                tip_length = max(32, int(spear_length * 0.23))
                                shaft_length = spear_length - tip_length
                                canvas_height = spear_width * 2
                                center_y = canvas_height / 2
                                half_shaft = spear_width / 2
                                half_canvas = canvas_height / 2.0

                                base_surface = pygame.Surface((spear_length, canvas_height), pygame.SRCALPHA)
                                spear_points = [
                                    (0, center_y - half_shaft),
                                    (shaft_length, center_y - half_shaft),
                                    (shaft_length, center_y - half_shaft * 0.55),
                                    (spear_length, center_y),
                                    (shaft_length, center_y + half_shaft * 0.55),
                                    (shaft_length, center_y + half_shaft),
                                    (0, center_y + half_shaft),
                                ]
                                spear_points_int = [(int(x), int(y)) for (x, y) in spear_points]
                                pygame.draw.polygon(base_surface, (255, 70, 70), spear_points_int)
                                pygame.draw.polygon(base_surface, (255, 170, 170), spear_points_int, width=2)
                                highlight_start = (int(shaft_length * 0.1), int(center_y))
                                highlight_end = (int(spear_length - tip_length * 0.25), int(center_y))
                                pygame.draw.line(base_surface, (255, 200, 200, 160), highlight_start, highlight_end, max(1, spear_width // 3))
                                surface_left = base_surface
                                surface_right = pygame.transform.flip(base_surface, True, False)

                                usable_top = max(half_canvas + 55, 80)
                                usable_bottom = HEIGHT - (half_canvas + 6)
                                if usable_bottom <= usable_top:
                                    usable_bottom = usable_top + half_canvas * 0.6
                                lane_positions = []
                                if lane_count <= 1 or usable_bottom <= usable_top:
                                    lane_positions = [HEIGHT / 2.0 for _ in range(max(1, lane_count))]
                                else:
                                    span = usable_bottom - usable_top
                                    compressed_span = span * 0.95
                                    step = compressed_span / max(1, lane_count - 1)
                                    start = (usable_top + usable_bottom) / 2.0 - compressed_span / 2.0
                                    for i in range(lane_count):
                                        lane_positions.append(start + step * i)

                                gap_index = random.randrange(max(1, lane_count))
                                gap_drop = spear_width * 0.75
                                adjusted_positions = []
                                for idx, base_lane_y in enumerate(lane_positions):
                                    lane_y = base_lane_y
                                    if idx == gap_index:
                                        lane_y += gap_drop
                                    lane_y = max(usable_top, min(HEIGHT - half_canvas - 4, lane_y))
                                    adjusted_positions.append(lane_y)

                                normal_left_tip = WIDTH / 2.0 - safe_half
                                normal_right_tip = WIDTH / 2.0 + safe_half
                                offscreen_buffer = spear_length * 0.7
                                spear_entries = []
                                for idx, lane_y in enumerate(adjusted_positions):
                                    left_target = max(50, normal_left_tip)
                                    right_target = min(WIDTH - 50, normal_right_tip)
                                    if idx == gap_index:
                                        center = WIDTH / 2.0
                                        left_target = max(40, center - safe_lane_half_gap)
                                        right_target = min(WIDTH - 40, center + safe_lane_half_gap)
                                    left_start_tip = -offscreen_buffer
                                    right_start_tip = WIDTH + offscreen_buffer
                                    left_rect = surface_left.get_rect(midright=(int(left_start_tip), int(lane_y)))
                                    right_rect = surface_right.get_rect(midleft=(int(right_start_tip), int(lane_y)))
                                    spear_entries.append({
                                        'side': 'left',
                                        'lane': idx,
                                        'y': lane_y,
                                        'tip_x': left_start_tip,
                                        'tip_start': left_start_tip,
                                        'tip_target': left_target,
                                        'surface': surface_left,
                                        'rect': left_rect
                                    })
                                    spear_entries.append({
                                        'side': 'right',
                                        'lane': idx,
                                        'y': lane_y,
                                        'tip_x': right_start_tip,
                                        'tip_start': right_start_tip,
                                        'tip_target': right_target,
                                        'surface': surface_right,
                                        'rect': right_rect
                                    })

                                extend_speed = 12 + int((1.0 - hp_ratio) * 6)
                                retract_speed = 14 + int((1.0 - hp_ratio) * 6)

                                boss_info['cross_wall_attack'] = {
                                    'state': 'telegraph',
                                    'timer': 0,
                                    'spears': spear_entries,
                                    'telegraph_duration': 32 if hp_ratio > 0.45 else 26,
                                    'hold_duration': 60 if hp_ratio > 0.35 else 44,
                                    'extend_speed': extend_speed,
                                    'retract_speed': retract_speed,
                                    'gap_index': gap_index,
                                    'lane_positions': adjusted_positions,
                                    'gap_drop': gap_drop
                                }
                                boss_info['cross_attack_timer'] = 0

                        updated_falls = []
                        for fall in boss_info['cross_falls']:
                            state = fall.get('state', 'fall')
                            if state != 'pause':
                                fall['vy'] += fall['gravity']
                                fall['y'] += fall['vy']
                                fall['x'] += fall['vx']
                            else:
                                fall['pause_timer'] = fall.get('pause_timer', 0) - 1
                                if fall['pause_timer'] <= 0:
                                    fall['state'] = 'fall'
                                    resumed_vy = fall.get('post_pause_vy', max(2.8, fall['gravity'] * 6))
                                    fall['vy'] = resumed_vy
                            if abs(fall.get('spin_speed', 0.0)) > 1e-3:
                                fall['spin_angle'] = (fall.get('spin_angle', 0.0) + fall['spin_speed']) % 360
                                rotated = pygame.transform.rotate(fall['base_surface'], fall['spin_angle'])
                            else:
                                rotated = fall.get('vertical_surface') or pygame.transform.rotate(fall['base_surface'], -90)
                            fall['surface'] = rotated
                            fall_rect = rotated.get_rect(center=(int(fall['x']), int(fall['y'])))
                            fall['rect'] = fall_rect
                            if fall.get('state', 'fall') != 'pause' and not fall.get('pause_done', False):
                                if fall_rect.top >= -fall_rect.height * 0.5:
                                    fall['pause_done'] = True
                                    fall['state'] = 'pause'
                                    fall['pause_timer'] = random.randint(12, 22)
                                    fall['post_pause_vy'] = max(fall['vy'], 3.6)
                                    fall['vy'] = 0.0
                            if fall.get('state') == 'pause':
                                fall['x'] += fall.get('pause_drift', 0.0)
                            if fall_rect.bottom < -120 or fall_rect.top > HEIGHT + 160:
                                continue
                            if fall_rect.right < -120 or fall_rect.left > WIDTH + 120:
                                continue
                            updated_falls.append(fall)
                        boss_info['cross_falls'] = updated_falls
                elif cross_mode == 'transition_explosion':
                    decay_transition_effects()
                    timer = boss_info.get('cross_transition_timer', 0) + 1
                    boss_info['cross_transition_timer'] = timer
                    prog = min(1.0, boss_info.get('cross_star_progress', 0.0) + 0.05)
                    boss_info['cross_star_progress'] = prog
                    if prog >= 0.999:
                        boss_info['cross_star_state'] = 'star'
                    spin = max(2.2, boss_info.get('cross_star_spin_speed', 1.6))
                    boss_info['cross_star_rotation'] = (boss_info.get('cross_star_rotation', 0.0) + spin) % 360
                    if timer % 3 == 0:
                        boss_info['cross_transition_effects'].append({
                            'x': boss_x + random.uniform(-boss_radius * 0.9, boss_radius * 0.9),
                            'y': boss_y + random.uniform(-boss_radius * 0.9, boss_radius * 0.9),
                            'radius': random.uniform(boss_radius * 0.6, boss_radius * 1.2),
                            'growth': random.uniform(4.5, 7.0),
                            'ttl': 28,
                            'max_ttl': 28
                        })
                    boss_info['cross_blackout_alpha'] = min(120, boss_info.get('cross_blackout_alpha', 0) + 3)
                    boss_info['cross_falls'] = []
                    boss_info['cross_wall_attack'] = None
                    if timer >= 60:
                        boss_info['cross_phase_mode'] = 'transition_blackout'
                        boss_info['cross_transition_timer'] = 0
                        # BGMをフェードアウト開始（2秒かけて）
                        fade_out_bgm(2000)
                elif cross_mode == 'transition_blackout':
                    decay_transition_effects(2.5)
                    timer = boss_info.get('cross_transition_timer', 0) + 1
                    boss_info['cross_transition_timer'] = timer
                    boss_info['cross_blackout_alpha'] = min(255, boss_info.get('cross_blackout_alpha', 120) + 8)
                    if timer % 7 == 0:
                        boss_info['cross_transition_effects'].append({
                            'x': boss_x + random.uniform(-boss_radius * 0.4, boss_radius * 0.4),
                            'y': boss_y + random.uniform(-boss_radius * 0.4, boss_radius * 0.4),
                            'radius': random.uniform(boss_radius * 0.4, boss_radius * 0.9),
                            'growth': random.uniform(2.5, 4.5),
                            'ttl': 24,
                            'max_ttl': 24
                        })
                    boss_info['cross_falls'] = []
                    boss_info['cross_wall_attack'] = None
                    if boss_info['cross_blackout_alpha'] >= 255 and timer >= 40:
                        boss_info['cross_phase_mode'] = 'phase2_intro'
                        boss_info['cross_phase2_intro_timer'] = 0
                        boss_info['cross_phase2_started'] = False
                        boss_info['cross_transition_timer'] = 0
                        boss_info['cross_star_state'] = 'star'
                        boss_info['cross_star_progress'] = 1.0
                        boss_info['cross_star_spin_speed'] = max(2.6, boss_info.get('cross_star_spin_speed', 1.6) * 1.4)
                elif cross_mode == 'phase2_intro':
                    decay_transition_effects(2.0)
                    intro = boss_info.get('cross_phase2_intro_timer', 0) + 1
                    boss_info['cross_phase2_intro_timer'] = intro
                    boss_info['cross_star_state'] = 'star'
                    boss_info['cross_star_progress'] = 1.0
                    boss_info['cross_star_rotation'] = (boss_info.get('cross_star_rotation', 0.0) + boss_info.get('cross_star_spin_speed', 2.6)) % 360
                    if intro == 1:
                        boss_info['cross_transition_effects'].append({
                            'x': boss_x,
                            'y': boss_y,
                            'radius': boss_radius * 0.8,
                            'growth': 5.0,
                            'ttl': 36,
                            'max_ttl': 36
                        })
                        boss_color = (255, 255, 255)
                        boss_info['color'] = boss_color
                    # フェードイン開始タイミング（暗転解除が始まる直前）
                    if intro == 25:  # hold_frames + 1
                        # arabiantechnoをフェードインで再生開始（1.5秒かけて）
                        play_bgm("arabiantechno", volume=0.45, fade_in_ms=1500)
                    hold_frames = 24
                    fade_frames = 60
                    if intro <= hold_frames:
                        boss_info['cross_blackout_alpha'] = 255
                    else:
                        fade = intro - hold_frames
                        alpha = max(0, 255 - int(255 * (fade / fade_frames)))
                        boss_info['cross_blackout_alpha'] = alpha
                    boss_info['cross_falls'] = []
                    boss_info['cross_wall_attack'] = None
                    if intro >= hold_frames + fade_frames:
                        boss_info['cross_phase_mode'] = 'phase2'
                        boss_info['cross_phase2_started'] = True
                        boss_info['cross_blackout_alpha'] = 0
                        boss_info['cross_transition_effects'] = []
                        boss_info['cross_phase2_settings_applied'] = False
                        boss_info['cross_active_hp_max'] = max(1, boss_info.get('cross_phase2_hp', boss_info.get('hp', 240)))
                        boss_hp = boss_info.get('cross_phase2_hp', boss_hp)
                        boss_info['cross_attack_timer'] = 0
                        boss_info['cross_phase2_state'] = 'idle'
                        boss_info['cross_phase2_timer'] = 0
                        boss_info['cross_phase2_pos'] = [float(boss_x), float(boss_y)]
                        boss_info['cross_phase2_disc_surface'] = None
                        # phase2チェックポイント設定
                        boss6_phase2_checkpoint = True
                        boss_info['cross_phase2_disc_radius'] = 0
                        boss_info['cross_phase2_disc_spin'] = 0.0
                        boss_info['cross_phase2_charge_ratio'] = 0.0
                        boss_info['cross_phase2_idle_cooldown'] = 120
                        boss_info['cross_phase2_target_center'] = (WIDTH / 2.0, boss_y)
                        boss_info['cross_phase2_bounce_vel'] = [0.0, 0.0]
                        boss_info['cross_phase2_bounce_hits'] = 0
                        boss_info['cross_phase2_bounce_goal'] = 5
                        boss_info['cross_phase2_bounce_speed'] = 7.4
                        boss_info['cross_phase2_bounce_timer'] = 0
                        boss_info['cross_phase2_bounce_limit'] = 360
                        boss_info['cross_phase2_active_pattern'] = None
                        boss_info['cross_phase2_next_pattern'] = 'bounce'
                        boss_info['cross_phase2_target_top'] = (WIDTH / 2.0, max(boss_radius + 70, 90))
                        boss_info['cross_phase2_target_bottom'] = (WIDTH / 2.0, HEIGHT - max(boss_radius + 52, 120))
                        boss_info['cross_phase2_fall_speed'] = 0.0
                        boss_info['cross_phase2_rainbow_timer'] = 0
                        boss_info['cross_phase2_rainbow_angle'] = 0.0
                        boss_info['cross_phase2_rainbow_burst_step'] = 0
                        boss_info['cross_phase2_ground_timer'] = 0
                        boss_info['cross_phase2_trapezoid_surface'] = None
                        boss_info['cross_phase2_trapezoid_width'] = 0
                        boss_info['cross_phase2_trapezoid_height'] = 0
                else:
                    decay_transition_effects(2.0)
                    boss_info['cross_falls'] = []
                    boss_info['cross_wall_attack'] = None
            else:
                boss_info['cross_falls'] = []
                boss_info['cross_transition_effects'] = []
                boss_info['star_rain_active'] = False
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
                    if not debug_infinite_hp:
                        player_lives -= 1
                    player_invincible = True
                    player_invincible_timer = 0
                    explosion_timer = 0
                    explosion_pos = (player.centerx, player.centery)
                    reset_boss_hazards_after_player_hit(boss_info)
                    bullets.remove(bullet)
                    break
        if boss_info and boss_info.get('name') == '赤バツボス':
            moon_beams = boss_info.get('cross_phase2_moon_beams', [])
            if moon_beams:
                px, py = player.center
                cushion = max(player.width, player.height) * 0.25
                for beam in moon_beams:
                    if beam.get('state') != 'firing':
                        continue
                    origin = beam.get('origin')
                    target = beam.get('target')
                    if not origin or not target:
                        continue
                    dist, _, _ = distance_point_to_segment(px, py, origin[0], origin[1], target[0], target[1])
                    if dist <= beam.get('hit_radius', 16) + cushion:
                        if not debug_infinite_hp:
                            player_lives -= 1
                        player_invincible = True
                        player_invincible_timer = 0
                        explosion_timer = 0
                        explosion_pos = (player.centerx, player.centery)
                        reset_boss_hazards_after_player_hit(boss_info)
                        break
                if player_invincible:
                    continue
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
                        if not debug_infinite_hp:
                            player_lives -= 1
                        player_invincible = True
                        player_invincible_timer = 0
                        explosion_timer = 0
                        explosion_pos = (player.centerx, player.centery)
                        reset_boss_hazards_after_player_hit(boss_info)
                        break
                # P2 も接触判定
                if player2:
                    for p in boss_info['parts']:
                        if not p.get('alive', True):
                            continue
                        if hit_crescent_point(player2.centerx, player2.centery, p['x'], p['y'], p.get('r', int(boss_radius*0.8)), p.get('face','right' if p['x'] < WIDTH//2 else 'left'), max(player2.width, player2.height)//2):
                            if not debug_infinite_hp:
                                player_lives -= 1
                            player_invincible = True
                            player_invincible_timer = 0
                            explosion_timer = 0
                            explosion_pos = (player2.centerx, player2.centery)
                            player2.x = WIDTH//2 + 40
                            player2.y = HEIGHT - 40
                            reset_boss_hazards_after_player_hit(boss_info)
                            break
            else:
                bx = player.centerx; by = player.centery
                if hit_crescent_point(bx, by, boss_x, boss_y, boss_radius, 'right', max(player.width, player.height)//2):
                    if not debug_infinite_hp:
                        player_lives -= 1
                    player_invincible = True
                    player_invincible_timer = 0
                    explosion_timer = 0
                    explosion_pos = (player.centerx, player.centery)
                    reset_boss_hazards_after_player_hit(boss_info)
            # 追加: 斬撃当たり判定
            for sl in boss_info.get('active_slashes', []):
                if sl['rect'].colliderect(player):
                    if not debug_infinite_hp:
                        player_lives -= 1
                    player_invincible = True
                    player_invincible_timer = 0
                    explosion_timer = 0
                    explosion_pos = (player.centerx, player.centery)
                    reset_boss_hazards_after_player_hit(boss_info)
        else:
            # 三日月形ボスでない通常ボス接触判定
            dx = player.centerx - boss_x
            dy = player.centery - boss_y
            if dx*dx + dy*dy < (boss_radius + max(player.width, player.height)//2)**2:
                if not debug_infinite_hp:
                    player_lives -= 1
                player_invincible = True
                player_invincible_timer = 0
                explosion_timer = 0
                explosion_pos = (player.centerx, player.centery)
                reset_boss_hazards_after_player_hit(boss_info)

    # 無敵時間管理
    if player_invincible:
        player_invincible_timer += 1
    if player_invincible_timer >= PLAYER_INVINCIBLE_DURATION and (globals().get('dash_state') or {'invincible_timer':0})['invincible_timer'] <= 0:
            player_invincible = False

    # 爆発表示管理
    if explosion_timer < EXPLOSION_DURATION and explosion_pos:
        explosion_timer += 1

    


