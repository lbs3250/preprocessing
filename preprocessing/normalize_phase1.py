"""
Outcome 데이터 정규화 스크립트 (Phase 1)

outcome_raw 테이블의 데이터를 읽어서 정규화하여 outcome_normalized 테이블에 삽입합니다.

주요 기능:
1. Measure Code 추출 및 매칭 (약어, 키워드, canonical_name 등)
2. Time Frame 파싱 및 정규화
3. Phase 정보 복사
4. Failure Reason 설정

사용법:
    python preprocessing/normalize_phase1.py
"""

import os
import re
import json
from typing import Dict, List, Optional, Tuple
from psycopg2.extras import RealDictCursor, execute_batch
from dotenv import load_dotenv
import psycopg2

# 같은 디렉토리의 모듈 import (직접 실행 시)
try:
    from normalization_patterns import (
        timeframe_patterns,
        measure_patterns,
        description_patterns
    )
except ImportError:
    # 모듈로 실행 시 (python -m preprocessing.normalize_phase1)
    from preprocessing.normalization_patterns import (
        timeframe_patterns,
        measure_patterns,
        description_patterns
    )

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'clinicaltrials'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

BATCH_SIZE = 1000


def get_db_connection():
    """PostgreSQL 연결 생성"""
    return psycopg2.connect(**DB_CONFIG)


def clean_text(text: str) -> str:
    """텍스트 클리닝 (공백 정리, 특수문자 처리)"""
    if not text:
        return ''
    # 연속된 공백을 하나로
    text = re.sub(r'\s+', ' ', text.strip())
    return text


def normalize_for_matching(text: str) -> str:
    """매칭용 텍스트 정규화 (소문자, 공백/하이픈/언더스코어 제거)"""
    if not text:
        return ''
    text = text.lower()
    # 공백, 하이픈, 언더스코어 제거
    text = re.sub(r'[\s\-_]', '', text)
    return text


def normalize_unit(unit: str) -> str:
    """단위 정규화"""
    if not unit:
        return ''
    
    unit_lower = unit.lower().strip()
    
    # 단위 매핑
    unit_map = {
        'wk': 'week',
        'w': 'week',
        'wks': 'weeks',
        'hr': 'hour',
        'hrs': 'hours',
        'min': 'minute',
        'mins': 'minutes',
        'mo': 'month',
        'mos': 'months',
        'yr': 'year',
        'yrs': 'years',
        'd': 'day',
        'ds': 'days'
    }
    
    # 복수형 처리
    if unit_lower.endswith('s') and unit_lower[:-1] in unit_map:
        return unit_map[unit_lower[:-1]] + 's'
    
    return unit_map.get(unit_lower, unit_lower)


