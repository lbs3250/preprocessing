"""
방금 추가된 약어 항목들을 사전에서 삭제하는 스크립트

add_numbered_abbreviations.py로 추가된 항목들을 롤백
"""

import os
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


def remove_added_abbreviations(conn):
    """
    방금 추가된 약어 항목들을 삭제
    
    add_numbered_abbreviations.py에서 추가한 항목들
    """
    
    # 삭제할 measure_code 목록
    codes_to_remove = [
        'ADAS_COG_11',
        'ADAS_COG_12',
        'ADAS_COG_13',
        'ADAS_COG_14',
        'GDS_15',
        'TEAES',
        'TOPS',
        'CIA',
        'AD',
        'FAB',
        'NDEV',
        'ADCS_CGIC',
        'COGSTATE',
        'BPSD',
        'PMC',
        'CNS_VS',
        'SAES',
        'ACU193',
        'PSS',
        'MPFC',
        'CGI_S',
        'BNT',
        'ADCS_IADL',
        'PANAS',
        'FER',
        'SAND',
        'CL',
        'BDNF',
        'VSS',
        'PVT',
        'SPPB',
        'ADAS',
        'MOS_SS',
        'TUG',
        'BMI',
    ]
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        deleted_count = 0
        not_found_count = 0
        
        for measure_code in codes_to_remove:
            # 존재하는지 확인
            cur.execute("""
                SELECT measure_code 
                FROM outcome_measure_dict 
                WHERE measure_code = %s
            """, (measure_code,))
            
            if cur.fetchone():
                # 삭제 (외래키 제약조건 때문에 outcome_normalized의 measure_code는 NULL로 설정됨)
                cur.execute("""
                    DELETE FROM outcome_measure_dict
                    WHERE measure_code = %s
                """, (measure_code,))
                deleted_count += 1
                print(f"  [DELETE] {measure_code}")
            else:
                not_found_count += 1
                print(f"  [NOT FOUND] {measure_code}")
        
        conn.commit()
        
        print(f"\n[OK] 완료:")
        print(f"  삭제: {deleted_count}개")
        print(f"  없음: {not_found_count}개")
        
        # 삭제 후 outcome_normalized에서 영향받은 레코드 확인
        cur.execute("""
            SELECT COUNT(*) as count
            FROM outcome_normalized
            WHERE measure_code IS NULL
              AND measure_abbreviation IS NOT NULL
        """)
        affected = cur.fetchone()['count']
        print(f"\n  영향받은 outcome_normalized 레코드: {affected:,}건 (measure_code가 NULL로 설정됨)")


def main():
    print("=" * 80)
    print("추가된 약어 항목 삭제 (롤백)")
    print("=" * 80)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        print("\n[1] 추가된 약어 항목 삭제 중...")
        remove_added_abbreviations(conn)
        
        # 통계 출력
        print("\n" + "=" * 80)
        print("사전 통계")
        print("=" * 80)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) as total FROM outcome_measure_dict")
            total = cur.fetchone()['total']
            print(f"총 Dictionary 항목 수: {total:,}개")
        
        conn.close()
        
        print("\n" + "=" * 80)
        print("[OK] 완료!")
        print("=" * 80)
        print("\n참고: outcome_normalized 테이블의 measure_code는 외래키 제약조건에 의해")
        print("      자동으로 NULL로 설정되었습니다. 정규화를 다시 실행하면")
        print("      필터링된 약어로 다시 매칭을 시도합니다.")
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


