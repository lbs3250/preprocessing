"""
통합 데이터 진단 스크립트

outcome_raw 데이터를 종합적으로 분석하고 Excel 리포트 생성을 위한 데이터 수집
"""

import os
import re
import json
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
from dotenv import load_dotenv
from io import StringIO

# 새로 분리된 모듈 import
from normalization_patterns import (
    timeframe_patterns,
    measure_patterns,
    description_patterns,
    get_sql_parseable_conditions
)
from diagnosis_queries import (
    set_excel_data,
    analyze_timeframe_patterns
)

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'clinicaltrials'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

# Excel 리포트를 위한 데이터 저장
excel_data = {
    'summary': {},
    'null_analysis': [],
    'timeframe_patterns': [],
    'measure_patterns': [],
    'description_patterns': [],
    'sponsor_analysis': [],
    'official_analysis': [],
    'sponsor_class_analysis': [],
    'failure_rates': [],
    'party_overview': {},
    'sponsor_parseability': [],
    'official_parseability': []
}


def get_db_connection():
    """PostgreSQL 연결 생성"""
    return psycopg2.connect(**DB_CONFIG)


def analyze_null_values(conn):
    """NULL/빈 값 분석 (Study 단위)"""
    print("=" * 80)
    print("1. NULL/빈 값 분석 (Study 단위)")
    print("=" * 80)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 전체 Study 수
        cur.execute("SELECT COUNT(DISTINCT nct_id) as total_studies FROM outcome_raw")
        total_studies = cur.fetchone()['total_studies']
        
        # Study 단위로 결측률 분석 (모든 outcome이 NULL이면 추출 불가능 = 결측)
        cur.execute("""
            WITH study_null_check AS (
                SELECT 
                    nct_id,
                    COUNT(*) as total_outcomes,
                    COUNT(CASE WHEN measure_raw IS NOT NULL AND measure_raw != '' THEN 1 END) as valid_measure_count,
                    COUNT(CASE WHEN description_raw IS NOT NULL AND description_raw != '' THEN 1 END) as valid_description_count,
                    COUNT(CASE WHEN time_frame_raw IS NOT NULL AND time_frame_raw != '' THEN 1 END) as valid_timeframe_count
                FROM outcome_raw
                GROUP BY nct_id
            )
            SELECT 
                COUNT(*) as total_studies,
                COUNT(CASE WHEN valid_measure_count = 0 THEN 1 END) as studies_with_null_measure,
                COUNT(CASE WHEN valid_description_count = 0 THEN 1 END) as studies_with_null_description,
                COUNT(CASE WHEN valid_timeframe_count = 0 THEN 1 END) as studies_with_null_timeframe
            FROM study_null_check
        """)
        stats = cur.fetchone()
        
        total = stats['total_studies']
        null_measure_studies = stats['studies_with_null_measure']
        null_description_studies = stats['studies_with_null_description']
        null_timeframe_studies = stats['studies_with_null_timeframe']
        
        print(f"\n📊 전체 Studies: {total:,}건")
        print(f"  ❌ measure_raw 결측 Study: {null_measure_studies:,}건 ({null_measure_studies/total*100:.1f}%)")
        print(f"  ❌ description_raw 결측 Study: {null_description_studies:,}건 ({null_description_studies/total*100:.1f}%)")
        print(f"  ❌ time_frame_raw 결측 Study: {null_timeframe_studies:,}건 ({null_timeframe_studies/total*100:.1f}%)")
        
        # 유효 데이터 Study 수
        valid_measure_studies = total - null_measure_studies
        valid_description_studies = total - null_description_studies
        valid_timeframe_studies = total - null_timeframe_studies
        
        print(f"\n✅ 유효 데이터 Study 수:")
        print(f"  ✓ measure_raw 유효: {valid_measure_studies:,}건 ({valid_measure_studies/total*100:.1f}%)")
        print(f"  ✓ description_raw 유효: {valid_description_studies:,}건 ({valid_description_studies/total*100:.1f}%)")
        print(f"  ✓ time_frame_raw 유효: {valid_timeframe_studies:,}건 ({valid_timeframe_studies/total*100:.1f}%)")
        
        # Excel 데이터 저장
        excel_data['null_analysis'] = {
            'total_studies': total,
            'studies_with_null_measure': null_measure_studies,
            'studies_with_null_measure_pct': null_measure_studies/total*100,
            'studies_with_null_description': null_description_studies,
            'studies_with_null_description_pct': null_description_studies/total*100,
            'studies_with_null_timeframe': null_timeframe_studies,
            'studies_with_null_timeframe_pct': null_timeframe_studies/total*100,
            'valid_measure_studies': valid_measure_studies,
            'valid_description_studies': valid_description_studies,
            'valid_timeframe_studies': valid_timeframe_studies
        }
        
        # PRIMARY vs SECONDARY 비교 (Study 단위)
        cur.execute("""
            WITH study_type_null AS (
                SELECT 
                    nct_id,
                    outcome_type,
                    COUNT(*) as total_outcomes,
                    COUNT(CASE WHEN measure_raw IS NOT NULL AND measure_raw != '' THEN 1 END) as valid_measure_count,
                    COUNT(CASE WHEN time_frame_raw IS NOT NULL AND time_frame_raw != '' THEN 1 END) as valid_timeframe_count
                FROM outcome_raw
                GROUP BY nct_id, outcome_type
            )
            SELECT 
                outcome_type,
                COUNT(DISTINCT nct_id) as study_count,
                COUNT(CASE WHEN valid_measure_count = 0 THEN 1 END) as studies_with_null_measure,
                COUNT(CASE WHEN valid_timeframe_count = 0 THEN 1 END) as studies_with_null_timeframe
            FROM study_type_null
            GROUP BY outcome_type
            ORDER BY outcome_type
        """)
        type_stats = cur.fetchall()
        
        print(f"\n📋 타입별 통계 (Study 단위):")
        for row in type_stats:
            study_count = row['study_count']
            null_measure = row['studies_with_null_measure']
            null_timeframe = row['studies_with_null_timeframe']
            print(f"\n  {row['outcome_type']}: {study_count:,}건")
            print(f"    ❌ measure 결측 Study: {null_measure:,}건 ({null_measure/study_count*100:.1f}%)")
            print(f"    ❌ timeFrame 결측 Study: {null_timeframe:,}건 ({null_timeframe/study_count*100:.1f}%)")


# analyze_timeframe_patterns 함수는 diagnosis_queries 모듈로 이동됨