def parse_timeframe(time_frame_raw: str) -> Dict:
    """
    Time Frame 파싱
    
    Returns:
        {
            'time_value_main': numeric or None,
            'time_unit_main': str or None,
            'time_points': list or None,
            'change_from_baseline_flag': bool,
            'pattern_code': str or None
        }
    """
    if not time_frame_raw:
        return {
            'time_value_main': None,
            'time_unit_main': None,
            'time_points': None,
            'change_from_baseline_flag': False,
            'pattern_code': None
        }
    
    time_frame = time_frame_raw.strip()
    result = {
        'time_value_main': None,
        'time_unit_main': None,
        'time_points': None,
        'change_from_baseline_flag': False,
        'pattern_code': None
    }
    
    # Baseline 체크
    if timeframe_patterns.baseline.search(time_frame):
        result['change_from_baseline_flag'] = True
        # baseline만 있고 숫자가 없으면 0 day로 처리
        if not re.search(r'\d+', time_frame):
            result['time_value_main'] = 0
            result['time_unit_main'] = 'day'
            result['pattern_code'] = timeframe_patterns.get_pattern_code(time_frame)
            return result
    
    # 패턴 코드 추출
    result['pattern_code'] = timeframe_patterns.get_pattern_code(time_frame)
    
    # 복수 시점 패턴 체크
    multiple_match = timeframe_patterns.multiple_timepoints.search(time_frame)
    if multiple_match:
        # 복수 시점 파싱
        time_points = []
        values = []
        
        # "Week 1, Week 14" 같은 패턴에서 숫자 추출
        numbers = re.findall(r'(?:week|weeks|day|days|month|months)\s+(\d+)', time_frame, re.IGNORECASE)
        units = re.findall(r'(week|weeks|day|days|month|months)', time_frame, re.IGNORECASE)
        
        if numbers and units:
            unit = normalize_unit(units[0])
            for num_str in numbers:
                num = int(num_str)
                values.append(num)
                time_points.append({'value': num, 'unit': unit})
            
            if values:
                # 최대값 사용
                result['time_value_main'] = max(values)
                result['time_unit_main'] = unit
                result['time_points'] = json.dumps(time_points)
        
        return result
    
    # 단일 시점 패턴들
    # "At Day/Week/Month N"
    at_day_match = timeframe_patterns.at_day.search(time_frame)
    at_week_match = timeframe_patterns.at_week.search(time_frame)
    at_month_match = timeframe_patterns.at_month.search(time_frame)
    
    if at_day_match or at_week_match or at_month_match:
        match = at_day_match or at_week_match or at_month_match
        unit_text = match.group(1).lower()
        number_match = re.search(r'\d+', match.group(0))
        if number_match:
            result['time_value_main'] = int(number_match.group())
            result['time_unit_main'] = normalize_unit(unit_text)
        return result
    
    # "Day N", "Week N", "Month N" 단독 패턴
    day_match = timeframe_patterns.day_standalone.search(time_frame)
    week_match = timeframe_patterns.week_standalone.search(time_frame)
    month_match = timeframe_patterns.month_standalone.search(time_frame)
    
    if day_match or week_match or month_match:
        match = day_match or week_match or month_match
        unit_text = match.group(1).lower()
        number_match = re.search(r'\d+', match.group(0))
        if number_match:
            result['time_value_main'] = int(number_match.group())
            result['time_unit_main'] = normalize_unit(unit_text)
        return result
    
    # "Day N to Day M", "Day N through M" 패턴
    day_to_match = timeframe_patterns.day_to.search(time_frame)
    day_through_match = timeframe_patterns.day_through.search(time_frame)
    
    if day_to_match or day_through_match:
        # 범위에서 최대값 추출
        numbers = re.findall(r'\d+', (day_to_match or day_through_match).group(0))
        if numbers:
            result['time_value_main'] = max(int(n) for n in numbers)
            result['time_unit_main'] = 'day'
        return result
    
    # "For N Months/Weeks/Days" 패턴
    for_period_match = timeframe_patterns.for_period.search(time_frame)
    if for_period_match:
        number_match = re.search(r'\d+', for_period_match.group(0))
        unit_text = for_period_match.group(1).lower()
        if number_match:
            result['time_value_main'] = int(number_match.group())
            result['time_unit_main'] = normalize_unit(unit_text)
        return result
    
    # 숫자+단위 패턴 (하이픈 포함)
    period_match = timeframe_patterns.period.search(time_frame)
    if period_match:
        number_match = re.search(r'\d+', period_match.group(0))
        unit_text = period_match.group(1).lower()
        if number_match:
            result['time_value_main'] = int(number_match.group())
            result['time_unit_main'] = normalize_unit(unit_text)
        return result
    
    # 텍스트 숫자 패턴 (모든 숫자 커버 - word2number 라이브러리 사용)
    text_number_match = timeframe_patterns.text_number.search(time_frame)
    if text_number_match:
        text_num_str = text_number_match.group(1).lower().strip()
        unit_text = text_number_match.group(2).lower()
        
        # word2number 라이브러리 사용 (모든 숫자 지원: "twenty-one", "one hundred", "ninety-nine" 등)
        try:
            from word2number import w2n
            result['time_value_main'] = w2n.word_to_num(text_num_str)
            result['time_unit_main'] = normalize_unit(unit_text)
        except (ImportError, ValueError, AttributeError):
            # word2number가 없거나 변환 실패 시 기본 딕셔너리 사용 (하위 호환성)
            text_to_number = {
                'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
                'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
                'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
                'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
                'nineteen': 19, 'twenty': 20, 'thirty': 30, 'forty': 40,
                'fifty': 50, 'sixty': 60, 'seventy': 70, 'eighty': 80,
                'ninety': 90, 'hundred': 100
            }
            # 복합 숫자 처리 (예: "twenty-one", "thirty-five")
            if '-' in text_num_str or ' ' in text_num_str:
                # 하이픈이나 공백으로 구분된 복합 숫자
                parts = re.split(r'[- ]+', text_num_str)
                if len(parts) == 2:
                    base = text_to_number.get(parts[0], 0)
                    remainder = text_to_number.get(parts[1], 0)
                    if base > 0 and remainder > 0:
                        result['time_value_main'] = base + remainder
                        result['time_unit_main'] = normalize_unit(unit_text)
                        return result
            elif text_num_str in text_to_number:
                result['time_value_main'] = text_to_number[text_num_str]
                result['time_unit_main'] = normalize_unit(unit_text)
        return result
    
    return result


