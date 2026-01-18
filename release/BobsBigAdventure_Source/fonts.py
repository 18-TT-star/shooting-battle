# fonts.py
# 日本語フォント解決とキャッシュ
import pygame
import os

# フォントモジュールを初期化（Font生成やmetrics使用のため）
try:
    if not pygame.font.get_init():
        pygame.font.init()
except Exception:
    # 失敗しても後で再試行されるので無視
    pass

# 追加: ローカルフォント探索 (プロジェクト内 assets/fonts や同ディレクトリ)
LOCAL_FONT_DIRS = [
    os.path.join(os.path.dirname(__file__), 'assets', 'fonts'),
    os.path.dirname(__file__),
]

JP_FONT_CANDIDATES = [
    # Noto/Source Han 系（推奨）
    "NotoSansCJKJP", "Noto Sans CJK JP", "Noto Sans JP", "NotoSansJP",
    "SourceHanSansJP", "Source Han Sans JP", "sourcehansansjp",
    # IPA/VL/Takao/Windows 系
    "IPAexGothic", "ipagothic", "ipamgothic",
    "TakaoPGothic", "VL PGothic",
    "Meiryo", "meiryo", "MS Gothic", "msgothic", "Yu Gothic", "yugothic",
    # 最後にジェネリック
    "DejaVu Sans", "dejavusans", "sansserif",
    # 幅広いグリフカバー（ある場合の最終手段）
    "Unifont", "unifont", "Unifont Upper"
]

# 記号・矢印・装飾シンボル用の候補
SYMBOL_FONT_CANDIDATES = [
    "Noto Sans Symbols 2", "Noto Sans Symbols2", "Noto Sans Symbols",
    "Symbola", "Segoe UI Symbol", "Apple Symbols",
    "DejaVu Sans", "Unifont", "Unifont Upper"
]
_JP_FONT_PATH = None
_SYM_FONT_PATH = None
_WARNED_FALLBACK = False

_TEST_JP_CHARS = "漢あア"
_TEST_SYMBOL_CHARS = "←→↑↓◆★♪☆→←✓✔✕✖•◦▶◀▲▼★☆♩♪♬♭♯"

def _font_has_glyphs(font_path: str, chars: str) -> bool:
    try:
        f = pygame.font.Font(font_path, 18)
        # metrics(char) は存在しないと None を返す
        for ch in chars:
            m = f.metrics(ch)
            if not m or not isinstance(m, (list, tuple)):
                return False
            m0 = m[0] if isinstance(m, (list, tuple)) else None
            if m0 is None:
                return False
        return True
    except Exception:
        return False
for _name in JP_FONT_CANDIDATES:
    try:
        p = pygame.font.match_font(_name)
    except Exception:
        p = None
    if p:
        # 日本語と記号の両方に対応しているかを優先
        if _font_has_glyphs(p, _TEST_JP_CHARS + _TEST_SYMBOL_CHARS):
            _JP_FONT_PATH = p
            break
# 条件を満たすフォントが見つからなかった場合、日本語だけでも描ける候補を再探索
if not _JP_FONT_PATH:
    for _name in JP_FONT_CANDIDATES:
        try:
            p = pygame.font.match_font(_name)
        except Exception:
            p = None
        if p and _font_has_glyphs(p, _TEST_JP_CHARS):
            _JP_FONT_PATH = p
            break
# それでも未決なら、利用可能フォント名一覧から "unifont" を検索
if not _JP_FONT_PATH:
    try:
        names = pygame.font.get_fonts()  # lower-case list
        for nm in names:
            if 'unifont' in nm:
                p = pygame.font.match_font(nm)
                if p:
                    _JP_FONT_PATH = p
                    break
    except Exception:
        pass
# ローカル ttf/otf/ttc を探索（見つからなかった場合）
if not _JP_FONT_PATH:
    exts = ('.ttf', '.otf', '.ttc')
    for d in LOCAL_FONT_DIRS:
        try:
            if not os.path.isdir(d):
                continue
            for fn in os.listdir(d):
                if fn.lower().endswith(exts):
                    cand = os.path.join(d, fn)
                    if _font_has_glyphs(cand, _TEST_JP_CHARS + _TEST_SYMBOL_CHARS) or _font_has_glyphs(cand, _TEST_JP_CHARS):
                        _JP_FONT_PATH = cand
                        break
            if _JP_FONT_PATH:
                break
        except Exception:
            pass

# 記号フォント探索（矢印や★などの装飾）
for _name in SYMBOL_FONT_CANDIDATES:
    try:
        p = pygame.font.match_font(_name)
    except Exception:
        p = None
    if p and _font_has_glyphs(p, _TEST_SYMBOL_CHARS):
        _SYM_FONT_PATH = p
        break
