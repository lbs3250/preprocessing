"""
전체 통계 보고서 생성 스크립트
"""
import psycopg2
from dotenv import load_dotenv
import os
import sys
from psycopg2.extras import RealDictCursor

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

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

def format_number(num):
    """숫자를 포맷팅"""
    if num is None:
        return '0'
    return f"{int(num):,}"

def format_percent(num):
    """퍼센트를 포맷팅"""
    if num is None:
        return '0.0'
    return f"{float(num):.1f}"

def print_section(title):
    """섹션 제목 출력"""
    print(f"\n{'=' * 80}")
    print(f"[{title}]")
    print('=' * 80)

def generate_summary_report():
    """전체 통계 보고서 생성"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # 1. 총 데이터수 대비 성공/실패 통계
        print_section("OUTCOME 단위 통계")
        
        cur.execute("""
            SELECT 
                COUNT(*) as total_outcomes,
                COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 1 END) as outcome_success_count,
                COUNT(CASE WHEN failure_reason = 'MEASURE_CODE_FAILED' OR failure_reason = 'BOTH_FAILED' THEN 1 END) as outcome_failed_count,
                ROUND(COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as outcome_success_rate_percent,
                COUNT(CASE WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 1 END) as timeframe_success_count,
                COUNT(CASE WHEN failure_reason = 'TIMEFRAME_FAILED' OR failure_reason = 'BOTH_FAILED' THEN 1 END) as timeframe_failed_count,
                COUNT(CASE WHEN (failure_reason = 'TIMEFRAME_FAILED' OR failure_reason = 'BOTH_FAILED') 
                           AND (time_frame_raw IS NULL OR time_frame_raw = '') THEN 1 END) as timeframe_failed_null_count,
                COUNT(CASE WHEN (failure_reason = 'TIMEFRAME_FAILED' OR failure_reason = 'BOTH_FAILED') 
                           AND time_frame_raw IS NOT NULL AND time_frame_raw != ''
                           AND NOT (
                               time_frame_raw ~* '(week|weeks|day|days|month|months)\\s+\\d+.*[,\\s]+(and\\s+)?\\d+'
                               OR time_frame_raw ~* '\\d+.*,\\s*\\d+.*(week|weeks|day|days|month|months)'
                               OR time_frame_raw ~* '(week|weeks|day|days|month|months)\\s+\\d+.*and.*\\d+'
                           ) THEN 1 END) as timeframe_failed_single_count,
                COUNT(CASE WHEN (failure_reason = 'TIMEFRAME_FAILED' OR failure_reason = 'BOTH_FAILED') 
                           AND time_frame_raw IS NOT NULL AND time_frame_raw != ''
                           AND (
                               time_frame_raw ~* '(week|weeks|day|days|month|months)\\s+\\d+.*[,\\s]+(and\\s+)?\\d+'
                               OR time_frame_raw ~* '\\d+.*,\\s*\\d+.*(week|weeks|day|days|month|months)'
                               OR time_frame_raw ~* '(week|weeks|day|days|month|months)\\s+\\d+.*and.*\\d+'
                           ) THEN 1 END) as timeframe_failed_multiple_count,
                ROUND(COUNT(CASE WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as timeframe_success_rate_percent,
                COUNT(CASE WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL 
                           AND (time_points IS NULL OR jsonb_array_length(time_points) <= 1) THEN 1 END) as timeframe_single_count,
                COUNT(CASE WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL 
                           AND jsonb_array_length(time_points) > 1 THEN 1 END) as timeframe_multiple_count,
                ROUND(COUNT(CASE WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL 
                           AND (time_points IS NULL OR jsonb_array_length(time_points) <= 1) THEN 1 END)::numeric / 
                      NULLIF(COUNT(CASE WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 1 END), 0) * 100, 2) as timeframe_single_rate_percent,
                ROUND(COUNT(CASE WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL 
                           AND jsonb_array_length(time_points) > 1 THEN 1 END)::numeric / 
                      NULLIF(COUNT(CASE WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 1 END), 0) * 100, 2) as timeframe_multiple_rate_percent,
                COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL 
                           AND time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 1 END) as both_success_count,
                ROUND(COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL 
                             AND time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as both_success_rate_percent,
                COUNT(DISTINCT nct_id) as total_nct_id_count,
                COUNT(DISTINCT CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN nct_id END) as outcome_success_nct_id_count,
                ROUND(COUNT(DISTINCT CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN nct_id END)::numeric / COUNT(DISTINCT nct_id) * 100, 2) as outcome_success_nct_id_rate_percent,
                COUNT(DISTINCT CASE WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN nct_id END) as timeframe_success_nct_id_count,
                ROUND(COUNT(DISTINCT CASE WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN nct_id END)::numeric / COUNT(DISTINCT nct_id) * 100, 2) as timeframe_success_nct_id_rate_percent,
                COUNT(DISTINCT CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL 
                                AND time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN nct_id END) as both_success_nct_id_count,
                ROUND(COUNT(DISTINCT CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL 
                              AND time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN nct_id END)::numeric / COUNT(DISTINCT nct_id) * 100, 2) as both_success_nct_id_rate_percent
            FROM outcome_normalized
        """)
        
        stats = cur.fetchone()
        
        total = stats['total_outcomes']
        print(f"  전체 Outcomes: {format_number(total)}건")
        print(f"  완벽 정규화 Outcomes: {format_number(stats['both_success_count'])}건 ({format_percent(stats['both_success_rate_percent'])}%)")
        print(f"  정규화 실패 Outcomes: {format_number(total - stats['both_success_count'])}건 ({format_percent(100 - stats['both_success_rate_percent'])}%)")
        print()
        print(f"  [Measure Code 정규화]")
        print(f"    성공: {format_number(stats['outcome_success_count'])}건 ({format_percent(stats['outcome_success_rate_percent'])}%)")
        print(f"    실패: {format_number(stats['outcome_failed_count'])}건 ({format_percent(100 - stats['outcome_success_rate_percent'])}%)")
        print()
        print(f"  [Timeframe 정규화]")
        print(f"    성공: {format_number(stats['timeframe_success_count'])}건 ({format_percent(stats['timeframe_success_rate_percent'])}%)")
        print(f"      - 단일 timeframe: {format_number(stats['timeframe_single_count'])}건 ({format_percent(stats['timeframe_single_rate_percent'])}%)")
        print(f"      - 복수 timeframe: {format_number(stats['timeframe_multiple_count'])}건 ({format_percent(stats['timeframe_multiple_rate_percent'])}%)")
        print(f"    실패: {format_number(stats['timeframe_failed_count'])}건 ({format_percent(100 - stats['timeframe_success_rate_percent'])}%)")
        failed_total = stats['timeframe_failed_count'] or 1
        print(f"      - NULL로 인한 실패: {format_number(stats['timeframe_failed_null_count'])}건 ({format_percent((stats['timeframe_failed_null_count'] or 0) / failed_total * 100)}%)")
        print(f"      - 단일 timeframe 실패: {format_number(stats['timeframe_failed_single_count'])}건 ({format_percent((stats['timeframe_failed_single_count'] or 0) / failed_total * 100)}%)")
        print(f"      - 복수 timeframe 실패: {format_number(stats['timeframe_failed_multiple_count'])}건 ({format_percent((stats['timeframe_failed_multiple_count'] or 0) / failed_total * 100)}%)")
        
        # 2. PRIMARY/SECONDARY 타입별 통계
        print_section("PRIMARY/SECONDARY 타입별 통계")
        
        cur.execute("""
            SELECT 
                outcome_type,
                COUNT(*) as total,
                COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL 
                          AND time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 1 END) as success_count,
                COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 1 END) as measure_success_count,
                COUNT(CASE WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 1 END) as timeframe_success_count,
                COUNT(CASE WHEN failure_reason IS NOT NULL THEN 1 END) as failed_count
            FROM outcome_normalized
            GROUP BY outcome_type
            ORDER BY outcome_type
        """)
        
        type_stats = cur.fetchall()
        
        print(f"  완벽 정규화:")
        for row in type_stats:
            print(f"    {row['outcome_type']}: {format_number(row['success_count'])}건")
        
        print(f"  정규화 실패:")
        for row in type_stats:
            print(f"    {row['outcome_type']}: {format_number(row['failed_count'])}건")
        
        print(f"  [Measure Code 정규화]")
        for row in type_stats:
            print(f"    {row['outcome_type']}: {format_number(row['measure_success_count'])}건 ({format_percent(row['measure_success_count'] / row['total'] * 100)}%)")
        
        print(f"  [Timeframe 정규화]")
        for row in type_stats:
            print(f"    {row['outcome_type']}: {format_number(row['timeframe_success_count'])}건 ({format_percent(row['timeframe_success_count'] / row['total'] * 100)}%)")
        
        # 3. 누락 필드 비율
        print_section("누락 필드 비율 (Outcome 기준)")
        
        cur.execute("""
            SELECT 
                COUNT(*) as total_outcomes,
                COUNT(CASE WHEN n.time_frame_raw IS NULL OR n.time_frame_raw = '' THEN 1 END) as timeframe_null_count,
                ROUND(COUNT(CASE WHEN n.time_frame_raw IS NULL OR n.time_frame_raw = '' THEN 1 END)::numeric / COUNT(*) * 100, 2) as timeframe_null_rate_percent,
                COUNT(CASE WHEN n.measure_raw IS NULL OR n.measure_raw = '' THEN 1 END) as measure_raw_null_count,
                ROUND(COUNT(CASE WHEN n.measure_raw IS NULL OR n.measure_raw = '' THEN 1 END)::numeric / COUNT(*) * 100, 2) as measure_raw_null_rate_percent,
                COUNT(CASE WHEN n.description_raw IS NULL OR n.description_raw = '' THEN 1 END) as description_raw_null_count,
                ROUND(COUNT(CASE WHEN n.description_raw IS NULL OR n.description_raw = '' THEN 1 END)::numeric / COUNT(*) * 100, 2) as description_raw_null_rate_percent,
                COUNT(CASE WHEN n.phase IS NULL OR n.phase = 'NA' THEN 1 END) as phase_null_or_na_count,
                ROUND(COUNT(CASE WHEN n.phase IS NULL OR n.phase = 'NA' THEN 1 END)::numeric / COUNT(*) * 100, 2) as phase_null_or_na_rate_percent,
                COUNT(CASE WHEN sp.nct_id IS NULL THEN 1 END) as lead_sponsor_null_count,
                ROUND(COUNT(CASE WHEN sp.nct_id IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as lead_sponsor_null_rate_percent
            FROM outcome_normalized n
            LEFT JOIN study_party_raw sp ON n.nct_id = sp.nct_id AND sp.party_type = 'LEAD_SPONSOR'
        """)
        
        null_stats = cur.fetchone()
        
        print(f"  time_frame_raw 누락: {format_number(null_stats['timeframe_null_count'])}건 ({format_percent(null_stats['timeframe_null_rate_percent'])}%)")
        print(f"  measure_raw 누락: {format_number(null_stats['measure_raw_null_count'])}건 ({format_percent(null_stats['measure_raw_null_rate_percent'])}%)")
        print(f"  description_raw 누락: {format_number(null_stats['description_raw_null_count'])}건 ({format_percent(null_stats['description_raw_null_rate_percent'])}%)")
        print(f"  phase 누락 (NULL 또는 NA): {format_number(null_stats['phase_null_or_na_count'])}건 ({format_percent(null_stats['phase_null_or_na_rate_percent'])}%)")
        print(f"  lead_sponsor 누락: {format_number(null_stats['lead_sponsor_null_count'])}건 ({format_percent(null_stats['lead_sponsor_null_rate_percent'])}%)")
        
        print("\n" + "=" * 80)
        print("[OK] 보고서 생성 완료!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    generate_summary_report()

