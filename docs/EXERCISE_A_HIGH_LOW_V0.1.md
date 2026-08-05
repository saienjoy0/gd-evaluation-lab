# Exercise A high / low 校正ケース v0.1

## 1. 目的

Generic Full-Episode Runner v0.1が、`state`を生成入力として読まずに、同じScenarioと同じ評価機会から異なる候補者行動を評価できることを確認する。

このPRではExercise Aへ次の2ケースを追加する。

- `high`: 論点構造化、複数案比較、懸念統合、合意条件、時間管理を明示したEpisode
- `low`: 評価機会には応答するが、対象・根拠・修正・合意条件・進捗管理が弱いEpisode

既存`medium`と合わせ、7軸すべてで`high > medium > low`を成立させる。

## 2. 統制するもの

3ケース間で次を同一にする。

- ScenarioとScenario version
- AI参加者、AI発言、AI/system品質
- 12個の評価機会
- 各評価機会のtrigger、phase、required context
- candidate responseの有無
- runner、resolver、rubricのversion

したがって、点数差は`state`ラベルやAI失敗ではなく、利用者本人の観察可能な発言差から生じる。

## 3. highケース

highでは全12機会へ応答し、次を複数phaseで観察できるようにする。

- 目的、対象、制約、成功基準、優先順位の構造化
- 静音専用案と時間帯分離案の比較
- 騒音、動線、運営工数を条件へ統合
- 未解決点を各立場へ確認
- 指標、閾値、中間レビュー、撤退条件を含む合意
- 残り時間、担当、月次確認、3か月レビューの提示

最終校正点は6軸が4、時間・プロセス管理が3とする。Score 4の証拠は必ず2phase以上にまたがる。

## 4. lowケース

lowでも全12機会は提供され、candidate responseも存在する。評価不能やsystem failureへ逃がさず、弱い行動を数値評価する。

- 優先対象と制約を定義しない
- 比較理由と根拠を示さない
- 懸念へ表面的に返答する
- 既出案を具体化しない
- 他者参加を促進しない
- 判断基準なしに結論を急ぐ
- 時間、担当、見直し条件を整理しない

AI/systemルールはすべてpassのまま、candidate/episode対象の`A-R02`、`A-R03`、`A-R05`だけをfailにする。

## 5. Feedbackの安全修正

従来のFeedback Builderは、最低点が1または2でも上位2領域を機械的に`strengths`へ入れられた。これではlowケースへ実際には観察されていない強い見出しを表示する可能性がある。

`strengths`の候補をScore 3以上へ限定する。mediumの既存出力は変えず、lowでは空配列とする。

## 6. CI完了条件

`check_exercise_a_high_low.py`で次を検査する。

- high / medium / lowの全oracle完全一致
- 各ケースの2回実行一致
- 出力Schemaと依存Manifestの検証
- AI品質と12評価機会が3ケースで同一
- 全7軸で`high > medium > low`
- highの決定論的ルールが全pass
- lowは`A-R02`、`A-R03`、`A-R05`のみfail
- low Feedbackに誤ったstrengthがない
- case IDとtarget participant IDが衝突しない

このPRはケース追加と校正検査に限定し、runnerへstate分岐を追加しない。
