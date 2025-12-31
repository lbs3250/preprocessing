# 통합 데이터 진단 결과

**생성 시간**: 2025-12-17 10:59:28

---

```
================================================================================
1. NULL/빈 값 분석 (Study 단위)
================================================================================

📊 전체 Studies: 3,867건
  ❌ measure_raw 결측 Study: 0건 (0.0%)
  ❌ description_raw 결측 Study: 673건 (17.4%)
  ❌ time_frame_raw 결측 Study: 109건 (2.8%)

✅ 유효 데이터 Study 수:
  ✓ measure_raw 유효: 3,867건 (100.0%)
  ✓ description_raw 유효: 3,194건 (82.6%)
  ✓ time_frame_raw 유효: 3,758건 (97.2%)

📋 타입별 통계 (Study 단위):

  PRIMARY: 3,867건
    ❌ measure 결측 Study: 0건 (0.0%)
    ❌ timeFrame 결측 Study: 111건 (2.9%)

  SECONDARY: 2,906건
    ❌ measure 결측 Study: 0건 (0.0%)
    ❌ timeFrame 결측 Study: 92건 (3.2%)

================================================================================
📋 정규화 룰 설명
================================================================================

🔧 1차 정규화 룰 (Phase 1):

1. 텍스트 클리닝:
   • 공백 정리 (연속 공백 → 단일 공백)
   • 오타 교정 (extention → extension 등)

2. timeFrame 파싱:
   ✅ 파싱 가능한 패턴:
      - Baseline 포함: "Baseline, Week 16" → change_from_baseline_flag = TRUE
      - At Day/Week/Month N: "At Day 1", "At Week 14", "At Month 12" → N, day/week/month
      - Day/Month/Week N 단독: "Day 1", "Month 3", "Week 12" → N, day/month/week
      - Day N to/through M: "Day 1 to day 30", "Day 1 through 7" → 시작일, 종료일 추출
      - For N Months/Weeks/Days: "For 10 Months" → 10, month
      - At Months N and M: "At Months 6 and 12" → 복수 시점 추출
      - 텍스트 숫자+단위: "Two years", "eight weeks" → 2, year / 8, week
      - 숫자+단위: "26 weeks" → 26, weeks
      - Year N: "Year 3.5" → 3.5, year
      - Up to: "up to 72 hours" → 72, hour
      - Through: "through study completion, an average of 1 year" → 1, year
   
   ❌ 파싱 어려운 패턴:
      - "% of exact responses" (응답률)
      - "The time to respond" (시간/속도)
      - "0 Hour (pre-dose) on Day 1" (복잡한 시점 표현)
      - "3 Days in each of the 4 dosing session" (복잡한 조건부 표현)
      - 기타 비표준 표현

3. change_from_baseline 플래그:
   • description에서 "change from baseline" 패턴 검색
   • 발견 시 플래그 = TRUE

4. Phase 태깅:
   • double-blind, extension, follow-up 등 키워드 추출


================================================================================
📊 기관/담당자 전체 통계
================================================================================

🏢 LEAD_SPONSOR (기관) 통계:
  총 기관 수: 1,317개
  총 Study 수: 3,987건
  총 레코드 수: 3,987건

  Study 분포:
    평균: 3.0건/기관
    최소: 1건
    최대: 62건

👤 OFFICIAL (담당자) 통계:
  총 담당자 수: 2,808명
  총 Study 수: 3,025건
  총 레코드 수: 3,746건

  Study 분포:
    평균: 1.3건/담당자
    최소: 1건
    최대: 65건

================================================================================
2. timeFrame 패턴 분석
================================================================================

📊 총 timeFrame 데이터: 25,257건

📈 패턴 분류 결과:
  • Baseline 포함 (change_from_baseline): 9,469건 (37.5%)
  • 기간 패턴 (At Day/Week/Month N): 265건 (1.0%)
  • 기간 패턴 (Day/Month/Week N 단독): 3,548건 (14.0%)
  • 기간 패턴 (Day N to/through M): 0건 (0.0%)
  • 기간 패턴 (For N Months/Weeks/Days): 62건 (0.2%)
  • 기간 패턴 (At Months N and M): 0건 (0.0%)
  • 기간 패턴 (텍스트 숫자+단위): 684건 (2.7%)
  • 기간 패턴 (숫자+단위): 8,543건 (33.8%)
  • 기간 패턴 (Year N): 30건 (0.1%)
  • 기간 패턴 (Up to): 1,360건 (5.4%)
  • 기간 패턴 (Through): 302건 (1.2%)
  • 응답률/비율: 1건 (0.0%)
  • 시간/속도: 0건 (0.0%)
  • 기타/불명확: 993건 (3.9%)

🎯 파싱 가능성 요약:
  ✅ 파싱 가능 (기간 패턴 + Baseline 포함): 24,263건 (96.1%)
  ❌ 파싱 어려움 (기타/불명확): 994건 (3.9%)

📝 패턴별 예시 (최대 3개):

  Baseline 포함 (change_from_baseline):
    - Baseline
    - Baseline
    - Baseline

  기간 패턴 (텍스트 숫자+단위):
    - eight weeks
    - within three months of study enrollment
    - within three months of study enrollment

  기간 패턴 (Day/Month/Week N 단독):
    - Initial training (Day 0), Day 7, Day 14, Day 28, and Month 3
    - Initial training (Day 0), Day 7, Day 14, Day 28, and Month 3
    - week 26

  기간 패턴 (숫자+단위):
    - 3 months
    - 12 months
    - 24 months

  기타/불명확:
    - during procedure
    - directly after intervention
    - directly after intervention

  기간 패턴 (Up to):
    - CSF will be collected at Visit 1 (up to 30 days after the screening visit)
    - Up to 5 weeks
    - Up to 5 weeks

  기간 패턴 (For N Months/Weeks/Days):
    - Daily for 90 days (the length of the diet intervention)
    - Every day for 28 days
    - At each office visit, for 96 months, until patient left the practice, or until d...

  기간 패턴 (Through):
    - through study completion , an average of 1 year
    - through study completion , an average of 1 year
    - through study completion , an average of 2 years

  기간 패턴 (Year N):
    - Year 1, Year 2-3
    - Year 1, Year 2-3
    - Year 1, Year 2-3

  기간 패턴 (At Day/Week/Month N):
    - Prior to version 6 of the protocol, final assessments were performed at Week 42,...
    - Primary efficacy analysis at Week 28
    - Slopes will be estimated by using SIB data at Week 0, 5, 9, 13, 15, 20, 24, and ...

  응답률/비율:
    - percentage

================================================================================
3. measure 패턴 분석 (Outcome 단위)
================================================================================

📏 measure_raw 길이 통계:
  평균: 63.4자
  최소: 2자
  최대: 255자

🔤 약어 사용 분석 (Outcome 단위):
  ✅ 괄호 안 약어 포함: 5,739건 (22.4%)
  ❌ 약어 없음: 19,854건 (77.6%)

🏆 상위 20개 measure (빈도순):
   1. [  48건] Neuropsychiatric Inventory (NPI)
   2. [  28건] Montreal Cognitive Assessment (MoCA)
   3. [  27건] Mini-Mental State Examination (MMSE)
   4. [  20건] Biological Parameters in blood
   5. [  20건] Adverse Events
   6. [  20건] Cognition
   7. [  20건] Cognitive function
   8. [  18건] Adverse events
   9. [  17건] MMSE
  10. [  17건] Caregiver Burden
  11. [  16건] Neuropsychiatric Inventory
  12. [  14건] Pharmacokinetics (PK) of J4 Dry Powder Capsule
  13. [  14건] Depression
  14. [  13건] Perceived Stress Scale
  15. [  13건] Acceptability
  16. [  12건] Zarit Burden Interview
  17. [  12건] Geriatric Depression Scale
  18. [  12건] Change From Baseline in Cognitive Measure
  19. [  12건] Preliminary efficacy data (screening)
  20. [  11건] Safety and tolerability

================================================================================
📊 measure 약어 추출 - Study 단위 분석
================================================================================

📋 전체 Study 수: 3,867건
  • Primary outcome 있는 Study: 3,867건
  • Secondary outcome 있는 Study: 2,906건

✅ 약어 추출 성공률 (해당 outcome이 있는 Study 기준):
  📌 PRIMARY: 966건 / 3,867건 (25.0%)
     → PRIMARY outcome이 있는 3,867건 중 966건에서 약어 추출 성공
  📌 SECONDARY: 1,183건 / 2,906건 (40.7%)
     → SECONDARY outcome이 있는 2,906건 중 1,183건에서 약어 추출 성공

🎯 상세 분류 (전체 3,867건 Study 기준):
  ✅ 둘 다 성공: 507건 (13.1%)
     → PRIMARY 약어 추출 성공 + SECONDARY 약어 추출 성공
  📌 PRIMARY만 성공: 459건 (11.9%)
     → PRIMARY 약어 추출 성공 + SECONDARY 약어 추출 실패
  📌 SECONDARY만 성공: 676건 (17.5%)
     → PRIMARY 약어 추출 실패 + SECONDARY 약어 추출 성공
  ❌ 둘 다 실패: 2,225건 (57.5%)
     → PRIMARY 약어 추출 실패 + SECONDARY 약어 추출 실패

  → 검증: 507 + 459 + 676 + 2,225 = 3,867건
  → 검증: PRIMARY 성공 = 507 + 459 = 966건 ✓
  → 검증: SECONDARY 성공 = 507 + 676 = 1,183건 ✓

================================================================================
📊 timeFrame 파싱 - Study 단위 분석
================================================================================

📋 전체 Study 수: 3,867건
  • PRIMARY outcome 있는 Study: 3,867건
  • SECONDARY outcome 있는 Study: 2,906건
  • PRIMARY outcome의 measure 약어 추출 성공: 966건
  • SECONDARY outcome의 measure 약어 추출 성공: 1,183건

✅ PRIMARY Outcome (measure 약어 추출 성공한 966건 기준):
  ✅ outcome + frame 둘 다 성공: 821건 (85.0%)
  📌 outcome만 성공 (frame 실패): 145건 (15.0%)
  📌 frame만 성공 (measure 실패, PRIMARY outcome 있음): 2,257건
  → 검증 (measure 성공 기준): 966건 = 966건
  → 검증 (PRIMARY outcome 전체 기준): 3,223건 ≤ 3,867건

✅ SECONDARY Outcome (measure 약어 추출 성공한 1,183건 기준):
  ✅ outcome + frame 둘 다 성공: 1,035건 (87.5%)
  📌 outcome만 성공 (frame 실패): 148건 (12.5%)
  📌 frame만 성공 (measure 실패, SECONDARY outcome 있음): 1,358건
  → 검증 (measure 성공 기준): 1,183건 = 1,183건
  → 검증 (SECONDARY outcome 전체 기준): 2,541건 ≤ 2,906건

================================================================================
4. description 패턴 분석
================================================================================

📊 'change from baseline' 패턴 분석:
  ✅ 발견: 1,838건 (8.5%)
  ❌ 미발견: 19,750건 (91.5%)
  📋 전체: 21,588건

================================================================================
🔬 파싱 불가능 케이스 - 기관/담당자별 원인 분석
================================================================================

[LEAD_SPONSOR별 파싱 실패 케이스]
순위    스폰서명                                     클래스             Total      Null       Unparseable     실패율       
--------------------------------------------------------------------------------------------------------------
1     Avid Radiopharmaceuticals                INDUSTRY        126        0          41              32.5     %
2     University Hospital, Grenoble            OTHER           49         0          38              77.6     %
3     Institut National de la Santé Et de la   OTHER_GOV       64         0          36              56.2     %
4     AstraZeneca                              INDUSTRY        143        0          35              24.5     %
5     Assistance Publique - Hôpitaux de Pari   OTHER           145        0          33              22.8     %
6     South China Center For Innovative Phar   OTHER           63         0          29              46.0     %
7     Phonak AG, Switzerland                   INDUSTRY        27         0          27              100.0    %
8     University Hospital, Tours               OTHER           71         0          23              32.4     %
9     University of Genova                     OTHER           34         0          22              64.7     %
10    Fondazione Don Carlo Gnocchi Onlus       OTHER           63         0          21              33.3     %
11    University Hospital, Bordeaux            OTHER           208        0          20              9.6      %
12    GlaxoSmithKline                          INDUSTRY        347        4          19              5.5      %
13    University of California, Los Angeles    OTHER           170        0          18              10.6     %
14    University of Paris 5 - Rene Descartes   OTHER           32         0          18              56.2     %
15    GE Healthcare                            INDUSTRY        38         7          16              51.6     %
16    Maastricht University Medical Center     OTHER           39         0          16              41.0     %
17    SK Chemicals Co., Ltd.                   INDUSTRY        16         0          16              100.0    %
18    Storz Medical AG                         INDUSTRY        58         0          15              25.9     %
19    Centre Hospitalier Universitaire de Ni   OTHER           89         0          15              16.9     %
20    Zhejiang Hospital                        OTHER           15         0          15              100.0    %

[파싱 실패 케이스 샘플]

📌 timeFrame 파싱 실패 샘플 (Top 20):
   1. [  34건] At inclusion
   2. [  25건] at inclusion
   3. [  24건] 0, 1st, 3rd month (plus 4th and 6th month for controls AD_WaitC & AD_ActC)
   4. [  21건] at enrollment
   5. [  18건] 30 minutes
   6. [  18건] Approximately 10-15 minutes
   7. [  16건] The 4th 、8th and 12th week after taking Silkworm pupa powder.
   8. [  15건] 5 minutes
   9. [  15건] 05/01/2008-05/30/2020
  10. [  14건] 50-60 min after injection
  11. [  13건] 10 minutes
  12. [  13건] 75 minutes
  13. [  13건] once a year
  14. [  12건] immediately post-treatment
  15. [  10건] enrollment visit
  16. [  10건] Screening
  17. [  10건] End of study : around May 2022
  18. [  10건] The 4th 、8th and 12th week after taking placebo.
  19. [   9건] acute (less than 60 minutes)
  20. [   9건] once during the third week of the follow-up

📌 measure 약어 추출 실패 샘플 (Top 20):
   1. [  20건] Cognitive function
   2. [  20건] Cognition
   3. [  20건] Adverse Events
   4. [  20건] Biological Parameters in blood
   5. [  18건] Adverse events
   6. [  17건] MMSE
   7. [  17건] Caregiver Burden
   8. [  16건] Neuropsychiatric Inventory
   9. [  14건] Depression
  10. [  13건] Perceived Stress Scale
  11. [  13건] Acceptability
  12. [  12건] Change From Baseline in Cognitive Measure
  13. [  12건] Zarit Burden Interview
  14. [  12건] Geriatric Depression Scale
  15. [  11건] Safety and tolerability
  16. [  11건] Efficacy
  17. [  11건] ADAS-cog
  18. [  11건] Blood pressure
  19. [  10건] Weight
  20. [  10건] Total ketones

--------------------------------------------------------------------------------
[OFFICIAL별 파싱 실패 케이스]
순위    담당자명                           소속                                  Total      Unparseable     실패율       
--------------------------------------------------------------------------------------------------------------
1     Pfizer CT.gov Call Center      Pfizer                              646        147             22.9     %
2     Bristol-Myers Squibb           Bristol-Myers Squibb                283        125             44.5     %
3     GSK Clinical Trials            GlaxoSmithKline                     341        58              17.0     %
4     Roland Beisteiner, Prof.       Medical University of Vienna        42         42              100.0    %
5     Clinical Trials                Hoffmann-La Roche                   376        36              9.6      %
6     Richard Levy, MD, PhD          Institut National de la Santé Et    45         36              80.0     %
7     Call 1-877-CTLILLY (1-877-28   Eli Lilly and Company               326        27              8.4      %
8     Kathleen Pichora-Fuller, Pro   University of Toronto               27         27              100.0    %
9     Chief Medical Officer          Avid Radiopharmaceuticals           55         25              45.5     %
10    Sophie Portrat                 Laboratoire de Psychologie et Neu   23         23              100.0    %
11    Benoit Lemaire                 Laboratoire de Psychologie et Neu   23         23              100.0    %
12    Nicola L Bragazzi, MD, PhD,    Universita degli Studi di Genova    22         22              100.0    %
13    Ramani S Moonesinghe, MBBS,    University College, London          21         20              95.2     %
14    Victoire LEROY, MD             CHRU de Tours                       18         18              100.0    %
15    Sophie SB Blanchet, Ph.D       University of Paris                 32         18              56.2     %

================================================================================
5. LEAD_SPONSOR별 분석
================================================================================

🏢 Top 20 LEAD_SPONSOR (Studies 기준):
순위    스폰서명                                     클래스             Studies    Outcomes   Parseable    Parse%    
--------------------------------------------------------------------------------------------------------------
1     Pfizer                                   INDUSTRY        62         640        303          47.6     %
2     Eli Lilly and Company                    INDUSTRY        49         484        213          44.9     %
3     Avid Radiopharmaceuticals                INDUSTRY        42         126        62           49.2     %
4     Indiana University                       OTHER           34         236        228          96.6     %
5     Massachusetts General Hospital           OTHER           32         204        137          67.2     %
6     Johns Hopkins University                 OTHER           31         189        197          104.2    %
7     Wyeth is now a wholly owned subsidiary   INDUSTRY        31         74         43           76.8     %
8     Merck Sharp & Dohme LLC                  INDUSTRY        30         207        183          88.4     %
9     GlaxoSmithKline                          INDUSTRY        30         347        95           27.7     %
10    Centre Hospitalier Universitaire de Ni   OTHER           30         89         45           50.6     %
11    Chang Gung Memorial Hospital             OTHER           29         148        74           50.0     %
12    Washington University School of Medici   OTHER           27         189        90           47.6     %
13    AstraZeneca                              INDUSTRY        26         143        54           37.8     %
14    University of Washington                 OTHER           26         136        99           73.9     %
15    Brigham and Women's Hospital             OTHER           25         77         79           102.6    %
16    Assistance Publique - Hôpitaux de Pari   OTHER           25         145        110          75.9     %
17    Emory University                         OTHER           25         254        149          60.6     %
18    Hoffmann-La Roche                        INDUSTRY        25         317        161          50.8     %
19    Eisai Inc.                               INDUSTRY        23         199        107          54.6     %
20    NYU Langone Health                       OTHER           23         187        95           50.8     %

--------------------------------------------------------------------------------
LEAD_SPONSOR별 timeFrame 패턴 (Top 10)
--------------------------------------------------------------------------------

  📌 Pfizer (총 640건):
     • Period pattern: 229건 (35.8%)
     • Year pattern: 0건 (0.0%)
     • Up to pattern: 39건 (6.1%)
     • Through pattern: 0건 (0.0%)
     • Null/Empty: 3건 (0.5%)
     → ✅ 파싱 가능: 268건 (41.9%)
     → ❌ 파싱 어려움: 369건 (57.7%)

  📌 Eli Lilly and Company (총 484건):
     • Period pattern: 127건 (26.2%)
     • Year pattern: 6건 (1.2%)
     • Up to pattern: 45건 (9.3%)
     • Through pattern: 4건 (0.8%)
     • Null/Empty: 10건 (2.1%)
     → ✅ 파싱 가능: 182건 (37.6%)
     → ❌ 파싱 어려움: 292건 (60.3%)

  📌 GlaxoSmithKline (총 347건):
     • Period pattern: 35건 (10.1%)
     • Year pattern: 0건 (0.0%)
     • Up to pattern: 38건 (11.0%)
     • Through pattern: 0건 (0.0%)
     • Null/Empty: 4건 (1.2%)
     → ✅ 파싱 가능: 73건 (21.0%)
     → ❌ 파싱 어려움: 270건 (77.8%)

  📌 Hoffmann-La Roche (총 317건):
     • Period pattern: 30건 (9.5%)
     • Year pattern: 0건 (0.0%)
     • Up to pattern: 66건 (20.8%)
     • Through pattern: 0건 (0.0%)
     • Null/Empty: 0건 (0.0%)
     → ✅ 파싱 가능: 96건 (30.3%)
     → ❌ 파싱 어려움: 221건 (69.7%)

  📌 Emory University (총 254건):
     • Period pattern: 117건 (46.1%)
     • Year pattern: 2건 (0.8%)
     • Up to pattern: 15건 (5.9%)
     • Through pattern: 0건 (0.0%)
     • Null/Empty: 8건 (3.1%)
     → ✅ 파싱 가능: 134건 (52.8%)
     → ❌ 파싱 어려움: 112건 (44.1%)

  📌 Indiana University (총 236건):
     • Period pattern: 156건 (66.1%)
     • Year pattern: 0건 (0.0%)
     • Up to pattern: 23건 (9.7%)
     • Through pattern: 13건 (5.5%)
     • Null/Empty: 0건 (0.0%)
     → ✅ 파싱 가능: 192건 (81.4%)
     → ❌ 파싱 어려움: 44건 (18.6%)

  📌 University Hospital, Bordeaux (총 208건):
     • Period pattern: 150건 (72.1%)
     • Year pattern: 0건 (0.0%)
     • Up to pattern: 5건 (2.4%)
     • Through pattern: 0건 (0.0%)
     • Null/Empty: 0건 (0.0%)
     → ✅ 파싱 가능: 155건 (74.5%)
     → ❌ 파싱 어려움: 53건 (25.5%)

  📌 Xuanwu Hospital, Beijing (총 207건):
     • Period pattern: 117건 (56.5%)
     • Year pattern: 27건 (13.0%)
     • Up to pattern: 49건 (23.7%)
     • Through pattern: 1건 (0.5%)
     • Null/Empty: 0건 (0.0%)
     → ✅ 파싱 가능: 194건 (93.7%)
     → ❌ 파싱 어려움: 13건 (6.3%)

  📌 Merck Sharp & Dohme LLC (총 207건):
     • Period pattern: 111건 (53.6%)
     • Year pattern: 0건 (0.0%)
     • Up to pattern: 37건 (17.9%)
     • Through pattern: 0건 (0.0%)
     • Null/Empty: 0건 (0.0%)
     → ✅ 파싱 가능: 148건 (71.5%)
     → ❌ 파싱 어려움: 59건 (28.5%)

  📌 Massachusetts General Hospital (총 204건):
     • Period pattern: 99건 (48.5%)
     • Year pattern: 0건 (0.0%)
     • Up to pattern: 18건 (8.8%)
     • Through pattern: 1건 (0.5%)
     • Null/Empty: 0건 (0.0%)
     → ✅ 파싱 가능: 118건 (57.8%)
     → ❌ 파싱 어려움: 86건 (42.2%)

================================================================================
6. OFFICIAL(담당자)별 분석
================================================================================

👤 Top 20 OFFICIAL (Studies 기준):
순위    담당자명                                소속                                       Studies    Outcomes   Parseable    Parse%    
-----------------------------------------------------------------------------------------------------------------------------
1     Pfizer CT.gov Call Center           Pfizer                                   64         646        318          49.5     %
2     Call 1-877-CTLILLY (1-877-285-455   Eli Lilly and Company                    35         326        115          35.8     %
3     Clinical Trials                     Hoffmann-La Roche                        30         376        179          47.6     %
4     Bristol-Myers Squibb                Bristol-Myers Squibb                     27         283        47           16.7     %
5     GSK Clinical Trials                 GlaxoSmithKline                          27         341        93           27.3     %
6     Medical Monitor                     Wyeth is now a wholly owned subsidiary   26         42         21           87.5     %
7     Chief Medical Officer               Avid Radiopharmaceuticals                22         55         33           60.0     %
8     Novartis Pharmaceuticals            Novartis Pharmaceuticals                 20         129        37           28.7     %
9     Medical Director                    Merck Sharp & Dohme LLC                  19         174        154          88.5     %
10    Janssen Research & Development, L   Janssen Research & Development, LLC      16         128        109          85.2     %
11    Madhav Thambisetty, MD, PhD         National Institute on Aging (NIA)        14         21         23           109.5    %
12    Medical Director                    Biogen                                   13         106        59           55.7     %
13    Johnson & Johnson Pharmaceutical    Johnson & Johnson Pharmaceutical Resea   12         24         0            0.0      %
14    Danna Jennings, MD                  Institute for Neurodegenerative Disord   12         21         18           90.0     %
15    Email contact via H. Lundbeck A/S   LundbeckClinicalTrials@lundbeck.com      11         64         4            6.2      %
16    Tammie Benzinger, MD, PhD           Washington University School of Medici   10         27         27           100.0    %
17    Chief Medical Officer               Avid Radiopharmaceuticals, Inc.          9          25         8            32.0     %
18    Suzanne Craft, PhD                  Wake Forest University Health Sciences   9          42         15           35.7     %
19    Mariana Figueiro, PhD               Icahn School of Medicine at Mount Sina   7          68         10           14.7     %
20    Call 1-877-CTLILLY (1-877-285-455   Eli Lilly and Company                    7          60         21           35.0     %

--------------------------------------------------------------------------------
OFFICIAL별 measure 패턴 (Top 10)
--------------------------------------------------------------------------------

  📌 Pfizer CT.gov Call Center (Pfizer) - 총 646건:
     • 약어 포함: 202건 (31.3%)
     • Change from baseline: 48건 (7.4%)

  📌 Clinical Trials (Hoffmann-La Roche) - 총 376건:
     • 약어 포함: 147건 (39.1%)
     • Change from baseline: 78건 (20.7%)

  📌 GSK Clinical Trials (GlaxoSmithKline) - 총 341건:
     • 약어 포함: 109건 (32.0%)
     • Change from baseline: 171건 (50.1%)

  📌 Call 1-877-CTLILLY (1-877-285-4559) or 1 (Eli Lilly and Company) - 총 326건:
     • 약어 포함: 145건 (44.5%)
     • Change from baseline: 50건 (15.3%)

  📌 Bristol-Myers Squibb (Bristol-Myers Squibb) - 총 283건:
     • 약어 포함: 100건 (35.3%)
     • Change from baseline: 23건 (8.1%)

  📌 Medical Director (Merck Sharp & Dohme LLC) - 총 174건:
     • 약어 포함: 62건 (35.6%)
     • Change from baseline: 44건 (25.3%)

  📌 Novartis Pharmaceuticals (Novartis Pharmaceuticals) - 총 129건:
     • 약어 포함: 57건 (44.2%)
     • Change from baseline: 25건 (19.4%)

  📌 Janssen Research & Development, LLC Clin (Janssen Research & Development, LLC) - 총 128건:
     • 약어 포함: 38건 (29.7%)
     • Change from baseline: 6건 (4.7%)

  📌 Medical Director (Biogen) - 총 106건:
     • 약어 포함: 38건 (35.8%)
     • Change from baseline: 20건 (18.9%)

  📌 Dimitrios I Kapogiannis, M.D. (National Institute on Aging (NIA)) - 총 104건:
     • 약어 포함: 70건 (67.3%)
     • Change from baseline: 0건 (0.0%)

================================================================================
7. Sponsor Class별 패턴 분석
================================================================================

📊 Sponsor Class별 통계:
Class                Studies      Outcomes     Period Pattern                 Abbrev                         Avg Length  
------------------------------------------------------------------------------------------------------------------------
OTHER                2449         15859        9,184건(57.9%) 3,027건(19.1%) 54.4       
INDUSTRY             1275         8917         2,353건(26.4%) 2,536건(28.4%) 80.3       
OTHER_GOV            68           471          285건(60.5%) 61건(13.0%) 51.9       
FED                  36           147          117건(79.6%) 29건(19.7%) 48.4       
NIH                  27           162          34건(21.0%) 80건(49.4%) 61.2       
NETWORK              11           34           20건(58.8%) 5건(14.7%) 64.0       
INDIV                1            3            3건(100.0%) 1건(33.3%) 50.3       

================================================================================
8. 기관/담당자별 예상 매핑 실패율 분석
================================================================================

[LEAD_SPONSOR별 - 예상 timeFrame 파싱 실패율]
스폰서명                                               Total      Null       Complex    Failure Rate
----------------------------------------------------------------------------------------------------
GemVax & Kael                                      22         0          22         100.0      %
G2GBio, Inc.                                       24         0          24         100.0      %
Shahid Sadoughi University of Medical Sciences a   28         0          28         100.0      %
REGEnLIFE SAS                                      31         0          31         100.0      %
University of California, Santa Barbara            23         0          23         100.0      %
Technical University of Madrid                     32         0          32         100.0      %
Phonak AG, Switzerland                             27         0          27         100.0      %
Hopeful Aging                                      56         0          56         100.0      %
Hope Biosciences LLC                               49         0          49         100.0      %
Uskudar University                                 36         0          36         100.0      %

================================================================================
📊 종합 리포트
================================================================================

📊 기본 통계:
  총 Studies: 3,867건
  총 Outcomes: 25,593건
  Study당 평균 Outcomes: 6.6개
  PRIMARY: 9,514건 (37.2%)
  SECONDARY: 16,079건 (62.8%)

================================================================================
✅ 진단 완료!
================================================================================

```