def analyze_measure_patterns(conn):
    """measure 패턴 분석 (outcome 단위)"""
    print("\n" + "=" * 80)
    print("3. measure 패턴 분석 (Outcome 단위)")
    print("=" * 80)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # measure 길이 분석
        cur.execute("""
            SELECT 
                AVG(LENGTH(measure_raw)) as avg_length,
                MIN(LENGTH(measure_raw)) as min_length,
                MAX(LENGTH(measure_raw)) as max_length,
                COUNT(*) as total
            FROM outcome_raw
            WHERE measure_raw IS NOT NULL AND measure_raw != ''
        """)
        length_stats = cur.fetchone()
        
        print(f"\n📏 measure_raw 길이 통계:")
        print(f"  평균: {length_stats['avg_length']:.1f}자")
        print(f"  최소: {length_stats['min_length']}자")
        print(f"  최대: {length_stats['max_length']}자")
        
        # 괄호 안 약어 포함 여부
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN measure_raw ~ '\\([A-Z][A-Z0-9\\-+\\s]+\\)' THEN 1 END) as has_abbreviation
            FROM outcome_raw
            WHERE measure_raw IS NOT NULL AND measure_raw != ''
        """)
        abbrev_stats = cur.fetchone()
        
        abbrev_pct = abbrev_stats['has_abbreviation'] / abbrev_stats['total'] * 100 if abbrev_stats['total'] > 0 else 0
        print(f"\n🔤 약어 사용 분석 (Outcome 단위):")
        print(f"  ✅ 괄호 안 약어 포함: {abbrev_stats['has_abbreviation']:,}건 ({abbrev_pct:.1f}%)")
        print(f"  ❌ 약어 없음: {abbrev_stats['total'] - abbrev_stats['has_abbreviation']:,}건 ({(100-abbrev_pct):.1f}%)")
        
        # Top 20 measure (빈도순)
        cur.execute("""
            SELECT measure_raw, COUNT(*) as count
            FROM outcome_raw
            WHERE measure_raw IS NOT NULL AND measure_raw != ''
            GROUP BY measure_raw
            ORDER BY count DESC
            LIMIT 20
        """)
        top_measures = cur.fetchall()
        
        print(f"\n🏆 상위 20개 measure (빈도순):")
        for i, row in enumerate(top_measures, 1):
            measure = row['measure_raw'][:70] + "..." if len(row['measure_raw']) > 70 else row['measure_raw']
            print(f"  {i:2d}. [{row['count']:4d}건] {measure}")
        
        # Excel 데이터 저장
        excel_data['measure_patterns'] = [
            {
                'rank': i+1,
                'measure': row['measure_raw'],
                'count': row['count']
            }
            for i, row in enumerate(top_measures)
        ]
        excel_data['summary']['measure_avg_length'] = length_stats['avg_length']
        excel_data['summary']['measure_has_abbreviation'] = abbrev_stats['has_abbreviation']
        excel_data['summary']['measure_total'] = abbrev_stats['total']


def analyze_measure_by_study(conn):
    """measure 약어 추출 - Study 단위 분석"""
    print("\n" + "=" * 80)
    print("📊 measure 약어 추출 - Study 단위 분석")
    print("=" * 80)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Study 단위로 약어 추출 성공 여부 분석
        cur.execute("""
            WITH study_abbrev AS (
                SELECT 
                    nct_id,
                    MAX(CASE WHEN outcome_type = 'PRIMARY' 
                             AND measure_raw IS NOT NULL 
                             AND measure_raw != ''
                             AND measure_raw ~ '\\([A-Z][A-Z0-9\\-+\\s]+\\)' 
                        THEN 1 ELSE 0 END) as primary_has_abbrev,
                    MAX(CASE WHEN outcome_type = 'SECONDARY' 
                             AND measure_raw IS NOT NULL 
                             AND measure_raw != ''
                             AND measure_raw ~ '\\([A-Z][A-Z0-9\\-+\\s]+\\)' 
                        THEN 1 ELSE 0 END) as secondary_has_abbrev,
                    MAX(CASE WHEN outcome_type = 'PRIMARY' THEN 1 ELSE 0 END) as has_primary,
                    MAX(CASE WHEN outcome_type = 'SECONDARY' THEN 1 ELSE 0 END) as has_secondary
                FROM outcome_raw
                GROUP BY nct_id
            )
            SELECT 
                COUNT(*) as total_studies,
                COUNT(CASE WHEN has_primary = 1 THEN 1 END) as studies_with_primary,
                COUNT(CASE WHEN has_secondary = 1 THEN 1 END) as studies_with_secondary,
                COUNT(CASE WHEN primary_has_abbrev = 1 THEN 1 END) as primary_success,
                COUNT(CASE WHEN secondary_has_abbrev = 1 THEN 1 END) as secondary_success,
                COUNT(CASE WHEN primary_has_abbrev = 1 AND secondary_has_abbrev = 1 THEN 1 END) as both_success,
                COUNT(CASE WHEN primary_has_abbrev = 1 AND secondary_has_abbrev = 0 THEN 1 END) as primary_only,
                COUNT(CASE WHEN primary_has_abbrev = 0 AND secondary_has_abbrev = 1 THEN 1 END) as secondary_only
            FROM study_abbrev
        """)
        
        stats = cur.fetchone()
        total = stats['total_studies']
        studies_with_primary = stats['studies_with_primary']
        studies_with_secondary = stats['studies_with_secondary']
        primary_success = stats['primary_success']
        secondary_success = stats['secondary_success']
        both_success = stats['both_success']
        primary_only = stats['primary_only']
        secondary_only = stats['secondary_only']
        
        print(f"\n📋 전체 Study 수: {total:,}건")
        print(f"  • Primary outcome 있는 Study: {studies_with_primary:,}건")
        print(f"  • Secondary outcome 있는 Study: {studies_with_secondary:,}건")
        
        print(f"\n✅ 약어 추출 성공률 (해당 outcome이 있는 Study 기준):")
        if studies_with_primary > 0:
            primary_pct = primary_success / studies_with_primary * 100
            print(f"  📌 PRIMARY: {primary_success:,}건 / {studies_with_primary:,}건 ({primary_pct:.1f}%)")
            print(f"     → PRIMARY outcome이 있는 {studies_with_primary:,}건 중 {primary_success:,}건에서 약어 추출 성공")
        else:
            print(f"  📌 PRIMARY: 0건 (Primary outcome이 있는 Study 없음)")
        
        if studies_with_secondary > 0:
            secondary_pct = secondary_success / studies_with_secondary * 100
            print(f"  📌 SECONDARY: {secondary_success:,}건 / {studies_with_secondary:,}건 ({secondary_pct:.1f}%)")
            print(f"     → SECONDARY outcome이 있는 {studies_with_secondary:,}건 중 {secondary_success:,}건에서 약어 추출 성공")
        else:
            print(f"  📌 SECONDARY: 0건 (Secondary outcome이 있는 Study 없음)")
        
        print(f"\n🎯 상세 분류 (전체 {total:,}건 Study 기준):")
        print(f"  ✅ 둘 다 성공: {both_success:,}건 ({both_success/total*100:.1f}%)")
        print(f"     → PRIMARY 약어 추출 성공 + SECONDARY 약어 추출 성공")
        print(f"  📌 PRIMARY만 성공: {primary_only:,}건 ({primary_only/total*100:.1f}%)")
        print(f"     → PRIMARY 약어 추출 성공 + SECONDARY 약어 추출 실패")
        print(f"  📌 SECONDARY만 성공: {secondary_only:,}건 ({secondary_only/total*100:.1f}%)")
        print(f"     → PRIMARY 약어 추출 실패 + SECONDARY 약어 추출 성공")
        both_failed = total - both_success - primary_only - secondary_only
        print(f"  ❌ 둘 다 실패: {both_failed:,}건 ({both_failed/total*100:.1f}%)")
        print(f"     → PRIMARY 약어 추출 실패 + SECONDARY 약어 추출 실패")
        print(f"\n  → 검증: {both_success:,} + {primary_only:,} + {secondary_only:,} + {both_failed:,} = {total:,}건")
        print(f"  → 검증: PRIMARY 성공 = {both_success:,} + {primary_only:,} = {primary_success:,}건 ✓")
        print(f"  → 검증: SECONDARY 성공 = {both_success:,} + {secondary_only:,} = {secondary_success:,}건 ✓")
        
        # Excel 데이터 저장
        excel_data['measure_by_study'] = {
            'total_studies': total,
            'studies_with_primary': studies_with_primary,
            'studies_with_secondary': studies_with_secondary,
            'primary_success': primary_success,
            'primary_success_pct': primary_success / studies_with_primary * 100 if studies_with_primary > 0 else 0,
            'secondary_success': secondary_success,
            'secondary_success_pct': secondary_success / studies_with_secondary * 100 if studies_with_secondary > 0 else 0,
            'both_success': both_success,
            'both_success_pct': both_success / total * 100,
            'primary_only': primary_only,
            'secondary_only': secondary_only,
            'both_failed': total - both_success - primary_only - secondary_only
        }


def analyze_timeframe_by_study(conn):
    """timeFrame 파싱 - Study 단위 분석"""
    print("\n" + "=" * 80)
    print("📊 timeFrame 파싱 - Study 단위 분석")
    print("=" * 80)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Study 단위로 timeFrame 파싱 성공 여부 분석
        # outcome 성공 = measure 약어 추출 성공 (괄호 안 약어 포함)
        cur.execute("""
            WITH study_timeframe AS (
                SELECT 
                    nct_id,
                    -- PRIMARY outcome 존재 여부
                    MAX(CASE WHEN outcome_type = 'PRIMARY' THEN 1 ELSE 0 END) as has_primary_outcome,
                    -- SECONDARY outcome 존재 여부
                    MAX(CASE WHEN outcome_type = 'SECONDARY' THEN 1 ELSE 0 END) as has_secondary_outcome,
                    -- PRIMARY outcome의 measure 약어 추출 성공 여부
                    MAX(CASE WHEN outcome_type = 'PRIMARY' 
                             AND measure_raw IS NOT NULL 
                             AND measure_raw != ''
                             AND measure_raw ~ '\\([A-Z][A-Z0-9\\-+\\s]+\\)'
                        THEN 1 ELSE 0 END) as has_primary_measure,
                    -- SECONDARY outcome의 measure 약어 추출 성공 여부
                    MAX(CASE WHEN outcome_type = 'SECONDARY' 
                             AND measure_raw IS NOT NULL 
                             AND measure_raw != ''
                             AND measure_raw ~ '\\([A-Z][A-Z0-9\\-+\\s]+\\)'
                        THEN 1 ELSE 0 END) as has_secondary_measure,
                    -- PRIMARY outcome의 timeFrame 파싱 성공 여부
                    MAX(CASE WHEN outcome_type = 'PRIMARY' 
                             AND time_frame_raw IS NOT NULL 
                             AND time_frame_raw != ''
                             AND (
                                 time_frame_raw ~* '(^|[^a-z])baseline([^a-z]|$)'
                                 OR time_frame_raw ~* '\\bat\\s+(day|days|week|weeks|month|months)\\s+\\d+'
                                 OR time_frame_raw ~* '\\b(day|days|month|months|week|weeks)\\s+\\d+'
                                 OR time_frame_raw ~* '\\bday\\s+\\d+\\s+(to|through)\\s+(day\\s+)?\\d+'
                                 OR time_frame_raw ~* '\\bfor\\s+\\d+\\s+(month|months|week|weeks|day|days)'
                                 OR time_frame_raw ~* '\\bat\\s+months?\\s+\\d+\\s+and\\s+\\d+'
                                 OR time_frame_raw ~* '(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)\\s+(week|weeks|month|months|year|years|day|days|hour|hours)'
                                 OR time_frame_raw ~ '\\d+\\s*(week|weeks|month|months|year|years|day|days|hour|hours)'
                                 OR time_frame_raw ~* 'year\\s*\\d+'
                                 OR time_frame_raw ~* 'up\\s+to\\s+\\d+'
                                 OR time_frame_raw ~* 'through.*completion.*\\d+\\s*(week|weeks|month|months|year|years)'
                             )
                        THEN 1 ELSE 0 END) as primary_timeframe_success,
                    -- SECONDARY outcome의 timeFrame 파싱 성공 여부
                    MAX(CASE WHEN outcome_type = 'SECONDARY' 
                             AND time_frame_raw IS NOT NULL 
                             AND time_frame_raw != ''
                             AND (
                                 time_frame_raw ~* '(^|[^a-z])baseline([^a-z]|$)'
                                 OR time_frame_raw ~* '\\bat\\s+(day|days|week|weeks|month|months)\\s+\\d+'
                                 OR time_frame_raw ~* '\\b(day|days|month|months|week|weeks)\\s+\\d+'
                                 OR time_frame_raw ~* '\\bday\\s+\\d+\\s+(to|through)\\s+(day\\s+)?\\d+'
                                 OR time_frame_raw ~* '\\bfor\\s+\\d+\\s+(month|months|week|weeks|day|days)'
                                 OR time_frame_raw ~* '\\bat\\s+months?\\s+\\d+\\s+and\\s+\\d+'
                                 OR time_frame_raw ~* '(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)\\s+(week|weeks|month|months|year|years|day|days|hour|hours)'
                                 OR time_frame_raw ~ '\\d+\\s*(week|weeks|month|months|year|years|day|days|hour|hours)'
                                 OR time_frame_raw ~* 'year\\s*\\d+'
                                 OR time_frame_raw ~* 'up\\s+to\\s+\\d+'
                                 OR time_frame_raw ~* 'through.*completion.*\\d+\\s*(week|weeks|month|months|year|years)'
                             )
                        THEN 1 ELSE 0 END) as secondary_timeframe_success
                FROM outcome_raw
                GROUP BY nct_id
            )
            SELECT 
                COUNT(*) as total_studies,
                -- PRIMARY outcome이 있는 Study 수 (measure 성공 여부와 무관)
                COUNT(CASE WHEN has_primary_outcome = 1 THEN 1 END) as studies_with_primary_outcome,
                -- SECONDARY outcome이 있는 Study 수 (measure 성공 여부와 무관)
                COUNT(CASE WHEN has_secondary_outcome = 1 THEN 1 END) as studies_with_secondary_outcome,
                -- PRIMARY outcome의 measure 약어 추출 성공한 Study 수
                COUNT(CASE WHEN has_primary_measure = 1 THEN 1 END) as studies_with_primary_measure,
                -- SECONDARY outcome의 measure 약어 추출 성공한 Study 수
                COUNT(CASE WHEN has_secondary_measure = 1 THEN 1 END) as studies_with_secondary_measure,
                -- PRIMARY: measure 성공 + timeFrame 성공
                COUNT(CASE WHEN has_primary_measure = 1 AND primary_timeframe_success = 1 THEN 1 END) as outcome_frame_both_primary,
                -- SECONDARY: measure 성공 + timeFrame 성공
                COUNT(CASE WHEN has_secondary_measure = 1 AND secondary_timeframe_success = 1 THEN 1 END) as outcome_frame_both_secondary,
                -- PRIMARY: measure 성공 + timeFrame 실패
                COUNT(CASE WHEN has_primary_measure = 1 AND primary_timeframe_success = 0 THEN 1 END) as outcome_only_primary,
                -- SECONDARY: measure 성공 + timeFrame 실패
                COUNT(CASE WHEN has_secondary_measure = 1 AND secondary_timeframe_success = 0 THEN 1 END) as outcome_only_secondary,
                -- PRIMARY: measure 실패 + timeFrame 성공 (PRIMARY outcome이 있는 Study 중에서만)
                COUNT(CASE WHEN has_primary_outcome = 1 AND has_primary_measure = 0 AND primary_timeframe_success = 1 THEN 1 END) as frame_only_primary,
                -- SECONDARY: measure 실패 + timeFrame 성공 (SECONDARY outcome이 있는 Study 중에서만)
                COUNT(CASE WHEN has_secondary_outcome = 1 AND has_secondary_measure = 0 AND secondary_timeframe_success = 1 THEN 1 END) as frame_only_secondary
            FROM study_timeframe
        """)
        
        stats = cur.fetchone()
        total = stats['total_studies']
        studies_with_primary_outcome = stats['studies_with_primary_outcome']
        studies_with_secondary_outcome = stats['studies_with_secondary_outcome']
        studies_with_primary_measure = stats['studies_with_primary_measure']
        studies_with_secondary_measure = stats['studies_with_secondary_measure']
        both_primary = stats['outcome_frame_both_primary']
        both_secondary = stats['outcome_frame_both_secondary']
        outcome_only_primary = stats['outcome_only_primary']
        outcome_only_secondary = stats['outcome_only_secondary']
        frame_only_primary = stats['frame_only_primary']
        frame_only_secondary = stats['frame_only_secondary']
        
        print(f"\n📋 전체 Study 수: {total:,}건")
        print(f"  • PRIMARY outcome 있는 Study: {studies_with_primary_outcome:,}건")
        print(f"  • SECONDARY outcome 있는 Study: {studies_with_secondary_outcome:,}건")
        print(f"  • PRIMARY outcome의 measure 약어 추출 성공: {studies_with_primary_measure:,}건")
        print(f"  • SECONDARY outcome의 measure 약어 추출 성공: {studies_with_secondary_measure:,}건")
        
        print(f"\n✅ PRIMARY Outcome (measure 약어 추출 성공한 {studies_with_primary_measure:,}건 기준):")
        if studies_with_primary_measure > 0:
            print(f"  ✅ outcome + frame 둘 다 성공: {both_primary:,}건 ({both_primary/studies_with_primary_measure*100:.1f}%)")
            print(f"  📌 outcome만 성공 (frame 실패): {outcome_only_primary:,}건 ({outcome_only_primary/studies_with_primary_measure*100:.1f}%)")
            # frame만 성공은 PRIMARY outcome이 있는 Study 중에서 measure 실패했지만 timeFrame 성공한 경우
            print(f"  📌 frame만 성공 (measure 실패, PRIMARY outcome 있음): {frame_only_primary:,}건")
            if studies_with_primary_outcome > 0:
                print(f"  → 검증 (measure 성공 기준): {both_primary + outcome_only_primary:,}건 = {studies_with_primary_measure:,}건")
                print(f"  → 검증 (PRIMARY outcome 전체 기준): {both_primary + outcome_only_primary + frame_only_primary:,}건 ≤ {studies_with_primary_outcome:,}건")
        else:
            print(f"  PRIMARY outcome의 measure 약어 추출 성공한 Study 없음")
        
        print(f"\n✅ SECONDARY Outcome (measure 약어 추출 성공한 {studies_with_secondary_measure:,}건 기준):")
        if studies_with_secondary_measure > 0:
            print(f"  ✅ outcome + frame 둘 다 성공: {both_secondary:,}건 ({both_secondary/studies_with_secondary_measure*100:.1f}%)")
            print(f"  📌 outcome만 성공 (frame 실패): {outcome_only_secondary:,}건 ({outcome_only_secondary/studies_with_secondary_measure*100:.1f}%)")
            # frame만 성공은 SECONDARY outcome이 있는 Study 중에서 measure 실패했지만 timeFrame 성공한 경우
            print(f"  📌 frame만 성공 (measure 실패, SECONDARY outcome 있음): {frame_only_secondary:,}건")
            if studies_with_secondary_outcome > 0:
                print(f"  → 검증 (measure 성공 기준): {both_secondary + outcome_only_secondary:,}건 = {studies_with_secondary_measure:,}건")
                print(f"  → 검증 (SECONDARY outcome 전체 기준): {both_secondary + outcome_only_secondary + frame_only_secondary:,}건 ≤ {studies_with_secondary_outcome:,}건")
        else:
            print(f"  SECONDARY outcome의 measure 약어 추출 성공한 Study 없음")
        
        # Excel 데이터 저장
        excel_data['timeframe_by_study'] = {
            'total_studies': total,
            'primary_both_success': both_primary,
            'primary_both_success_pct': both_primary / total * 100,
            'primary_outcome_only': outcome_only_primary,
            'primary_frame_only': frame_only_primary,
            'secondary_both_success': both_secondary,
            'secondary_both_success_pct': both_secondary / total * 100,
            'secondary_outcome_only': outcome_only_secondary,
            'secondary_frame_only': frame_only_secondary
        }


def analyze_description_patterns(conn):
    """description 패턴 분석"""
    print("\n" + "=" * 80)
    print("4. description 패턴 분석")
    print("=" * 80)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # change from baseline 패턴
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN description_raw ~* 'change.*from.*baseline|difference.*from.*baseline' THEN 1 END) as has_change_from_baseline
            FROM outcome_raw
            WHERE description_raw IS NOT NULL AND description_raw != ''
        """)
        baseline_stats = cur.fetchone()
        
        baseline_pct = baseline_stats['has_change_from_baseline'] / baseline_stats['total'] * 100 if baseline_stats['total'] > 0 else 0
        print(f"\n📊 'change from baseline' 패턴 분석:")
        print(f"  ✅ 발견: {baseline_stats['has_change_from_baseline']:,}건 ({baseline_pct:.1f}%)")
        print(f"  ❌ 미발견: {baseline_stats['total'] - baseline_stats['has_change_from_baseline']:,}건 ({(100-baseline_pct):.1f}%)")
        print(f"  📋 전체: {baseline_stats['total']:,}건")
        
        # Excel 데이터 저장
        excel_data['description_patterns'] = {
            'total': baseline_stats['total'],
            'has_change_from_baseline': baseline_stats['has_change_from_baseline'],
            'no_change_from_baseline': baseline_stats['total'] - baseline_stats['has_change_from_baseline']
        }


