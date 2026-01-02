"""
Primary/Secondary Outcome Dictionary 생성 스크립트

빈도수와 키워드 기반으로 outcome_measure_dict 테이블에 데이터 추가
"""

import os
import re
from collections import Counter
from typing import Dict, List, Tuple, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'clinicaltrials'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}


def extract_keywords(measure_clean: str) -> str:
    """
    measure_clean에서 키워드 추출
    - 소문자 변환
    - 특수문자 제거
    - 공백으로 구분된 키워드 리스트 반환
    """
    if not measure_clean:
        return ""
    
    # 소문자 변환
    text = measure_clean.lower()
    
    # 특수문자 제거 (하이픈, 슬래시는 공백으로 변환)
    text = re.sub(r'[-/]', ' ', text)
    
    # 특수문자 제거 (괄호, 쉼표 등)
    text = re.sub(r'[^\w\s]', '', text)
    
    # 연속 공백 제거
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def analyze_outcomes_by_type(conn, outcome_type: str) -> List[Dict]:
    """
    Primary 또는 Secondary outcome 분석
    
    Returns:
        List of dicts with measure_clean, frequency, abbreviation, keywords
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                measure_clean,
                measure_abbreviation,
                COUNT(*) as frequency,
                COUNT(DISTINCT nct_id) as study_count,
                STRING_AGG(DISTINCT measure_raw, ' | ' ORDER BY measure_raw) as sample_raw_texts
            FROM outcome_normalized_success
            WHERE outcome_type = %s
              AND measure_clean IS NOT NULL
              AND measure_clean != ''
            GROUP BY measure_clean, measure_abbreviation
            ORDER BY frequency DESC
        """, (outcome_type,))
        
        results = cur.fetchall()
        
        # 키워드 추출 및 정리
        outcome_list = []
        for row in results:
            keywords = extract_keywords(row['measure_clean'])
            outcome_list.append({
                'measure_clean': row['measure_clean'],
                'abbreviation': row['measure_abbreviation'],
                'frequency': row['frequency'],
                'study_count': row['study_count'],
                'keywords': keywords,
                'sample_raw_texts': row['sample_raw_texts']
            })
        
        return outcome_list


def generate_measure_code(measure_clean: str, abbreviation: Optional[str] = None) -> str:
    """
    measure_code 생성
    - abbreviation이 있으면 사용
    - 없으면 measure_clean에서 키워드 추출하여 생성
    """
    if abbreviation:
        # 괄호 제거하고 정리
        code = abbreviation.strip('()').upper().replace(' ', '_').replace('-', '_')
        # 특수문자 제거
        code = re.sub(r'[^\w]', '', code)
        return code[:50]  # VARCHAR(50) 제한
    
    # abbreviation이 없으면 measure_clean에서 키워드 추출
    keywords = extract_keywords(measure_clean)
    words = keywords.split()[:3]  # 처음 3개 단어만 사용
    code = '_'.join(words).upper()
    code = re.sub(r'[^\w]', '', code)
    return code[:50]


def main():
    print("=" * 80)
    print("Primary/Secondary Outcome Dictionary 생성")
    print("=" * 80)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        # Primary Outcomes 분석
        print("\n[1] Primary Outcomes 분석 중...")
        primary_outcomes = analyze_outcomes_by_type(conn, 'PRIMARY')
        print(f"  총 {len(primary_outcomes):,}개 패턴 발견")
        
        # Secondary Outcomes 분석
        print("\n[2] Secondary Outcomes 분석 중...")
        secondary_outcomes = analyze_outcomes_by_type(conn, 'SECONDARY')
        print(f"  총 {len(secondary_outcomes):,}개 패턴 발견")
        
        # 통합 (중복 제거)
        print("\n[3] 통합 및 중복 제거 중...")
        all_outcomes = {}
        
        for outcome in primary_outcomes + secondary_outcomes:
            measure_clean = outcome['measure_clean']
            if measure_clean not in all_outcomes:
                all_outcomes[measure_clean] = {
                    'measure_clean': measure_clean,
                    'abbreviation': outcome['abbreviation'],
                    'frequency': outcome['frequency'],
                    'study_count': outcome['study_count'],
                    'keywords': outcome['keywords'],
                    'sample_raw_texts': outcome['sample_raw_texts'],
                    'primary_count': 0,
                    'secondary_count': 0
                }
            
            # 빈도수 누적
            if outcome in primary_outcomes:
                all_outcomes[measure_clean]['primary_count'] += outcome['frequency']
            else:
                all_outcomes[measure_clean]['secondary_count'] += outcome['frequency']
        
        print(f"  통합 후 {len(all_outcomes):,}개 고유 패턴")
        
        # Dictionary에 삽입 (빈도수 상위 N개만)
        print("\n[4] Dictionary에 삽입 중...")
        sorted_outcomes = sorted(all_outcomes.values(), key=lambda x: x['frequency'], reverse=True)
        
        with conn.cursor() as cur:
            inserted_count = 0
            for outcome in sorted_outcomes:
                measure_code = generate_measure_code(
                    outcome['measure_clean'],
                    outcome['abbreviation']
                )
                
                # 중복 체크
                cur.execute("SELECT measure_code FROM outcome_measure_dict WHERE measure_code = %s", (measure_code,))
                if cur.fetchone():
                    # 이미 존재하면 스킵 (또는 업데이트)
                    continue
                
                # 키워드 정리 (세미콜론으로 구분)
                keywords = outcome['keywords'].replace(' ', ';')
                
                # abbreviation 길이 제한 (VARCHAR(100))
                abbrev = None
                if outcome['abbreviation']:
                    abbrev = outcome['abbreviation'].strip('()')[:100]
                
                cur.execute("""
                    INSERT INTO outcome_measure_dict 
                    (measure_code, canonical_name, abbreviation, keywords, domain, unit_type, score_direction)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (measure_code) DO NOTHING
                """, (
                    measure_code,
                    outcome['measure_clean'],
                    abbrev,
                    keywords[:500] if keywords else None,  # TEXT 제한 고려
                    None,  # domain은 추후 수동 설정
                    None,  # unit_type은 추후 수동 설정
                    None   # score_direction은 추후 수동 설정
                ))
                inserted_count += 1
                
                if inserted_count % 100 == 0:
                    print(f"  진행: {inserted_count:,}개 삽입 완료")
            
            conn.commit()
            print(f"\n[OK] 총 {inserted_count:,}개 항목 Dictionary에 추가 완료")
        
        # 통계 출력
        print("\n" + "=" * 80)
        print("Dictionary 통계")
        print("=" * 80)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) as total FROM outcome_measure_dict")
            total = cur.fetchone()['total']
            print(f"총 Dictionary 항목 수: {total:,}개")
        
        conn.close()
        
        print("\n" + "=" * 80)
        print("[OK] Dictionary 생성 완료!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

