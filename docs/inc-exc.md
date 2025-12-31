1. 배경
   ClinicalTrials.gov의 Inclusion / Exclusion Criteria 데이터는
   임상시험 연구자가 직접 입력한 자유 서술형(free-text) 데이터로 구성되어 있다.

본 프로젝트에서는 해당 데이터를 구조화하여 분석·검색·정규화에 활용하고자 하나,
Rule-based 전처리 방식으로는 한계가 명확하여
LLM 기반 전처리 접근을 채택한다.

2. Rule-based 전처리가 어려운 이유
   2.1 데이터가 비정형 자유 텍스트이다
   Inclusion / Exclusion 기준은 정해진 입력 포맷이 없음

연구자마다 문장 구조, 길이, 표현 방식이 모두 다름

동일한 의미라도 문장 표현이 매우 다양함

예:

Patients aged 18 to 65

Subjects must be between eighteen and sixty-five years old

Age ≥18 and ≤65

→ 의미는 동일하지만 문자열 패턴은 완전히 다름

2.2 동일 개념에 대한 표현 다양성이 매우 큼
Rule-based 방식은 정해진 패턴 매칭에 의존하지만,
본 데이터는 표현의 변형(variation)이 매우 많음

용어 다양성

Hypertension / HTN / High blood pressure

숫자·조건 표현 다양성

≥, at least, more than, greater than

부정/제외 표현 방식 다양

must not have

no history of

patients with a history of X are excluded

→ 모든 케이스를 rule로 처리할 경우
룰 수가 기하급수적으로 증가

2.3 문맥(Context)에 따라 의미가 달라진다
Rule-based 방식은 키워드 추출은 가능하지만
문맥에 따른 의미 해석은 불가능

예:

Patients with diabetes are excluded

Patients without diabetes

Patients with diabetes unless well-controlled

→ 동일한 키워드(diabetes)를 포함하지만
포함 / 제외 / 조건부 포함으로 의미가 완전히 다름

2.4 Inclusion / Exclusion 경계가 명확하지 않다
Inclusion / Exclusion 항목이 명확히 분리되지 않은 경우가 많음

하나의 문장에 여러 조건이 혼합됨

Inclusion 문장 내부에 Exclusion 조건이 포함되기도 함

예:

Patients aged 18–65 with no history of cancer except non-melanoma skin cancer.

→ Rule-based 방식으로는
조건 분해 및 의미 구분이 매우 어려움

2.5 데이터 품질 편차와 노이즈가 큼
사람이 직접 입력한 데이터 특성상 다음 문제가 빈번함:

문법 오류, 철자 오류

줄바꿈, bullet, 번호 형식 혼재

특수문자, 복사/붙여넣기 오류

→ Rule-based 전처리는
노이즈에 매우 취약

2.6 유지보수 및 확장성이 없음
새로운 표현이 등장할 때마다 rule 추가 필요

rule 간 충돌 가능성 증가

파이프라인 복잡도 급증

→ 초기 일부 케이스는 처리 가능하나
장기적으로 유지보수 불가능

3. LLM 기반 전처리가 적합한 이유
   LLM은 다음과 같은 작업에 강점을 가짐:

의미 기반 이해 (Semantic understanding)

다양한 표현을 동일 개념으로 해석

문맥을 고려한 inclusion / exclusion 판단

하나의 문장에서 조건을 분해하여 구조화

즉,

Rule-based는 문자열 처리에 적합하고,
LLM은 사람이 작성한 텍스트 이해에 적합하다

Clinical Trial inclusion/exclusion 데이터는
본질적으로 사람이 사람에게 설명하듯 작성된 텍스트이기 때문에
LLM 기반 접근이 구조적으로 더 적합하다.

4. 결론
   Inclusion / Exclusion 데이터는 비정형·문맥 의존·표현 다양성이 매우 큼

Rule-based 전처리는 정확성, 확장성, 유지보수성 모두에서 한계 존재

LLM 기반 전처리를 통해 의미 중심 구조화가 필수적
