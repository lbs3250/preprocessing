"""
Success 테이블에서 Dictionary 매칭 안된 항목 조회
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
    print("Success 테이블에서 Dictionary 매칭 안된 항목 조회")
    print("=" * 80)
    
    # 먼저 success 테이블의 전체 통계 확인
    print("\n[0] Success 테이블 전체 통계")
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(measure_code) as with_measure_code,
            COUNT(*) - COUNT(measure_code) as without_measure_code
        FROM outcome_normalized_success
    """)
    total_stats = cur.fetchone()
    print(f"  총 Success 건수: {total_stats['total']:,}개")
    print(f"  measure_code 있는 건수: {total_stats['with_measure_code']:,}개")
    print(f"  measure_code 없는 건수: {total_stats['without_measure_code']:,}개")
    
    # 1. 통계
    print("\n[1] Dictionary 매칭 안된 항목 통계")
    cur.execute("""
        SELECT 
            COUNT(*) as total_unmatched,
            COUNT(DISTINCT nct_id) as study_count,
            COUNT(DISTINCT measure_clean) as unique_measures,
            COUNT(CASE WHEN outcome_type = 'PRIMARY' THEN 1 END) as primary_count,
            COUNT(CASE WHEN outcome_type = 'SECONDARY' THEN 1 END) as secondary_count
        FROM outcome_normalized_success
        WHERE measure_code IS NULL
    """)
    stats = cur.fetchone()
    print(f"  총 매칭 실패 건수: {stats['total_unmatched']:,}개")
    print(f"  Study 수: {stats['study_count']:,}개")
    print(f"  고유 measure_clean 수: {stats['unique_measures']:,}개")
    print(f"  PRIMARY: {stats['primary_count']:,}개")
    print(f"  SECONDARY: {stats['secondary_count']:,}개")
    
    if stats['total_unmatched'] == 0:
        print("\n[참고] Success 테이블의 모든 항목이 measure_code를 가지고 있습니다.")
        print("      전체 정규화 테이블(outcome_normalized)에서 확인해보겠습니다...")
        
        # 전체 테이블에서 확인
        cur.execute("""
            SELECT 
                COUNT(*) as total_unmatched,
                COUNT(DISTINCT nct_id) as study_count,
                COUNT(DISTINCT measure_clean) as unique_measures
            FROM outcome_normalized
            WHERE measure_code IS NULL
        """)
        all_stats = cur.fetchone()
        print(f"\n  전체 테이블에서 매칭 실패 건수: {all_stats['total_unmatched']:,}개")
        print(f"  Study 수: {all_stats['study_count']:,}개")
        print(f"  고유 measure_clean 수: {all_stats['unique_measures']:,}개")
        
        # Success 테이블에 있는 항목 중 매칭 안된 것 (timeframe은 성공했지만 measure_code는 없는 경우)
        cur.execute("""
            SELECT 
                COUNT(*) as total_unmatched_in_success
            FROM outcome_normalized_success
            WHERE measure_code IS NULL
        """)
        success_unmatched = cur.fetchone()
        print(f"\n  Success 테이블에서 매칭 실패: {success_unmatched['total_unmatched_in_success']:,}개")
        
        conn.close()
        return
    
    # 2. measure_clean 빈도수 (Top 50)
    print("\n[2] Top 50 measure_clean 빈도수")
    cur.execute("""
        SELECT 
            measure_clean,
            COUNT(*) as frequency,
            COUNT(DISTINCT nct_id) as study_count,
            STRING_AGG(DISTINCT measure_abbreviation, ', ' ORDER BY measure_abbreviation) 
                FILTER (WHERE measure_abbreviation IS NOT NULL) as abbreviations
        FROM outcome_normalized_success
        WHERE measure_code IS NULL
          AND measure_clean IS NOT NULL
          AND measure_clean != ''
        GROUP BY measure_clean
        ORDER BY frequency DESC, measure_clean
        LIMIT 50
    """)
    print(f"{'measure_clean':<60} {'빈도수':>10} {'Study':>10} {'약어':>20}")
    print("-" * 100)
    for row in cur.fetchall():
        abbrev = row['abbreviations'] or ''
        if len(abbrev) > 20:
            abbrev = abbrev[:17] + '...'
        measure_clean = row['measure_clean'] or ''
        if len(measure_clean) > 60:
            measure_clean = measure_clean[:57] + '...'
        print(f"{measure_clean:<60} {row['frequency']:>10,} {row['study_count']:>10,} {abbrev:>20}")
    
    # 3. measure_abbreviation 빈도수 (약어는 있는데 매칭 안된 경우)
    print("\n[3] Top 50 measure_abbreviation 빈도수 (약어는 있는데 매칭 안된 경우)")
    cur.execute("""
        SELECT 
            measure_abbreviation,
            COUNT(*) as frequency,
            COUNT(DISTINCT nct_id) as study_count,
            STRING_AGG(DISTINCT measure_clean, ', ' ORDER BY measure_clean) 
                FILTER (WHERE measure_clean IS NOT NULL) as measure_cleans
        FROM outcome_normalized_success
        WHERE measure_code IS NULL
          AND measure_abbreviation IS NOT NULL
          AND measure_abbreviation != ''
        GROUP BY measure_abbreviation
        ORDER BY frequency DESC, measure_abbreviation
        LIMIT 50
    """)
    print(f"{'measure_abbreviation':<30} {'빈도수':>10} {'Study':>10} {'measure_clean':>40}")
    print("-" * 90)
    for row in cur.fetchall():
        measure_cleans = row['measure_cleans'] or ''
        if len(measure_cleans) > 40:
            measure_cleans = measure_cleans[:37] + '...'
        abbrev = row['measure_abbreviation'] or ''
        if len(abbrev) > 30:
            abbrev = abbrev[:27] + '...'
        print(f"{abbrev:<30} {row['frequency']:>10,} {row['study_count']:>10,} {measure_cleans:>40}")
    
    # 4. 전체 리스트 샘플 (처음 20개)
    print("\n[4] 전체 리스트 샘플 (처음 20개)")
    cur.execute("""
        SELECT 
            nct_id,
            outcome_type,
            outcome_order,
            measure_raw,
            measure_clean,
            measure_abbreviation,
            time_frame_raw
        FROM outcome_normalized_success
        WHERE measure_code IS NULL
        ORDER BY measure_clean NULLS LAST, nct_id, outcome_type, outcome_order
        LIMIT 20
    """)
    print(f"{'nct_id':<15} {'type':<10} {'order':<6} {'measure_clean':<40} {'약어':<20} {'time_frame':<30}")
    print("-" * 120)
    for row in cur.fetchall():
        measure_clean = (row['measure_clean'] or '')[:40]
        abbrev = (row['measure_abbreviation'] or '')[:20]
        time_frame = (row['time_frame_raw'] or '')[:30]
        print(f"{row['nct_id']:<15} {row['outcome_type']:<10} {row['outcome_order']:<6} {measure_clean:<40} {abbrev:<20} {time_frame:<30}")
    
    print("\n" + "=" * 80)
    print("완료!")
    print("=" * 80)
    
    conn.close()

if __name__ == '__main__':
    main()