if not _SYM_FONT_PATH:
    exts = ('.ttf', '.otf', '.ttc')
    for d in LOCAL_FONT_DIRS:
        try:
            if not os.path.isdir(d):
                continue
            for fn in os.listdir(d):
                if fn.lower().endswith(exts):
                    cand = os.path.join(d, fn)
                    if _font_has_glyphs(cand, _TEST_SYMBOL_CHARS):
                        _SYM_FONT_PATH = cand
                        break
            if _SYM_FONT_PATH:
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

# 記号フォント取得（必要時のみ）
_sym_font_cache = {}
def symbol_font(size: int):
    f = _sym_font_cache.get(size)
    if f:
        return f
    if _SYM_FONT_PATH:
        f = pygame.font.Font(_SYM_FONT_PATH, size)
    else:
        f = pygame.font.SysFont(None, size)
    _sym_font_cache[size] = f
    return f

# 選択されたフォントを一度だけ表示（デバッグ用）
_printed_info = False
def _print_font_info_once():
    global _printed_info
    if _printed_info:
        return
    try:
        jp_name = os.path.basename(_JP_FONT_PATH) if _JP_FONT_PATH else "(SysFont)"
        sym_name = os.path.basename(_SYM_FONT_PATH) if _SYM_FONT_PATH else "(SysFont)"
        print(f"[fonts] JP font: {jp_name}  |  Symbol font: {sym_name}")
    except Exception:
        pass
    _printed_info = True

def _font_can_draw_char(font_obj: pygame.font.Font, ch: str) -> bool:
    try:
        m = font_obj.metrics(ch)
        return bool(m and m[0] is not None)
    except Exception:
        return False

def text_surface(text: str, size: int, color=(255,255,255), antialias=True) -> pygame.Surface:
    """
    文字ごとにフォントをフォールバックしつつ描画した Surface を返す。
    優先順位: jp_font(size) -> symbol_font(size) -> DejaVu Sans -> SysFont(None)
    改行 '\n' に対応。
    """
    _print_font_info_once()
    primary = jp_font(size)
    sym = symbol_font(size)
    # 追加の保険フォント
    extra_paths = []
    for name in ("DejaVu Sans", "Noto Sans Symbols 2", "Noto Sans Symbols"):
        try:
            p = pygame.font.match_font(name)
            if p and p not in extra_paths:
                extra_paths.append(p)
        except Exception:
            pass
    extra_fonts = [pygame.font.Font(p, size) for p in extra_paths]

    # 1パス目: 各行の幅・高さを見積もる
    lines = text.split('\n')
    line_metrics = []  # list of (width, height)
    for line in lines:
        x = 0
        h = 0
        for ch in line:
            f = primary if _font_can_draw_char(primary, ch) else (
                sym if _font_can_draw_char(sym, ch) else None
            )
            if f is None:
                for ef in extra_fonts:
                    if _font_can_draw_char(ef, ch):
                        f = ef
                        break
            if f is None:
                f = pygame.font.SysFont(None, size)
            cw, ch_h = f.size(ch)
            x += cw
            h = max(h, ch_h)
        if line == "":
            # 空行
            h = max(h, primary.get_linesize())
        line_metrics.append((x, h))

    surf_w = max((w for w, _ in line_metrics), default=1)
    surf_h = sum((h for _, h in line_metrics)) + max(0, len(lines) - 1) * 0
    if surf_w <= 0:
        surf_w = 1
    if surf_h <= 0:
        surf_h = primary.get_linesize()
    surface = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)

    # 2パス目: 実際に描画
    y = 0
    for idx, line in enumerate(lines):
        x = 0
        line_h = line_metrics[idx][1]
        # 同一フォントの連続ランでまとめ描き
        run_font = None
        run_text = ""
        def flush_run():
            nonlocal x, run_font, run_text
            if run_text and run_font:
                run_surf = run_font.render(run_text, antialias, color)
                surface.blit(run_surf, (x, y))
                x += run_surf.get_width()
            run_font = None
            run_text = ""
        for ch in line:
            f = primary if _font_can_draw_char(primary, ch) else (
                sym if _font_can_draw_char(sym, ch) else None
            )
            if f is None:
                for ef in extra_fonts:
                    if _font_can_draw_char(ef, ch):
                        f = ef
                        break
            if f is None:
                f = pygame.font.SysFont(None, size)
            if run_font is None:
                run_font = f
                run_text = ch
            elif f == run_font:
                run_text += ch
            else:
                flush_run()
                run_font = f
                run_text = ch
        flush_run()
        y += line_h
    return surface

