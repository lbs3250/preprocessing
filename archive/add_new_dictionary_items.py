"""
dic.csv에서 DB에 없는 항목만 추가하는 스크립트
"""
import csv
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# DB 연결 설정
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'clinicaltrials'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}


def get_db_connection():
    """DB 연결"""
    return psycopg2.connect(**DB_CONFIG)


def get_existing_measure_codes(conn):
    """DB에 이미 존재하는 measure_code 목록 조회"""
    with conn.cursor() as cur:
        cur.execute("SELECT measure_code FROM outcome_measure_dict")
        return set(row[0] for row in cur.fetchall())


def add_new_items(conn, csv_file='dic.csv'):
    """dic.csv에서 DB에 없는 항목만 추가"""
    print("=" * 60)
    print("Dictionary 항목 추가 시작")
    print("=" * 60)
    
    # 기존 measure_code 조회
    print("\n[1] 기존 Dictionary 조회 중...")
    existing_codes = get_existing_measure_codes(conn)
    print(f"  기존 항목 수: {len(existing_codes):,}개")
    
    # CSV 파일 읽기
    print(f"\n[2] {csv_file} 파일 읽기 중...")
    new_items = []
    skipped_items = []
    csv_total = 0
    
    # 파일을 직접 읽어서 모든 행 처리 (헤더 포함)
    with open(csv_file, 'r', encoding='utf-8') as f:
        # 모든 행을 한 번에 읽기
        all_rows = list(csv.reader(f))
    
    seen_codes = set()  # 중복 제거용
    row_num = 0
    
    for row in all_rows:
        row_num += 1
        
        # 헤더 행 감지 (첫 번째 컬럼이 'measure_code'인 경우)
        # 두 번째 헤더도 처리할 수 있도록 계속 진행
        if row and len(row) > 0 and row[0].strip().lower() == 'measure_code':
            continue  # 헤더는 스킵하고 다음 행으로
        
        # 빈 행 스킵
        if not row or len(row) == 0:
            continue
        
        # 컬럼 개수 확인
        if len(row) < 2:
            continue
        
        measure_code = row[0].strip() if len(row) > 0 and row[0] else ''
        canonical_name = row[1].strip() if len(row) > 1 and row[1] else ''
        
        # 빈 행 스킵
        if not measure_code or not canonical_name:
            continue
        
        csv_total += 1
        
        # 이미 처리한 항목 스킵 (CSV에 중복이 있을 수 있음)
        if measure_code in seen_codes:
            if measure_code not in skipped_items:
                skipped_items.append(measure_code)
            continue
        seen_codes.add(measure_code)
        
        abbreviation = row[2].strip() if len(row) > 2 and row[2] else None
        domain = row[3].strip() if len(row) > 3 and row[3] else None
        typical_role = row[4].strip() if len(row) > 4 and row[4] else None
        keywords = row[5].strip() if len(row) > 5 and row[5] else None
        
        # 빈 문자열을 None으로 변환
        abbreviation = abbreviation if abbreviation else None
        domain = domain if domain else None
        typical_role = typical_role if typical_role else None
        keywords = keywords if keywords else None
        
        if measure_code in existing_codes:
            skipped_items.append(measure_code)
        else:
            new_items.append({
                'measure_code': measure_code,
                'canonical_name': canonical_name,
                'abbreviation': abbreviation,
                'domain': domain,
                'typical_role': typical_role,
                'keywords': keywords
            })
    
    print(f"  CSV 총 행 수: {row_num:,}개")
    print(f"  CSV 총 항목 수: {csv_total:,}개")
    print(f"  기존 항목 (스킵): {len(skipped_items):,}개")
    print(f"  신규 항목 (추가 예정): {len(new_items):,}개")
    
    if not new_items:
        print("\n[OK] 추가할 항목이 없습니다.")
        return
    
    # 신규 항목 출력 (인코딩 문제로 일부만 출력)
    print(f"\n[3] 신규 항목 목록 (처음 10개만):")
    for i, item in enumerate(new_items[:10], 1):
        try:
            print(f"  {i:2d}. {item['measure_code']:20s} - {item['canonical_name'][:50]}")
        except:
            print(f"  {i:2d}. {item['measure_code']:20s}")
    
    # DB에 추가
    print(f"\n[4] DB에 추가 중...")
    with conn.cursor() as cur:
        added_count = 0
        for item in new_items:
            try:
                cur.execute("""
                    INSERT INTO outcome_measure_dict 
                    (measure_code, canonical_name, abbreviation, domain, keywords)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (measure_code) DO NOTHING
                """, (
                    item['measure_code'],
                    item['canonical_name'],
                    item['abbreviation'],
                    item['domain'],
                    item['keywords']
                ))
                if cur.rowcount > 0:
                    added_count += 1
            except Exception as e:
                print(f"  [ERROR] {item['measure_code']} 추가 실패: {e}")
        
        conn.commit()
    
    print(f"\n[OK] {added_count:,}개 항목 추가 완료!")
    print("=" * 60)


def main():
    """메인 함수"""
    try:
        conn = get_db_connection()
        add_new_items(conn)
        conn.close()
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