def extract_measure_abbreviation(measure_raw: str) -> Optional[str]:
    """
    Measure에서 약어 추출 (괄호 전후 모두 확인)
    
    Returns:
        약어 문자열 (예: "(ADAS-Cog)") 또는 None
    """
    if not measure_raw:
        return None
    
    # 약어 초기화 (매우 중요! 괄호가 없을 때 None을 확실히 반환하기 위해)
    abbrev_candidates = []
    
    # 괄호 안 약어 추출
    abbrev_matches = measure_patterns.abbreviation.findall(measure_raw)
    for abbrev_text in abbrev_matches:
        # 괄호 제거
        abbrev_clean = abbrev_text.strip('()')
        if measure_patterns.is_valid_abbreviation(abbrev_clean):
            abbrev_candidates.append(abbrev_text)
    
    # 괄호 전 텍스트에서 마지막 단어 추출
    before_paren_match = re.search(r'([A-Za-z0-9\-+\s/]+)\s*\(', measure_raw)
    if before_paren_match:
        before_text_full = before_paren_match.group(1).strip()
        before_words = before_text_full.split()
        before_text = before_words[-1] if before_words else None
        
        # 괄호 전 마지막 단어가 약어인지 확인
        if before_text and measure_patterns.is_valid_abbreviation(before_text):
            abbrev_candidates.append(f"({before_text})")
    
    # 약어가 있으면 첫 번째 반환, 없으면 명시적으로 None 반환
    if abbrev_candidates:
        return abbrev_candidates[0]
    else:
        return None


