# Shooting Battle Gameplay Spec & Tunables

最終更新: 2025-09-15

このドキュメントは現行 `shooting_game.py` 実装の仕様と主な調整用パラメータ(tunables)を俯瞰できるよう整理したもの。新ボス追加や難易度調整、コード分割の足掛かりとして利用する。

---
## 1. 全体アーキテクチャ概要
- メインループ単一ファイル構成 (`shooting_game.py`).
- 外部モジュール:
  - `constants.py`: 画面サイズ・色・ボス定数・コア/ビーム/バウンド関連値。
  - `gameplay.py`: プレイヤー弾生成・移動、ダッシュ制御。
- データ構造:
  - 弾: `dict(rect, type, power, vx, vy, reflect, ...)` のリスト。
  - ボス: `boss_info` (name, radius, hp, 各ボス専用状態キー動的追加)。
  - 報酬: `unlocked_*` (永続レベル間) と `has_*` (そのステージ内) を分離。
- 1フレーム更新順: 入力→（開始待ち処理/リトライ処理）→ 弾発射 → プレイヤー移動/ダッシュ → ボスAI/攻撃 → 弾移動/相殺/反射 → 当たり判定 → 爆発/演出 → 描画。

## 2. プレイヤー
| 項目 | 値 / 挙動 | 備考 |
|------|-----------|------|
| 初期ライフ | 3 | ヒットで -1 → 無敵へ |
| 移動速度 | 5〜7 (開始条件で差異) | 定数化検討 |
| 通常無敵 | `PLAYER_INVINCIBLE_DURATION=120` フレーム | 被弾時付与 |
| ダッシュ無敵 | `DASH_INVINCIBLE_FRAMES=24` | ダッシュ発動時上書き |
| ダッシュ距離 | 140px | `DASH_DISTANCE` |
| ダッシュCT | 180f | `DASH_COOLDOWN_FRAMES` |
| ダブルタップ猶予 | 12f | `DASH_DOUBLE_TAP_WINDOW` |
| 弾種 | normal / homing / spread | Vキー巡回 |
| homing 追尾速度 | vx,vy 再計算: 目標へ正規化 * 6 | boss_alive 時のみ |
| spread | 3WAY (±0.18rad), 各 power=0.5 | 敵弾相殺可 |

## 3. 報酬システム
| ボス | 解放 | フラグ | 初期装備化 | 備考 |
|------|------|--------|------------|------|
| Boss A | homing弾 | unlocked_homing / has_homing | しない | Vで選択可能に |
| 蛇 | リーフシールド | unlocked_leaf_shield / has_leaf_shield | しない | 周囲防御回転 |
| 楕円ボス | spread弾 | unlocked_spread / has_spread | しない | 相殺 & 3WAY |
| バウンドボス | ダッシュ | unlocked_dash / has_dash | - | ←← / →→ で発動 |

- 撃破判定: `boss_alive` が False になった最初のフレームで `reward_granted` チェックし一度だけ付与。
- `has_*` は新規レベル開始時に `unlocked_*` をコピー。

## 4. ボス個別仕様
### 4.1 Boss A (Stomp)
- 状態: idle → descending → pause → ascending → cooldown。
- パラ: `stomp_interval=120`, `stomp_grace=180`。
- 改良余地: 落下速度定数化 / テレグラフ短点滅。

### 4.2 蛇 (Satellite + Stomp)
- 回転セグメント: 5 (`ROTATE_SEGMENTS_NUM`)。
- 半径: `ROTATE_RADIUS = boss_radius + 30`。
- 速度: `ROTATE_SPEED=0.03`。
- 反射: 衛星 or 本体矩形衝突で reflect, homing→normal 化。
- Stomp 派生: snake_* interval=150, grace=210。

### 4.3 楕円ボス (Core + Dual Beam)
- Core Cycle: `OVAL_CORE_CYCLE_INTERVAL=240` → opening → firing(60f) → open_hold(120f) → closing。
- Gap 制御: `OVAL_CORE_GAP_STEP=4`, 目標 `OVAL_CORE_GAP_TARGET=40`。
- 開放判定: gap > `OVAL_CORE_GAP_HIT_THRESHOLD=3`。
- リング弾: firing 中 (timer%12==1) で RING_NUM=10, speed=4, 位相回転あり。
- ビーム同期: `OVAL_BEAM_INTERVAL=170` で左右 telegraph→firing。
- 開放中弱点: コア円 + 楕円本体全体（ただし homing 弾は反射判定を持続）。

### 4.4 バウンドボス (Bounce + Squish + Shrink)
- 初期落下→底到達後 斜めランダム方向。
- リング弾: バウンド接触時（底以外）14方向 speed=4。
- 縮小: HP 5 減少ごとに `BOUNCE_BOSS_SHRINK_STEP=0.05` 比率縮小。
- 加速: 同タイミングで `BOUNCE_BOSS_SPEED_STEP=0.15` 増速。
- 角度乱数: ±`BOUNCE_BOSS_ANGLE_JITTER_DEG=40` + 微Jitter。
- Squish 演出: 16f (`BOUNCE_BOSS_SQUISH_DURATION`) 移動停止。

