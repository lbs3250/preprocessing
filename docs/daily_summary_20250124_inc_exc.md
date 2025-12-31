# 일일 작업 요약 (2025-01-24) - Inclusion/Exclusion 전처리 고도화

## 주요 작업: Inclusion/Exclusion 프롬프트 고도화 및 재전처리 준비

### 1. 프롬프트 고도화 작업

#### 1.1 "present" 관련 애매한 설명 제거 및 명확화
- **문제점**: "단순히 'present'만 있으면 → operator: '=', value: feature의 값"이라는 설명이 애매하고 혼란스러움
- **해결**: 명확한 예시로 대체
  ```python
  # 변경 전 (애매함)
  단순히 "present"만 있으면 → operator: "=", value: feature의 값
  
  # 변경 후 (명확함)
  - "Patients must meet NINCDS-ADRDA criteria" → 
    feature: "patient", operator: "=", value: "NINCDS-ADRDA criteria"
  - "Patients must have disrupted sleep" → 
    feature: "patient", operator: "=", value: "disrupted sleep"
  ```

#### 1.2 번호 리스트 및 중첩 불릿 포인트 처리 규칙 추가
- **문제점**: `example.json`과 같은 복잡한 구조에서 실패 발생
  - 번호가 매겨진 리스트 (1., 2., 3. ...)
  - 중첩된 불릿 포인트 (*)
  - 매우 긴 문장
- **해결**: 명확한 처리 규칙 추가
  ```python
  **중요: 번호가 매겨진 리스트와 중첩 불릿 포인트 처리**
  - 번호가 매겨진 리스트 (1., 2., 3. ...): 각 번호 항목을 하나의 criterion으로 처리
  - 중첩된 불릿 포인트 (*): 각 * 불릿 포인트를 별도의 criterion으로 처리
    * 예: "3. Clinical findings consistent with:
         * other primary degenerative dementia
         * other neurodegenerative condition
         * cerebrovascular disease"
    → 3개의 별도 criterion으로 처리
  - 매우 긴 문장: 하나의 criterion으로 처리하되, 핵심 조건만 추출
  ```

#### 1.3 범위 조건 처리 방식 변경 (중요!)
- **변경 전**: 최소값 기준으로 하나의 criterion으로 처리
  ```json
  "MMSE ≥18 and ≤26" → {"feature": "MMSE", "operator": ">=", "value": 18}
  ```
- **변경 후**: 반드시 두 개의 별도 criterion으로 분리
  ```json
  "MMSE ≥18 and ≤26" → 
    {"feature": "MMSE", "operator": ">=", "value": 18},
    {"feature": "MMSE", "operator": "<=", "value": 26}
  ```
- **이유**: Inclusion criteria는 기본적으로 AND 로직이므로, 두 개로 분리해도 문제없음
- **적용 예시**:
  - "Age 50-85 years" → 두 개로 분리 (≥50, ≤85)
  - "BMI between 18 and 35" → 두 개로 분리 (≥18, ≤35)
  - "MMSE ≥18 and ≤26" → 두 개로 분리 (≥18, ≤26)

#### 1.4 복잡한 구조 처리 예시 추가
- `example.json`의 실제 구조를 반영한 예시 추가:
  ```python
  - 번호 리스트: "2. Age 50-85 years" → 두 개로 분리
  - 중첩 불릿: "3. Clinical findings consistent with: * other primary degenerative dementia" → 별도 criterion
  - 범위 조건: "6. Mild to moderate stage of AD according to MMSE ≥18 and ≤26" → 두 개로 분리
  - 복합 조건: "9. Absence of major depressive disease according to GDS of < 5" → 단일 criterion
  - 긴 문장: "4. Patients who show CSF biomarker data..." → 핵심 조건만 추출
  ```

### 2. nct_id 누락 문제 해결

#### 2.1 문제 상황
- `[PARSE_ERROR] LLM 응답에 nct_id가 없음.` 에러가 너무 빈번하게 발생
- LLM이 응답에서 nct_id를 포함하지 않는 경우가 많음

#### 2.2 해결 방법

##### 2.2.1 프롬프트 강화
- `llm_prompts.py`: nct_id 필수 포함을 더 강조
  ```python
  **⚠️ 필수: 각 JSON 객체의 최상위 레벨에 반드시 "nct_id" 필드를 포함하세요. 
  입력 데이터의 첫 번째 부분(nct_id)을 그대로 사용하세요. 
  nct_id가 없으면 응답이 무효화됩니다.**
  ```

