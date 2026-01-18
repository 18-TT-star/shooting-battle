# デバッグ機能バックアップ
# 2026年1月18日にshooting_game.pyから削除されたデバッグ機能
# 必要に応じて復元できるように保存

"""
デバッグ機能一覧:

1. タイトル画面でDキー: 真エンディング状態に即座に設定（削除済み）
   - 全レベルクリア
   - ボス1-5を金の星
   - ボス6を虹の星
   - 全装備アンロック

2. メニュー画面・ゲーム中でIキー: 全装備を即座に取得・装備（削除済み）
   - ホーミング弾
   - リーフシールド
   - 拡散弾
   - ダッシュ
   - HP+2
   - ライフを5に設定

3. メニュー画面・ゲーム中でHキー: 無限HP切り替え（削除済み）
   - debug_infinite_hp フラグのON/OFF
   - ONの時はライフを最大値に設定

4. バトル中でTキー: ボス即撃破（削除済み）
   - 通常ボス: 即座にHP0にして撃破
   - 赤バツボス: phase1→phase2移行、phase2→フルスクリーンモード移行、それ以外は即撃破

注意: メニュー画面でのTキー（タイトル画面に戻る）は通常機能として残っています
"""

# ========== タイトル画面のDキー処理 ==========
# Line 1401-1417付近
"""
if event.key == pygame.K_d:
    # 全レベルをクリア状態に
    for i in range(7):
        level_cleared[i] = True
    # ボス1-5を金の星に
    for i in range(1, 6):
        level_cleared_no_equipment[i] = True
    # ボス6を虹の星に
    level_cleared_rainbow_star[6] = True
    # 全装備をアンロック
    unlocked_homing = True
    unlocked_leaf_shield = True
    unlocked_spread = True
    unlocked_dash = True
    unlocked_hp_boost = True
    print("[DEBUG] 真エンディング状態に設定しました！")
    play_menu_beep()
"""

# ========== メニュー画面のTキー処理 ==========
# Line 1590-1594付近
"""
if event.key == pygame.K_t:
    menu_mode = False
    title_mode = True
    play_menu_beep()
"""

# ========== バトル中のTキー処理（ボス即撃破） ==========
# Line 2270-2328付近
"""
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
        elif cross_mode == 'phase2':
            # 虹星形態中: 体力を50%に削ってフルスクリーンモードへ
            active_max = boss_info.get('cross_active_hp_max', boss_hp)
            target_hp = max(1, active_max * 0.5)
            boss_info['cross_phase2_hp'] = target_hp
            boss_info['hp'] = target_hp
            boss_hp = target_hp
            # フルスクリーンをアンロック＆有効化
            fullscreen_unlocked = True
            if not is_fullscreen:
                set_display_mode(True)
            boss_info['cross_phase2_fullscreen_done'] = True
            # フルスクリーンモード状態を設定
            boss_info['cross_phase_mode'] = 'fullscreen_starstorm'
            boss_info['cross_phase2_state'] = 'fullscreen_starstorm'
            # 攻撃タイマーをリセット
            boss_info['cross_attack_timer'] = 0
            boss_info['cross_phase2_timer'] = 0
            # デバッグモードでは保護期間をスキップ
            boss_info['fullscreen_initialized'] = True
            boss_info['fullscreen_wait_timer'] = 300  # 保護期間を即座に終了
            boss_info['fullscreen_invincible'] = False  # 無敵解除
            # ワープ状態を初期化
            boss_info['fullscreen_warp_state'] = 'warning'
            boss_info['fullscreen_warp_timer'] = 0
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
"""

# ========== メニュー画面のIキー処理 ==========
# Line 1626-1635付近
"""
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
"""

# ========== メニュー画面のHキー処理 ==========
# Line 1637-1640付近
"""
if event.key == pygame.K_h:
    debug_infinite_hp = not debug_infinite_hp
    if debug_infinite_hp:
        player_lives = max(player_lives, 5 if (unlocked_hp_boost and equipment_enabled['hp_boost']) else 3)
"""

# ========== ゲーム中のIキー処理 ==========
# Line 2191-2200付近 と Line 2307-2316付近
"""
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
"""

# ========== ゲーム中のHキー処理 ==========
# Line 2202-2205付近 と Line 2318-2321付近
"""
if event.type == pygame.KEYDOWN and event.key == pygame.K_h:
    debug_infinite_hp = not debug_infinite_hp
    if debug_infinite_hp:
        player_lives = max(player_lives, 5 if (unlocked_hp_boost and equipment_enabled['hp_boost']) else 3)
"""

# ========== debug_infinite_hp 初期化 ==========
# Line 1349付近
"""
debug_infinite_hp = False
"""

# ========== debug_infinite_hp の使用箇所 ==========
# プレイヤーがダメージを受ける箇所で使用
"""
if not debug_infinite_hp:
    player_lives -= 1
"""

# 復元方法:
# 1. 上記のコードを該当箇所にコピー&ペースト
# 2. debug_infinite_hp 変数の初期化を追加
# 3. ダメージ処理に if not debug_infinite_hp: を追加
