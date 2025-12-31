"""
OverallStatus 통계 분석 스크립트

raw.json에서 overallStatus를 추출하고 통계를 분석합니다.
- Phase NA 처리 항목 통계
- OverallStatus별 기본 통계
- 실패 항목과 성공 항목의 overallStatus 분포 비교
"""

import os
import json
import platform
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
from datetime import datetime
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'clinicaltrials'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

RAW_JSON_PATH = 'data/raw.json'

# 한글 폰트 설정
def setup_korean_font():
    """한글 폰트 설정"""
    if platform.system() == 'Windows':
        font_list = ['Malgun Gothic', '맑은 고딕', 'NanumGothic', '나눔고딕', 'Gulim', '굴림', 'Batang', '바탕', 'MS Gothic']
        available_fonts = [f.name for f in fm.fontManager.ttflist]
        
        selected_font = None
        font_path = None
        
        for font in font_list:
            if font in available_fonts:
                selected_font = font
                for font_file in fm.fontManager.ttflist:
                    if font_file.name == selected_font:
                        font_path = font_file.fname
                        break
                if font_path:
                    break
        
        if selected_font and font_path:
            plt.rcParams['font.family'] = 'sans-serif'
            current_sans = plt.rcParams['font.sans-serif']
            new_sans = [selected_font] + [f for f in current_sans if f != selected_font]
            plt.rcParams['font.sans-serif'] = new_sans
        elif selected_font:
            plt.rcParams['font.family'] = 'sans-serif'
            current_sans = plt.rcParams['font.sans-serif']
            new_sans = [selected_font] + [f for f in current_sans if f != selected_font]
            plt.rcParams['font.sans-serif'] = new_sans
    
    plt.rcParams['axes.unicode_minus'] = False

def get_korean_font_prop():
    """한글 폰트 속성 반환"""
    if platform.system() == 'Windows':
        font_list = ['Malgun Gothic', '맑은 고딕', 'NanumGothic', '나눔고딕', 'Gulim', '굴림', 'Batang', '바탕', 'MS Gothic']
        available_fonts = [f.name for f in fm.fontManager.ttflist]
        
        for font in font_list:
            if font in available_fonts:
                for font_file in fm.fontManager.ttflist:
                    if font_file.name == font:
                        return fm.FontProperties(fname=font_file.fname)
        for font in font_list:
            if font in available_fonts:
                return fm.FontProperties(family=font)
    return fm.FontProperties()

# 폰트 설정 실행
setup_korean_font()
KOREAN_FONT_PROP = get_korean_font_prop()
sns.set_style("whitegrid")


def get_db_connection():
    """PostgreSQL 연결 생성"""
    return psycopg2.connect(**DB_CONFIG)


