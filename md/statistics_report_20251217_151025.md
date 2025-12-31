# 계층적 통계 보고서

생성 일시: 2025-12-17 15:10:25

---

## NCTID 기준

| Level | Entity Type | Group Key | Status | Sub Status | Count | Total | Percentage |
|-------|-------------|-----------|-------|------------|-------|-------|------------|
| 0 | nctid | ALL | TOTAL |  | 1,370 | 1,370 | 100.00% |
| 1 | nctid | ALL | &nbsp;&nbsp;FAILURE |  | 701 | 1,370 | 51.17% |
| 1 | nctid | ALL | &nbsp;&nbsp;SUCCESS |  | 669 | 1,370 | 48.83% |
| 2 | nctid | ALL | &nbsp;&nbsp;&nbsp;&nbsp;FAILURE | &nbsp;&nbsp;&nbsp;&nbsp;FULL_FAIL | 219 | 1,370 | 15.99% |
| 2 | nctid | ALL | &nbsp;&nbsp;&nbsp;&nbsp;FAILURE | &nbsp;&nbsp;&nbsp;&nbsp;PARTIAL_FAIL | 482 | 1,370 | 35.18% |

---

## Outcome 기준

| Level | Entity Type | Group Key | Status | Sub Status | Count | Total | Percentage |
|-------|-------------|-----------|-------|------------|-------|-------|------------|
| 0 | outcome | ALL | TOTAL |  | 9,030 | 9,030 | 100.00% |
| 1 | outcome | ALL | &nbsp;&nbsp;FAILURE |  | 2,169 | 9,030 | 24.02% |
| 1 | outcome | ALL | &nbsp;&nbsp;SUCCESS |  | 6,861 | 9,030 | 75.98% |
| 2 | outcome | ALL | &nbsp;&nbsp;&nbsp;&nbsp;FAILURE | &nbsp;&nbsp;&nbsp;&nbsp;BOTH_FAIL | 131 | 9,030 | 1.45% |
| 2 | outcome | ALL | &nbsp;&nbsp;&nbsp;&nbsp;FAILURE | &nbsp;&nbsp;&nbsp;&nbsp;MEASURE_FAIL | 1,647 | 9,030 | 18.24% |
| 2 | outcome | ALL | &nbsp;&nbsp;&nbsp;&nbsp;FAILURE | &nbsp;&nbsp;&nbsp;&nbsp;TIME_FAIL | 391 | 9,030 | 4.33% |

---

## Primary/Secondary 기준

| Level | Entity Type | Group Key | Status | Sub Status | Count | Total | Percentage |
|-------|-------------|-----------|-------|------------|-------|-------|------------|
| 0 | outcome_type | PRIMARY | TOTAL |  | 3,078 | 3,078 | 100.00% |
| 0 | outcome_type | SECONDARY | TOTAL |  | 5,952 | 5,952 | 100.00% |
| 1 | outcome_type | PRIMARY | &nbsp;&nbsp;FAILURE |  | 798 | 3,078 | 25.93% |
| 1 | outcome_type | PRIMARY | &nbsp;&nbsp;SUCCESS |  | 2,280 | 3,078 | 74.07% |
| 1 | outcome_type | SECONDARY | &nbsp;&nbsp;FAILURE |  | 1,371 | 5,952 | 23.03% |
| 1 | outcome_type | SECONDARY | &nbsp;&nbsp;SUCCESS |  | 4,581 | 5,952 | 76.97% |
| 2 | outcome_type | PRIMARY | &nbsp;&nbsp;&nbsp;&nbsp;FAILURE | &nbsp;&nbsp;&nbsp;&nbsp;BOTH_FAIL | 62 | 3,078 | 2.01% |
| 2 | outcome_type | PRIMARY | &nbsp;&nbsp;&nbsp;&nbsp;FAILURE | &nbsp;&nbsp;&nbsp;&nbsp;MEASURE_FAIL | 562 | 3,078 | 18.26% |
| 2 | outcome_type | PRIMARY | &nbsp;&nbsp;&nbsp;&nbsp;FAILURE | &nbsp;&nbsp;&nbsp;&nbsp;TIME_FAIL | 174 | 3,078 | 5.65% |
| 2 | outcome_type | SECONDARY | &nbsp;&nbsp;&nbsp;&nbsp;FAILURE | &nbsp;&nbsp;&nbsp;&nbsp;BOTH_FAIL | 69 | 5,952 | 1.16% |
| 2 | outcome_type | SECONDARY | &nbsp;&nbsp;&nbsp;&nbsp;FAILURE | &nbsp;&nbsp;&nbsp;&nbsp;MEASURE_FAIL | 1,085 | 5,952 | 18.23% |
| 2 | outcome_type | SECONDARY | &nbsp;&nbsp;&nbsp;&nbsp;FAILURE | &nbsp;&nbsp;&nbsp;&nbsp;TIME_FAIL | 217 | 5,952 | 3.65% |