def match_measure_code(measure_clean: str, measure_abbreviation: Optional[str], 
                      description_raw: Optional[str], conn) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Measure Code 매칭
    
    Returns:
        (measure_code, match_type, match_keyword)
    """
    if not measure_clean and not measure_abbreviation:
        return None, None, None
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 0순위: measure_code 직접 매칭
        if measure_clean:
            measure_norm = normalize_for_matching(measure_clean)
            cur.execute("""
                SELECT measure_code 
                FROM outcome_measure_dict 
                WHERE LOWER(measure_code) = %s
            """, (measure_norm,))
            row = cur.fetchone()
            if row:
                return row['measure_code'], 'MEASURE_CODE', measure_clean
        
        # 1순위: abbreviation 매칭
        if measure_abbreviation:
            abbrev_clean = measure_abbreviation.strip('()')
            abbrev_norm = normalize_for_matching(abbrev_clean)
            
            # abbreviation 필드 매칭
            cur.execute("""
                SELECT measure_code 
                FROM outcome_measure_dict 
                WHERE LOWER(abbreviation) = %s
            """, (abbrev_norm,))
            row = cur.fetchone()
            if row:
                return row['measure_code'], 'ABBREVIATION', measure_abbreviation
            
            # keywords에서 약어 검색
            cur.execute("""
                SELECT measure_code, keywords 
                FROM outcome_measure_dict 
                WHERE keywords IS NOT NULL
            """)
            for row in cur.fetchall():
                if row['keywords']:
                    keywords = [k.strip().lower() for k in row['keywords'].split(';')]
                    if abbrev_norm in [normalize_for_matching(k) for k in keywords]:
                        return row['measure_code'], 'ABBREVIATION', measure_abbreviation
        
        # 2순위: canonical_name 매칭 (완전 일치 + 부분 포함)
        if measure_clean:
            measure_norm = normalize_for_matching(measure_clean)
            cur.execute("""
                SELECT measure_code, canonical_name 
                FROM outcome_measure_dict 
                WHERE LENGTH(canonical_name) >= 5
            """)
            for row in cur.fetchall():
                canonical_norm = normalize_for_matching(row['canonical_name'])
                # 완전 일치
                if canonical_norm == measure_norm:
                    return row['measure_code'], 'CANONICAL_NAME', row['canonical_name']
                # 부분 포함 (최소 5자 이상)
                if len(canonical_norm) >= 5 and canonical_norm in measure_norm:
                    return row['measure_code'], 'CANONICAL_NAME', row['canonical_name']
        
        # 3순위: keywords 매칭 (완전 일치 + 부분 포함)
        if measure_clean:
            cur.execute("""
                SELECT measure_code, keywords 
                FROM outcome_measure_dict 
                WHERE keywords IS NOT NULL
            """)
            for row in cur.fetchall():
                if row['keywords']:
                    keywords = [k.strip() for k in row['keywords'].split(';')]
                    for keyword in keywords:
                        if len(keyword) >= 3:
                            # 단어 경계 고려하여 매칭
                            keyword_pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                            if re.search(keyword_pattern, measure_clean.lower()):
                                return row['measure_code'], 'KEYWORD', keyword
        
        # 4순위: description_raw에서 매칭 시도
        if description_raw:
            desc_norm = normalize_for_matching(description_raw)
            
            # measure_code 직접 매칭
            cur.execute("""
                SELECT measure_code 
                FROM outcome_measure_dict 
                WHERE LOWER(measure_code) = %s
            """, (desc_norm[:50],))  # 처음 50자만 확인
            row = cur.fetchone()
            if row:
                return row['measure_code'], 'MEASURE_CODE', description_raw[:50]
            
            # canonical_name 부분 매칭
            cur.execute("""
                SELECT measure_code, canonical_name 
                FROM outcome_measure_dict 
                WHERE LENGTH(canonical_name) >= 5
            """)
            for row in cur.fetchall():
                canonical_norm = normalize_for_matching(row['canonical_name'])
                if len(canonical_norm) >= 5 and canonical_norm in desc_norm:
                    return row['measure_code'], 'CANONICAL_NAME', row['canonical_name']
            
            # keywords 매칭
            cur.execute("""
                SELECT measure_code, keywords 
                FROM outcome_measure_dict 
                WHERE keywords IS NOT NULL
            """)
            for row in cur.fetchall():
                if row['keywords']:
                    keywords = [k.strip() for k in row['keywords'].split(';')]
                    for keyword in keywords:
                        if len(keyword) >= 3:
                            keyword_pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                            if re.search(keyword_pattern, description_raw.lower()):
                                return row['measure_code'], 'KEYWORD', keyword
    
    return None, None, None


def normalize_outcome(row: Dict, conn) -> Dict:
    """
    단일 Outcome 정규화
    
    Args:
        row: outcome_raw 테이블의 행 데이터
        conn: 데이터베이스 연결
    
    Returns:
        정규화된 outcome 딕셔너리
    """
    # Measure 정규화
    measure_raw = row.get('measure_raw', '') or ''
    measure_clean = clean_text(measure_raw)
    
    # 약어 초기화 (매우 중요! 각 row 처리 시작 시 명시적으로 None으로 초기화)
    # 괄호가 없거나 약어를 찾을 수 없으면 반드시 None이어야 함
    # 이전 row의 값이 남아있지 않도록 항상 새로 추출
    measure_abbreviation = None
    if measure_raw:
        measure_abbreviation = extract_measure_abbreviation(measure_raw)
    # measure_raw가 비어있으면 이미 None이므로 추가 처리 불필요
    
    # Measure Code 매칭
    description_raw = row.get('description_raw', '') or ''
    measure_code, match_type, match_keyword = match_measure_code(
        measure_clean, measure_abbreviation, description_raw, conn
    )
    
    # Domain 추출 (measure_code가 있으면)
    domain = None
    if measure_code:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT domain 
                FROM outcome_measure_dict 
                WHERE measure_code = %s
            """, (measure_code,))
            domain_row = cur.fetchone()
            if domain_row:
                domain = domain_row['domain']
    
    # Time Frame 정규화
    time_frame_raw = row.get('time_frame_raw', '') or ''
    timeframe_result = parse_timeframe(time_frame_raw)
    
    # Change from baseline 체크
    change_from_baseline_flag = timeframe_result['change_from_baseline_flag']
    if description_raw and description_patterns.has_change_from_baseline(description_raw):
        change_from_baseline_flag = True
    
    # Failure Reason 설정
    failure_reason = None
    if not measure_code and (not timeframe_result['time_value_main'] or not timeframe_result['time_unit_main']):
        failure_reason = 'BOTH_FAILED'
    elif not measure_code:
        failure_reason = 'MEASURE_FAILED'
    elif not timeframe_result['time_value_main'] or not timeframe_result['time_unit_main']:
        failure_reason = 'TIMEFRAME_FAILED'
    
    # Phase 정보 복사
    phase = row.get('phase') or 'NA'
    
    return {
        'nct_id': row['nct_id'],
        'outcome_type': row['outcome_type'],
        'outcome_order': row['outcome_order'],
        'measure_raw': measure_raw,
        'measure_clean': measure_clean,
        'measure_abbreviation': measure_abbreviation,
        'measure_norm': (normalize_for_matching(measure_clean)[:200] if measure_clean else None),
        'measure_code': measure_code[:50] if measure_code else None,  # VARCHAR(50) 제한
        'match_type': match_type[:20] if match_type else None,  # VARCHAR(20) 제한
        'match_keyword': match_keyword,  # TEXT이므로 제한 없음
        'domain': domain[:100] if domain else None,  # VARCHAR(100) 제한
        'time_frame_raw': time_frame_raw,
        'time_value_main': timeframe_result['time_value_main'],
        'time_unit_main': (timeframe_result['time_unit_main'][:20] if timeframe_result['time_unit_main'] else None),  # VARCHAR(20) 제한
        'time_points': timeframe_result['time_points'],
        'time_phase': None,
        'phase': phase[:50] if phase else 'NA',  # VARCHAR(50) 제한
        'change_from_baseline_flag': change_from_baseline_flag,
        'description_raw': description_raw,
        'description_norm': clean_text(description_raw) if description_raw else None,
        'failure_reason': failure_reason[:50] if failure_reason else None,  # VARCHAR(50) 제한
        'parsing_method': 'RULE_BASED',
        'num_arms': None,
        'pattern_code': (timeframe_result['pattern_code'][:20] if timeframe_result['pattern_code'] else None)  # VARCHAR(20) 제한
    }


