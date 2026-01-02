"""
Time Frame 파싱 결과 검증 스크립트

time_frame_raw와 파싱 결과(time_value_main, time_unit_main, time_points)를 비교하여
잘못 파싱된 케이스들을 찾아냅니다.
"""

import os
import json
import re
from typing import Dict, List, Optional
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


def extract_number_unit_pairs(text: str) -> List[Dict]:
    """텍스트에서 숫자-단위 쌍 추출"""
    if not text:
        return []
    
    pairs = []
    
    # 패턴 1: "숫자 단위" (예: "48 hours", "37 weeks")
    pattern1 = r'(\d+\.?\d*)\s+(week|weeks|day|days|month|months|year|years|hour|hours|hr|hrs|min|mins|minute|minutes)\b'
    matches1 = re.finditer(pattern1, text, re.IGNORECASE)
    for match in matches1:
        pairs.append({
            'value': float(match.group(1)),
            'unit': normalize_unit(match.group(2)),
            'text': match.group(0)
        })
    
    # 패턴 2: "단위 숫자" (예: "Week 48", "Day 1")
    pattern2 = r'\b(week|weeks|day|days|month|months|year|years|hour|hours|hr|hrs|min|mins|minute|minutes)\s+(\d+\.?\d*)'
    matches2 = re.finditer(pattern2, text, re.IGNORECASE)
    for match in matches2:
        pairs.append({
            'value': float(match.group(2)),
            'unit': normalize_unit(match.group(1)),
            'text': match.group(0)
        })
    
    return pairs


def find_max_value_unit_pair(text: str) -> Optional[Dict]:
    """텍스트에서 가장 큰 숫자와 그 단위 찾기"""
    pairs = extract_number_unit_pairs(text)
    if not pairs:
        return None
    
    # 같은 단위끼리 그룹화
    unit_groups = {}
    for pair in pairs:
        unit = pair['unit']
        if unit not in unit_groups:
            unit_groups[unit] = []
        unit_groups[unit].append(pair['value'])
    
    # 각 단위별 최대값 찾기
    max_pairs = []
    for unit, values in unit_groups.items():
        max_pairs.append({
            'value': max(values),
            'unit': unit
        })
    
    # 모든 단위 중 가장 큰 값 찾기
    if max_pairs:
        return max(max_pairs, key=lambda x: x['value'])
    return None


def normalize_unit(unit: str) -> str:
    """단위 정규화"""
    if not unit:
        return unit
    unit_lower = unit.lower().strip()
    unit_map = {
        'weeks': 'week',
        'days': 'day',
        'months': 'month',
        'years': 'year',
        'hours': 'hour',
        'hrs': 'hour',
        'hr': 'hour',
        'mins': 'min',
        'minutes': 'min'
    }
    return unit_map.get(unit_lower, unit_lower)


def parse_time_points_json(time_points_json: str) -> List[Dict]:
    """time_points JSON 문자열 파싱"""
    if not time_points_json:
        return []
    try:
        return json.loads(time_points_json)
    except:
        return []