def analyze_party_overview(conn):
    """기관/담당자 전체 통계"""
    print("\n" + "=" * 80)
    print("📊 기관/담당자 전체 통계")
    print("=" * 80)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # LEAD_SPONSOR 통계
        cur.execute("""
            SELECT 
                COUNT(DISTINCT name_raw) as total_sponsors,
                COUNT(DISTINCT nct_id) as total_studies,
                COUNT(*) as total_records
            FROM study_party_raw
            WHERE party_type = 'LEAD_SPONSOR'
        """)
        sponsor_stats = cur.fetchone()
        
        # OFFICIAL 통계
        cur.execute("""
            SELECT 
                COUNT(DISTINCT name_raw) as total_officials,
                COUNT(DISTINCT nct_id) as total_studies,
                COUNT(*) as total_records
            FROM study_party_raw
            WHERE party_type = 'OFFICIAL'
        """)
        official_stats = cur.fetchone()
        
        # 기관별 study 분포
        cur.execute("""
            SELECT 
                COUNT(*) as sponsor_count,
                AVG(study_count) as avg_studies,
                MIN(study_count) as min_studies,
                MAX(study_count) as max_studies
            FROM (
                SELECT 
                    name_raw,
                    COUNT(DISTINCT nct_id) as study_count
                FROM study_party_raw
                WHERE party_type = 'LEAD_SPONSOR'
                GROUP BY name_raw
            ) sub
        """)
        sponsor_dist = cur.fetchone()
        
        # 담당자별 study 분포
        cur.execute("""
            SELECT 
                COUNT(*) as official_count,
                AVG(study_count) as avg_studies,
                MIN(study_count) as min_studies,
                MAX(study_count) as max_studies
            FROM (
                SELECT 
                    name_raw,
                    COUNT(DISTINCT nct_id) as study_count
                FROM study_party_raw
                WHERE party_type = 'OFFICIAL'
                GROUP BY name_raw
            ) sub
        """)
        official_dist = cur.fetchone()
        
        print(f"\n🏢 LEAD_SPONSOR (기관) 통계:")
        print(f"  총 기관 수: {sponsor_stats['total_sponsors']:,}개")
        print(f"  총 Study 수: {sponsor_stats['total_studies']:,}건")
        print(f"  총 레코드 수: {sponsor_stats['total_records']:,}건")
        print(f"\n  Study 분포:")
        print(f"    평균: {sponsor_dist['avg_studies']:.1f}건/기관")
        print(f"    최소: {sponsor_dist['min_studies']:,}건")
        print(f"    최대: {sponsor_dist['max_studies']:,}건")
        
        print(f"\n👤 OFFICIAL (담당자) 통계:")
        print(f"  총 담당자 수: {official_stats['total_officials']:,}명")
        print(f"  총 Study 수: {official_stats['total_studies']:,}건")
        print(f"  총 레코드 수: {official_stats['total_records']:,}건")
        print(f"\n  Study 분포:")
        print(f"    평균: {official_dist['avg_studies']:.1f}건/담당자")
        print(f"    최소: {official_dist['min_studies']:,}건")
        print(f"    최대: {official_dist['max_studies']:,}건")
        
        # Excel 데이터 저장
        excel_data['party_overview'] = {
            'total_sponsors': sponsor_stats['total_sponsors'],
            'total_sponsor_studies': sponsor_stats['total_studies'],
            'total_sponsor_records': sponsor_stats['total_records'],
            'sponsor_avg_studies': float(sponsor_dist['avg_studies']),
            'sponsor_min_studies': sponsor_dist['min_studies'],
            'sponsor_max_studies': sponsor_dist['max_studies'],
            'total_officials': official_stats['total_officials'],
            'total_official_studies': official_stats['total_studies'],
            'total_official_records': official_stats['total_records'],
            'official_avg_studies': float(official_dist['avg_studies']),
            'official_min_studies': official_dist['min_studies'],
            'official_max_studies': official_dist['max_studies']
        }


