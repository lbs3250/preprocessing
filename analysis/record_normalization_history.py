"""
정규화 실행 이력 기록 스크립트

정규화 실행 후 자동으로 이력을 기록하여
정규화 단계별 성공률 변화를 추적합니다.
"""

import os
import json
from datetime import datetime
from typing import Dict, Optional
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


def get_db_connection():
    """PostgreSQL 연결 생성"""
    return psycopg2.connect(**DB_CONFIG)


def create_history_table(conn):
    """정규화 이력 테이블 생성"""
    with conn.cursor() as cur:
        # 전체 통계 이력 테이블
        cur.execute("""
            CREATE TABLE IF NOT EXISTS normalization_history (
                history_id BIGSERIAL PRIMARY KEY,
                processing_round VARCHAR(20) NOT NULL,
                execution_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_outcomes INTEGER NOT NULL,
                success_count INTEGER NOT NULL,
                failed_count INTEGER NOT NULL,
                success_rate NUMERIC(5, 2) NOT NULL,
                notes TEXT,
                config_snapshot JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_normalization_history_round 
                ON normalization_history(processing_round);
            CREATE INDEX IF NOT EXISTS idx_normalization_history_date 
                ON normalization_history(execution_date);
        """)
        
        # Study별 이력 테이블
        cur.execute("""
            CREATE TABLE IF NOT EXISTS study_normalization_history (
                history_id BIGSERIAL PRIMARY KEY,
                processing_round VARCHAR(20) NOT NULL,
                execution_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                nct_id VARCHAR(20) NOT NULL,
                total_outcomes INTEGER NOT NULL,
                success_count INTEGER NOT NULL,
                failed_count INTEGER NOT NULL,
                success_rate NUMERIC(5, 2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT unique_study_round UNIQUE (processing_round, nct_id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_study_normalization_history_round 
                ON study_normalization_history(processing_round);
            CREATE INDEX IF NOT EXISTS idx_study_normalization_history_nct_id 
                ON study_normalization_history(nct_id);
            CREATE INDEX IF NOT EXISTS idx_study_normalization_history_date 
                ON study_normalization_history(execution_date);
            CREATE INDEX IF NOT EXISTS idx_study_normalization_history_success_rate 
                ON study_normalization_history(success_rate);
        """)
        conn.commit()


def get_current_statistics(conn) -> Dict:
    """현재 정규화 통계 조회"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                COUNT(*) as total_outcomes,
                COUNT(*) FILTER (WHERE measure_code IS NOT NULL AND failure_reason IS NULL) as success_count,
                COUNT(*) FILTER (WHERE measure_code IS NULL OR failure_reason IS NOT NULL) as failed_count
            FROM outcome_normalized
        """)
        stats = cur.fetchone()
        
        total = stats['total_outcomes']
        success = stats['success_count']
        failed = stats['failed_count']
        success_rate = (success / total * 100) if total > 0 else 0.0
        
        return {
            'total_outcomes': total,
            'success_count': success,
            'failed_count': failed,
            'success_rate': round(success_rate, 2)
        }


def get_failure_reason_stats(conn) -> Dict:
    """실패 원인별 통계"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                COALESCE(failure_reason, 'SUCCESS') as failure_reason,
                COUNT(*) as count
            FROM outcome_normalized
            GROUP BY failure_reason
            ORDER BY count DESC
        """)
        return {row['failure_reason']: row['count'] for row in cur.fetchall()}


def get_study_statistics(conn) -> list:
    """Study별 정규화 통계 조회"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                nct_id,
                COUNT(*) as total_outcomes,
                COUNT(*) FILTER (WHERE measure_code IS NOT NULL AND failure_reason IS NULL) as success_count,
                COUNT(*) FILTER (WHERE measure_code IS NULL OR failure_reason IS NOT NULL) as failed_count
            FROM outcome_normalized
            GROUP BY nct_id
            ORDER BY nct_id
        """)
        studies = cur.fetchall()
        
        # 성공률 계산
        result = []
        for study in studies:
            total = study['total_outcomes']
            success = study['success_count']
            failed = study['failed_count']
            success_rate = (success / total * 100) if total > 0 else 0.0
            
            result.append({
                'nct_id': study['nct_id'],
                'total_outcomes': total,
                'success_count': success,
                'failed_count': failed,
                'success_rate': round(success_rate, 2)
            })
        
        return result


