"""
LLM 결과 분석 스크립트

LLM 전처리 및 검증 결과를 분석하고 리포트를 생성합니다.
"""

import os
import platform
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
from datetime import datetime
from typing import Dict, List
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

# 프로젝트 루트 디렉토리 설정
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'clinicaltrials'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

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


def get_llm_preprocessing_stats(conn):
    """LLM 전처리 통계"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE llm_parsed_measure_code IS NOT NULL 
                                 AND llm_parsed_time_value IS NOT NULL 
                                 AND llm_parsed_time_unit IS NOT NULL) as success_count,
                COUNT(*) FILTER (WHERE llm_parsed_measure_code IS NULL 
                                 OR llm_parsed_time_value IS NULL 
                                 OR llm_parsed_time_unit IS NULL) as failed_count,
                COUNT(*) as total_count,
                AVG(llm_validation_confidence) as avg_confidence
            FROM outcome_normalized
            WHERE parsing_method = 'LLM'
        """)
        return cur.fetchone()


def get_llm_validation_stats(conn):
    """LLM 검증 통계"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                llm_validation_status,
                COUNT(*) as count,
                AVG(llm_validation_confidence) as avg_confidence
            FROM outcome_normalized
            WHERE llm_validation_status IS NOT NULL
            GROUP BY llm_validation_status
            ORDER BY count DESC
        """)
        return cur.fetchall()


def get_rule_vs_llm_comparison(conn):
    """Rule-based vs LLM-based 비교"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                parsing_method,
                COUNT(*) as total_count,
                COUNT(*) FILTER (WHERE measure_code IS NOT NULL AND failure_reason IS NULL) as success_count,
                ROUND(
                    COUNT(*) FILTER (WHERE measure_code IS NOT NULL AND failure_reason IS NULL)::NUMERIC / 
                    COUNT(*)::NUMERIC * 100, 
                    2
                ) as success_rate
            FROM outcome_normalized
            WHERE parsing_method IN ('RULE_BASED', 'LLM')
            GROUP BY parsing_method
        """)
        return cur.fetchall()


