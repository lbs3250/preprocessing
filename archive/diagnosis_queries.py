"""
DB 쿼리 및 분석 함수 모듈

데이터베이스 쿼리와 분석 로직을 담당하는 모듈
정규화 패턴은 normalization_patterns 모듈을 사용
"""

import os
from typing import Dict, List
from collections import defaultdict
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from normalization_patterns import (
    timeframe_patterns,
    measure_patterns,
    description_patterns,
    get_sql_parseable_conditions,
    get_sql_unparseable_condition
)

load_dotenv()

# Excel 리포트를 위한 데이터 저장 (전역 변수)
# 이 변수는 diagnose_all.py에서 초기화됨
excel_data = {}


def set_excel_data(data_dict: Dict):
    """Excel 데이터 딕셔너리 설정"""
    global excel_data
    excel_data = data_dict


def get_unparseable_sql_conditions() -> str:
    """
    SQL 쿼리에서 사용할 파싱 불가능 조건 반환
    
    Returns:
        파싱 불가능한 패턴을 제외하는 SQL 조건 문자열
    """
    conditions = get_sql_parseable_conditions()
    
    # 모든 파싱 가능한 패턴을 NOT 조건으로 결합
    not_conditions = [
        f"NOT (o.time_frame_raw ~* '{pattern_regex}')"
        for pattern_regex in conditions.values()
    ]
    
    return " AND ".join(not_conditions)


def analyze_timeframe_patterns(conn):
    """timeFrame 패턴 분석 (normalization_patterns 사용)"""
    print("\n" + "=" * 80)
    print("2. timeFrame 패턴 분석")
    print("=" * 80)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 모든 timeFrame 가져오기
        cur.execute("""
            SELECT time_frame_raw 
            FROM outcome_raw 
            WHERE time_frame_raw IS NOT NULL AND time_frame_raw != ''
        """)
        timeframes = [row['time_frame_raw'] for row in cur.fetchall()]
        
        total = len(timeframes)
        print(f"\n📊 총 timeFrame 데이터: {total:,}건")
        
        # 패턴 분류 (normalization_patterns 사용)
        pattern_mapping = {
            'baseline': 'Baseline 포함 (change_from_baseline)',
            'at_day_week_month': '기간 패턴 (At Day/Week/Month N)',
            'day_month_week_standalone': '기간 패턴 (Day/Month/Week N 단독)',
            'day_to_through': '기간 패턴 (Day N to/through M)',
            'for_period': '기간 패턴 (For N Months/Weeks/Days)',
            'at_months_and': '기간 패턴 (At Months N and M)',
            'text_number': '기간 패턴 (텍스트 숫자+단위)',
            'period': '기간 패턴 (숫자+단위)',
            'year': '기간 패턴 (Year N)',
            'upto': '기간 패턴 (Up to)',
            'through': '기간 패턴 (Through)',
            'percent': '응답률/비율',
            'time': '시간/속도',
            'unparseable': '기타/불명확'
        }
        
        patterns = {name: 0 for name in pattern_mapping.values()}
        examples = defaultdict(list)
        
        for tf in timeframes:
            pattern_type = timeframe_patterns.classify_timeframe(tf)
            pattern_name = pattern_mapping.get(pattern_type, '기타/불명확')
            patterns[pattern_name] += 1
            
            if len(examples[pattern_name]) < 5:
                examples[pattern_name].append(tf)
        
        print(f"\n📈 패턴 분류 결과:")
        for pattern, count in patterns.items():
            pct = count / total * 100 if total > 0 else 0
            print(f"  • {pattern}: {count:,}건 ({pct:.1f}%)")
        
        # 성공/실패 요약
        success_patterns = [
            'Baseline 포함 (change_from_baseline)',
            '기간 패턴 (At Day/Week/Month N)',
            '기간 패턴 (Day/Month/Week N 단독)',
            '기간 패턴 (Day N to/through M)',
            '기간 패턴 (For N Months/Weeks/Days)',
            '기간 패턴 (At Months N and M)',
            '기간 패턴 (텍스트 숫자+단위)',
            '기간 패턴 (숫자+단위)',
            '기간 패턴 (Year N)',
            '기간 패턴 (Up to)',
            '기간 패턴 (Through)'
        ]
        success_count = sum(patterns[p] for p in success_patterns)
        failure_count = patterns['기타/불명확'] + patterns['응답률/비율'] + patterns['시간/속도']
        
        print(f"\n🎯 파싱 가능성 요약:")
        print(f"  ✅ 파싱 가능 (기간 패턴 + Baseline 포함): {success_count:,}건 ({success_count/total*100:.1f}%)")
        print(f"  ❌ 파싱 어려움 (기타/불명확): {failure_count:,}건 ({failure_count/total*100:.1f}%)")
        
        # Excel 데이터 저장
        for pattern, count in patterns.items():
            excel_data['timeframe_patterns'].append({
                'pattern': pattern,
                'count': count,
                'percentage': count / total * 100 if total > 0 else 0
            })
        
        excel_data['summary']['timeframe_parseable'] = success_count
        excel_data['summary']['timeframe_unparseable'] = failure_count
        excel_data['summary']['timeframe_total'] = total
        
        print(f"\n📝 패턴별 예시 (최대 3개):")
        for pattern, ex_list in examples.items():
            if ex_list:
                print(f"\n  {pattern}:")
                for ex in ex_list[:3]:
                    print(f"    - {ex[:80]}..." if len(ex) > 80 else f"    - {ex}")