## 5. 反射 / 相殺ロジック
- Spread vs enemy: 二重ループで矩形衝突→双方除去。
- Reflect: 弾が当該領域接触で `reflect=True` / vy下向き正方向化 / vxランダム(-3〜3)。
- Homing → Reflect 後 normal 化（再追尾防止）。

## 6. ダッシュシステム詳細
- state: `{cooldown, invincible_timer, last_tap{left/right}, active}`。
- 発動条件: last_tap差 <= 12f。
- 効果: 即座に x±140 移動, 無敵24f, CT180f。
- UI: 円弧セグメント 12。CT割合で塗り進行。

## 7. 視覚/演出
| 項目 | 値 | 備考 |
|------|----|------|
| 小爆発 | 30f | 弾ヒット時等 |
| ボス撃破爆発 | 60f | 最終演出 |
| ウィンドウシェイク | 期間36f, 振幅26px | バウンド衝突等 |

## 8. 主な調整レバー早見
| カテゴリ | 定数 | 難易度への影響 (↓値 / ↑値) |
|----------|------|-----------------------------|
| Stomp頻度 | stomp_interval | ↓→頻度↑ / ↑→頻度↓ |
| Beam周期 | OVAL_BEAM_INTERVAL | ↓→被弾圧↑ / ↑→余裕↑ |
| Core開放周期 | OVAL_CORE_CYCLE_INTERVAL | ↓→機会&弾幕↑ / ↑→間延び |
| Bounce角揺らぎ | BOUNCE_BOSS_ANGLE_JITTER_DEG | ↓→予測容易 / ↑→カオス |
| 縮小率 | BOUNCE_BOSS_SHRINK_STEP | ↓→終盤当てにくい / ↑→終盤楽 |
| 加速率 | BOUNCE_BOSS_SPEED_STEP | ↓→安定 / ↑→後半圧迫 |
| ダッシュCT | DASH_COOLDOWN_FRAMES | ↓→回避頻度↑ / ↑→回避制限 |
| 無敵時間 | PLAYER_INVINCIBLE_DURATION | ↓→被弾リスク↑ / ↑→緩和 |

## 9. 改善余地 / 推奨次ステップ
| 項目 | 現状課題 | 改善案 |
|------|----------|--------|
| ファイル分割 | 1ファイル巨大 | `bosses/*.py`, `systems/` へ分割 |
| 魔法数散在 | 値がコード埋め込み | `tuning.py` へ集約 |
| 反射分岐冗長 | if ネスト深い | 形状判定関数抽出 / Strategy化 |
| 報酬UI | テキストのみ/瞬間的 | 画面上部アイコン常駐 + 点滅 |
| 計測 | バランス比較困難 | クリアタイム/被弾ログ出力 |
| 再利用性 | Boss追加コスト高 | 共通 BaseBoss クラス導入 |
| Spreadバランス | 3WAY=1.5倍総合火力 | 角度/威力スケール定数化試行 |
| Homing挙動 | 瞬間方向転換 | 緩和: 最大旋回角 (lerp) 導入 |

## 10. 扇ボス再実装スケッチ (将来)
- `FanBoss`: state machine (IDLE, PREP, DIVE, IAIGIRI, CRESCENT, HITO, COOLDOWN)。
- SwordAnimator: draw-back → swing 曲線補間 (`easeOutCubic`, `overshoot`)。
- Attack Weights: JSON で調整可能化例 `{dive:1, iai:1, crescent:0.7, hito:0.4}`。
- 予測回避: プレイヤー弾位置 + 速度ベクトル → 短期衝突予測し横シフト。

## 11. テスト / メトリクス導入案
| 目的 | 試験内容 |
|------|----------|
| ダッシュ発動安定性 | ダブルタップ短時間スクリプトで100回成功率 |
| 反射後挙動 | homing→reflect→normal化を自動検証 |
| ビーム密度 | 90秒間ビーム発射回数カウント |
| Bounce速度進行 | HP毎の速度ログ出力 |

## 12. 既知仕様上の注意
- Homing弾は core 開放中でも（弱点判定より）先に reflect 分岐に入るケースあり（変更するなら force_reflect 条件見直し）。
- プレイヤー矩形サイズ変更時（30x15→30x30）で一部当たり判定の余白差異発生し得る。
- ウィンドウシェイクはウィンドウマネージャ依存で揺れ頻度が見えづらい環境あり。

---
## 付録: 追加調整アイデア集 (短) 
- Spread: 中央弾1.0 / サイド0.4 x2 に再配分し総威力ほぼ据え置き + 精度報酬化。
- Bounce: 底面バウンド時にだけ波紋エフェクト（無弾）を足し緊張緩和フェーズ演出。
- Oval: 開放保持時間を被弾数に応じ短縮させ “攻め急げ” メカニクス化。
- 共通: 難易度プリセット `EASY/MID/HARD` で主要定数スケール適用。

---
(以上) この文書を更新する際は変更日と差分要約を先頭に追記すること。