def normalize_batch(conn, batch: List[Dict]) -> List[Dict]:
    """배치 정규화"""
    normalized = []
    for row in batch:
        try:
            normalized_row = normalize_outcome(row, conn)
            normalized.append(normalized_row)
        except Exception as e:
            print(f"  [ERROR] outcome_id {row.get('id')}: {e}")
            import traceback
            traceback.print_exc()
    return normalized


def insert_normalized(conn, normalized_data: List[Dict]):
    """정규화된 데이터 삽입"""
    if not normalized_data:
        return
    
    # 먼저 기존 데이터 삭제 (중복 방지)
    with conn.cursor() as cur:
        for row in normalized_data:
            cur.execute("""
                DELETE FROM outcome_normalized 
                WHERE nct_id = %(nct_id)s 
                  AND outcome_type = %(outcome_type)s 
                  AND outcome_order = %(outcome_order)s
            """, {
                'nct_id': row['nct_id'],
                'outcome_type': row['outcome_type'],
                'outcome_order': row['outcome_order']
            })
    
    # 새 데이터 삽입
    insert_sql = """
        INSERT INTO outcome_normalized (
            nct_id, outcome_type, outcome_order,
            measure_raw, measure_clean, measure_abbreviation, measure_norm,
            measure_code, match_type, match_keyword, domain,
            time_frame_raw, time_value_main, time_unit_main, time_points, time_phase,
            phase, change_from_baseline_flag,
            description_raw, description_norm,
            failure_reason, parsing_method, num_arms, pattern_code
        ) VALUES (
            %(nct_id)s, %(outcome_type)s, %(outcome_order)s,
            %(measure_raw)s, %(measure_clean)s, %(measure_abbreviation)s, %(measure_norm)s,
            %(measure_code)s, %(match_type)s, %(match_keyword)s, %(domain)s,
            %(time_frame_raw)s, %(time_value_main)s, %(time_unit_main)s, %(time_points)s, %(time_phase)s,
            %(phase)s, %(change_from_baseline_flag)s,
            %(description_raw)s, %(description_norm)s,
            %(failure_reason)s, %(parsing_method)s, %(num_arms)s, %(pattern_code)s
        )
    """
    
    with conn.cursor() as cur:
        execute_batch(cur, insert_sql, normalized_data)
    conn.commit()


