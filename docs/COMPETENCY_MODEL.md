# GD行動コンピテンシーモデル v0.1

## 1. 内部7軸

内部評価では、次の7軸を独立して保持する。

| ID | 評価軸 | 要点 |
|---|---|---|
| `issue_framing` | 課題設定・論点形成 | 目的、前提、制約、判断基準を整理する |
| `logical_reasoning` | 論理的思考・根拠 | 主張、理由、根拠、条件、反証を接続する |
| `listening_and_response` | 傾聴・応答 | 他者発言を理解し、意味のある応答を行う |
| `valuable_contribution` | 価値ある貢献 | 議論を前進させる新しい価値を追加する |
| `collaboration_and_relationship` | 協働・関係構築 | 参加しやすい環境と建設的な対立を作る |
| `decision_and_consensus` | 意思決定・合意形成 | 基準を使って案を比較し、合意へ進める |
| `process_and_time_management` | 時間・議論プロセス管理 | 進捗、順序、時間配分、収束方法を調整する |

## 2. 利用者表示用3領域

### 考える力

- 課題設定・論点形成
- 論理的思考・根拠
- 価値ある貢献

### 協働する力

- 傾聴・応答
- 協働・関係構築

### 前へ進める力

- 意思決定・合意形成
- 時間・議論プロセス管理

3領域は利用者向けの要約であり、校正前に7軸の単純平均を表示しない。v0.1では`coverage`、`bottleneck_dimension`、要約を返し、3領域の数値は`null`とする。

## 3. 旧5項目との対応

| 旧項目 | v0.1での扱い |
|---|---|
| 論理性 | `issue_framing`と`logical_reasoning`へ分解 |
| 積極性 | コア能力から外し、発言機会・発言量の補助統計へ移行 |
| 協調性 | `listening_and_response`と`collaboration_and_relationship`へ分解 |
| 表現力 | 話速・フィラー等を練習用コーチング情報として保持 |
| 解決策 | `valuable_contribution`と`decision_and_consensus`へ分解 |

## 4. 評価対象外

次は能力点へ直接使用しない。

- 発言回数だけ
- 発言時間だけ
- フィラー回数だけ
- 役割名だけ
- 同意回数だけ
- 音声・映像から推定した人格や属性

## 5. 複数機会の原則

一つの発言から全軸を採点しない。シナリオは、各軸の機会をID付きで明示する。

```json
{
  "evaluation_opportunities": [
    {
      "opportunity_id": "A-OP-IS-01",
      "dimension": "issue_framing",
      "phase": "problem_definition",
      "trigger": "after_initial_positions",
      "expected_actor": "candidate",
      "required_context": ["priority_target_undefined"],
      "invalidated_by": ["A-PROH-01"]
    }
  ]
}
```

機会数は配列から算出する。必要な評価機会が提供されなかった場合、影響する軸は`NE`とする。