def get_config_snapshot() -> Dict:
    """현재 설정 스냅샷 생성"""
    # 정규식 패턴 정보 등 추후 추가 가능
    return {
        'timestamp': datetime.now().isoformat(),
        'normalization_version': '1.0',
        'note': 'Config snapshot placeholder'
    }


def record_history(
    conn,
    processing_round: str,
    notes: Optional[str] = None,
    config_snapshot: Optional[Dict] = None
):
    """
    정규화 실행 이력 기록
    
    Args:
        conn: 데이터베이스 연결
        processing_round: 정규화 단계 ('ROUND1', 'ROUND2', 'ROUND3' 등)
        notes: 추가 메모
        config_snapshot: 설정 스냅샷 (JSON)
    """
    # 테이블 생성 확인
    create_history_table(conn)
    
    # 현재 통계 조회
    stats = get_current_statistics(conn)
    failure_stats = get_failure_reason_stats(conn)
    
    # 설정 스냅샷
    if config_snapshot is None:
        config_snapshot = get_config_snapshot()
    
    # 실패 원인별 통계 추가
    config_snapshot['failure_reason_stats'] = failure_stats
    
    # 이력 기록
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO normalization_history (
                processing_round,
                total_outcomes,
                success_count,
                failed_count,
                success_rate,
                notes,
                config_snapshot
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            processing_round,
            stats['total_outcomes'],
            stats['success_count'],
            stats['failed_count'],
            stats['success_rate'],
            notes,
            json.dumps(config_snapshot)
        ))
        conn.commit()
    
    print(f"\n[OK] 정규화 이력 기록 완료: {processing_round}")
    print(f"  전체 Outcomes: {stats['total_outcomes']:,}건")
    print(f"  성공: {stats['success_count']:,}건 ({stats['success_rate']:.2f}%)")
    print(f"  실패: {stats['failed_count']:,}건 ({100 - stats['success_rate']:.2f}%)")


def record_study_history(conn, processing_round: str):
    """
    Study별 정규화 실행 이력 기록
    
    Args:
        conn: 데이터베이스 연결
        processing_round: 정규화 단계 ('ROUND1', 'ROUND2', 'ROUND3' 등)
    """
    # 테이블 생성 확인
    create_history_table(conn)
    
    # Study별 통계 조회
    study_stats = get_study_statistics(conn)
    
    if not study_stats:
        print("[WARN] Study별 통계가 없습니다.")
        return
    
    # Study별 이력 기록
    with conn.cursor() as cur:
        # 기존 동일 round 데이터 삭제 (재실행 시)
        cur.execute("""
            DELETE FROM study_normalization_history 
            WHERE processing_round = %s
        """, (processing_round,))
        
        # 배치 삽입
        insert_query = """
            INSERT INTO study_normalization_history (
                processing_round,
                nct_id,
                total_outcomes,
                success_count,
                failed_count,
                success_rate
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (processing_round, nct_id) 
            DO UPDATE SET
                execution_date = CURRENT_TIMESTAMP,
                total_outcomes = EXCLUDED.total_outcomes,
                success_count = EXCLUDED.success_count,
                failed_count = EXCLUDED.failed_count,
                success_rate = EXCLUDED.success_rate
        """
        
        from psycopg2.extras import execute_batch
        data = [
            (
                processing_round,
                study['nct_id'],
                study['total_outcomes'],
                study['success_count'],
                study['failed_count'],
                study['success_rate']
            )
            for study in study_stats
        ]
        
        execute_batch(cur, insert_query, data, page_size=1000)
        conn.commit()
    
    # 통계 요약
    total_studies = len(study_stats)
    perfect_success = sum(1 for s in study_stats if s['success_rate'] == 100.0)
    partial_success = sum(1 for s in study_stats if 0 < s['success_rate'] < 100.0)
    complete_failure = sum(1 for s in study_stats if s['success_rate'] == 0.0)
    
    print(f"\n[OK] Study별 이력 기록 완료: {processing_round}")
    print(f"  전체 Studies: {total_studies:,}개")
    print(f"  완전 성공 (100%): {perfect_success:,}개 ({perfect_success/total_studies*100:.1f}%)")
    print(f"  부분 성공 (1-99%): {partial_success:,}개 ({partial_success/total_studies*100:.1f}%)")
    print(f"  완전 실패 (0%): {complete_failure:,}개 ({complete_failure/total_studies*100:.1f}%)")


