"""
전체 정규화 테이블에서 Dictionary 매칭 안된 항목 조회
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'clinicaltrials'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("=" * 80)
    print("전체 정규화 테이블에서 Dictionary 매칭 안된 항목 조회")
    print("=" * 80)
    
    # 1. 통계
    print("\n[1] Dictionary 매칭 안된 항목 통계")
    cur.execute("""
        SELECT 
            COUNT(*) as total_unmatched,
            COUNT(DISTINCT nct_id) as study_count,
            COUNT(DISTINCT measure_clean) as unique_measures,
            COUNT(CASE WHEN outcome_type = 'PRIMARY' THEN 1 END) as primary_count,
            COUNT(CASE WHEN outcome_type = 'SECONDARY' THEN 1 END) as secondary_count,
            COUNT(CASE WHEN failure_reason IS NULL THEN 1 END) as timeframe_success_count
        FROM outcome_normalized
        WHERE measure_code IS NULL
    """)
    stats = cur.fetchone()
    print(f"  총 매칭 실패 건수: {stats['total_unmatched']:,}개")
    print(f"  Study 수: {stats['study_count']:,}개")
    print(f"  고유 measure_clean 수: {stats['unique_measures']:,}개")
    print(f"  PRIMARY: {stats['primary_count']:,}개")
    print(f"  SECONDARY: {stats['secondary_count']:,}개")
    print(f"  TimeFrame 성공 (measure_code만 없는 경우): {stats['timeframe_success_count']:,}개")
    
    # 2. measure_clean 빈도수 (Top 50)
    print("\n[2] Top 50 measure_clean 빈도수")
    cur.execute("""
        SELECT 
            measure_clean,
            COUNT(*) as frequency,
            COUNT(DISTINCT nct_id) as study_count,
            COUNT(CASE WHEN failure_reason IS NULL THEN 1 END) as timeframe_success,
            STRING_AGG(DISTINCT measure_abbreviation, ', ' ORDER BY measure_abbreviation) 
                FILTER (WHERE measure_abbreviation IS NOT NULL) as abbreviations
        FROM outcome_normalized
        WHERE measure_code IS NULL
          AND measure_clean IS NOT NULL
          AND measure_clean != ''
        GROUP BY measure_clean
        ORDER BY frequency DESC, measure_clean
        LIMIT 50
    """)
    print(f"{'measure_clean':<60} {'빈도수':>10} {'Study':>10} {'TF성공':>10} {'약어':>20}")
    print("-" * 110)
    for row in cur.fetchall():
        abbrev = row['abbreviations'] or ''
        if len(abbrev) > 20:
            abbrev = abbrev[:17] + '...'
        measure_clean = row['measure_clean'] or ''
        if len(measure_clean) > 60:
            measure_clean = measure_clean[:57] + '...'
        print(f"{measure_clean:<60} {row['frequency']:>10,} {row['study_count']:>10,} {row['timeframe_success']:>10,} {abbrev:>20}")
    
    # 3. measure_abbreviation 빈도수 (약어는 있는데 매칭 안된 경우)
    print("\n[3] Top 50 measure_abbreviation 빈도수 (약어는 있는데 매칭 안된 경우)")
    cur.execute("""
        SELECT 
            measure_abbreviation,
            COUNT(*) as frequency,
            COUNT(DISTINCT nct_id) as study_count,
            COUNT(CASE WHEN failure_reason IS NULL THEN 1 END) as timeframe_success,
            STRING_AGG(DISTINCT measure_clean, ', ' ORDER BY measure_clean) 
                FILTER (WHERE measure_clean IS NOT NULL) as measure_cleans
        FROM outcome_normalized
        WHERE measure_code IS NULL
          AND measure_abbreviation IS NOT NULL
          AND measure_abbreviation != ''
        GROUP BY measure_abbreviation
        ORDER BY frequency DESC, measure_abbreviation
        LIMIT 50
    """)
    print(f"{'measure_abbreviation':<30} {'빈도수':>10} {'Study':>10} {'TF성공':>10} {'measure_clean':>40}")
    print("-" * 100)
    for row in cur.fetchall():
        measure_cleans = row['measure_cleans'] or ''
        if len(measure_cleans) > 40:
            measure_cleans = measure_cleans[:37] + '...'
        abbrev = row['measure_abbreviation'] or ''
        if len(abbrev) > 30:
            abbrev = abbrev[:27] + '...'
        print(f"{abbrev:<30} {row['frequency']:>10,} {row['study_count']:>10,} {row['timeframe_success']:>10,} {measure_cleans:>40}")
    
    # 4. TimeFrame 성공했지만 measure_code가 없는 경우 (Success 테이블에 들어갈 수 있었던 항목들)
    print("\n[4] TimeFrame 성공했지만 measure_code가 없는 항목 (Success 가능했던 항목)")
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT nct_id) as study_count,
            COUNT(DISTINCT measure_clean) as unique_measures
        FROM outcome_normalized
        WHERE measure_code IS NULL
          AND failure_reason IS NULL
    """)
    tf_success = cur.fetchone()
    print(f"  총 건수: {tf_success['total']:,}개")
    print(f"  Study 수: {tf_success['study_count']:,}개")
    print(f"  고유 measure_clean 수: {tf_success['unique_measures']:,}개")
    
    # 5. 전체 리스트 샘플 (처음 30개)
    print("\n[5] 전체 리스트 샘플 (처음 30개)")
    cur.execute("""
        SELECT 
            nct_id,
            outcome_type,
            outcome_order,
            measure_raw,
            measure_clean,
            measure_abbreviation,
            time_frame_raw,
            failure_reason
        FROM outcome_normalized
        WHERE measure_code IS NULL
        ORDER BY failure_reason NULLS FIRST, measure_clean NULLS LAST, nct_id, outcome_type, outcome_order
        LIMIT 30
    """)
    print(f"{'nct_id':<15} {'type':<10} {'order':<6} {'measure_clean':<35} {'약어':<15} {'TF':<10} {'time_frame':<25}")
    print("-" * 120)
    for row in cur.fetchall():
        measure_clean = (row['measure_clean'] or '')[:35]
        abbrev = (row['measure_abbreviation'] or '')[:15]
        tf_status = '성공' if row['failure_reason'] is None else '실패'
        time_frame = (row['time_frame_raw'] or '')[:25]
        print(f"{row['nct_id']:<15} {row['outcome_type']:<10} {row['outcome_order']:<6} {measure_clean:<35} {abbrev:<15} {tf_status:<10} {time_frame:<25}")
    
    print("\n" + "=" * 80)
    print("완료!")
    print("=" * 80)
    
    conn.close()

if __name__ == '__main__':
    main()






