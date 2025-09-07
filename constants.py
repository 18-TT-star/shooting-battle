# constants.py
# ゲーム全体で共有する定数・色・レベル/ボス定義

# 画面サイズ
WIDTH, HEIGHT = 480, 640

# 時間/演出関連
EXPLOSION_DURATION = 30        # 小爆発表示フレーム
BOSS_EXPLOSION_DURATION = 60   # ボス撃破時派手演出
PLAYER_INVINCIBLE_DURATION = 120
BOSS_ATTACK_INTERVAL = 180

# 楕円ボス コア調整
OVAL_CORE_RADIUS = 28          # 弱点赤丸半径
OVAL_CORE_GAP_HIT_THRESHOLD = 3
OVAL_CORE_NO_REFLECT_WHEN_OPEN = True
OVAL_CORE_GAP_TARGET = 40
OVAL_CORE_CYCLE_INTERVAL = 240
OVAL_CORE_FIRING_DURATION = 60
OVAL_CORE_OPEN_HOLD = 120
OVAL_CORE_GAP_STEP = 4  # 開閉1フレームあたり増減

# 楕円ボス ビーム同時発射用
OVAL_BEAM_INTERVAL = 170

# 色定義
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY  = (120, 120, 120)
RED   = (255, 0, 0)

# 弾カラー
BULLET_COLOR_NORMAL  = WHITE
BULLET_COLOR_HOMING  = (50, 200, 255)
BULLET_COLOR_ENEMY   = (255, 120, 40)
BULLET_COLOR_REFLECT = (255, 255, 0)
BULLET_COLOR_SPREAD  = (255, 100, 255)  # 拡散弾（3WAY）

# ボス / レベル定義
# HP をメインファイル側の最新調整値に合わせ統一 (蛇:40 / 楕円:10)
boss_list = [
    {"name": "Boss A", "radius": 60, "hp": 35, "color": RED},
    {"name": "蛇", "radius": 70, "hp": 40, "color": (128, 0, 128)},
    {"name": "楕円ボス", "radius": 70, "hp": 10, "color": (255, 165, 0)}
]

# レベル数を 6 までに縮小。index は 1..MAX_LEVEL を使用（0 番は未使用保険で None）。
MAX_LEVEL = 6
level_list = [
    {"level": 0, "boss": None},      # ダミー（インデックス合わせ）
    {"level": 1, "boss": boss_list[0]},
    {"level": 2, "boss": boss_list[1]},
    {"level": 3, "boss": boss_list[2]},
    {"level": 4, "boss": None},
    {"level": 5, "boss": None},
    {"level": 6, "boss": None},
]