def analyze_by_lead_sponsor(conn):
    """LEAD_SPONSOR별 분석"""
    print("\n" + "=" * 80)
    print("5. LEAD_SPONSOR별 분석")
    print("=" * 80)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # LEAD_SPONSOR별 통계 (파싱 가능성 포함)
        cur.execute("""
            SELECT 
                sp.name_raw as sponsor_name,
                sp.class_raw as sponsor_class,
                COUNT(DISTINCT o.nct_id) as study_count,
                COUNT(*) as outcome_count,
                COUNT(CASE WHEN o.outcome_type = 'PRIMARY' THEN 1 END) as primary_count,
                COUNT(CASE WHEN o.outcome_type = 'SECONDARY' THEN 1 END) as secondary_count,
                COUNT(CASE WHEN o.time_frame_raw IS NULL OR o.time_frame_raw = '' THEN 1 END) as null_timeframe,
                COUNT(CASE WHEN o.time_frame_raw ~ '\\d+\\s*(week|weeks|month|months|year|years|day|days|hour|hours)' THEN 1 END) as period_pattern,
                COUNT(CASE WHEN o.time_frame_raw ~* 'year\\s*\\d+' THEN 1 END) as year_pattern,
                COUNT(CASE WHEN o.time_frame_raw ~* 'up\\s+to\\s+\\d+' THEN 1 END) as upto_pattern,
                COUNT(CASE WHEN o.time_frame_raw ~* 'through.*completion.*\\d+\\s*(week|weeks|month|months|year|years)' THEN 1 END) as through_pattern
            FROM outcome_raw o
            INNER JOIN study_party_raw sp ON o.nct_id = sp.nct_id
            WHERE sp.party_type = 'LEAD_SPONSOR'
            GROUP BY sp.name_raw, sp.class_raw
            ORDER BY study_count DESC
            LIMIT 20
        """)
        
        sponsors = cur.fetchall()
        
        print(f"\n🏢 Top 20 LEAD_SPONSOR (Studies 기준):")
        print(f"{'순위':<5} {'스폰서명':<40} {'클래스':<15} {'Studies':<10} {'Outcomes':<10} {'Parseable':<12} {'Parse%':<10}")
        print("-" * 110)
        
        for i, row in enumerate(sponsors, 1):
            sponsor_name = (row['sponsor_name'] or 'N/A')[:38]
            sponsor_class = (row['sponsor_class'] or 'N/A')[:13]
            total = row['outcome_count']
            null_count = row['null_timeframe']
            valid_count = total - null_count
            
            # 파싱 가능한 패턴 합계
            parseable = (row['period_pattern'] + row['year_pattern'] + 
                        row['upto_pattern'] + row['through_pattern'])
            parseable_pct = (parseable / valid_count * 100) if valid_count > 0 else 0
            
            print(f"{i:<5} {sponsor_name:<40} {sponsor_class:<15} {row['study_count']:<10} "
                  f"{total:<10} {parseable:<12} {parseable_pct:<9.1f}%")
            
            # Excel 데이터 저장
            excel_data['sponsor_analysis'].append({
                'rank': i,
                'sponsor_name': row['sponsor_name'],
                'sponsor_class': row['sponsor_class'],
                'study_count': row['study_count'],
                'outcome_count': total,
                'null_timeframe': null_count,
                'parseable_count': parseable,
                'parseable_pct': parseable_pct
            })
            
            # 파싱 가능성 상세 데이터 저장
            excel_data['sponsor_parseability'].append({
                'rank': i,
                'sponsor_name': row['sponsor_name'],
                'sponsor_class': row['sponsor_class'],
                'study_count': row['study_count'],
                'total_outcomes': total,
                'null_count': null_count,
                'valid_count': valid_count,
                'period_pattern': row['period_pattern'],
                'year_pattern': row['year_pattern'],
                'upto_pattern': row['upto_pattern'],
                'through_pattern': row['through_pattern'],
                'parseable_count': parseable,
                'parseable_pct': parseable_pct,
                'unparseable_count': valid_count - parseable,
                'unparseable_pct': ((valid_count - parseable) / valid_count * 100) if valid_count > 0 else 0
            })
        
        # LEAD_SPONSOR별 timeFrame 패턴 분석 (우선순위 적용하여 중복 제거)
        print("\n" + "-" * 80)
        print("LEAD_SPONSOR별 timeFrame 패턴 (Top 10)")
        print("-" * 80)
        
        cur.execute("""
            WITH sponsor_timeframe_patterns AS (
                SELECT 
                    sp.name_raw as sponsor_name,
                    o.time_frame_raw,
                    CASE 
                        WHEN o.time_frame_raw IS NULL OR o.time_frame_raw = '' THEN 'null'
                        WHEN o.time_frame_raw ~* 'year\\s*\\d+' THEN 'year'
                        WHEN o.time_frame_raw ~* 'up\\s+to\\s+\\d+' THEN 'upto'
                        WHEN o.time_frame_raw ~* 'through.*completion.*\\d+\\s*(week|weeks|month|months|year|years)' THEN 'through'
                        WHEN o.time_frame_raw ~ '\\d+\\s*(week|weeks|month|months|year|years|day|days|hour|hours)' THEN 'period'
                        ELSE 'unparseable'
                    END as pattern_type
                FROM outcome_raw o
                INNER JOIN study_party_raw sp ON o.nct_id = sp.nct_id
                WHERE sp.party_type = 'LEAD_SPONSOR'
            )
            SELECT 
                sponsor_name,
                COUNT(*) as total_outcomes,
                COUNT(CASE WHEN pattern_type = 'null' THEN 1 END) as null_pattern,
                COUNT(CASE WHEN pattern_type = 'year' THEN 1 END) as year_pattern,
                COUNT(CASE WHEN pattern_type = 'upto' THEN 1 END) as upto_pattern,
                COUNT(CASE WHEN pattern_type = 'through' THEN 1 END) as through_pattern,
                COUNT(CASE WHEN pattern_type = 'period' THEN 1 END) as period_pattern,
                COUNT(CASE WHEN pattern_type = 'unparseable' THEN 1 END) as unparseable_pattern
            FROM sponsor_timeframe_patterns
            GROUP BY sponsor_name
            HAVING COUNT(*) >= 10
            ORDER BY total_outcomes DESC
            LIMIT 10
        """)
        
        sponsor_patterns = cur.fetchall()
        
        for row in sponsor_patterns:
            sponsor_name = (row['sponsor_name'] or 'N/A')[:50]
            total = row['total_outcomes']
            period = row['period_pattern']
            year = row['year_pattern']
            upto = row['upto_pattern']
            through = row['through_pattern']
            null_count = row['null_pattern']
            unparseable = row['unparseable_pattern']
            
            # 파싱 가능한 패턴 합계 (중복 제거됨)
            parseable = period + year + upto + through
            
            print(f"\n  📌 {sponsor_name} (총 {total:,}건):")
            print(f"     • Period pattern: {period:,}건 ({period/total*100:.1f}%)")
            print(f"     • Year pattern: {year:,}건 ({year/total*100:.1f}%)")
            print(f"     • Up to pattern: {upto:,}건 ({upto/total*100:.1f}%)")
            print(f"     • Through pattern: {through:,}건 ({through/total*100:.1f}%)")
            print(f"     • Null/Empty: {null_count:,}건 ({null_count/total*100:.1f}%)")
            print(f"     → ✅ 파싱 가능: {parseable:,}건 ({parseable/total*100:.1f}%)")
            print(f"     → ❌ 파싱 어려움: {unparseable:,}건 ({unparseable/total*100:.1f}%)")


