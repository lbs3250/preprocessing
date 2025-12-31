# 일일 작업 요약 (2025-01-24) - Inclusion/Exclusion 전처리 고도화

## 주요 작업: Inclusion/Exclusion 프롬프트 고도화 및 재전처리 준비

## 1. Inclusion/Exclusion 프롬프트 개선

### 1.1 "present" 관련 애매한 설명 제거

- **문제**: "단순히 'present'만 있으면 → operator: '=', value: feature의 값"이라는 설명이 애매함
- **해결**: 명확한 예시로 대체
  - "Patients must meet NINCDS-ADRDA criteria" → `feature: "patient", operator: "=", value: "NINCDS-ADRDA criteria"`
  - "Patients must have disrupted sleep" → `feature: "patient", operator: "=", value: "disrupted sleep"`

### 1.2 번호 리스트 및 중첩 불릿 포인트 처리 규칙 추가

- **문제**: `example.json`과 같은 복잡한 구조(번호 리스트, 중첩 불릿 포인트)에서 실패 발생
- **해결**: 명확한 처리 규칙 추가
  - 번호가 매겨진 리스트 (1., 2., 3. ...): 각 번호 항목을 하나의 criterion으로 처리
  - 중첩된 불릿 포인트 (_): 각 _ 불릿 포인트를 별도의 criterion으로 처리
  - 범위 조건: 두 개의 별도 criterion으로 분리 (아래 참조)
  - 매우 긴 문장: 하나의 criterion으로 처리하되, 핵심 조건만 추출

### 1.3 범위 조건 처리 방식 변경

- **변경 전**: 최소값 기준으로 하나의 criterion으로 처리
- **변경 후**: 반드시 두 개의 별도 criterion으로 분리
  - 예: "MMSE ≥18 and ≤26" →
    - `{"feature": "MMSE", "operator": ">=", "value": 18}`
    - `{"feature": "MMSE", "operator": "<=", "value": 26}`
  - 예: "Age 50-85 years" →
    - `{"feature": "age", "operator": ">=", "value": 50, "unit": "years"}`
    - `{"feature": "age", "operator": "<=", "value": 85, "unit": "years"}`
- **이유**: Inclusion criteria는 기본적으로 AND 로직이므로, 두 개로 분리해도 문제없음

## 2. nct_id 누락 문제 해결

### 2.1 문제 상황

- `[PARSE_ERROR] LLM 응답에 nct_id가 없음.` 에러가 너무 빈번하게 발생

### 2.2 해결 방법

#### 2.2.1 프롬프트 강화

- `llm_prompts.py`: nct_id 필수 포함을 더 강조
  - "⚠️ 필수: 각 JSON 객체의 최상위 레벨에 반드시 'nct_id' 필드를 포함하세요. nct_id가 없으면 응답이 무효화됩니다."

#### 2.2.2 부분 파싱 복구 시 순서 기반 nct_id 복구

- `llm_preprocess_inclusion_exclusion.py`의 `call_gemini_api` 함수 수정
  - `nct_id_list` 파라미터 추가
  - 부분 파싱 복구 단계에서 nct_id가 없으면 순서 기반으로 복구 시도
  ```python
  if not nct_id or not isinstance(nct_id, str) or not nct_id.strip():
      if nct_id_list and idx < len(nct_id_list):
          nct_id = nct_id_list[idx]
          item['nct_id'] = nct_id
          print(f"  [복구] nct_id 누락 항목을 순서 기반으로 복구: {nct_id}")
  ```

#### 2.2.3 매핑 실패 시 추가 복구 로직

- `preprocess_batch_eligibility` 함수에서 매핑 단계에서도 순서 기반 복구 시도
- 모든 복구 시도 실패 시에만 `[PARSE_ERROR]` 발생

### 2.3 결과

- nct_id 누락 에러가 크게 감소할 것으로 예상됨
- LLM 응답에 nct_id가 없어도 순서 기반으로 복구 시도

## 3. 통계 확인

### 3.1 Outcome LLM 전처리 성공률

- **전체**: 9,030개
- **성공 (SUCCESS)**: 8,912개 (98.69%)
- **Measure 실패**: 17개 (0.19%)
- **Timeframe 실패**: 88개 (0.97%)
- **둘 다 실패**: 13개 (0.14%)
- **API 실패**: 0개 (0.00%)

### 3.2 Outcome LLM 검증 성공률

- **전체 SUCCESS 항목**: 8,912개

  - **Verified**: 2,688개 (30.16%)
  - **Uncertain**: 96개 (1.08%)
  - **Measure Failed**: 19개 (0.21%)
  - **Timeframe Failed**: 190개 (2.13%)
  - **Both Failed**: 2개 (0.02%)
  - **Not Validated (NULL)**: 5,917개 (66.39%) — 아직 검증 미완료

- **검증 완료 항목 기준** (2,995개):
  - **Verified**: 2,688개 (89.75%)
  - **Uncertain**: 96개 (3.21%)
  - **Failed**: 211개 (7.05%)

## 4. 수정된 파일 목록

1. `llm/llm_prompts.py`

   - Inclusion/Exclusion 프롬프트 규칙 개선
   - 번호 리스트 및 중첩 불릿 포인트 처리 규칙 추가
   - 범위 조건 처리 방식 변경 (최소값 기준 → 두 개로 분리)
   - "present" 관련 애매한 설명 제거 및 명확한 예시 추가

2. `llm/llm_preprocess_inclusion_exclusion.py`

   - `call_gemini_api` 함수에 `nct_id_list` 파라미터 추가
   - 부분 파싱 복구 시 순서 기반 nct_id 복구 로직 추가
   - `preprocess_batch_eligibility` 함수에서 매핑 실패 시 추가 복구 로직 구현

3. `check_validation_stats.py` (임시 스크립트)
   - Outcome LLM 검증 통계 확인용 스크립트 생성

## 5. 다음 작업 예정

1. Inclusion/Exclusion 전처리 테스트

   - 개선된 프롬프트로 `example.json`과 같은 복잡한 구조 처리 테스트
   - nct_id 복구 로직 검증

2. Outcome LLM 검증 완료

   - 남은 5,917개 항목 검증 진행 (현재 33.61% 완료)

3. Inclusion/Exclusion 전처리 및 검증 진행
   - 데이터 수집 완료 상태 확인
   - 전처리 및 검증 스크립트 실행