##### 2.2.2 부분 파싱 복구 시 순서 기반 nct_id 복구
- `llm_preprocess_inclusion_exclusion.py`의 `call_gemini_api` 함수 수정
  - `nct_id_list` 파라미터 추가
  - 부분 파싱 복구 단계에서 nct_id가 없으면 순서 기반으로 복구 시도
  ```python
  def call_gemini_api(prompt: str, nct_id_list: List[str] = None) -> Optional[List]:
      # ...
      # 부분 파싱 복구 시
      if not nct_id or not isinstance(nct_id, str) or not nct_id.strip():
          if nct_id_list and idx < len(nct_id_list):
              nct_id = nct_id_list[idx]
              item['nct_id'] = nct_id
              print(f"  [복구] nct_id 누락 항목을 순서 기반으로 복구: {nct_id}")
  ```

##### 2.2.3 매핑 실패 시 추가 복구 로직
- `preprocess_batch_eligibility` 함수에서 매핑 단계에서도 순서 기반 복구 시도
- 모든 복구 시도 실패 시에만 `[PARSE_ERROR]` 발생
  ```python
  # 매핑 단계에서도 순서 기반 복구
  for idx, r in enumerate(result):
      nct_id = r.get('nct_id')
      if not nct_id or not isinstance(nct_id, str):
          if idx < len(nct_id_list):
              recovered_nct_id = nct_id_list[idx]
              r['nct_id'] = recovered_nct_id
              print(f"  [복구] 매핑 단계에서 nct_id 복구: {recovered_nct_id}")
  ```

### 3. 수정된 파일 목록

#### 3.1 `llm/llm_prompts.py`
- **INCLUSION_EXCLUSION_PREPROCESS_RULES** 섹션 전면 개선
  - "present" 관련 애매한 설명 제거
  - 번호 리스트 및 중첩 불릿 포인트 처리 규칙 추가
  - 범위 조건 처리 방식 변경 (최소값 기준 → 두 개로 분리)
  - 복잡한 구조 처리 예시 추가 (`example.json` 기반)

#### 3.2 `llm/llm_preprocess_inclusion_exclusion.py`
- `call_gemini_api` 함수
  - `nct_id_list` 파라미터 추가
  - 부분 파싱 복구 시 순서 기반 nct_id 복구 로직 추가
- `preprocess_batch_eligibility` 함수
  - `call_gemini_api` 호출 시 `nct_id_list` 전달
  - 매핑 실패 시 순서 기반 복구 로직 구현

### 4. 재전처리 준비 사항

#### 4.1 개선된 프롬프트 적용
- 기존 전처리 결과와 비교하여 개선 사항 확인 필요
- 특히 범위 조건이 두 개로 분리되는지 확인

#### 4.2 nct_id 복구 로직 검증
- 실제 전처리 실행 시 nct_id 누락 에러 감소 확인
- 순서 기반 복구가 제대로 작동하는지 검증

#### 4.3 복잡한 구조 처리 검증
- `example.json`과 같은 복잡한 구조에서 성공률 확인
- 번호 리스트, 중첩 불릿 포인트가 올바르게 처리되는지 확인

### 5. 예상 효과

1. **범위 조건 처리 개선**
   - "MMSE ≥18 and ≤26" 같은 조건이 두 개의 명확한 criterion으로 분리됨
   - Inclusion criteria의 AND 로직과 일치하는 구조

2. **nct_id 누락 에러 감소**
   - 순서 기반 복구 로직으로 대부분의 nct_id 누락 문제 해결 예상
   - `[PARSE_ERROR] LLM 응답에 nct_id가 없음.` 에러 크게 감소

3. **복잡한 구조 처리 개선**
   - 번호 리스트, 중첩 불릿 포인트 등 복잡한 구조 처리 성공률 향상 예상
   - `example.json`과 같은 실제 데이터에서도 정상 처리 가능

### 6. 다음 단계

1. **재전처리 실행**
   - 개선된 프롬프트로 Inclusion/Exclusion 데이터 재전처리
   - 기존 결과와 비교 분석

2. **결과 검증**
   - 범위 조건이 두 개로 분리되었는지 확인
   - nct_id 누락 에러 감소 확인
   - 복잡한 구조 처리 성공률 확인

3. **추가 개선 사항 확인**
   - 재전처리 결과를 바탕으로 추가 개선 필요 사항 파악