def main():
    """메인 함수"""
    print("=" * 80)
    print("[START] Outcome 정규화 시작")
    print("=" * 80)
    
    conn = get_db_connection()
    
    try:
        # 전체 데이터 개수 확인
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) as count FROM outcome_raw")
            total_count = cur.fetchone()['count']
            print(f"\n전체 데이터: {total_count:,}건")
        
        if total_count == 0:
            print("\n[ERROR] outcome_raw 테이블에 데이터가 없습니다!")
            return
        
        # 배치 처리
        processed = 0
        batch = []
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, nct_id, outcome_type, outcome_order,
                       measure_raw, description_raw, time_frame_raw, phase
                FROM outcome_raw
                ORDER BY nct_id, outcome_type, outcome_order
            """)
            
            for row in cur:
                batch.append(dict(row))
                
                if len(batch) >= BATCH_SIZE:
                    normalized_batch = normalize_batch(conn, batch)
                    insert_normalized(conn, normalized_batch)
                    processed += len(batch)
                    print(f"  처리 중: {processed:,}/{total_count:,}건 ({processed/total_count*100:.1f}%)")
                    batch = []
            
            # 마지막 배치 처리
            if batch:
                normalized_batch = normalize_batch(conn, batch)
                insert_normalized(conn, normalized_batch)
                processed += len(batch)
        
        print(f"\n[OK] 정규화 완료: {processed:,}건")
        
        # 통계 출력
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 1 END) as success,
                    COUNT(CASE WHEN failure_reason = 'MEASURE_FAILED' THEN 1 END) as measure_failed,
                    COUNT(CASE WHEN failure_reason = 'TIMEFRAME_FAILED' THEN 1 END) as timeframe_failed,
                    COUNT(CASE WHEN failure_reason = 'BOTH_FAILED' THEN 1 END) as both_failed
                FROM outcome_normalized
            """)
            stats = cur.fetchone()
            
            print("\n" + "=" * 80)
            print("[STATISTICS] 정규화 결과 통계")
            print("=" * 80)
            print(f"전체: {stats['total']:,}건")
            print(f"성공: {stats['success']:,}건 ({stats['success']/stats['total']*100:.1f}%)")
            print(f"Measure 실패: {stats['measure_failed']:,}건 ({stats['measure_failed']/stats['total']*100:.1f}%)")
            print(f"TimeFrame 실패: {stats['timeframe_failed']:,}건 ({stats['timeframe_failed']/stats['total']*100:.1f}%)")
            print(f"둘 다 실패: {stats['both_failed']:,}건 ({stats['both_failed']/stats['total']*100:.1f}%)")
            print("=" * 80)
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    main()

