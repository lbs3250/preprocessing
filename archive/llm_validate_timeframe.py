"""
LLM 기반 Time Frame 파싱 검증 및 정규식 수정 스크립트

100개씩 데이터를 가져와서 검증하고, 문제가 있는 패턴을 찾아 정규식 수정 제안을 생성합니다.
"""

import os
import sys
import json
import re
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'clinicaltrials'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}


def get_batch_data(conn, batch_size=100, offset=0):
    """데이터를 배치로 가져오기"""
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
    LIMIT %s OFFSET %s
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, (batch_size, offset))
        return cur.fetchall()


def analyze_parsing_issue(time_frame_raw: str, time_value_main, time_unit_main, time_points_json: str) -> Dict:
    """
    LLM 기반 파싱 문제 분석
    
    time_frame_raw를 분석하여 올바른 파싱 결과를 예측하고,
    실제 파싱 결과와 비교하여 문제점을 찾습니다.
    """
    # time_points 파싱
    time_points = []
    if time_points_json:
        try:
            time_points = json.loads(time_points_json) if isinstance(time_points_json, str) else time_points_json
        except:
            pass
    
    # 원본 텍스트 분석
    analysis = {
        'time_frame_raw': time_frame_raw,
        'parsed_value': time_value_main,
        'parsed_unit': time_unit_main,
        'parsed_time_points': time_points,
        'issues': [],
        'expected_value': None,
        'expected_unit': None,
        'expected_time_points': []
    }
    
    # Baseline 제외
    if 'baseline' in time_frame_raw.lower():
        return {**analysis, 'skipped': True, 'reason': 'Baseline 포함'}
    
    # 원본에서 숫자-단위 쌍 추출
    # 패턴 1: "weeks N, M, O and P" 형태
    weeks_pattern = re.search(
        r'\b(week|weeks|day|days|month|months|year|years|hour|hours|hr|hrs|min|mins|minute|minutes)\s+(\d+(?:\.\d+)?)(?:\s*,\s*(\d+(?:\.\d+)?))*(?:\s+and\s+(\d+(?:\.\d+)?))?',
        time_frame_raw.lower(),
        re.IGNORECASE
    )
    
    if weeks_pattern:
        unit = weeks_pattern.group(1)
        # 매칭된 부분에서 모든 숫자 추출
        matched_text = weeks_pattern.group(0)
        numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', matched_text)
        if numbers:
            numbers_float = [float(n) for n in numbers]
            analysis['expected_time_points'] = [{'value': int(n) if n.is_integer() else n, 'unit': unit.rstrip('s')} for n in numbers_float]
            analysis['expected_value'] = max(numbers_float)
            analysis['expected_unit'] = unit.rstrip('s')
    
    # 패턴 2: "N weeks", "N days" 등 (숫자 + 단위)
    if not analysis['expected_value']:
        number_unit_patterns = re.finditer(
            r'\b(\d+(?:\.\d+)?)\s+(week|weeks|day|days|month|months|year|years|hour|hours|hr|hrs|min|mins|minute|minutes)\b',
            time_frame_raw.lower(),
            re.IGNORECASE
        )
        values_units = []
        for match in number_unit_patterns:
            num = float(match.group(1))
            unit = match.group(2).rstrip('s')
            values_units.append((num, unit))
        
        if values_units:
            # 가장 큰 값 찾기
            max_pair = max(values_units, key=lambda x: x[0])
            analysis['expected_value'] = max_pair[0]
            analysis['expected_unit'] = max_pair[1]
            analysis['expected_time_points'] = [{'value': int(v) if v.is_integer() else v, 'unit': u} for v, u in values_units]
    
    # 패턴 3: "Week N", "Day N" 등 (단위 + 숫자)
    if not analysis['expected_value']:
        unit_number_patterns = re.finditer(
            r'\b(week|weeks|day|days|month|months|year|years|hour|hours|hr|hrs|min|mins|minute|minutes)\s+(\d+(?:\.\d+)?)',
            time_frame_raw.lower(),
            re.IGNORECASE
        )
        values_units = []
        for match in unit_number_patterns:
            unit = match.group(1).rstrip('s')
            num = float(match.group(2))
            values_units.append((num, unit))
        
        if values_units:
            max_pair = max(values_units, key=lambda x: x[0])
            analysis['expected_value'] = max_pair[0]
            analysis['expected_unit'] = max_pair[1]
            analysis['expected_time_points'] = [{'value': int(v) if v.is_integer() else v, 'unit': u} for v, u in values_units]
    
    # 문제점 검증
    if analysis['expected_value']:
        # 값 비교
        if time_value_main is not None:
            if abs(float(time_value_main) - float(analysis['expected_value'])) > 0.01:
                analysis['issues'].append(f"값 불일치: 파싱={time_value_main}, 예상={analysis['expected_value']}")
        
        # 단위 비교
        if time_unit_main and analysis['expected_unit']:
            if time_unit_main.lower().rstrip('s') != analysis['expected_unit'].lower():
                analysis['issues'].append(f"단위 불일치: 파싱={time_unit_main}, 예상={analysis['expected_unit']}")
        
        # time_points 비교
        if analysis['expected_time_points']:
            expected_values = sorted([tp['value'] for tp in analysis['expected_time_points']])
            parsed_values = sorted([float(tp.get('value', 0)) for tp in time_points if tp.get('value') is not None])
            
            if expected_values != parsed_values:
                analysis['issues'].append(f"time_points 불일치: 파싱={parsed_values}, 예상={expected_values}")
    
    analysis['has_issues'] = len(analysis['issues']) > 0
    return analysis


