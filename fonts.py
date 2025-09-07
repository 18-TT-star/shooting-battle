# fonts.py
# 日本語フォント解決とキャッシュ
import pygame

JP_FONT_CANDIDATES = [
    "NotoSansCJKJP", "Noto Sans CJK JP", "notosanscjkjp", "notosansjp",
    "SourceHanSansJP", "sourcehansansjp", "ipagothic", "ipamgothic",
    "TakaoPGothic", "VL PGothic", "meiryo", "msgothic", "Yu Gothic", "yugothic", "sansserif"
]
_JP_FONT_PATH = None
for _name in JP_FONT_CANDIDATES:
    try:
        p = pygame.font.match_font(_name)
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
