# Exercise B Four-State Matrix v0.1

| State | System Quality | Offered | Invalid | Numeric | NE | issue_framing | logical_reasoning | listening_and_response | valuable_contribution | collaboration_and_relationship | decision_and_consensus | process_and_time_management |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | pass | 15 | 0 | 7 | - | 4 | 4 | 4 | 4 | 4 | 4 | 3 |
| medium | pass | 15 | 0 | 7 | - | 3 | 3 | 3 | 3 | 3 | 3 | 2 |
| low | pass | 15 | 0 | 7 | - | 1 | 1 | 2 | 1 | 1 | 1 | 1 |
| system_failure | fail | 11 | 4 | 5 | issue_framing, decision_and_consensus | NE | 3 | 3 | 3 | 3 | NE | 2 |

## Cross-state assertions

- Normal-state AI messages are identical: true
- Normal-state System Quality is identical: true
- Normal-state opportunity supply is identical: true
- Runner receives the state label: false
- Core state literals: none
- Score order: high > medium > low
- Low remains fully numeric: true
- system_failure NE scope: issue_framing, decision_and_consensus
- system_failure unaffected dimensions match medium: true
- system_failure failed rules: B-PROH-01