---

## Phase 기준

| Level | Entity Type | Group Key | Status | Sub Status | Count | Total | Percentage |
|-------|-------------|-----------|-------|------------|-------|-------|------------|
| 0 | phase | PHASE1 | TOTAL |  | 2,476 | 2,476 | 100.00% |
| 0 | phase | PHASE2 | TOTAL |  | 2,790 | 2,790 | 100.00% |
| 0 | phase | PHASE3 | TOTAL |  | 1,856 | 1,856 | 100.00% |
| 0 | phase | PHASE4 | TOTAL |  | 567 | 567 | 100.00% |
| 0 | phase | PHASE1,PHASE2 | TOTAL |  | 432 | 432 | 100.00% |
| 0 | phase | PHASE2,PHASE3 | TOTAL |  | 287 | 287 | 100.00% |
| 0 | phase | NA | TOTAL |  | 448 | 448 | 100.00% |
| 0 | phase | EARLY_PHASE1 | TOTAL |  | 174 | 174 | 100.00% |
| 1 | phase | PHASE1 | &nbsp;&nbsp;FAILURE |  | 464 | 2,476 | 18.74% |
| 1 | phase | PHASE1 | &nbsp;&nbsp;SUCCESS |  | 2,012 | 2,476 | 81.26% |
| 1 | phase | PHASE2 | &nbsp;&nbsp;FAILURE |  | 653 | 2,790 | 23.41% |
| 1 | phase | PHASE2 | &nbsp;&nbsp;SUCCESS |  | 2,137 | 2,790 | 76.59% |
| 1 | phase | PHASE3 | &nbsp;&nbsp;FAILURE |  | 453 | 1,856 | 24.41% |
| 1 | phase | PHASE3 | &nbsp;&nbsp;SUCCESS |  | 1,403 | 1,856 | 75.59% |
| 1 | phase | PHASE4 | &nbsp;&nbsp;FAILURE |  | 222 | 567 | 39.15% |
| 1 | phase | PHASE4 | &nbsp;&nbsp;SUCCESS |  | 345 | 567 | 60.85% |
| 1 | phase | PHASE1,PHASE2 | &nbsp;&nbsp;FAILURE |  | 116 | 432 | 26.85% |
| 1 | phase | PHASE2,PHASE3 | &nbsp;&nbsp;FAILURE |  | 73 | 287 | 25.44% |
| 1 | phase | EARLY_PHASE1 | &nbsp;&nbsp;FAILURE |  | 46 | 174 | 26.44% |
| 1 | phase | NA | &nbsp;&nbsp;FAILURE |  | 142 | 448 | 31.70% |
| 1 | phase | NA | &nbsp;&nbsp;SUCCESS |  | 306 | 448 | 68.30% |
| 1 | phase | PHASE2,PHASE3 | &nbsp;&nbsp;SUCCESS |  | 214 | 287 | 74.56% |
| 1 | phase | PHASE1,PHASE2 | &nbsp;&nbsp;SUCCESS |  | 316 | 432 | 73.15% |
| 1 | phase | EARLY_PHASE1 | &nbsp;&nbsp;SUCCESS |  | 128 | 174 | 73.56% |

---

