---
title: Candidate Assessment Scenario Pack v0.1 Decision
type: decision
tags: [gd, evaluation, scenario, opportunity]
permalink: candidate-assessment-scenario-pack-v0-1-decision
updated: 2026-08-04
---

# Candidate Assessment Scenario Pack v0.1 Decision

## Observations

- [decision] 利用者能力評価用の標準演習を、既存のシステム品質シナリオとは別にA・B・Cの3本で管理する
- [decision] Aは曖昧課題の構造化、Bは利害対立と統合、Cは時間制約下の意思決定を主題とする
- [decision] Scenario Pack全体で内部7軸に最低2つの評価機会を用意する
- [decision] 機会提供の有無と、利用者が期待行動を実行したかを別データとして扱う
- [decision] 有効な機会で観察された不完全行動は数値評価し、シナリオ欠陥で機会が消えた場合はNEにする
- [scope] participant role、private concern、required/forbidden move、instance-level rubricを各演習へ定義する
- [scope] positive、negative、NEの機会判定fixtureとCI検査を追加する
- [non_goal] 12完全Episode、人間二重評価、LLM Judge、GD APP実行統合は後続PRとする

## Relations

- part_of [[GD Evaluation Lab Project Overview]]
- follows [[Validation and Human Annotation Foundation Decision]]
- updates [[Current Status]]
