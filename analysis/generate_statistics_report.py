"""
통계 보고서 생성 스크립트
SQL 쿼리 결과를 Markdown 보고서로 변환
"""

import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from datetime import datetime

# DB 연결 설정
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

def execute_statistics_query(conn):
    """통계 쿼리 실행"""
    query = """
    -- 전체 쿼리를 하나의 WITH 절로 시작
    WITH measure_stats AS (
        SELECT 
            outcome_type,
            COUNT(*) as total_count,
            COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 1 END) as success_count,
            COUNT(CASE WHEN failure_reason IS NOT NULL THEN 1 END) as failed_count
        FROM outcome_normalized
        GROUP BY outcome_type
    ),
    timeframe_stats AS (
        SELECT 
            COUNT(*) FILTER (WHERE time_value_main IS NOT NULL OR (time_points IS NOT NULL AND jsonb_array_length(time_points) > 0)) as total_success,
            COUNT(*) FILTER (WHERE (time_value_main IS NOT NULL AND (time_points IS NULL OR jsonb_array_length(time_points) = 0)) OR (time_points IS NOT NULL AND jsonb_array_length(time_points) = 1)) as single_success,
            COUNT(*) FILTER (WHERE time_points IS NOT NULL AND jsonb_array_length(time_points) > 1) as multiple_success,
            COUNT(*) FILTER (WHERE failure_reason IN ('TIMEFRAME_FAILED', 'BOTH_FAILED')) as total_failed,
            COUNT(*) as total_all
        FROM outcome_normalized
    ),
    phase_totals AS (
        SELECT 
            COALESCE(NULLIF(phase, ''), 'NA') as phase,
            COUNT(*) as phase_total_count
        FROM outcome_normalized
        GROUP BY phase
    ),
    phase_failures AS (
        SELECT 
            COALESCE(NULLIF(phase, ''), 'NA') as phase,
            COUNT(*) as failed_count
        FROM outcome_normalized
        WHERE failure_reason IS NOT NULL
        GROUP BY phase
    ),
    total_all_outcomes AS (
        SELECT COUNT(*) as total_all
        FROM outcome_normalized
    )
    -- 1. Measure Code 정규화 결과
    SELECT 
        'measure' as report_type,
        outcome_type as group_key,
        'TOTAL' as status,
        NULL::VARCHAR as sub_status,
        SUM(total_count) as count,
        SUM(total_count) as total,
        ROUND(SUM(total_count)::numeric / SUM(total_count) * 100, 2) as percentage,
        NULL::INTEGER as phase_total
    FROM measure_stats
    GROUP BY outcome_type

    UNION ALL

    SELECT 
        'measure' as report_type,
        outcome_type as group_key,
        'SUCCESS' as status,
        NULL::VARCHAR as sub_status,
        SUM(success_count) as count,
        SUM(total_count) as total,
        ROUND(SUM(success_count)::numeric / SUM(total_count) * 100, 2) as percentage,
        NULL::INTEGER as phase_total
    FROM measure_stats
    GROUP BY outcome_type

    UNION ALL

    SELECT 
        'measure' as report_type,
        outcome_type as group_key,
        'FAILED' as status,
        NULL::VARCHAR as sub_status,
        SUM(failed_count) as count,
        SUM(total_count) as total,
        ROUND(SUM(failed_count)::numeric / SUM(total_count) * 100, 2) as percentage,
        NULL::INTEGER as phase_total
    FROM measure_stats
    GROUP BY outcome_type

    UNION ALL

    -- 2. Timeframe 정규화 결과
    SELECT 
        'timeframe' as report_type,
        'ALL' as group_key,
        'TOTAL_SUCCESS' as status,
        NULL::VARCHAR as sub_status,
        total_success as count,
        total_all as total,
        ROUND(total_success::numeric / NULLIF(total_all, 0) * 100, 2) as percentage,
        NULL::INTEGER as phase_total
    FROM timeframe_stats

    UNION ALL

    SELECT 
        'timeframe' as report_type,
        'ALL' as group_key,
        'SINGLE_SUCCESS' as status,
        NULL::VARCHAR as sub_status,
        single_success as count,
        total_all as total,
        ROUND(single_success::numeric / NULLIF(total_all, 0) * 100, 2) as percentage,
        NULL::INTEGER as phase_total
    FROM timeframe_stats

    UNION ALL

    SELECT 
        'timeframe' as report_type,
        'ALL' as group_key,
        'MULTIPLE_SUCCESS' as status,
        NULL::VARCHAR as sub_status,
        multiple_success as count,
        total_all as total,
        ROUND(multiple_success::numeric / NULLIF(total_all, 0) * 100, 2) as percentage,
        NULL::INTEGER as phase_total
    FROM timeframe_stats

    UNION ALL

    SELECT 
        'timeframe' as report_type,
        'ALL' as group_key,
        'TOTAL_FAILED' as status,
        NULL::VARCHAR as sub_status,
        total_failed as count,
        total_all as total,
        ROUND(total_failed::numeric / NULLIF(total_all, 0) * 100, 2) as percentage,
        NULL::INTEGER as phase_total
    FROM timeframe_stats

    UNION ALL

    -- 3. 필드 누락 현황
    SELECT 
        'missing_fields' as report_type,
        'time_frame_raw' as group_key,
        'MISSING' as status,
        NULL::VARCHAR as sub_status,
        COUNT(*) as count,
        (SELECT COUNT(*) FROM outcome_raw) as total,
        ROUND(COUNT(*)::numeric / NULLIF((SELECT COUNT(*) FROM outcome_raw), 0) * 100, 2) as percentage,
        NULL::INTEGER as phase_total
    FROM outcome_raw
    WHERE time_frame_raw IS NULL OR time_frame_raw = ''

    UNION ALL

    SELECT 
        'missing_fields' as report_type,
        'measure_raw' as group_key,
        'MISSING' as status,
        NULL::VARCHAR as sub_status,
        COUNT(*) as count,
        (SELECT COUNT(*) FROM outcome_raw) as total,
        ROUND(COUNT(*)::numeric / NULLIF((SELECT COUNT(*) FROM outcome_raw), 0) * 100, 2) as percentage,
        NULL::INTEGER as phase_total
    FROM outcome_raw
    WHERE measure_raw IS NULL OR measure_raw = ''

    UNION ALL

    SELECT 
        'missing_fields' as report_type,
        'description_raw' as group_key,
        'MISSING' as status,
        NULL::VARCHAR as sub_status,
        COUNT(*) as count,
        (SELECT COUNT(*) FROM outcome_raw) as total,
        ROUND(COUNT(*)::numeric / NULLIF((SELECT COUNT(*) FROM outcome_raw), 0) * 100, 2) as percentage,
        NULL::INTEGER as phase_total
    FROM outcome_raw
    WHERE description_raw IS NULL OR description_raw = ''

    UNION ALL

    SELECT 
        'missing_fields' as report_type,
        'phase' as group_key,
        'MISSING' as status,
        NULL::VARCHAR as sub_status,
        COUNT(*) as count,
        (SELECT COUNT(*) FROM outcome_normalized) as total,
        ROUND(COUNT(*)::numeric / NULLIF((SELECT COUNT(*) FROM outcome_normalized), 0) * 100, 2) as percentage,
        NULL::INTEGER as phase_total
    FROM outcome_normalized
    WHERE phase IS NULL OR phase = '' OR phase = 'NA'

    UNION ALL

    -- 4. Phase별 Outcome 실패 현황
    SELECT 
        'phase_failure' as report_type,
        pt.phase as group_key,
        'FAILED' as status,
        NULL::VARCHAR as sub_status,
        COALESCE(pf.failed_count, 0) as count,
        (SELECT total_all FROM total_all_outcomes) as total,
        ROUND(COALESCE(pf.failed_count, 0)::numeric / NULLIF((SELECT total_all FROM total_all_outcomes), 0) * 100, 2) as percentage,
        pt.phase_total_count as phase_total
    FROM phase_totals pt
    LEFT JOIN phase_failures pf ON pt.phase = pf.phase

    ORDER BY report_type, group_key, status;
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query)
        return pd.DataFrame(cur.fetchall())

def format_value(value):
    """값 포맷팅"""
    if pd.isna(value) or value == '' or (isinstance(value, str) and value.upper() == 'NULL'):
        return ''
    if isinstance(value, (int, float)):
        if isinstance(value, float):
            return f"{value:.2f}"
        return f"{value:,}"
    return str(value).strip()

def print_console_report(df):
    """콘솔에 보고서 출력"""
    print("\n" + "=" * 80)
    print("📊 Outcome 데이터 정규화 1차 결과")
    print("=" * 80)
    
    # 1. Measure Code 정규화 결과
    print("\n4.1 Measure Code 정규화 결과")
    print("(Primary / Secondary Outcome Name 기준)")
    print("\n| 구분 | 건수 | 비율 (%) |")
    print("|------|------|----------|")
    
    measure_df = df[df['report_type'] == 'measure']
    for outcome_type in ['PRIMARY', 'SECONDARY']:
        type_df = measure_df[measure_df['group_key'] == outcome_type]
        if not type_df.empty:
            success_row = type_df[type_df['status'] == 'SUCCESS']
            failed_row = type_df[type_df['status'] == 'FAILED']
            
            if not success_row.empty:
                print(f"| {outcome_type} 성공 | {int(success_row.iloc[0]['count']):,} | {success_row.iloc[0]['percentage']:.1f} |")
            if not failed_row.empty:
                print(f"| {outcome_type} 실패 | {int(failed_row.iloc[0]['count']):,} | {failed_row.iloc[0]['percentage']:.1f} |")
    
    # 전체 합계
    total_success = measure_df[measure_df['status'] == 'SUCCESS']['count'].sum()
    total_failed = measure_df[measure_df['status'] == 'FAILED']['count'].sum()
    total_all = measure_df[measure_df['status'] == 'TOTAL']['count'].sum()
    
    print(f"\n| 전체 성공 | {int(total_success):,} | {total_success/total_all*100:.1f} |")
    print(f"| 전체 실패 | {int(total_failed):,} | {total_failed/total_all*100:.1f} |")
    
    # 2. Timeframe 정규화 결과
    print("\n4.2 Timeframe 정규화 결과")
    print("\n| 구분 | 건수 | 비율 (%) |")
    print("|------|------|----------|")
    
    timeframe_df = df[df['report_type'] == 'timeframe']
    total_success_row = timeframe_df[timeframe_df['status'] == 'TOTAL_SUCCESS']
    single_success_row = timeframe_df[timeframe_df['status'] == 'SINGLE_SUCCESS']
    multiple_success_row = timeframe_df[timeframe_df['status'] == 'MULTIPLE_SUCCESS']
    total_failed_row = timeframe_df[timeframe_df['status'] == 'TOTAL_FAILED']
    
    if not total_success_row.empty:
        total_success_count = int(total_success_row.iloc[0]['count'])
        total_success_pct = total_success_row.iloc[0]['percentage']
        print(f"| 전체 성공 | {total_success_count:,} | {total_success_pct:.1f} |")
    
    if not single_success_row.empty:
        single_count = int(single_success_row.iloc[0]['count'])
        single_pct = single_success_row.iloc[0]['percentage']
        print(f"| 단일 timeframe 성공 | {single_count:,} | {single_pct:.1f} |")
    
    if not multiple_success_row.empty:
        multiple_count = int(multiple_success_row.iloc[0]['count'])
        multiple_pct = multiple_success_row.iloc[0]['percentage']
        print(f"| 복수 timeframe 성공 | {multiple_count:,} | {multiple_pct:.1f} |")
    
    if not total_failed_row.empty:
        failed_count = int(total_failed_row.iloc[0]['count'])
        failed_pct = total_failed_row.iloc[0]['percentage']
        print(f"| 전체 실패 | {failed_count:,} | {failed_pct:.1f} |")
    
    # 3. 필드 누락 현황
    print("\n5. 데이터 품질 및 누락 현황")
    print("\n5.1 필드 누락 현황")
    print("(Outcome 기준)")
    print("\n| 필드명 | 누락 건수 | 누락 비율 (%) |")
    print("|--------|-----------|---------------|")
    
    missing_df = df[df['report_type'] == 'missing_fields']
    field_names = {
        'time_frame_raw': 'time_frame_raw',
        'measure_raw': 'measure_raw',
        'description_raw': 'description_raw',
        'phase': 'phase',
        'lead_sponsor': 'lead_sponsor'
    }
    
    for field_key, field_name in field_names.items():
        field_row = missing_df[missing_df['group_key'] == field_key]
        if not field_row.empty:
            count = int(field_row.iloc[0]['count'])
            pct = field_row.iloc[0]['percentage']
            print(f"| {field_name} | {count:,} | {pct:.1f} |")
    
    # 4. Phase별 Outcome 실패 현황
    print("\n5.2 Phase별 Outcome 실패 현황 (1차)")
    print("\n| Phase | Phase별 Outcome 건수 | 실패 건수 | 전체 Outcome | 실패율 (%) |")
    print("|-------|---------------------|-----------|-------------|------------|")
    
    phase_df = df[df['report_type'] == 'phase_failure']
    # 모든 phase를 가져와서 정렬 (NA 먼저, 그 다음 알파벳 순)
    all_phases = sorted(phase_df['group_key'].unique().tolist(), key=lambda x: (x != 'NA', x))
    
    # 전체 outcome 수 (첫 번째 행의 total 값 사용)
    total_all = int(phase_df.iloc[0]['total']) if not phase_df.empty else 0
    
    for phase in all_phases:
        phase_row = phase_df[phase_df['group_key'] == phase]
        if not phase_row.empty:
            phase_total = int(phase_row.iloc[0].get('phase_total', phase_row.iloc[0]['total'])) if 'phase_total' in phase_row.iloc[0] else int(phase_row.iloc[0]['total'])
            failed_count = int(phase_row.iloc[0]['count'])
            pct = phase_row.iloc[0]['percentage']
            print(f"| {phase} | {phase_total:,} | {failed_count:,} | {total_all:,} | {pct:.2f} |")

def create_markdown_report(df, output_file='statistics_report.md'):
    """Markdown 보고서 생성"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Outcome 데이터 정규화 1차 결과\n\n")
        f.write(f"생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        
        # 1. Measure Code 정규화 결과
        f.write("## 4. Outcome 데이터 정규화 1차 결과\n\n")
        f.write("### 4.1 Measure Code 정규화 결과\n\n")
        f.write("(Primary / Secondary Outcome Name 기준)\n\n")
        f.write("| 구분 | 건수 | 비율 (%) |\n")
        f.write("|------|------|----------|\n")
        
        measure_df = df[df['report_type'] == 'measure']
        for outcome_type in ['PRIMARY', 'SECONDARY']:
            type_df = measure_df[measure_df['group_key'] == outcome_type]
            if not type_df.empty:
                success_row = type_df[type_df['status'] == 'SUCCESS']
                failed_row = type_df[type_df['status'] == 'FAILED']
                
                if not success_row.empty:
                    f.write(f"| {outcome_type} 성공 | {int(success_row.iloc[0]['count']):,} | {success_row.iloc[0]['percentage']:.1f} |\n")
                if not failed_row.empty:
                    f.write(f"| {outcome_type} 실패 | {int(failed_row.iloc[0]['count']):,} | {failed_row.iloc[0]['percentage']:.1f} |\n")
        
        # 전체 합계
        total_success = measure_df[measure_df['status'] == 'SUCCESS']['count'].sum()
        total_failed = measure_df[measure_df['status'] == 'FAILED']['count'].sum()
        total_all = measure_df[measure_df['status'] == 'TOTAL']['count'].sum()
        
        f.write(f"\n| 전체 성공 | {int(total_success):,} | {total_success/total_all*100:.1f} |\n")
        f.write(f"| 전체 실패 | {int(total_failed):,} | {total_failed/total_all*100:.1f} |\n")
        
        f.write("\nMeasure 명칭의 표현 다양성 및 비정형 서술로 인해 일정 수준의 실패가 발생\n\n")
        f.write("실패 케이스는 이후 보완 작업 대상으로 분류\n\n")
        
        # 2. Timeframe 정규화 결과
        f.write("### 4.2 Timeframe 정규화 결과\n\n")
        f.write("| 구분 | 건수 | 비율 (%) |\n")
        f.write("|------|------|----------|\n")
        
        timeframe_df = df[df['report_type'] == 'timeframe']
        total_success_row = timeframe_df[timeframe_df['status'] == 'TOTAL_SUCCESS']
        single_success_row = timeframe_df[timeframe_df['status'] == 'SINGLE_SUCCESS']
        multiple_success_row = timeframe_df[timeframe_df['status'] == 'MULTIPLE_SUCCESS']
        total_failed_row = timeframe_df[timeframe_df['status'] == 'TOTAL_FAILED']
        
        if not total_success_row.empty:
            total_success_count = int(total_success_row.iloc[0]['count'])
            total_success_pct = total_success_row.iloc[0]['percentage']
            f.write(f"| 전체 성공 | {total_success_count:,} | {total_success_pct:.1f} |\n")
        
        if not single_success_row.empty:
            single_count = int(single_success_row.iloc[0]['count'])
            single_pct = single_success_row.iloc[0]['percentage']
            f.write(f"| 단일 timeframe 성공 | {single_count:,} | {single_pct:.1f} |\n")
        
        if not multiple_success_row.empty:
            multiple_count = int(multiple_success_row.iloc[0]['count'])
            multiple_pct = multiple_success_row.iloc[0]['percentage']
            f.write(f"| 복수 timeframe 성공 | {multiple_count:,} | {multiple_pct:.1f} |\n")
        
        if not total_failed_row.empty:
            failed_count = int(total_failed_row.iloc[0]['count'])
            failed_pct = total_failed_row.iloc[0]['percentage']
            f.write(f"| 전체 실패 | {failed_count:,} | {failed_pct:.1f} |\n")
        
        f.write("\nTimeframe 정규화는 전반적으로 높은 성공률을 보임\n\n")
        f.write("다만 복수 timeframe 성공 케이스는 데이터 구조가 복잡하여 추가적인 검토 및 보완이 필요하다고 판단됨\n\n")
        
        # 3. 필드 누락 현황
        f.write("## 5. 데이터 품질 및 누락 현황\n\n")
        f.write("### 5.1 필드 누락 현황\n\n")
        f.write("(Outcome 기준)\n\n")
        f.write("| 필드명 | 누락 건수 | 누락 비율 (%) |\n")
        f.write("|--------|-----------|---------------|\n")
        
        missing_df = df[df['report_type'] == 'missing_fields']
        field_names = {
            'time_frame_raw': 'time_frame_raw',
            'measure_raw': 'measure_raw',
            'description_raw': 'description_raw',
            'phase': 'phase'
        }
        
        for field_key, field_name in field_names.items():
            field_row = missing_df[missing_df['group_key'] == field_key]
            if not field_row.empty:
                count = int(field_row.iloc[0]['count'])
                pct = field_row.iloc[0]['percentage']
                f.write(f"| {field_name} | {count:,} | {pct:.1f} |\n")
        
        f.write("\n단일 timeframe 실패의 다수는 time_frame_raw 필드 누락으로 인한 실패로 판단됨\n\n")
        
        # 4. Phase별 Outcome 실패 현황
        f.write("### 5.2 Phase별 Outcome 실패 현황 (1차)\n\n")
        f.write("| Phase | Phase별 Outcome 건수 | 실패 건수 | 전체 Outcome | 실패율 (%) |\n")
        f.write("|-------|---------------------|-----------|-------------|------------|\n")
        
        phase_df = df[df['report_type'] == 'phase_failure']
        # 모든 phase를 가져와서 정렬 (NA 먼저, 그 다음 알파벳 순)
        all_phases = sorted(phase_df['group_key'].unique().tolist(), key=lambda x: (x != 'NA', x))
        
        # 전체 outcome 수 (첫 번째 행의 total 값 사용)
        total_all = int(phase_df.iloc[0]['total']) if not phase_df.empty else 0
        
        for phase in all_phases:
            phase_row = phase_df[phase_df['group_key'] == phase]
            if not phase_row.empty:
                phase_total = int(phase_row.iloc[0].get('phase_total', phase_row.iloc[0]['total'])) if 'phase_total' in phase_row.iloc[0] else int(phase_row.iloc[0]['total'])
                failed_count = int(phase_row.iloc[0]['count'])
                pct = phase_row.iloc[0]['percentage']
                f.write(f"| {phase} | {phase_total:,} | {failed_count:,} | {total_all:,} | {pct:.2f} |\n")
        
        f.write("\nPhase 정보가 누락된 경우 실패율이 현저히 높게 나타남\n\n")
        f.write("Phase 누락 데이터는 이후 전처리 대상에서 제외하거나 별도 처리하는 방안 검토 필요\n")
    
    print(f"✅ Markdown 보고서 생성 완료: {output_file}")

def main():
    """메인 함수"""
    print("=" * 80)
    print("통계 보고서 생성")
    print("=" * 80)
    
    conn = get_db_connection()
    
    try:
        print("\n📊 통계 데이터 수집 중...")
        df = execute_statistics_query(conn)
        print(f"   ✅ {len(df)}건 수집 완료")
        
        # 콘솔 출력
        print_console_report(df)
        
        # Markdown 보고서 생성
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'statistics_report_{timestamp}.md'
        create_markdown_report(df, output_file)
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    main()