def get_complete_verified_studies(conn):
    """VERIFIED 기준으로 모든 outcome이 성공한 study 수"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 전체 검증된 study 수
        cur.execute("""
            SELECT COUNT(DISTINCT nct_id) as total_verified_studies
            FROM outcome_normalized
            WHERE llm_validation_status IS NOT NULL
        """)
        total_stats = cur.fetchone()
        
        # 모든 outcome이 VERIFIED인 study 수
        cur.execute("""
            SELECT COUNT(DISTINCT nct_id) as complete_verified_study_count
            FROM (
                SELECT nct_id
                FROM outcome_normalized
                WHERE llm_validation_status IS NOT NULL
                GROUP BY nct_id
                HAVING COUNT(*) = COUNT(*) FILTER (WHERE llm_validation_status = 'VERIFIED')
            ) AS verified_studies
        """)
        complete_stats = cur.fetchone()
        
        return {
            'total_verified_studies': total_stats['total_verified_studies'] if total_stats else 0,
            'complete_verified_study_count': complete_stats['complete_verified_study_count'] if complete_stats else 0
        }


def plot_llm_validation_distribution(validation_stats, output_dir='visualization'):
    """LLM 검증 결과 분포 Pie Chart"""
    if not validation_stats:
        print("[WARN] LLM 검증 데이터가 없습니다.")
        return
    
    labels = [s['llm_validation_status'] for s in validation_stats]
    sizes = [s['count'] for s in validation_stats]
    colors = {'VERIFIED': '#2ecc71', 'UNCERTAIN': '#f39c12', 'FAILED': '#e74c3c'}
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    
    pie_colors = [colors.get(label, '#95a5a6') for label in labels]
    wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                                      colors=pie_colors, startangle=90,
                                      textprops={'fontsize': 11, 'fontproperties': KOREAN_FONT_PROP})
    
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(10)
        autotext.set_fontweight('bold')
    
    ax.set_title('LLM 검증 결과 분포', fontsize=14, fontweight='bold', pad=20, fontproperties=KOREAN_FONT_PROP)
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/llm_validation_distribution.png', dpi=300, bbox_inches='tight')
    print(f"[OK] 그래프 저장: {output_dir}/llm_validation_distribution.png")
    plt.close()


def plot_rule_vs_llm_comparison(comparison_stats, output_dir=None):
    if output_dir is None:
        output_dir = os.path.join(ROOT_DIR, 'visualization')
    """Rule-based vs LLM-based 비교 Bar Chart"""
    if not comparison_stats:
        print("[WARN] 비교 데이터가 없습니다.")
        return
    
    methods = [s['parsing_method'] for s in comparison_stats]
    success_rates = [float(s['success_rate']) for s in comparison_stats]
    success_counts = [s['success_count'] for s in comparison_stats]
    total_counts = [s['total_count'] for s in comparison_stats]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = ['#3498db' if m == 'RULE_BASED' else '#2ecc71' for m in methods]
    bars = ax.bar(methods, success_rates, color=colors, alpha=0.7)
    
    # 값 표시
    for bar, rate, success, total in zip(bars, success_rates, success_counts, total_counts):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{rate:.2f}%\n({success:,}/{total:,})',
               ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    ax.set_xlabel('파싱 방법', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_ylabel('성공률 (%)', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_title('Rule-based vs LLM-based 성공률 비교', fontsize=14, fontweight='bold', pad=20, fontproperties=KOREAN_FONT_PROP)
    ax.set_ylim(0, 105)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/rule_vs_llm_comparison.png', dpi=300, bbox_inches='tight')
    print(f"[OK] 그래프 저장: {output_dir}/rule_vs_llm_comparison.png")
    plt.close()


def generate_llm_report(preprocessing_stats, validation_stats, comparison_stats, complete_verified_studies=None, output_dir=None):
    if output_dir is None:
        output_dir = os.path.join(ROOT_DIR, 'reports')
    """LLM 결과 리포트 생성"""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = f'{output_dir}/llm_validation_statistics_{timestamp}.md'
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('# LLM 검증 통계 리포트\n\n')
        f.write(f'생성일시: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
        
        # LLM 검증 통계
        if validation_stats:
            f.write('## 1. LLM 검증 통계\n\n')
            f.write('| 검증 상태 | 개수 | 비율 | 평균 신뢰도 |\n')
            f.write('|----------|------|------|------------|\n')
            total_validated = sum(s['count'] for s in validation_stats)
            for stat in validation_stats:
                percentage = stat['count'] / total_validated * 100 if total_validated > 0 else 0
                avg_conf = float(stat['avg_confidence']) if stat['avg_confidence'] else 0
                f.write(f"| {stat['llm_validation_status']} | {stat['count']:,} | {percentage:.2f}% | {avg_conf:.2f} |\n")
            f.write(f'\n**전체 검증 항목**: {total_validated:,}개\n\n')
        
        # VERIFIED 기준 완전 성공 Study 통계
        if complete_verified_studies:
            f.write('## 2. VERIFIED 기준 완전 성공 Study 통계\n\n')
            total_studies = complete_verified_studies['total_verified_studies']
            complete_studies = complete_verified_studies['complete_verified_study_count']
            if total_studies > 0:
                percentage = (complete_studies / total_studies) * 100
                f.write(f"- 전체 검증된 Study: {total_studies:,}개\n")
                f.write(f"- 모든 outcome이 VERIFIED인 Study: {complete_studies:,}개 ({percentage:.2f}%)\n")
            else:
                f.write("- 검증된 Study가 없습니다.\n")
            f.write('\n')
        
        # LLM 전처리 통계
        if preprocessing_stats and preprocessing_stats['total_count'] > 0:
            f.write('## 3. LLM 전처리 통계\n\n')
            f.write(f"- 전체 처리 항목: {preprocessing_stats['total_count']:,}개\n")
            f.write(f"- 성공 (measure_code + time 파싱): {preprocessing_stats['success_count']:,}개 ")
            f.write(f"({preprocessing_stats['success_count']/preprocessing_stats['total_count']*100:.2f}%)\n")
            f.write(f"- 실패: {preprocessing_stats['failed_count']:,}개 ")
            f.write(f"({preprocessing_stats['failed_count']/preprocessing_stats['total_count']*100:.2f}%)\n")
            if preprocessing_stats['avg_confidence']:
                f.write(f"- 평균 신뢰도: {float(preprocessing_stats['avg_confidence']):.2f}\n")
            f.write('\n')
        
        # Rule-based vs LLM 비교
        if comparison_stats:
            f.write('## 4. Rule-based vs LLM-based 비교\n\n')
            f.write('| 파싱 방법 | 전체 개수 | 성공 개수 | 성공률 |\n')
            f.write('|----------|----------|----------|--------|\n')
            for stat in comparison_stats:
                f.write(f"| {stat['parsing_method']} | {stat['total_count']:,} | {stat['success_count']:,} | {stat['success_rate']:.2f}% |\n")
            f.write('\n')
    
    print(f"[OK] 리포트 저장: {report_path}")


def main():
    """메인 함수"""
    print("=" * 80)
    print("[START] LLM 결과 분석 시작")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        
        # LLM 전처리 통계
        print("\n[STEP 1] LLM 전처리 통계 조회 중...")
        preprocessing_stats = get_llm_preprocessing_stats(conn)
        
        if preprocessing_stats and preprocessing_stats['total_count'] > 0:
            print(f"\n[INFO] LLM 전처리 통계:")
            print(f"  전체: {preprocessing_stats['total_count']:,}개")
            print(f"  성공: {preprocessing_stats['success_count']:,}개 ({preprocessing_stats['success_count']/preprocessing_stats['total_count']*100:.2f}%)")
            print(f"  실패: {preprocessing_stats['failed_count']:,}개 ({preprocessing_stats['failed_count']/preprocessing_stats['total_count']*100:.2f}%)")
        else:
            print("  LLM 전처리 데이터가 없습니다.")
        
        # LLM 검증 통계
        print("\n[STEP 2] LLM 검증 통계 조회 중...")
        validation_stats = get_llm_validation_stats(conn)
        
        if validation_stats:
            print(f"\n[INFO] LLM 검증 통계:")
            for stat in validation_stats:
                print(f"  {stat['llm_validation_status']}: {stat['count']:,}개")
        else:
            print("  LLM 검증 데이터가 없습니다.")
        
        # VERIFIED 기준 완전 성공 Study 통계
        print("\n[STEP 3] VERIFIED 기준 완전 성공 Study 조회 중...")
        complete_verified_studies = get_complete_verified_studies(conn)
        
        if complete_verified_studies:
            total_studies = complete_verified_studies['total_verified_studies']
            complete_studies = complete_verified_studies['complete_verified_study_count']
            if total_studies > 0:
                percentage = (complete_studies / total_studies) * 100
                print(f"\n[INFO] VERIFIED 기준 완전 성공 Study:")
                print(f"  전체 검증된 Study: {total_studies:,}개")
                print(f"  모든 outcome이 VERIFIED인 Study: {complete_studies:,}개 ({percentage:.2f}%)")
            else:
                print("  검증된 Study가 없습니다.")
        
        # Rule-based vs LLM 비교
        print("\n[STEP 4] Rule-based vs LLM-based 비교 조회 중...")
        comparison_stats = get_rule_vs_llm_comparison(conn)
        
        if comparison_stats:
            print(f"\n[INFO] 파싱 방법별 비교:")
            for stat in comparison_stats:
                print(f"  {stat['parsing_method']}: {stat['success_rate']:.2f}% ({stat['success_count']:,}/{stat['total_count']:,})")
        
        # 시각화
        if validation_stats:
            print("\n[STEP 5] LLM 검증 결과 분포 그래프 생성 중...")
            plot_llm_validation_distribution(validation_stats)
        
        if comparison_stats:
            print("\n[STEP 6] Rule-based vs LLM-based 비교 그래프 생성 중...")
            plot_rule_vs_llm_comparison(comparison_stats)
        
        # 리포트 생성
        print("\n[STEP 7] 리포트 생성 중...")
        generate_llm_report(preprocessing_stats, validation_stats, comparison_stats, complete_verified_studies)
        
        print("\n" + "=" * 80)
        print("[OK] LLM 결과 분석 완료!")
        print("=" * 80)
        print("\n생성된 파일:")
        if validation_stats:
            print("  - visualization/llm_validation_distribution.png")
        if comparison_stats:
            print("  - visualization/rule_vs_llm_comparison.png")
        print("  - reports/llm_validation_statistics_*.md")
        
        conn.close()
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()

