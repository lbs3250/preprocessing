import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import os
import json

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'clinicaltrials'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

def get_db_connection():
    """PostgreSQL 연결 생성"""
    return psycopg2.connect(**DB_CONFIG)

conn = get_db_connection()
cur = conn.cursor(cursor_factory=RealDictCursor)

# 상위 50개 가져오기 (time_value_main 내림차순)
cur.execute("""
    SELECT 
        nct_id,
        outcome_type,
        outcome_order,
        time_frame_raw,
        time_value_main,
        time_unit_main,
        time_points,
        change_from_baseline_flag,
        measure_raw,
        measure_code,
        failure_reason
    FROM outcome_normalized 
    WHERE time_value_main IS NOT NULL
    ORDER BY time_value_main DESC
    LIMIT 50
""")

rows = cur.fetchall()

print("=" * 100)
print("상위 50개 레코드 분석 (time_value_main 내림차순)")
print("=" * 100)

issues = []

for idx, row in enumerate(rows, 1):
    print(f"\n[{idx}] NCT ID: {row['nct_id']}")
    print(f"    원본: {row['time_frame_raw']}")
    print(f"    파싱: {row['time_value_main']} {row['time_unit_main']}")
    print(f"    time_points: {json.dumps(row['time_points'], indent=6, ensure_ascii=False) if row['time_points'] else None}")
    
    # 단위 혼용 체크
    time_frame_raw = row['time_frame_raw'].lower()
    units_found = []
    
    if 'day' in time_frame_raw or 'days' in time_frame_raw:
        units_found.append('day')
    if 'week' in time_frame_raw or 'weeks' in time_frame_raw:
        units_found.append('week')
    if 'month' in time_frame_raw or 'months' in time_frame_raw:
        units_found.append('month')
    if 'hour' in time_frame_raw or 'hours' in time_frame_raw or 'hr' in time_frame_raw or 'hrs' in time_frame_raw:
        units_found.append('hour')
    if 'min' in time_frame_raw or 'minute' in time_frame_raw or 'mins' in time_frame_raw or 'minutes' in time_frame_raw:
        units_found.append('minute')
    if 'year' in time_frame_raw or 'years' in time_frame_raw:
        units_found.append('year')
    
    # 중복 제거
    units_found = list(set(units_found))
    
    if len(units_found) > 1:
        print(f"    [WARNING] 단위 혼용 발견: {', '.join(units_found)}")
        
        # 원본에서 각 단위별 최대값 추출
        import re
        max_values = {}
        for unit in units_found:
            if unit == 'day':
                pattern = r'\b(\d+(?:\.\d+)?)\s*(?:day|days)\b'
            elif unit == 'week':
                pattern = r'\b(\d+(?:\.\d+)?)\s*(?:week|weeks)\b'
            elif unit == 'month':
                pattern = r'\b(\d+(?:\.\d+)?)\s*(?:month|months)\b'
            elif unit == 'hour':
                pattern = r'\b(\d+(?:\.\d+)?)\s*(?:hour|hours|hr|hrs)\b'
            elif unit == 'minute':
                pattern = r'\b(\d+(?:\.\d+)?)\s*(?:min|mins|minute|minutes)\b'
            elif unit == 'year':
                pattern = r'\b(\d+(?:\.\d+)?)\s*(?:year|years)\b'
            
            matches = re.findall(pattern, time_frame_raw, re.IGNORECASE)
            if matches:
                max_values[unit] = max([float(m) for m in matches])
        
        print(f"    원본 최대값: {max_values}")
        
        # 파싱된 값과 비교
        parsed_unit = row['time_unit_main']
        parsed_value = row['time_value_main']
        
        if parsed_unit and parsed_unit in max_values:
            expected_max = max_values[parsed_unit]
            if abs(float(parsed_value) - expected_max) > 0.01:
                print(f"    [ERROR] 불일치: 파싱={parsed_value} {parsed_unit}, 예상 최대값={expected_max} {parsed_unit}")
                issues.append({
                    'row': row,
                    'issue': f'단위 혼용 및 값 불일치: 파싱={parsed_value} {parsed_unit}, 예상={expected_max} {parsed_unit}',
                    'units_found': units_found,
                    'max_values': max_values
                })
        elif parsed_unit not in units_found:
            print(f"    [ERROR] 단위 불일치: 파싱 단위={parsed_unit}, 원본 단위={units_found}")
            issues.append({
                'row': row,
                'issue': f'단위 불일치: 파싱 단위={parsed_unit}, 원본 단위={units_found}',
                'units_found': units_found,
                'max_values': max_values
            })
    
    print("-" * 100)

print(f"\n\n총 {len(issues)}개 문제 발견")
print("=" * 100)

conn.close()