def analyze_by_official(conn):
    """OFFICIAL(담당자)별 분석"""
    print("\n" + "=" * 80)
    print("6. OFFICIAL(담당자)별 분석")
    print("=" * 80)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # OFFICIAL별 통계 (파싱 가능성 포함)
        cur.execute("""
            SELECT 
                sp.name_raw as official_name,
                sp.affiliation_raw as affiliation,
                COUNT(DISTINCT o.nct_id) as study_count,
                COUNT(*) as outcome_count,
                COUNT(CASE WHEN o.outcome_type = 'PRIMARY' THEN 1 END) as primary_count,
                COUNT(CASE WHEN o.outcome_type = 'SECONDARY' THEN 1 END) as secondary_count,
                COUNT(CASE WHEN o.time_frame_raw IS NULL OR o.time_frame_raw = '' THEN 1 END) as null_timeframe,
                COUNT(CASE WHEN o.time_frame_raw ~ '\\d+\\s*(week|weeks|month|months|year|years|day|days|hour|hours)' THEN 1 END) as period_pattern,
                COUNT(CASE WHEN o.time_frame_raw ~* 'year\\s*\\d+' THEN 1 END) as year_pattern,
                COUNT(CASE WHEN o.time_frame_raw ~* 'up\\s+to\\s+\\d+' THEN 1 END) as upto_pattern,
                COUNT(CASE WHEN o.time_frame_raw ~* 'through.*completion.*\\d+\\s*(week|weeks|month|months|year|years)' THEN 1 END) as through_pattern
            FROM outcome_raw o
            INNER JOIN study_party_raw sp ON o.nct_id = sp.nct_id
            WHERE sp.party_type = 'OFFICIAL'
            GROUP BY sp.name_raw, sp.affiliation_raw
            ORDER BY study_count DESC
            LIMIT 20
        """)
        
        officials = cur.fetchall()
        
        print(f"\n👤 Top 20 OFFICIAL (Studies 기준):")
        print(f"{'순위':<5} {'담당자명':<35} {'소속':<40} {'Studies':<10} {'Outcomes':<10} {'Parseable':<12} {'Parse%':<10}")
        print("-" * 125)
        
        for i, row in enumerate(officials, 1):
            official_name = (row['official_name'] or 'N/A')[:33]
            affiliation = (row['affiliation'] or 'N/A')[:38]
            total = row['outcome_count']
            null_count = row['null_timeframe']
            valid_count = total - null_count
            
            # 파싱 가능한 패턴 합계
            parseable = (row['period_pattern'] + row['year_pattern'] + 
                        row['upto_pattern'] + row['through_pattern'])
            parseable_pct = (parseable / valid_count * 100) if valid_count > 0 else 0
            
            print(f"{i:<5} {official_name:<35} {affiliation:<40} {row['study_count']:<10} "
                  f"{total:<10} {parseable:<12} {parseable_pct:<9.1f}%")
            
            # Excel 데이터 저장
            excel_data['official_analysis'].append({
                'rank': i,
                'official_name': row['official_name'],
                'affiliation': row['affiliation'],
                'study_count': row['study_count'],
                'outcome_count': total,
                'null_timeframe': null_count,
                'parseable_count': parseable,
                'parseable_pct': parseable_pct
            })
            
            # 파싱 가능성 상세 데이터 저장
            excel_data['official_parseability'].append({
                'rank': i,
                'official_name': row['official_name'],
                'affiliation': row['affiliation'],
                'study_count': row['study_count'],
                'total_outcomes': total,
                'null_count': null_count,
                'valid_count': valid_count,
                'period_pattern': row['period_pattern'],
                'year_pattern': row['year_pattern'],
                'upto_pattern': row['upto_pattern'],
                'through_pattern': row['through_pattern'],
                'parseable_count': parseable,
                'parseable_pct': parseable_pct,
                'unparseable_count': valid_count - parseable,
                'unparseable_pct': ((valid_count - parseable) / valid_count * 100) if valid_count > 0 else 0
            })
        
        # OFFICIAL별 measure 패턴 분석
        print("\n" + "-" * 80)
        print("OFFICIAL별 measure 패턴 (Top 10)")
        print("-" * 80)
        
        cur.execute("""
            SELECT 
                sp.name_raw as official_name,
                sp.affiliation_raw as affiliation,
                COUNT(*) as total_outcomes,
                COUNT(CASE WHEN o.measure_raw ~ '\\([A-Z][A-Z0-9\\-+\\s]+\\)' THEN 1 END) as has_abbreviation,
                COUNT(CASE WHEN o.description_raw ~* 'change.*from.*baseline' THEN 1 END) as change_from_baseline
            FROM outcome_raw o
            INNER JOIN study_party_raw sp ON o.nct_id = sp.nct_id
            WHERE sp.party_type = 'OFFICIAL'
            GROUP BY sp.name_raw, sp.affiliation_raw
            HAVING COUNT(*) >= 10
            ORDER BY total_outcomes DESC
            LIMIT 10
        """)
        
        official_patterns = cur.fetchall()
        
        for row in official_patterns:
            official_name = (row['official_name'] or 'N/A')[:40]
            affiliation = (row['affiliation'] or 'N/A')[:40]
            total = row['total_outcomes']
            has_abbrev = row['has_abbreviation']
            has_baseline = row['change_from_baseline']
            
            print(f"\n  📌 {official_name} ({affiliation}) - 총 {total:,}건:")
            print(f"     • 약어 포함: {has_abbrev:,}건 ({has_abbrev/total*100:.1f}%)")
            print(f"     • Change from baseline: {has_baseline:,}건 ({has_baseline/total*100:.1f}%)")


