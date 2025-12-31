"""
LLM 전처리 결과 Study별 Outcome 분포 시각화 스크립트

outcome_llm_preprocessed 테이블의 Study별 outcome 성공/실패 분포를 시각화합니다.
- Study별 성공한 outcome 개수 Histogram
- 성공률 구간별 Bar Chart
"""

import os
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import platform
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import numpy as np

load_dotenv()

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
            print(f"[INFO] 한글 폰트 설정: {selected_font} (경로: {font_path})")
        elif selected_font:
            plt.rcParams['font.family'] = 'sans-serif'
            current_sans = plt.rcParams['font.sans-serif']
            new_sans = [selected_font] + [f for f in current_sans if f != selected_font]
            plt.rcParams['font.sans-serif'] = new_sans
            print(f"[INFO] 한글 폰트 설정: {selected_font}")
        else:
            plt.rcParams['font.family'] = 'DejaVu Sans'
            print("[WARN] 한글 폰트를 찾을 수 없습니다. 기본 폰트를 사용합니다.")
    elif platform.system() == 'Darwin':
        plt.rcParams['font.family'] = 'AppleGothic'
        print("[INFO] 한글 폰트 설정: AppleGothic")
    else:
        plt.rcParams['font.family'] = 'NanumGothic'
        print("[INFO] 한글 폰트 설정: NanumGothic")
    
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


def get_study_statistics(conn):
    """Study별 outcome 성공률 통계 조회 (outcome_llm_preprocessed)"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                nct_id,
                COUNT(*) as total_outcomes,
                COUNT(*) FILTER (WHERE llm_status = 'SUCCESS') as success_count,
                COUNT(*) FILTER (WHERE llm_status != 'SUCCESS') as failed_count,
                ROUND(
                    COUNT(*) FILTER (WHERE llm_status = 'SUCCESS')::NUMERIC / 
                    COUNT(*)::NUMERIC * 100, 
                    2
                ) as success_rate
            FROM outcome_llm_preprocessed
            GROUP BY nct_id
            ORDER BY success_rate, total_outcomes DESC
        """)
        return cur.fetchall()


