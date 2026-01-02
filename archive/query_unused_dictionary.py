"""
Dictionary 테이블에서 한 번도 사용되지 않은 항목 조회
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
    print("Dictionary 테이블에서 한 번도 사용되지 않은 항목 조회")
    print("=" * 80)
    
    # 1. 전체 Dictionary 통계
    print("\n[1] Dictionary 전체 통계")
    cur.execute("""
        SELECT 
            COUNT(*) as total_dict_items,
            COUNT(DISTINCT domain) as unique_domains
        FROM outcome_measure_dict
    """)
    dict_stats = cur.fetchone()
    print(f"  총 Dictionary 항목 수: {dict_stats['total_dict_items']:,}개")
    print(f"  Domain 수: {dict_stats['unique_domains']:,}개")
    
    # 2. 사용된 Dictionary 항목 통계
    print("\n[2] 사용된 Dictionary 항목 통계")
    cur.execute("""
        SELECT 
            COUNT(DISTINCT measure_code) as used_count
        FROM outcome_normalized
        WHERE measure_code IS NOT NULL
    """)
    used_stats = cur.fetchone()
    print(f"  사용된 Dictionary 항목 수: {used_stats['used_count']:,}개")
    
    # 3. 사용되지 않은 Dictionary 항목 조회
    print("\n[3] 사용되지 않은 Dictionary 항목 목록")
    cur.execute("""
        SELECT 
            d.measure_code,
            d.canonical_name,
            d.abbreviation,
            d.domain,
            d.keywords
        FROM outcome_measure_dict d
        LEFT JOIN outcome_normalized n ON d.measure_code = n.measure_code
        WHERE n.measure_code IS NULL
        ORDER BY d.domain, d.measure_code
    """)
    unused_items = cur.fetchall()
    print(f"  사용되지 않은 Dictionary 항목 수: {len(unused_items):,}개")
    
    if len(unused_items) == 0:
        print("\n  [OK] 모든 Dictionary 항목이 사용되었습니다!")
    else:
        print(f"\n  {'measure_code':<25} {'canonical_name':<50} {'domain':<15} {'abbreviation':<20}")
        print("-" * 110)
        for item in unused_items:
            canonical = item['canonical_name'] or ''
            if len(canonical) > 50:
                canonical = canonical[:47] + '...'
            abbrev = item['abbreviation'] or ''
            if len(abbrev) > 20:
                abbrev = abbrev[:17] + '...'
            print(f"  {item['measure_code']:<25} {canonical:<50} {item['domain'] or 'NULL':<15} {abbrev:<20}")
    
    # 4. Domain별 사용되지 않은 항목 통계
    print("\n[4] Domain별 사용되지 않은 항목 통계")
    cur.execute("""
        SELECT 
            d.domain,
            COUNT(*) as unused_count,
            COUNT(CASE WHEN d.abbreviation IS NOT NULL THEN 1 END) as with_abbreviation,
            COUNT(CASE WHEN d.keywords IS NOT NULL THEN 1 END) as with_keywords
        FROM outcome_measure_dict d
        LEFT JOIN outcome_normalized n ON d.measure_code = n.measure_code
        WHERE n.measure_code IS NULL
        GROUP BY d.domain
        ORDER BY unused_count DESC
    """)
    print(f"  {'Domain':<20} {'미사용':>10} {'약어있음':>10} {'키워드있음':>12}")
    print("-" * 55)
    for row in cur.fetchall():
        domain = row['domain'] or 'NULL'
        print(f"  {domain:<20} {row['unused_count']:>10,} {row['with_abbreviation']:>10,} {row['with_keywords']:>12,}")
    
    # 5. 사용 빈도가 낮은 Dictionary 항목 (1회만 사용된 항목)
    print("\n[5] 사용 빈도가 낮은 Dictionary 항목 (5회 이하)")
    cur.execute("""
        SELECT 
            d.measure_code,
            d.canonical_name,
            d.domain,
            COUNT(n.outcome_id) as usage_count
        FROM outcome_measure_dict d
        LEFT JOIN outcome_normalized n ON d.measure_code = n.measure_code
        GROUP BY d.measure_code, d.canonical_name, d.domain
        HAVING COUNT(n.outcome_id) <= 5
        ORDER BY usage_count ASC, d.domain, d.measure_code
    """)
    low_usage = cur.fetchall()
    print(f"  사용 빈도가 낮은 항목 수: {len(low_usage):,}개")
    print(f"\n  {'measure_code':<25} {'canonical_name':<45} {'domain':<15} {'사용횟수':>10}")
    print("-" * 95)
    for item in low_usage[:30]:  # 처음 30개만 출력
        canonical = item['canonical_name'] or ''
        if len(canonical) > 45:
            canonical = canonical[:42] + '...'
        print(f"  {item['measure_code']:<25} {canonical:<45} {item['domain'] or 'NULL':<15} {item['usage_count']:>10,}")
    
    # 6. 사용 빈도가 높은 Dictionary 항목 (참고용)
    print("\n[6] 사용 빈도가 높은 Dictionary 항목 (Top 10)")
    cur.execute("""
        SELECT 
            d.measure_code,
            d.canonical_name,
            d.domain,
            COUNT(n.outcome_id) as usage_count
        FROM outcome_measure_dict d
        LEFT JOIN outcome_normalized n ON d.measure_code = n.measure_code
        GROUP BY d.measure_code, d.canonical_name, d.domain
        HAVING COUNT(n.outcome_id) > 0
        ORDER BY usage_count DESC
        LIMIT 10
    """)
    high_usage = cur.fetchall()
    print(f"  {'measure_code':<25} {'canonical_name':<45} {'domain':<15} {'사용횟수':>10}")
    print("-" * 95)
    for item in high_usage:
        canonical = item['canonical_name'] or ''
        if len(canonical) > 45:
            canonical = canonical[:42] + '...'
        print(f"  {item['measure_code']:<25} {canonical:<45} {item['domain'] or 'NULL':<15} {item['usage_count']:>10,}")
    
    print("\n" + "=" * 80)
    print("완료!")
    print("=" * 80)
    
    conn.close()

if __name__ == '__main__':
    main()






