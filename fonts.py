# fonts.py
# 日本語フォント解決とキャッシュ
import pygame
import os

# 追加: ローカルフォント探索 (プロジェクト内 assets/fonts や同ディレクトリ)
LOCAL_FONT_DIRS = [
    os.path.join(os.path.dirname(__file__), 'assets', 'fonts'),
    os.path.dirname(__file__),
]

JP_FONT_CANDIDATES = [
    "NotoSansCJKJP", "Noto Sans CJK JP", "notosanscjkjp", "notosansjp",
    "SourceHanSansJP", "sourcehansansjp", "ipagothic", "ipamgothic",
    "TakaoPGothic", "VL PGothic", "meiryo", "msgothic", "Yu Gothic", "yugothic", "sansserif"
]
_JP_FONT_PATH = None
_WARNED_FALLBACK = False
for _name in JP_FONT_CANDIDATES:
    try:
        p = pygame.font.match_font(_name)
    except Exception:
        p = None
    if p:
        _JP_FONT_PATH = p
        break
# ローカル ttf/otf/ttc を探索（見つからなかった場合）
if not _JP_FONT_PATH:
    exts = ('.ttf', '.otf', '.ttc')
    for d in LOCAL_FONT_DIRS:
        try:
            if not os.path.isdir(d):
                continue
            for fn in os.listdir(d):
                if fn.lower().endswith(exts):
                    _JP_FONT_PATH = os.path.join(d, fn)
                    break
            if _JP_FONT_PATH:
                break
        except Exception:
            pass
_font_cache = {}

def jp_font(size: int):
    f = _font_cache.get(size)
    if f:
        return f
    if _JP_FONT_PATH:
        f = pygame.font.Font(_JP_FONT_PATH, size)
    else:
        # フォールバック（警告は一度だけ）
        global _WARNED_FALLBACK
        if not _WARNED_FALLBACK:
            print("[fonts] 日本語フォントが見つかりません。Noto Sans CJK JP 等の導入を推奨します。")
            _WARNED_FALLBACK = True
        f = pygame.font.SysFont(None, size)
    _font_cache[size] = f
    return f