def analyze_sponsor_class_patterns(conn):
    """Sponsor Class별 패턴 분석"""
    print("\n" + "=" * 80)
    print("7. Sponsor Class별 패턴 분석")
    print("=" * 80)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                sp.class_raw as sponsor_class,
                COUNT(DISTINCT o.nct_id) as study_count,
                COUNT(*) as outcome_count,
                COUNT(CASE WHEN o.time_frame_raw ~ '\\d+\\s*(week|weeks|month|months|year|years)' THEN 1 END) as period_pattern_count,
                COUNT(CASE WHEN o.measure_raw ~ '\\([A-Z][A-Z0-9\\-+\\s]+\\)' THEN 1 END) as abbreviation_count,
                AVG(LENGTH(o.measure_raw)) as avg_measure_length
            FROM outcome_raw o
            INNER JOIN study_party_raw sp ON o.nct_id = sp.nct_id
            WHERE sp.party_type = 'LEAD_SPONSOR'
                AND sp.class_raw IS NOT NULL
            GROUP BY sp.class_raw
            ORDER BY study_count DESC
        """)
        
        classes = cur.fetchall()
        
        print(f"\n📊 Sponsor Class별 통계:")
        print(f"{'Class':<20} {'Studies':<12} {'Outcomes':<12} {'Period Pattern':<30} {'Abbrev':<30} {'Avg Length':<12}")
        print("-" * 120)
        
        for row in classes:
            sponsor_class = (row['sponsor_class'] or 'N/A')[:18]
            total = row['outcome_count']
            period_count = row['period_pattern_count']
            abbrev_count = row['abbreviation_count']
            period_pct = (period_count / total * 100) if total > 0 else 0
            abbrev_pct = (abbrev_count / total * 100) if total > 0 else 0
            avg_length = row['avg_measure_length'] or 0
            
            print(f"{sponsor_class:<20} {row['study_count']:<12} {total:<12} "
                  f"{period_count:,}건({period_pct:.1f}%) {abbrev_count:,}건({abbrev_pct:.1f}%) {avg_length:<11.1f}")
            
            # Excel 데이터 저장
            excel_data['sponsor_class_analysis'].append({
                'sponsor_class': row['sponsor_class'],
                'study_count': row['study_count'],
                'outcome_count': total,
                'period_pattern_count': period_count,
                'period_pattern_pct': period_pct,
                'abbreviation_count': abbrev_count,
                'abbreviation_pct': abbrev_pct,
                'avg_measure_length': float(avg_length) if avg_length else 0
            })


def analyze_failure_rates_by_party(conn):
    """기관/담당자별 매핑 실패율 분석"""
    print("\n" + "=" * 80)
    print("8. 기관/담당자별 예상 매핑 실패율 분석")
    print("=" * 80)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # LEAD_SPONSOR별
        print("\n[LEAD_SPONSOR별 - 예상 timeFrame 파싱 실패율]")
        cur.execute("""
            SELECT 
                sp.name_raw as sponsor_name,
                COUNT(*) as total,
                COUNT(CASE WHEN o.time_frame_raw IS NULL OR o.time_frame_raw = '' THEN 1 END) as null_count,
                COUNT(CASE WHEN o.time_frame_raw !~ '\\d+\\s*(week|weeks|month|months|year|years|day|days|hour|hours)' 
                          AND o.time_frame_raw !~* 'year\\s*\\d+'
                          AND o.time_frame_raw !~* 'up\\s+to'
                          AND o.time_frame_raw !~* 'through.*completion'
                          AND o.time_frame_raw IS NOT NULL 
                          AND o.time_frame_raw != '' THEN 1 END) as complex_pattern_count,
                CASE 
                    WHEN COUNT(*) - COUNT(CASE WHEN o.time_frame_raw IS NULL OR o.time_frame_raw = '' THEN 1 END) > 0
                    THEN (COUNT(CASE WHEN o.time_frame_raw !~ '\\d+\\s*(week|weeks|month|months|year|years|day|days|hour|hours)' 
                              AND o.time_frame_raw !~* 'year\\s*\\d+'
                              AND o.time_frame_raw !~* 'up\\s+to'
                              AND o.time_frame_raw !~* 'through.*completion'
                              AND o.time_frame_raw IS NOT NULL 
                              AND o.time_frame_raw != '' THEN 1 END)::float / 
                          NULLIF(COUNT(*) - COUNT(CASE WHEN o.time_frame_raw IS NULL OR o.time_frame_raw = '' THEN 1 END), 0) * 100)
                    ELSE 0
                END as failure_rate
            FROM outcome_raw o
            INNER JOIN study_party_raw sp ON o.nct_id = sp.nct_id
            WHERE sp.party_type = 'LEAD_SPONSOR'
            GROUP BY sp.name_raw
            HAVING COUNT(*) >= 20
            ORDER BY failure_rate DESC
            LIMIT 10
        """)
        
        failure_rates = cur.fetchall()
        
        print(f"{'스폰서명':<50} {'Total':<10} {'Null':<10} {'Complex':<10} {'Failure Rate':<12}")
        print("-" * 100)
        
        for row in failure_rates:
            sponsor_name = (row['sponsor_name'] or 'N/A')[:48]
            total = row['total']
            null_count = row['null_count']
            complex_count = row['complex_pattern_count']
            failure_rate = row['failure_rate'] or 0
            
            print(f"{sponsor_name:<50} {total:<10} {null_count:<10} {complex_count:<10} {failure_rate:<11.1f}%")
            
            # Excel 데이터 저장
            excel_data['failure_rates'].append({
                'sponsor_name': row['sponsor_name'],
                'total': total,
                'null_count': null_count,
                'complex_count': complex_count,
                'failure_rate': float(failure_rate)
            })


def explain_normalization_rules():
    """정규화 룰 설명"""
    print("\n" + "=" * 80)
    print("📋 정규화 룰 설명")
    print("=" * 80)
    
    print("""
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
""")
    
    # Excel 데이터 저장
    excel_data['normalization_rules'] = {
        'text_cleaning': {
            'description': '공백 정리, 오타 교정',
            'rules': ['연속 공백 → 단일 공백', 'extention → extension']
        },
        'timeframe_parsing': {
            'parseable_patterns': [
                'Baseline 포함: "Baseline, Week 16" → change_from_baseline_flag = TRUE',
                'At Day/Week/Month N: "At Day 1", "At Week 14", "At Month 12" → N, day/week/month',
                'Day/Month/Week N 단독: "Day 1", "Month 3", "Week 12" → N, day/month/week',
                'Day N to/through M: "Day 1 to day 30", "Day 1 through 7" → 시작일, 종료일 추출',
                'For N Months/Weeks/Days: "For 10 Months" → 10, month',
                'At Months N and M: "At Months 6 and 12" → 복수 시점 추출',
                '텍스트 숫자+단위: "Two years", "eight weeks" → 2, year / 8, week',
                '숫자+단위: "26 weeks" → 26, weeks',
                'Year N: "Year 3.5" → 3.5, year',
                'Up to: "up to 72 hours" → 72, hour',
                'Through: "through study completion, an average of 1 year" → 1, year'
            ],
            'baseline_patterns': [
                'Baseline, Week 16 → change_from_baseline_flag = TRUE',
                'Baseline (Week 1 [Day 1]), Week 16 → change_from_baseline_flag = TRUE'
            ],
            'unparseable_patterns': [
                '% of exact responses (응답률)',
                'The time to respond (시간/속도)',
                '기타 비표준 표현'
            ]
        },
        'change_from_baseline': {
            'description': 'description에서 "change from baseline" 패턴 검색',
            'patterns': [
                'change from baseline',
                'change of .* from baseline',
                'difference from baseline'
            ]
        },
        'phase_tagging': {
            'keywords': ['double-blind', 'extension', 'follow-up', 'open-label']
        }
    }


def analyze_unparseable_by_party(conn):
    """파싱 불가능한 것들을 기관/담당자별로 원인 분석"""
    print("\n" + "=" * 80)
    print("🔬 파싱 불가능 케이스 - 기관/담당자별 원인 분석")
    print("=" * 80)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # LEAD_SPONSOR별 파싱 실패 케이스 분석
        print("\n[LEAD_SPONSOR별 파싱 실패 케이스]")
        cur.execute("""
            SELECT 
                sp.name_raw as sponsor_name,
                sp.class_raw as sponsor_class,
                COUNT(*) as total_outcomes,
                COUNT(CASE WHEN o.time_frame_raw IS NULL OR o.time_frame_raw = '' THEN 1 END) as null_count,
                COUNT(CASE WHEN o.time_frame_raw IS NOT NULL 
                          AND o.time_frame_raw != ''
                          -- 파싱 가능한 패턴 모두 제외
                          AND NOT (o.time_frame_raw ~* '(^|[^a-z])baseline([^a-z]|$)')
                          AND NOT (o.time_frame_raw ~* '(^|[^a-z])(day|days|week|weeks|month|months)\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* '\\d+\\s*-?\\s*(day|days|week|weeks|month|months|year|years|hour|hours|hr|hrs)')
                          AND NOT (o.time_frame_raw ~* 'at\\s+(day|days|week|weeks|month|months)\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* 'day\\s+\\d+\\s+(to|through)\\s+(day\\s+)?\\d+')
                          AND NOT (o.time_frame_raw ~* 'for\\s+\\d+\\s+(month|months|week|weeks|day|days)')
                          AND NOT (o.time_frame_raw ~* 'at\\s+months?\\s+\\d+\\s+and\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* '(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)\\s+(week|weeks|month|months|year|years|day|days|hour|hours)')
                          AND NOT (o.time_frame_raw ~* 'year\\s*\\d+')
                          AND NOT (o.time_frame_raw ~* 'up\\s*to\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* 'up\\s*to\\s+(day|days|week|weeks|month|months|year|years)\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* '(week|weeks|day|days|month|months)\\s+\\d+.*?,\\s*(week|weeks|day|days|month|months)\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* 'through.*completion.*\\d+\\s*(week|weeks|month|months|year|years)')
                          THEN 1 END) as unparseable_count
            FROM outcome_raw o
            INNER JOIN study_party_raw sp ON o.nct_id = sp.nct_id
            WHERE sp.party_type = 'LEAD_SPONSOR'
            GROUP BY sp.name_raw, sp.class_raw
            HAVING COUNT(CASE WHEN o.time_frame_raw IS NOT NULL 
                          AND o.time_frame_raw != ''
                          -- 파싱 가능한 패턴 모두 제외
                          AND NOT (o.time_frame_raw ~* '(^|[^a-z])baseline([^a-z]|$)')
                          AND NOT (o.time_frame_raw ~* '(^|[^a-z])(day|days|week|weeks|month|months)\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* '\\d+\\s*-?\\s*(day|days|week|weeks|month|months|year|years|hour|hours|hr|hrs)')
                          AND NOT (o.time_frame_raw ~* 'at\\s+(day|days|week|weeks|month|months)\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* 'day\\s+\\d+\\s+(to|through)\\s+(day\\s+)?\\d+')
                          AND NOT (o.time_frame_raw ~* 'for\\s+\\d+\\s+(month|months|week|weeks|day|days)')
                          AND NOT (o.time_frame_raw ~* 'at\\s+months?\\s+\\d+\\s+and\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* '(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)\\s+(week|weeks|month|months|year|years|day|days|hour|hours)')
                          AND NOT (o.time_frame_raw ~* 'year\\s*\\d+')
                          AND NOT (o.time_frame_raw ~* 'up\\s*to\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* 'up\\s*to\\s+(day|days|week|weeks|month|months|year|years)\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* '(week|weeks|day|days|month|months)\\s+\\d+.*?,\\s*(week|weeks|day|days|month|months)\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* 'through.*completion.*\\d+\\s*(week|weeks|month|months|year|years)')
                          THEN 1 END) > 0
            ORDER BY unparseable_count DESC
            LIMIT 20
        """)
        
        sponsor_failures = cur.fetchall()
        
        print(f"{'순위':<5} {'스폰서명':<40} {'클래스':<15} {'Total':<10} {'Null':<10} {'Unparseable':<15} {'실패율':<10}")
        print("-" * 110)
        
        for i, row in enumerate(sponsor_failures, 1):
            sponsor_name = (row['sponsor_name'] or 'N/A')[:38]
            sponsor_class = (row['sponsor_class'] or 'N/A')[:13]
            total = row['total_outcomes']
            null_count = row['null_count']
            unparseable = row['unparseable_count']
            valid_count = total - null_count
            failure_rate = (unparseable / valid_count * 100) if valid_count > 0 else 0
            
            print(f"{i:<5} {sponsor_name:<40} {sponsor_class:<15} {total:<10} {null_count:<10} "
                  f"{unparseable:<15} {failure_rate:<9.1f}%")
            
            # Excel 데이터 저장
            excel_data['unparseable_by_sponsor'] = excel_data.get('unparseable_by_sponsor', [])
            excel_data['unparseable_by_sponsor'].append({
                'rank': i,
                'sponsor_name': row['sponsor_name'],
                'sponsor_class': row['sponsor_class'],
                'total_outcomes': total,
                'null_count': null_count,
                'unparseable_count': unparseable,
                'failure_rate': failure_rate
            })
        
        # 파싱 실패 케이스 샘플 추출 (timeFrame + measure 모두)
        print("\n[파싱 실패 케이스 샘플]")
        
        # timeFrame 파싱 실패 샘플 (빈도수 포함)
        print("\n📌 timeFrame 파싱 실패 샘플 (Top 20):")
        cur.execute("""
            SELECT 
                o.time_frame_raw,
                COUNT(*) as frequency
            FROM outcome_raw o
            WHERE o.time_frame_raw IS NOT NULL 
              AND o.time_frame_raw != ''
              -- 파싱 가능한 패턴 모두 제외
              AND NOT (o.time_frame_raw ~* '(^|[^a-z])baseline([^a-z]|$)')
              AND NOT (o.time_frame_raw ~* '(^|[^a-z])(day|days|week|weeks|month|months)\\s+\\d+')
              AND NOT (o.time_frame_raw ~* '\\d+\\s*-?\\s*(day|days|week|weeks|month|months|year|years|hour|hours|hr|hrs)')
              AND NOT (o.time_frame_raw ~* 'at\\s+(day|days|week|weeks|month|months)\\s+\\d+')
              AND NOT (o.time_frame_raw ~* 'day\\s+\\d+\\s+(to|through)\\s+(day\\s+)?\\d+')
              AND NOT (o.time_frame_raw ~* 'for\\s+\\d+\\s+(month|months|week|weeks|day|days)')
              AND NOT (o.time_frame_raw ~* 'at\\s+months?\\s+\\d+\\s+and\\s+\\d+')
              AND NOT (o.time_frame_raw ~* '(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)\\s+(week|weeks|month|months|year|years|day|days|hour|hours)')
              AND NOT (o.time_frame_raw ~* 'year\\s*\\d+')
              AND NOT (o.time_frame_raw ~* 'up\\s*to\\s+\\d+')
              AND NOT (o.time_frame_raw ~* 'up\\s*to\\s+(day|days|week|weeks|month|months|year|years)\\s+\\d+')
              AND NOT (o.time_frame_raw ~* '(week|weeks|day|days|month|months)\\s+\\d+.*?,\\s*(week|weeks|day|days|month|months)\\s+\\d+')
              AND NOT (o.time_frame_raw ~* 'through.*completion.*\\d+\\s*(week|weeks|month|months|year|years)')
            GROUP BY o.time_frame_raw
            ORDER BY frequency DESC
            LIMIT 20
        """)
        
        timeframe_samples = cur.fetchall()
        for i, sample in enumerate(timeframe_samples, 1):
            tf = sample['time_frame_raw']
            freq = sample['frequency']
            display_text = tf[:100] + "..." if len(tf) > 100 else tf
            print(f"  {i:2d}. [{freq:4d}건] {display_text}")
        
        # measure 약어 추출 실패 샘플 (빈도수 포함)
        print("\n📌 measure 약어 추출 실패 샘플 (Top 20):")
        cur.execute("""
            SELECT 
                o.measure_raw,
                COUNT(*) as frequency
            FROM outcome_raw o
            WHERE o.measure_raw IS NOT NULL 
              AND o.measure_raw != ''
              AND o.measure_raw !~ '\\([A-Za-z][A-Za-z0-9\\-+\\s/]+\\)'
            GROUP BY o.measure_raw
            ORDER BY frequency DESC
            LIMIT 20
        """)
        
        measure_samples = cur.fetchall()
        for i, sample in enumerate(measure_samples, 1):
            measure = sample['measure_raw']
            freq = sample['frequency']
            display_text = measure[:100] + "..." if len(measure) > 100 else measure
            print(f"  {i:2d}. [{freq:4d}건] {display_text}")
        
        # OFFICIAL별 파싱 실패 케이스 분석
        print("\n" + "-" * 80)
        print("[OFFICIAL별 파싱 실패 케이스]")
        cur.execute("""
            SELECT 
                sp.name_raw as official_name,
                sp.affiliation_raw as affiliation,
                COUNT(*) as total_outcomes,
                COUNT(CASE WHEN o.time_frame_raw IS NULL OR o.time_frame_raw = '' THEN 1 END) as null_count,
                COUNT(CASE WHEN o.time_frame_raw IS NOT NULL 
                          AND o.time_frame_raw != ''
                          -- 파싱 가능한 패턴 모두 제외
                          AND NOT (o.time_frame_raw ~* '(^|[^a-z])baseline([^a-z]|$)')
                          AND NOT (o.time_frame_raw ~* '\\bat\\s+(day|days|week|weeks|month|months)\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* '\\b(day|days|month|months|week|weeks)\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* '\\bday\\s+\\d+\\s+(to|through)\\s+(day\\s+)?\\d+')
                          AND NOT (o.time_frame_raw ~* '\\bfor\\s+\\d+\\s+(month|months|week|weeks|day|days)')
                          AND NOT (o.time_frame_raw ~* '\\bat\\s+months?\\s+\\d+\\s+and\\s+\\d+')
                          AND NOT (o.time_frame_raw ~ '\\d+\\s*-?\\s*(week|weeks|month|months|year|years|day|days|hour|hours|hr|hrs)')
                          AND NOT (o.time_frame_raw ~* '(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)\\s+(week|weeks|month|months|year|years|day|days|hour|hours)')
                          AND NOT (o.time_frame_raw ~* 'year\\s*\\d+')
                          AND NOT (o.time_frame_raw ~* 'up\\s*to\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* 'up\\s*to\\s+(day|days|week|weeks|month|months|year|years)\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* '(week|weeks|day|days|month|months)\\s+\\d+.*?,\\s*(week|weeks|day|days|month|months)\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* 'through.*completion.*\\d+\\s*(week|weeks|month|months|year|years)')
                          THEN 1 END) as unparseable_count
            FROM outcome_raw o
            INNER JOIN study_party_raw sp ON o.nct_id = sp.nct_id
            WHERE sp.party_type = 'OFFICIAL'
            GROUP BY sp.name_raw, sp.affiliation_raw
            HAVING COUNT(CASE WHEN o.time_frame_raw IS NOT NULL 
                          AND o.time_frame_raw != ''
                          -- 파싱 가능한 패턴 모두 제외
                          AND NOT (o.time_frame_raw ~* '(^|[^a-z])baseline([^a-z]|$)')
                          AND NOT (o.time_frame_raw ~* '(^|[^a-z])(day|days|week|weeks|month|months)\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* '\\d+\\s*-?\\s*(day|days|week|weeks|month|months|year|years|hour|hours|hr|hrs)')
                          AND NOT (o.time_frame_raw ~* 'at\\s+(day|days|week|weeks|month|months)\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* 'day\\s+\\d+\\s+(to|through)\\s+(day\\s+)?\\d+')
                          AND NOT (o.time_frame_raw ~* 'for\\s+\\d+\\s+(month|months|week|weeks|day|days)')
                          AND NOT (o.time_frame_raw ~* 'at\\s+months?\\s+\\d+\\s+and\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* '(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)\\s+(week|weeks|month|months|year|years|day|days|hour|hours)')
                          AND NOT (o.time_frame_raw ~* 'year\\s*\\d+')
                          AND NOT (o.time_frame_raw ~* 'up\\s*to\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* 'up\\s*to\\s+(day|days|week|weeks|month|months|year|years)\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* '(week|weeks|day|days|month|months)\\s+\\d+.*?,\\s*(week|weeks|day|days|month|months)\\s+\\d+')
                          AND NOT (o.time_frame_raw ~* 'through.*completion.*\\d+\\s*(week|weeks|month|months|year|years)')
                          THEN 1 END) > 0
            ORDER BY unparseable_count DESC
            LIMIT 15
        """)
        
        official_failures = cur.fetchall()
        
        print(f"{'순위':<5} {'담당자명':<30} {'소속':<35} {'Total':<10} {'Unparseable':<15} {'실패율':<10}")
        print("-" * 110)
        
        for i, row in enumerate(official_failures, 1):
            official_name = (row['official_name'] or 'N/A')[:28]
            affiliation = (row['affiliation'] or 'N/A')[:33]
            total = row['total_outcomes']
            null_count = row['null_count']
            unparseable = row['unparseable_count']
            valid_count = total - null_count
            failure_rate = (unparseable / valid_count * 100) if valid_count > 0 else 0
            
            print(f"{i:<5} {official_name:<30} {affiliation:<35} {total:<10} "
                  f"{unparseable:<15} {failure_rate:<9.1f}%")
            
            # Excel 데이터 저장
            excel_data['unparseable_by_official'] = excel_data.get('unparseable_by_official', [])
            excel_data['unparseable_by_official'].append({
                'rank': i,
                'official_name': row['official_name'],
                'affiliation': row['affiliation'],
                'total_outcomes': total,
                'null_count': null_count,
                'unparseable_count': unparseable,
                'failure_rate': failure_rate
            })


def generate_summary_report(conn):
    """종합 리포트"""
    print("\n" + "=" * 80)
    print("📊 종합 리포트")
    print("=" * 80)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 기본 통계
        cur.execute("""
            SELECT 
                COUNT(DISTINCT o.nct_id) as total_studies,
                COUNT(*) as total_outcomes,
                COUNT(CASE WHEN o.outcome_type = 'PRIMARY' THEN 1 END) as primary_count,
                COUNT(CASE WHEN o.outcome_type = 'SECONDARY' THEN 1 END) as secondary_count
            FROM outcome_raw o
        """)
        summary = cur.fetchone()
        
        cur.execute("""
            SELECT AVG(outcome_count) as avg_outcomes
            FROM (
                SELECT o.nct_id, COUNT(*) as outcome_count
                FROM outcome_raw o
                GROUP BY o.nct_id
            ) subq
        """)
        avg_outcomes = cur.fetchone()['avg_outcomes']
        
        print(f"\n📊 기본 통계:")
        print(f"  총 Studies: {summary['total_studies']:,}건")
        print(f"  총 Outcomes: {summary['total_outcomes']:,}건")
        print(f"  Study당 평균 Outcomes: {avg_outcomes:.1f}개")
        if summary['total_outcomes'] > 0:
            print(f"  PRIMARY: {summary['primary_count']:,}건 ({summary['primary_count']/summary['total_outcomes']*100:.1f}%)")
            print(f"  SECONDARY: {summary['secondary_count']:,}건 ({summary['secondary_count']/summary['total_outcomes']*100:.1f}%)")
        
        # Excel 데이터 저장
        excel_data['summary'] = {
            'total_studies': summary['total_studies'],
            'total_outcomes': summary['total_outcomes'],
            'avg_outcomes_per_study': float(avg_outcomes) if avg_outcomes else 0,
            'primary_count': summary['primary_count'],
            'secondary_count': summary['secondary_count'],
            'primary_pct': summary['primary_count']/summary['total_outcomes']*100 if summary['total_outcomes'] > 0 else 0,
            'secondary_pct': summary['secondary_count']/summary['total_outcomes']*100 if summary['total_outcomes'] > 0 else 0
        }


def save_to_json():
    """Excel 생성을 위한 JSON 파일 저장"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"diagnosis_data_{timestamp}.json"
    
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(excel_data, f, ensure_ascii=False, indent=2, default=str)
    
    return json_filename


def main():
    """메인 함수"""
    import sys
    from io import StringIO
    
    # 출력을 캡처하기 위한 StringIO
    output_buffer = StringIO()
    original_stdout = sys.stdout
    
    class TeeOutput:
        """출력을 화면과 버퍼에 동시에 쓰기"""
        def __init__(self, *files):
            self.files = files
        def write(self, obj):
            for f in self.files:
                f.write(obj)
                f.flush()
        def flush(self):
            for f in self.files:
                f.flush()
    
    print("=" * 80)
    print("🔍 통합 데이터 진단 시작")
    print("=" * 80)
    
    try:
        # Excel 데이터 딕셔너리를 diagnosis_queries 모듈에 설정
        set_excel_data(excel_data)
        
        conn = get_db_connection()
        
        # 데이터 존재 여부 확인
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM outcome_raw")
            outcome_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM study_party_raw WHERE party_type IN ('LEAD_SPONSOR', 'OFFICIAL')")
            party_count = cur.fetchone()[0]
            
            if outcome_count == 0:
                print("\n[ERROR] outcome_raw 테이블에 데이터가 없습니다!")
                print("먼저 collect_outcomes.py를 실행하여 데이터를 수집하세요.")
                return
            
            print(f"\n📋 데이터 확인:")
            print(f"  Outcomes: {outcome_count:,}건")
            print(f"  Party records (LEAD_SPONSOR/OFFICIAL): {party_count:,}건")
        
        # 출력을 화면과 버퍼에 동시에
        sys.stdout = TeeOutput(original_stdout, output_buffer)
        
        # 각 분석 실행
        analyze_null_values(conn)  # 1. 컬럼별 누락 건수
        explain_normalization_rules()  # 2. 정규화 룰 설명
        analyze_party_overview(conn)  # 기관/담당자 전체 통계
        analyze_timeframe_patterns(conn)
        analyze_measure_patterns(conn)
        analyze_measure_by_study(conn)  # measure 약어 추출 - Study 단위
        analyze_timeframe_by_study(conn)  # timeFrame 파싱 - Study 단위
        analyze_description_patterns(conn)
        analyze_unparseable_by_party(conn)  # 4. 파싱 못하는 것들 기관/담당자별 원인 분석
        analyze_by_lead_sponsor(conn)  # 기관별 상세 분석 (파싱 가능성 포함)
        analyze_by_official(conn)  # 담당자별 상세 분석 (파싱 가능성 포함)
        analyze_sponsor_class_patterns(conn)
        analyze_failure_rates_by_party(conn)
        generate_summary_report(conn)
        
        print("\n" + "=" * 80)
        print("✅ 진단 완료!")
        print("=" * 80)
        
        # 원래 stdout으로 복구
        sys.stdout = original_stdout
        
        # MD 파일로 저장
        output_content = output_buffer.getvalue()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_filename = f"diagnosis_complete_{timestamp}.md"
        
        with open(md_filename, 'w', encoding='utf-8') as f:
            f.write(f"# 통합 데이터 진단 결과\n\n")
            f.write(f"**생성 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            f.write("```\n")
            f.write(output_content)
            f.write("\n```\n")
        
        # Excel 생성을 위한 JSON 파일 저장
        json_filename = save_to_json()
        
        print(f"\n📄 파일 저장 완료:")
        print(f"  • MD 리포트: {md_filename}")
        print(f"  • Excel용 데이터: {json_filename}")
        print(f"\n💡 다음 단계:")
        print(f"  1. {json_filename} 파일을 사용하여 Excel 리포트 생성")
        print(f"  2. 진단 결과를 바탕으로 정규화 규칙 설계")
        
        conn.close()
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout = original_stdout
        if 'conn' in locals():
            conn.close()
    finally:
        if 'output_buffer' in locals():
            output_buffer.close()


if __name__ == "__main__":
    main()