def to_float(value):
    """값을 float로 변환 (Decimal, int, float 모두 처리)"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    # Decimal 타입 처리
    return float(str(value))


def validate_parsing(row: Dict) -> Dict:
    """파싱 결과 검증"""
    time_frame_raw = row.get('time_frame_raw', '')
    time_value_main = row.get('time_value_main')
    time_unit_main = row.get('time_unit_main')
    time_points_json = row.get('time_points')
    
    # Baseline은 건너뛰기
    if 'baseline' in time_frame_raw.lower():
        return {
            'has_issues': False,
            'issues': [],
            'skipped': True,
            'reason': 'Baseline 포함'
        }
    
    issues = []
    
    # 1. 원본에서 가장 큰 숫자-단위 쌍 찾기
    expected_pair = find_max_value_unit_pair(time_frame_raw)
    
    # 2. time_points 파싱
    time_points = parse_time_points_json(time_points_json) if time_points_json else []
    time_points_values = [to_float(tp.get('value', 0)) for tp in time_points if tp.get('value') is not None]
    time_points_units = [normalize_unit(tp.get('unit', '')) for tp in time_points if tp.get('unit')]
    
    # 3. 검증 항목들
    
    if expected_pair:
        expected_value = expected_pair['value']
        expected_unit = expected_pair['unit']
        
        # 3-1. time_value_main이 원본의 최대값과 일치하는지
        if time_value_main is not None:
            time_value_float = to_float(time_value_main)
            expected_value_float = to_float(expected_value)
            if abs(time_value_float - expected_value_float) > 0.01:  # 부동소수점 오차 고려
                issues.append(f"❌ 값 불일치: 파싱={time_value_main}, 원본 최대값={expected_value}")
        
        # 3-2. time_unit_main이 원본의 단위와 일치하는지
        if time_unit_main:
            normalized_main_unit = normalize_unit(time_unit_main)
            if normalized_main_unit != expected_unit:
                issues.append(f"❌ 단위 불일치: 파싱={time_unit_main}, 원본 단위={expected_unit}")
        
        # 3-3. time_points의 최대값이 원본과 일치하는지
        if time_points_values:
            max_timepoint = max(time_points_values)
            expected_value_float = to_float(expected_value)
            if abs(max_timepoint - expected_value_float) > 0.01:
                issues.append(f"❌ time_points 최대값 불일치: {max_timepoint} vs 원본 {expected_value}")
        
        # 3-4. time_points의 최대값 단위가 원본과 일치하는지
        if time_points_units and time_points_values:
            max_idx = time_points_values.index(max(time_points_values))
            if max_idx < len(time_points_units):
                max_unit = normalize_unit(time_points_units[max_idx])
                if max_unit != expected_unit:
                    issues.append(f"❌ time_points 단위 불일치: {time_points_units[max_idx]} vs 원본 {expected_unit}")
    
    return {
        'has_issues': len(issues) > 0,
        'issues': issues,
        'expected_pair': expected_pair,
        'time_points_values': time_points_values,
        'time_points_units': time_points_units,
        'skipped': False
    }


def main():
    print("=" * 80)
    print("Time Frame 파싱 결과 검증")
    print("=" * 80)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        # 데이터 조회
        query = """
        SELECT DISTINCT ON (time_points)
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
        WHERE time_points IS NOT NULL
        ORDER BY time_points, nct_id, outcome_type, outcome_order
        """
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            rows = cur.fetchall()
            
            total_count = len(rows)
            print(f"\n총 {total_count:,}개의 고유한 time_points 레코드 발견")
            print(f"100줄씩 검증합니다...\n")
            
            issue_count = 0
            batch_size = 100
            
            for batch_start in range(0, total_count, batch_size):
                batch_end = min(batch_start + batch_size, total_count)
                batch = rows[batch_start:batch_end]
                
                print(f"\n{'='*80}")
                print(f"[{batch_start+1:,} ~ {batch_end:,} / {total_count:,}] 검증 중...")
                print(f"{'='*80}\n")
                
                for idx, row in enumerate(batch, start=batch_start+1):
                    validation = validate_parsing(row)
                    
                    if validation.get('skipped'):
                        continue  # Baseline은 건너뛰기
                    
                    if validation['has_issues']:
                        issue_count += 1
                        print(f"\n[#{idx}] ❌ 문제 발견")
                        print(f"  nct_id: {row['nct_id']}")
                        print(f"  outcome_type: {row['outcome_type']}")
                        print(f"  time_frame_raw: {row['time_frame_raw']}")
                        print(f"  파싱 결과:")
                        print(f"    - time_value_main: {row['time_value_main']}")
                        print(f"    - time_unit_main: {row['time_unit_main']}")
                        print(f"    - time_points: {row['time_points']}")
                        if validation['expected_pair']:
                            print(f"  원본에서 추출한 최대값:")
                            print(f"    - 값: {validation['expected_pair']['value']}")
                            print(f"    - 단위: {validation['expected_pair']['unit']}")
                        print(f"  time_points 값들: {validation['time_points_values']}")
                        print(f"  time_points 단위들: {validation['time_points_units']}")
                        print(f"  문제점:")
                        for issue in validation['issues']:
                            print(f"    {issue}")
                    else:
                        # 문제 없는 경우도 간단히 표시
                        if idx % 10 == 0:  # 10개마다 진행 상황 표시
                            print(f"  [{idx:,}] ✓ 정상")
                
                # 배치별 요약
                batch_issues = sum(1 for row in batch if validate_parsing(row)['has_issues'])
                print(f"\n[배치 요약] 문제 발견: {batch_issues}/{len(batch)}개")
                
                # 사용자 입력 대기 (다음 배치 확인)
                if batch_end < total_count:
                    input(f"\n다음 배치를 확인하려면 Enter를 누르세요... (Ctrl+C로 중단)")
        
        print(f"\n{'='*80}")
        print(f"검증 완료!")
        print(f"총 {total_count:,}개 중 문제 발견: {issue_count:,}개")
        print(f"{'='*80}")
        
        conn.close()
        
    except KeyboardInterrupt:
        print("\n\n검증이 중단되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