def format_analysis_for_llm(analyses: List[Dict]) -> str:
    """LLM이 읽을 수 있도록 분석 결과 포맷팅"""
    output = []
    output.append("=" * 80)
    output.append("Time Frame 파싱 검증 결과 (LLM 분석용)")
    output.append("=" * 80)
    output.append("")
    
    issue_count = 0
    for idx, analysis in enumerate(analyses, 1):
        if analysis.get('skipped'):
            continue
        
        if analysis['has_issues']:
            issue_count += 1
            output.append(f"[#{idx}] [문제 발견]")
            output.append(f"  time_frame_raw: \"{analysis['time_frame_raw']}\"")
            output.append(f"  파싱 결과:")
            output.append(f"    - time_value_main: {analysis['parsed_value']}")
            output.append(f"    - time_unit_main: {analysis['parsed_unit']}")
            output.append(f"    - time_points: {json.dumps(analysis['parsed_time_points'], indent=6)}")
            output.append(f"  예상 결과:")
            output.append(f"    - expected_value: {analysis['expected_value']}")
            output.append(f"    - expected_unit: {analysis['expected_unit']}")
            output.append(f"    - expected_time_points: {json.dumps(analysis['expected_time_points'], indent=6)}")
            output.append(f"  문제점:")
            for issue in analysis['issues']:
                output.append(f"    - {issue}")
            output.append("")
    
    output.append(f"\n총 {len(analyses)}개 중 {issue_count}개 문제 발견")
    return "\n".join(output)