def get_history_summary(conn) -> list:
    """정규화 이력 요약 조회"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                processing_round,
                execution_date,
                total_outcomes,
                success_count,
                failed_count,
                success_rate,
                notes
            FROM normalization_history
            ORDER BY execution_date ASC
        """)
        return cur.fetchall()


def get_study_history_summary(conn, processing_round: str = None) -> list:
    """Study별 정규화 이력 요약 조회"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if processing_round:
            cur.execute("""
                SELECT 
                    processing_round,
                    COUNT(*) as total_studies,
                    COUNT(*) FILTER (WHERE success_rate = 100.0) as perfect_success_count,
                    COUNT(*) FILTER (WHERE success_rate > 0 AND success_rate < 100.0) as partial_success_count,
                    COUNT(*) FILTER (WHERE success_rate = 0.0) as complete_failure_count,
                    AVG(success_rate) as avg_success_rate,
                    MIN(success_rate) as min_success_rate,
                    MAX(success_rate) as max_success_rate
                FROM study_normalization_history
                WHERE processing_round = %s
                GROUP BY processing_round
            """, (processing_round,))
        else:
            cur.execute("""
                SELECT 
                    processing_round,
                    COUNT(*) as total_studies,
                    COUNT(*) FILTER (WHERE success_rate = 100.0) as perfect_success_count,
                    COUNT(*) FILTER (WHERE success_rate > 0 AND success_rate < 100.0) as partial_success_count,
                    COUNT(*) FILTER (WHERE success_rate = 0.0) as complete_failure_count,
                    AVG(success_rate) as avg_success_rate,
                    MIN(success_rate) as min_success_rate,
                    MAX(success_rate) as max_success_rate
                FROM study_normalization_history
                GROUP BY processing_round
                ORDER BY processing_round
            """)
        return cur.fetchall()


def main():
    """메인 함수"""
    import sys
    
    if len(sys.argv) < 2:
        print("사용법: python record_normalization_history.py <ROUND1|ROUND2|ROUND3> [notes]")
        print("\n예시:")
        print("  python record_normalization_history.py ROUND1 '1차 정규화 완료'")
        print("  python record_normalization_history.py ROUND2 '2차 정규화 완료 (drug 필터 적용)'")
        sys.exit(1)
    
    processing_round = sys.argv[1].upper()
    notes = sys.argv[2] if len(sys.argv) > 2 else None
    
    if processing_round not in ['ROUND1', 'ROUND2', 'ROUND3', 'ROUND4', 'ROUND5']:
        print(f"[ERROR] 잘못된 processing_round: {processing_round}")
        print("사용 가능한 값: ROUND1, ROUND2, ROUND3, ROUND4, ROUND5")
        sys.exit(1)
    
    try:
        conn = get_db_connection()
        
        # 데이터 존재 여부 확인
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM outcome_normalized")
            count = cur.fetchone()[0]
            if count == 0:
                print("[ERROR] outcome_normalized 테이블에 데이터가 없습니다!")
                return
        
        # 전체 통계 이력 기록
        record_history(conn, processing_round, notes)
        
        # Study별 이력 기록
        print("\n[STEP 2] Study별 이력 기록 중...")
        record_study_history(conn, processing_round)
        
        # 이력 요약 출력
        print("\n" + "=" * 80)
        print("[HISTORY] 전체 정규화 이력 요약")
        print("=" * 80)
        history = get_history_summary(conn)
        for record in history:
            print(f"\n{record['processing_round']} ({record['execution_date']}):")
            print(f"  성공률: {record['success_rate']:.2f}%")
            print(f"  성공: {record['success_count']:,}건 / 전체: {record['total_outcomes']:,}건")
            if record['notes']:
                print(f"  메모: {record['notes']}")
        
        # Study별 이력 요약 출력
        print("\n" + "=" * 80)
        print("[HISTORY] Study별 정규화 이력 요약")
        print("=" * 80)
        study_history = get_study_history_summary(conn)
        for record in study_history:
            print(f"\n{record['processing_round']}:")
            print(f"  전체 Studies: {record['total_studies']:,}개")
            print(f"  평균 성공률: {float(record['avg_success_rate']):.2f}%")
            print(f"  완전 성공 (100%): {record['perfect_success_count']:,}개")
            print(f"  부분 성공 (1-99%): {record['partial_success_count']:,}개")
            print(f"  완전 실패 (0%): {record['complete_failure_count']:,}개")
            print(f"  성공률 범위: {float(record['min_success_rate']):.2f}% ~ {float(record['max_success_rate']):.2f}%")
        
        conn.close()
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()