def plot_success_count_histogram(study_stats, output_dir='visualization'):
    """Study별 성공한 outcome 개수 Histogram"""
    if not study_stats:
        print("[WARN] Study 통계 데이터가 없습니다.")
        return
    
    success_counts = [s['success_count'] for s in study_stats]
    total_outcomes = [s['total_outcomes'] for s in study_stats]
    
    # 최대 outcome 개수
    max_outcomes = max(total_outcomes) if total_outcomes else 0
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Histogram 생성
    bins = range(0, max_outcomes + 2)
    counts, edges, patches = ax.hist(success_counts, bins=bins, edgecolor='black', alpha=0.7, color='#3498db')
    
    # 각 막대 위에 개수 표시
    for i, (count, patch) in enumerate(zip(counts, patches)):
        if count > 0:
            ax.text(patch.get_x() + patch.get_width()/2., count,
                   f'{int(count)}',
                   ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    ax.set_xlabel('Study별 성공한 Outcome 개수', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_ylabel('Study 수', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_title('LLM 전처리: Study별 성공한 Outcome 개수 분포', fontsize=14, fontweight='bold', pad=20, fontproperties=KOREAN_FONT_PROP)
    ax.grid(axis='y', alpha=0.3)
    ax.set_xticks(range(0, max_outcomes + 1, max(1, max_outcomes // 20)))
    
    # 통계 정보 표시
    total_studies = len(study_stats)
    perfect_success = sum(1 for s in study_stats if s['success_count'] == s['total_outcomes'])
    complete_failure = sum(1 for s in study_stats if s['success_count'] == 0)
    
    stats_text = f'전체 Studies: {total_studies:,}개\n'
    stats_text += f'완전 성공 (100%): {perfect_success:,}개 ({perfect_success/total_studies*100:.1f}%)\n'
    stats_text += f'완전 실패 (0%): {complete_failure:,}개 ({complete_failure/total_studies*100:.1f}%)'
    
    ax.text(0.98, 0.98, stats_text,
           transform=ax.transAxes, ha='right', va='top',
           fontsize=10, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
           fontproperties=KOREAN_FONT_PROP)
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/llm_study_outcome_success_count_histogram.png', dpi=300, bbox_inches='tight')
    print(f"[OK] 그래프 저장: {output_dir}/llm_study_outcome_success_count_histogram.png")
    plt.close()


def plot_success_rate_distribution(study_stats, output_dir='visualization'):
    """성공률 구간별 Bar Chart (10% 단위)"""
    if not study_stats:
        print("[WARN] Study 통계 데이터가 없습니다.")
        return
    
    # 성공률 구간 정의 (10% 단위)
    bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    labels = ['0%', '1-10%', '11-20%', '21-30%', '31-40%', '41-50%', '51-60%', '61-70%', '71-80%', '81-90%', '91-99%', '100%']
    
    success_rates = [float(s['success_rate']) for s in study_stats]
    
    # 구간별 개수 계산 (12개 구간: 0%, 1-10%, ..., 91-99%, 100%)
    counts = [0] * len(labels)
    for rate in success_rates:
        if rate == 0:
            counts[0] += 1
        elif rate == 100:
            counts[-1] += 1
        else:
            # 1-99% 구간 처리
            for i in range(len(bins) - 1):
                if bins[i] < rate <= bins[i + 1]:
                    counts[i + 1] += 1  # i+1인 이유는 0%가 첫 번째이므로
                    break
    
    fig, ax = plt.subplots(figsize=(18, 8))
    
    # 색상 설정: 실패(0%)는 빨강, 완전 성공(100%)은 초록, 그 외는 회색
    colors = []
    for i, label in enumerate(labels):
        if label == '0%':
            colors.append('#e74c3c')  # 빨강
        elif label == '100%':
            colors.append('#2ecc71')  # 초록
        else:
            colors.append('#95a5a6')  # 회색
    
    bars = ax.bar(labels, counts, color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)
    
    # 값 표시 (막대 위 중앙)
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        if height > 0:
            percentage = count/len(study_stats)*100
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(count):,}\n({percentage:.1f}%)',
                   ha='center', va='bottom', fontsize=9, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    
    ax.set_xlabel('성공률 구간', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_ylabel('Study 수', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_title('LLM 전처리: Study별 Outcome 성공률 구간 분포 (10% 단위)', fontsize=14, fontweight='bold', pad=20, fontproperties=KOREAN_FONT_PROP)
    ax.grid(axis='y', alpha=0.3)
    ax.tick_params(axis='x', rotation=45)
    
    # 범례 추가 (왼쪽에)
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#e74c3c', alpha=0.8, label='완전 실패 (0%)'),
        Patch(facecolor='#95a5a6', alpha=0.8, label='부분 성공 (1-99%)'),
        Patch(facecolor='#2ecc71', alpha=0.8, label='완전 성공 (100%)')
    ]
    ax.legend(handles=legend_elements, prop=KOREAN_FONT_PROP, loc='upper left')
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/llm_study_outcome_success_rate_distribution.png', dpi=300, bbox_inches='tight')
    print(f"[OK] 그래프 저장: {output_dir}/llm_study_outcome_success_rate_distribution.png")
    plt.close()


def plot_success_vs_total_scatter(study_stats, output_dir='visualization'):
    """성공 개수 vs 전체 개수 Scatter Plot"""
    if not study_stats:
        print("[WARN] Study 통계 데이터가 없습니다.")
        return
    
    total_counts = [s['total_outcomes'] for s in study_stats]
    success_counts = [s['success_count'] for s in study_stats]
    success_rates = [float(s['success_rate']) for s in study_stats]
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 성공률에 따라 색상 구분
    scatter = ax.scatter(total_counts, success_counts, c=success_rates, 
                        cmap='RdYlGn', s=50, alpha=0.6, edgecolors='black', linewidth=0.5)
    
    # 대각선 (완전 성공 라인)
    max_total = max(total_counts) if total_counts else 1
    ax.plot([0, max_total], [0, max_total], 'r--', linewidth=2, alpha=0.5, label='완전 성공 (100%)')
    
    ax.set_xlabel('전체 Outcome 개수', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_ylabel('성공한 Outcome 개수', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_title('LLM 전처리: Study별 Outcome 성공 개수 vs 전체 개수', fontsize=14, fontweight='bold', pad=20, fontproperties=KOREAN_FONT_PROP)
    ax.grid(alpha=0.3)
    ax.legend(prop=KOREAN_FONT_PROP)
    
    # 컬러바 추가
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('성공률 (%)', fontsize=10, fontproperties=KOREAN_FONT_PROP)
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/llm_study_outcome_success_vs_total_scatter.png', dpi=300, bbox_inches='tight')
    print(f"[OK] 그래프 저장: {output_dir}/llm_study_outcome_success_vs_total_scatter.png")
    plt.close()


def main():
    """메인 함수"""
    print("=" * 80)
    print("[START] LLM 전처리 결과 Study별 Outcome 분포 시각화 시작")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        
        # Study별 통계 조회
        print("\n[STEP 1] Study별 통계 조회 중...")
        study_stats = get_study_statistics(conn)
        
        if not study_stats:
            print("[ERROR] Study 통계 데이터가 없습니다!")
            conn.close()
            return
        
        total_studies = len(study_stats)
        perfect_success = sum(1 for s in study_stats if s['success_rate'] == 100.0)
        partial_success = sum(1 for s in study_stats if 0 < s['success_rate'] < 100.0)
        complete_failure = sum(1 for s in study_stats if s['success_rate'] == 0.0)
        
        print(f"\n[INFO] Study 통계:")
        print(f"  전체 Studies: {total_studies:,}개")
        print(f"  완전 성공 (100%): {perfect_success:,}개 ({perfect_success/total_studies*100:.1f}%)")
        print(f"  부분 성공 (1-99%): {partial_success:,}개 ({partial_success/total_studies*100:.1f}%)")
        print(f"  완전 실패 (0%): {complete_failure:,}개 ({complete_failure/total_studies*100:.1f}%)")
        
        # 시각화
        print("\n[STEP 2] Study별 성공한 outcome 개수 Histogram 생성 중...")
        plot_success_count_histogram(study_stats)
        
        print("\n[STEP 3] 성공률 구간별 Bar Chart 생성 중...")
        plot_success_rate_distribution(study_stats)
        
        print("\n[STEP 4] 성공 개수 vs 전체 개수 Scatter Plot 생성 중...")
        plot_success_vs_total_scatter(study_stats)
        
        print("\n" + "=" * 80)
        print("[OK] 시각화 완료!")
        print("=" * 80)
        print("\n생성된 파일:")
        print("  - visualization/llm_study_outcome_success_count_histogram.png")
        print("  - visualization/llm_study_outcome_success_rate_distribution.png")
        print("  - visualization/llm_study_outcome_success_vs_total_scatter.png")
        
        conn.close()
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()