def main():
    print("=" * 80)
    print("LLM 기반 Time Frame 파싱 검증")
    print("=" * 80)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        # 전체 개수 확인
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(DISTINCT time_points) 
                FROM outcome_normalized 
                WHERE time_points IS NOT NULL
            """)
            total_count = cur.fetchone()[0]
        
        print(f"\n총 {total_count:,}개의 고유한 time_points 레코드")
        print(f"100개씩 배치로 자동 검증합니다...\n")
        
        batch_size = 100
        total_issues = []
        pattern_groups = {}  # 패턴별로 그룹화
        
        for offset in range(0, total_count, batch_size):
            batch_end = min(offset + batch_size, total_count)
            batch_num = offset//batch_size + 1
            total_batches = (total_count + batch_size - 1) // batch_size
            
            print(f"\n{'='*80}")
            print(f"[배치 {batch_num}/{total_batches}] {offset+1:,} ~ {batch_end:,} / {total_count:,} 검증 중...")
            print(f"{'='*80}")
            
            # 배치 데이터 가져오기
            batch_data = get_batch_data(conn, batch_size, offset)
            
            # 각 레코드 분석
            analyses = []
            for row in batch_data:
                analysis = analyze_parsing_issue(
                    row['time_frame_raw'],
                    row['time_value_main'],
                    row['time_unit_main'],
                    row['time_points']
                )
                analyses.append(analysis)
            
            # 문제가 있는 케이스만 필터링
            issues = [a for a in analyses if a.get('has_issues')]
            total_issues.extend(issues)
            
            # 패턴별로 그룹화
            for issue in issues:
                raw = issue['time_frame_raw']
                # 패턴 키 생성
                if 'weeks' in raw.lower() and ',' in raw:
                    pattern_key = 'weeks_comma_and'
                elif 'days' in raw.lower() and ',' in raw:
                    pattern_key = 'days_comma_and'
                elif 'day' in raw.lower() and ' and ' in raw.lower():
                    pattern_key = 'day_and'
                elif 'week' in raw.lower() and ' and ' in raw.lower():
                    pattern_key = 'week_and'
                elif ',' in raw:
                    pattern_key = 'comma_separated'
                elif ' and ' in raw.lower():
                    pattern_key = 'and_separated'
                else:
                    pattern_key = 'other'
                
                if pattern_key not in pattern_groups:
                    pattern_groups[pattern_key] = []
                pattern_groups[pattern_key].append(issue)
            
            # 진행 상황 출력
            if issues:
                print(f"  [문제 발견] {len(issues)}개")
            else:
                print(f"  [OK] 문제 없음")
            
            # 진행률 표시
            progress = (batch_end / total_count) * 100
            print(f"  진행률: {progress:.1f}%")
        
        # 전체 요약 및 패턴 분석
        print(f"\n{'='*80}")
        print("검증 완료!")
        print(f"{'='*80}")
        print(f"총 {total_count:,}개 중 문제 발견: {len(total_issues):,}개")
        
        # 문제 패턴별 상세 분석
        if total_issues:
            print(f"\n{'='*80}")
            print("문제 패턴별 분석 및 정규식 수정 제안")
            print(f"{'='*80}\n")
            
            for pattern_key, issues in sorted(pattern_groups.items(), key=lambda x: len(x[1]), reverse=True):
                print(f"\n[{pattern_key}] - {len(issues)}개 문제")
                print("-" * 80)
                
                # 대표 샘플 5개 출력
                for idx, issue in enumerate(issues[:5], 1):
                    print(f"\n  샘플 #{idx}:")
                    print(f"    원본: \"{issue['time_frame_raw']}\"")
                    print(f"    파싱: {issue['parsed_value']} {issue['parsed_unit']}")
                    print(f"    예상: {issue['expected_value']} {issue['expected_unit']}")
                    print(f"    time_points 파싱: {issue['parsed_time_points']}")
                    print(f"    time_points 예상: {issue['expected_time_points']}")
                    print(f"    문제: {', '.join(issue['issues'])}")
                
                if len(issues) > 5:
                    print(f"\n  ... 외 {len(issues) - 5}개 더")
            
            # 정규식 수정 제안
            print(f"\n{'='*80}")
            print("정규식 수정 제안")
            print(f"{'='*80}\n")
            
            if 'weeks_comma_and' in pattern_groups or 'days_comma_and' in pattern_groups:
                print("1. 'weeks/days N, M, O and P' 패턴 개선 필요")
                print("   - 현재 패턴 4가 처리하지만, 더 강력한 정규식 필요")
                print("   - 예: \"Days 8, 15, 22 and 29\" → [8, 15, 22, 29] 모두 추출")
            
            if 'day_and' in pattern_groups or 'week_and' in pattern_groups:
                print("\n2. 'Day/Week N and M' 패턴 개선 필요")
                print("   - 패턴 4-2가 처리하지만, 패턴 1보다 우선 실행되어야 함")
                print("   - 예: \"Day 13 and 15\" → [13, 15] 모두 추출")
            
            if 'comma_separated' in pattern_groups:
                print("\n3. 쉼표로 구분된 복수 시점 패턴 개선 필요")
                print("   - 패턴 5가 처리하지만, 단위가 앞에 오는 경우도 고려 필요")
                print("   - 예: \"month 0, 6, 12\" → [0, 6, 12] 모두 추출")
        
        conn.close()
        
    except KeyboardInterrupt:
        print("\n\n검증이 중단되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