def create_status_table(conn):
    """study_status_raw 테이블 생성"""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS study_status_raw (
                nct_id VARCHAR(20) PRIMARY KEY,
                overall_status VARCHAR(50),
                status_verified_date VARCHAR(20),
                has_expanded_access BOOLEAN,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_study_status_raw_status 
                ON study_status_raw(overall_status);
            CREATE INDEX IF NOT EXISTS idx_study_status_raw_date 
                ON study_status_raw(extracted_at);
        """)
        conn.commit()


def extract_status_from_raw_json(json_path: str) -> List[Dict]:
    """raw.json에서 overallStatus 추출"""
    print(f"\n[STEP 1] raw.json에서 overallStatus 추출 중...")
    print(f"  파일 경로: {json_path}")
    
    statuses = []
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            studies = json.load(f)
        
        if not isinstance(studies, list):
            print("[ERROR] raw.json이 배열 형식이 아닙니다!")
            return []
        
        print(f"  전체 Studies: {len(studies):,}개")
        
        for i, study in enumerate(studies):
            if (i + 1) % 100 == 0:
                print(f"  처리 중: {i + 1:,}/{len(studies):,}개")
            
            nct_id = study.get('protocolSection', {}).get('identificationModule', {}).get('nctId')
            if not nct_id:
                continue
            
            status_module = study.get('protocolSection', {}).get('statusModule', {})
            overall_status = status_module.get('overallStatus')
            status_verified_date = status_module.get('statusVerifiedDate')
            expanded_access_info = status_module.get('expandedAccessInfo', {})
            has_expanded_access = expanded_access_info.get('hasExpandedAccess', False)
            
            statuses.append({
                'nct_id': nct_id,
                'overall_status': overall_status,
                'status_verified_date': status_verified_date,
                'has_expanded_access': has_expanded_access
            })
        
        print(f"  추출 완료: {len(statuses):,}개")
        return statuses
        
    except FileNotFoundError:
        print(f"[ERROR] 파일을 찾을 수 없습니다: {json_path}")
        return []
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 파싱 오류: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return []


def insert_status_data(conn, statuses: List[Dict]):
    """study_status_raw 테이블에 데이터 삽입"""
    if not statuses:
        return
    
    print(f"\n[STEP 2] 데이터베이스에 저장 중...")
    
    create_status_table(conn)
    
    insert_sql = """
        INSERT INTO study_status_raw 
        (nct_id, overall_status, status_verified_date, has_expanded_access)
        VALUES (%(nct_id)s, %(overall_status)s, %(status_verified_date)s, %(has_expanded_access)s)
        ON CONFLICT (nct_id) 
        DO UPDATE SET
            overall_status = EXCLUDED.overall_status,
            status_verified_date = EXCLUDED.status_verified_date,
            has_expanded_access = EXCLUDED.has_expanded_access,
            extracted_at = CURRENT_TIMESTAMP
    """
    
    with conn.cursor() as cur:
        execute_batch(cur, insert_sql, statuses, page_size=100)
        conn.commit()
    
    print(f"  저장 완료: {len(statuses):,}개")


def get_phase_statistics(conn):
    """Phase별 통계 조회"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                COALESCE(phase, 'NA') as phase,
                COUNT(*) as count,
                COUNT(*) FILTER (WHERE measure_code IS NOT NULL AND failure_reason IS NULL) as success_count,
                COUNT(*) FILTER (WHERE measure_code IS NULL OR failure_reason IS NOT NULL) as failed_count,
                ROUND(
                    COUNT(*) FILTER (WHERE measure_code IS NOT NULL AND failure_reason IS NULL)::NUMERIC / 
                    COUNT(*)::NUMERIC * 100, 
                    2
                ) as success_rate
            FROM outcome_normalized
            GROUP BY phase
            ORDER BY phase
        """)
        return cur.fetchall()


def get_overall_status_statistics(conn):
    """OverallStatus별 통계 조회"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                COALESCE(s.overall_status, 'UNKNOWN') as overall_status,
                COUNT(DISTINCT o.nct_id) as study_count,
                COUNT(*) as outcome_count,
                COUNT(*) FILTER (WHERE o.measure_code IS NOT NULL AND o.failure_reason IS NULL) as success_outcomes,
                COUNT(*) FILTER (WHERE o.measure_code IS NULL OR o.failure_reason IS NOT NULL) as failed_outcomes,
                ROUND(
                    COUNT(*) FILTER (WHERE o.measure_code IS NOT NULL AND o.failure_reason IS NULL)::NUMERIC / 
                    COUNT(*)::NUMERIC * 100, 
                    2
                ) as success_rate
            FROM outcome_normalized o
            LEFT JOIN study_status_raw s ON o.nct_id = s.nct_id
            GROUP BY s.overall_status
            ORDER BY study_count DESC
        """)
        return cur.fetchall()


def plot_phase_statistics(phase_stats, output_dir='visualization'):
    """Phase별 통계 Bar Chart"""
    if not phase_stats:
        return
    
    phases = [s['phase'] for s in phase_stats]
    counts = [s['count'] for s in phase_stats]
    success_rates = [float(s['success_rate']) for s in phase_stats]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Outcome 개수
    bars1 = ax1.bar(phases, counts, color='#3498db', alpha=0.7)
    for bar, count in zip(bars1, counts):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{count:,}',
                ha='center', va='bottom', fontsize=9)
    
    ax1.set_xlabel('Phase', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax1.set_ylabel('Outcome 개수', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax1.set_title('Phase별 Outcome 개수', fontsize=14, fontweight='bold', pad=20, fontproperties=KOREAN_FONT_PROP)
    ax1.grid(axis='y', alpha=0.3)
    
    # 성공률
    bars2 = ax2.bar(phases, success_rates, color='#2ecc71', alpha=0.7)
    for bar, rate in zip(bars2, success_rates):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{rate:.1f}%',
                ha='center', va='bottom', fontsize=9)
    
    ax2.set_xlabel('Phase', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax2.set_ylabel('성공률 (%)', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax2.set_title('Phase별 성공률', fontsize=14, fontweight='bold', pad=20, fontproperties=KOREAN_FONT_PROP)
    ax2.set_ylim(0, 105)
    ax2.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/phase_statistics.png', dpi=300, bbox_inches='tight')
    print(f"[OK] 그래프 저장: {output_dir}/phase_statistics.png")
    plt.close()


def plot_overall_status_distribution(status_stats, output_dir='visualization'):
    """OverallStatus별 분포 Bar Chart"""
    if not status_stats:
        return
    
    statuses = [s['overall_status'] for s in status_stats]
    study_counts = [s['study_count'] for s in status_stats]
    success_rates = [float(s['success_rate']) for s in status_stats]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
    
    # Study 개수
    bars1 = ax1.bar(statuses, study_counts, color='#3498db', alpha=0.7)
    for bar, count in zip(bars1, study_counts):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{count:,}',
                ha='center', va='bottom', fontsize=9, rotation=45)
    
    ax1.set_xlabel('Overall Status', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax1.set_ylabel('Study 개수', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax1.set_title('OverallStatus별 Study 개수', fontsize=14, fontweight='bold', pad=20, fontproperties=KOREAN_FONT_PROP)
    ax1.grid(axis='y', alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    
    # 성공률
    bars2 = ax2.bar(statuses, success_rates, color='#2ecc71', alpha=0.7)
    for bar, rate in zip(bars2, success_rates):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{rate:.1f}%',
                ha='center', va='bottom', fontsize=9, rotation=45)
    
    ax2.set_xlabel('Overall Status', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax2.set_ylabel('성공률 (%)', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax2.set_title('OverallStatus별 성공률', fontsize=14, fontweight='bold', pad=20, fontproperties=KOREAN_FONT_PROP)
    ax2.set_ylim(0, 105)
    ax2.grid(axis='y', alpha=0.3)
    ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/overall_status_distribution.png', dpi=300, bbox_inches='tight')
    print(f"[OK] 그래프 저장: {output_dir}/overall_status_distribution.png")
    plt.close()


def generate_report(phase_stats, status_stats, output_dir='reports'):
    """통계 리포트 생성"""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = f'{output_dir}/overall_status_statistics_{timestamp}.md'
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('# OverallStatus 통계 리포트\n\n')
        f.write(f'생성일시: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
        
        f.write('## 1. Phase별 통계\n\n')
        f.write('| Phase | Outcome 개수 | 성공 개수 | 실패 개수 | 성공률 |\n')
        f.write('|-------|-------------|----------|----------|--------|\n')
        for stat in phase_stats:
            f.write(f"| {stat['phase']} | {stat['count']:,} | {stat['success_count']:,} | {stat['failed_count']:,} | {stat['success_rate']:.2f}% |\n")
        
        f.write('\n## 2. OverallStatus별 통계\n\n')
        f.write('| Overall Status | Study 개수 | Outcome 개수 | 성공 Outcome | 실패 Outcome | 성공률 |\n')
        f.write('|----------------|-----------|-------------|-------------|-------------|--------|\n')
        for stat in status_stats:
            f.write(f"| {stat['overall_status']} | {stat['study_count']:,} | {stat['outcome_count']:,} | {stat['success_outcomes']:,} | {stat['failed_outcomes']:,} | {stat['success_rate']:.2f}% |\n")
        
        # Phase NA 통계
        na_phase = next((s for s in phase_stats if s['phase'] == 'NA'), None)
        if na_phase:
            f.write('\n## 3. Phase NA 처리 항목\n\n')
            f.write(f"- 전체 Outcome 개수: {na_phase['count']:,}개\n")
            f.write(f"- 성공 개수: {na_phase['success_count']:,}개 ({na_phase['success_rate']:.2f}%)\n")
            f.write(f"- 실패 개수: {na_phase['failed_count']:,}개 ({100 - na_phase['success_rate']:.2f}%)\n")
        
        # OverallStatus 없는 항목
        unknown_status = next((s for s in status_stats if s['overall_status'] == 'UNKNOWN'), None)
        if unknown_status:
            f.write('\n## 4. OverallStatus 없는 항목\n\n')
            f.write(f"- Study 개수: {unknown_status['study_count']:,}개\n")
            f.write(f"- Outcome 개수: {unknown_status['outcome_count']:,}개\n")
            f.write(f"- 성공률: {unknown_status['success_rate']:.2f}%\n")
    
    print(f"[OK] 리포트 저장: {report_path}")


def main():
    """메인 함수"""
    print("=" * 80)
    print("[START] OverallStatus 통계 분석 시작")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        
        # raw.json에서 overallStatus 추출 및 저장
        statuses = extract_status_from_raw_json(RAW_JSON_PATH)
        if statuses:
            insert_status_data(conn, statuses)
        
        # Phase별 통계
        print("\n[STEP 3] Phase별 통계 조회 중...")
        phase_stats = get_phase_statistics(conn)
        
        print("\n[INFO] Phase별 통계:")
        for stat in phase_stats:
            print(f"  {stat['phase']}: {stat['count']:,}개 (성공률: {stat['success_rate']:.2f}%)")
        
        # OverallStatus별 통계
        print("\n[STEP 4] OverallStatus별 통계 조회 중...")
        status_stats = get_overall_status_statistics(conn)
        
        print("\n[INFO] OverallStatus별 통계:")
        for stat in status_stats[:10]:  # 상위 10개만 출력
            print(f"  {stat['overall_status']}: {stat['study_count']:,}개 Studies, 성공률: {stat['success_rate']:.2f}%")
        
        # 시각화
        print("\n[STEP 5] Phase별 통계 그래프 생성 중...")
        plot_phase_statistics(phase_stats)
        
        print("\n[STEP 6] OverallStatus별 분포 그래프 생성 중...")
        plot_overall_status_distribution(status_stats)
        
        # 리포트 생성
        print("\n[STEP 7] 통계 리포트 생성 중...")
        generate_report(phase_stats, status_stats)
        
        print("\n" + "=" * 80)
        print("[OK] 통계 분석 완료!")
        print("=" * 80)
        print("\n생성된 파일:")
        print("  - visualization/phase_statistics.png")
        print("  - visualization/overall_status_distribution.png")
        print("  - reports/overall_status_statistics_*.md")
        
        conn.close()
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()

