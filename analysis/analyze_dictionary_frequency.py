"""
Dictionary 빈도수 분석 스크립트

measure_code 검출 빈도수와 약어 검출 빈도수를 분석합니다.
- Outcome 기준 measure_code 검출 빈도수
- Study 기준 measure_code 검출 빈도수 (대표 outcome으로 변환 후)
- 괄호 안 약어 검출 빈도수
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


def get_measure_code_frequency_by_outcome(conn):
    """Outcome 기준 measure_code 검출 빈도수"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                o.measure_code,
                d.canonical_name,
                d.domain,
                COUNT(*) as detection_count,
                COUNT(DISTINCT o.nct_id) as study_count,
                COUNT(*) FILTER (WHERE o.outcome_type = 'PRIMARY') as primary_count,
                COUNT(*) FILTER (WHERE o.outcome_type = 'SECONDARY') as secondary_count
            FROM outcome_normalized o
            JOIN outcome_measure_dict d ON o.measure_code = d.measure_code
            WHERE o.measure_code IS NOT NULL
            GROUP BY o.measure_code, d.canonical_name, d.domain
            ORDER BY detection_count DESC
        """)
        return cur.fetchall()


def get_measure_code_frequency_by_study(conn):
    """Study 기준 measure_code 검출 빈도수 (대표 outcome으로 변환 후)"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            WITH study_measures AS (
                SELECT 
                    nct_id,
                    measure_code,
                    COUNT(*) as count
                FROM outcome_normalized
                WHERE measure_code IS NOT NULL
                GROUP BY nct_id, measure_code
            )
            SELECT 
                sm.measure_code,
                d.canonical_name,
                d.domain,
                COUNT(DISTINCT sm.nct_id) as study_count,
                SUM(sm.count) as total_outcome_count
            FROM study_measures sm
            JOIN outcome_measure_dict d ON sm.measure_code = d.measure_code
            GROUP BY sm.measure_code, d.canonical_name, d.domain
            ORDER BY study_count DESC
        """)
        return cur.fetchall()


def get_abbreviation_frequency(conn):
    """괄호 안 약어 검출 빈도수"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                measure_abbreviation,
                COUNT(*) as detection_count,
                COUNT(DISTINCT nct_id) as study_count,
                COUNT(*) FILTER (WHERE measure_code IS NOT NULL) as matched_count,
                COUNT(*) FILTER (WHERE measure_code IS NULL) as unmatched_count,
                ROUND(
                    COUNT(*) FILTER (WHERE measure_code IS NOT NULL)::NUMERIC / 
                    COUNT(*)::NUMERIC * 100, 
                    2
                ) as match_rate
            FROM outcome_normalized
            WHERE measure_abbreviation IS NOT NULL
            GROUP BY measure_abbreviation
            ORDER BY detection_count DESC
        """)
        return cur.fetchall()


def get_unmatched_abbreviation_frequency(conn):
    """Dictionary에 매칭되지 않은 약어 검출 빈도수"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                measure_abbreviation,
                COUNT(*) as detection_count,
                COUNT(DISTINCT nct_id) as study_count,
                COUNT(*) FILTER (WHERE outcome_type = 'PRIMARY') as primary_count,
                COUNT(*) FILTER (WHERE outcome_type = 'SECONDARY') as secondary_count,
                (
                    SELECT STRING_AGG(measure_raw, ' | ' ORDER BY measure_raw)
                    FROM (
                        SELECT DISTINCT measure_raw
                        FROM outcome_normalized o2
                        WHERE o2.measure_abbreviation = o.measure_abbreviation
                          AND o2.measure_code IS NULL
                        LIMIT 5
                    ) sub
                ) as sample_measures
            FROM outcome_normalized o
            WHERE measure_abbreviation IS NOT NULL
              AND measure_code IS NULL
            GROUP BY measure_abbreviation
            ORDER BY detection_count DESC
        """)
        return cur.fetchall()


def plot_measure_code_frequency_by_outcome(measure_stats, output_dir='visualization', top_n=50):
    """Outcome 기준 measure_code 빈도수 Bar Chart"""
    if not measure_stats:
        return
    
    top_measures = measure_stats[:top_n]
    codes = [m['measure_code'] for m in top_measures]
    counts = [m['detection_count'] for m in top_measures]
    
    fig, ax = plt.subplots(figsize=(16, 10))
    
    bars = ax.barh(range(len(codes)), counts, color='#3498db', alpha=0.7)
    
    # 값 표시
    for i, (bar, count) in enumerate(zip(bars, counts)):
        ax.text(bar.get_width(), bar.get_y() + bar.get_height()/2.,
               f'{count:,}',
               ha='left', va='center', fontsize=9, fontweight='bold')
    
    ax.set_yticks(range(len(codes)))
    ax.set_yticklabels(codes, fontsize=9)
    ax.set_xlabel('검출 빈도수 (Outcome 기준)', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_ylabel('Measure Code', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_title(f'Top {top_n} Measure Code 검출 빈도수 (Outcome 기준)', fontsize=14, fontweight='bold', pad=20, fontproperties=KOREAN_FONT_PROP)
    ax.grid(axis='x', alpha=0.3)
    ax.invert_yaxis()
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/measure_code_frequency_by_outcome_top{top_n}.png', dpi=300, bbox_inches='tight')
    print(f"[OK] 그래프 저장: {output_dir}/measure_code_frequency_by_outcome_top{top_n}.png")
    plt.close()


def plot_measure_code_frequency_by_study(study_stats, output_dir='visualization', top_n=50):
    """Study 기준 measure_code 빈도수 Bar Chart"""
    if not study_stats:
        return
    
    top_measures = study_stats[:top_n]
    codes = [m['measure_code'] for m in top_measures]
    counts = [m['study_count'] for m in top_measures]
    
    fig, ax = plt.subplots(figsize=(16, 10))
    
    bars = ax.barh(range(len(codes)), counts, color='#2ecc71', alpha=0.7)
    
    # 값 표시
    for i, (bar, count) in enumerate(zip(bars, counts)):
        ax.text(bar.get_width(), bar.get_y() + bar.get_height()/2.,
               f'{count:,}',
               ha='left', va='center', fontsize=9, fontweight='bold')
    
    ax.set_yticks(range(len(codes)))
    ax.set_yticklabels(codes, fontsize=9)
    ax.set_xlabel('검출 빈도수 (Study 기준)', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_ylabel('Measure Code', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_title(f'Top {top_n} Measure Code 검출 빈도수 (Study 기준)', fontsize=14, fontweight='bold', pad=20, fontproperties=KOREAN_FONT_PROP)
    ax.grid(axis='x', alpha=0.3)
    ax.invert_yaxis()
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/measure_code_frequency_by_study_top{top_n}.png', dpi=300, bbox_inches='tight')
    print(f"[OK] 그래프 저장: {output_dir}/measure_code_frequency_by_study_top{top_n}.png")
    plt.close()


def plot_unmatched_abbreviation_frequency(unmatched_stats, output_dir='visualization', top_n=50):
    """매칭되지 않은 약어 검출 빈도수 Bar Chart"""
    if not unmatched_stats:
        print("[WARN] 매칭되지 않은 약어가 없습니다.")
        return
    
    top_abbrevs = unmatched_stats[:top_n]
    abbrevs = [a['measure_abbreviation'] for a in top_abbrevs]
    counts = [a['detection_count'] for a in top_abbrevs]
    
    fig, ax = plt.subplots(figsize=(16, 12))
    
    bars = ax.barh(range(len(abbrevs)), counts, color='#e74c3c', alpha=0.7)
    
    # 값 표시
    for i, (bar, count) in enumerate(zip(bars, counts)):
        ax.text(bar.get_width(), bar.get_y() + bar.get_height()/2.,
               f'{count:,}',
               ha='left', va='center', fontsize=9, fontweight='bold')
    
    ax.set_yticks(range(len(abbrevs)))
    ax.set_yticklabels(abbrevs, fontsize=9)
    ax.set_xlabel('검출 빈도수', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_ylabel('약어', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_title(f'Top {top_n} 매칭되지 않은 약어 검출 빈도수', fontsize=14, fontweight='bold', pad=20, fontproperties=KOREAN_FONT_PROP)
    ax.grid(axis='x', alpha=0.3)
    ax.invert_yaxis()
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/unmatched_abbreviation_frequency_top{top_n}.png', dpi=300, bbox_inches='tight')
    print(f"[OK] 그래프 저장: {output_dir}/unmatched_abbreviation_frequency_top{top_n}.png")
    plt.close()


def plot_abbreviation_frequency(abbrev_stats, output_dir='visualization', top_n=50):
    """약어 검출 빈도수 Bar Chart"""
    if not abbrev_stats:
        return
    
    top_abbrevs = abbrev_stats[:top_n]
    abbrevs = [a['measure_abbreviation'] for a in top_abbrevs]
    counts = [a['detection_count'] for a in top_abbrevs]
    match_rates = [float(a['match_rate']) for a in top_abbrevs]
    
    fig, ax = plt.subplots(figsize=(16, 10))
    
    # 색상: 매칭률에 따라 구분
    colors = ['#2ecc71' if rate >= 50 else '#f39c12' if rate > 0 else '#e74c3c' for rate in match_rates]
    
    bars = ax.barh(range(len(abbrevs)), counts, color=colors, alpha=0.7)
    
    # 값 표시
    for i, (bar, count, rate) in enumerate(zip(bars, counts, match_rates)):
        ax.text(bar.get_width(), bar.get_y() + bar.get_height()/2.,
               f'{count:,} ({rate:.1f}%)',
               ha='left', va='center', fontsize=9, fontweight='bold')
    
    ax.set_yticks(range(len(abbrevs)))
    ax.set_yticklabels(abbrevs, fontsize=9)
    ax.set_xlabel('검출 빈도수', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_ylabel('약어', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_title(f'Top {top_n} 약어 검출 빈도수 (괄호 안 약어)', fontsize=14, fontweight='bold', pad=20, fontproperties=KOREAN_FONT_PROP)
    ax.grid(axis='x', alpha=0.3)
    ax.invert_yaxis()
    
    # 범례
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#2ecc71', alpha=0.7, label='매칭률 ≥50%'),
        Patch(facecolor='#f39c12', alpha=0.7, label='매칭률 1-49%'),
        Patch(facecolor='#e74c3c', alpha=0.7, label='매칭률 0%')
    ]
    ax.legend(handles=legend_elements, prop=KOREAN_FONT_PROP, loc='lower right')
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/abbreviation_frequency_top{top_n}.png', dpi=300, bbox_inches='tight')
    print(f"[OK] 그래프 저장: {output_dir}/abbreviation_frequency_top{top_n}.png")
    plt.close()


def plot_domain_distribution(measure_stats, output_dir='visualization'):
    """Domain별 분포 Pie Chart"""
    if not measure_stats:
        return
    
    domain_counts = {}
    for stat in measure_stats:
        domain = stat['domain'] or 'UNKNOWN'
        domain_counts[domain] = domain_counts.get(domain, 0) + stat['detection_count']
    
    domains = list(domain_counts.keys())
    counts = list(domain_counts.values())
    
    # 상위 10개만 표시하고 나머지는 "기타"로 합침
    sorted_domains = sorted(zip(domains, counts), key=lambda x: x[1], reverse=True)
    top_domains = sorted_domains[:10]
    other_count = sum(count for _, count in sorted_domains[10:])
    
    if other_count > 0:
        top_domains.append(('기타', other_count))
    
    labels = [d[0] for d in top_domains]
    sizes = [d[1] for d in top_domains]
    
    fig, ax = plt.subplots(figsize=(12, 10))
    
    colors = plt.cm.Set3(range(len(labels)))
    wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                                      colors=colors, startangle=90,
                                      textprops={'fontsize': 10, 'fontproperties': KOREAN_FONT_PROP})
    
    for autotext in autotexts:
        autotext.set_color('black')
        autotext.set_fontsize(9)
        autotext.set_fontweight('bold')
    
    ax.set_title('Domain별 Measure Code 분포', fontsize=14, fontweight='bold', pad=20, fontproperties=KOREAN_FONT_PROP)
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/domain_distribution.png', dpi=300, bbox_inches='tight')
    print(f"[OK] 그래프 저장: {output_dir}/domain_distribution.png")
    plt.close()


def generate_unmatched_report(unmatched_stats, output_dir='reports'):
    """매칭되지 않은 약어 리포트 생성"""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = f'{output_dir}/unmatched_abbreviation_report_{timestamp}.md'
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('# 매칭되지 않은 약어 리포트\n\n')
        f.write(f'생성일시: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
        f.write('## Top 50 매칭되지 않은 약어\n\n')
        f.write('| 약어 | 검출 횟수 | Study 수 | Primary | Secondary | 샘플 Measure |\n')
        f.write('|------|----------|---------|---------|----------|-------------|\n')
        for stat in unmatched_stats[:50]:
            sample = stat['sample_measures'] or 'N/A'
            if len(sample) > 50:
                sample = sample[:47] + '...'
            f.write(f"| {stat['measure_abbreviation']} | {stat['detection_count']:,} | "
                   f"{stat['study_count']:,} | {stat['primary_count']:,} | "
                   f"{stat['secondary_count']:,} | {sample} |\n")
        
        total_unmatched = sum(s['detection_count'] for s in unmatched_stats)
        f.write(f'\n## 전체 통계\n\n')
        f.write(f"- 전체 매칭되지 않은 약어 종류: {len(unmatched_stats):,}개\n")
        f.write(f"- 전체 매칭되지 않은 약어 검출 횟수: {total_unmatched:,}건\n")
    
    print(f"[OK] 리포트 저장: {report_path}")


def generate_report(outcome_stats, study_stats, abbrev_stats, output_dir='reports'):
    """통계 리포트 생성"""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = f'{output_dir}/dictionary_frequency_report_{timestamp}.md'
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('# Dictionary 빈도수 분석 리포트\n\n')
        f.write(f'생성일시: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
        
        f.write('## 1. Outcome 기준 Measure Code 검출 빈도수 (Top 20)\n\n')
        f.write('| Measure Code | Canonical Name | Domain | 검출 횟수 | Study 수 | Primary | Secondary |\n')
        f.write('|-------------|---------------|--------|----------|---------|---------|----------|\n')
        for stat in outcome_stats[:20]:
            f.write(f"| {stat['measure_code']} | {stat['canonical_name']} | {stat['domain'] or 'N/A'} | "
                   f"{stat['detection_count']:,} | {stat['study_count']:,} | "
                   f"{stat['primary_count']:,} | {stat['secondary_count']:,} |\n")
        
        f.write('\n## 2. Study 기준 Measure Code 검출 빈도수 (Top 20)\n\n')
        f.write('| Measure Code | Canonical Name | Domain | Study 수 | Outcome 수 |\n')
        f.write('|-------------|---------------|--------|---------|----------|\n')
        for stat in study_stats[:20]:
            f.write(f"| {stat['measure_code']} | {stat['canonical_name']} | {stat['domain'] or 'N/A'} | "
                   f"{stat['study_count']:,} | {stat['total_outcome_count']:,} |\n")
        
        f.write('\n## 3. 약어 검출 빈도수 (Top 20)\n\n')
        f.write('| 약어 | 검출 횟수 | Study 수 | 매칭 성공 | 매칭 실패 | 매칭률 |\n')
        f.write('|------|----------|---------|----------|----------|--------|\n')
        for stat in abbrev_stats[:20]:
            f.write(f"| {stat['measure_abbreviation']} | {stat['detection_count']:,} | "
                   f"{stat['study_count']:,} | {stat['matched_count']:,} | "
                   f"{stat['unmatched_count']:,} | {stat['match_rate']:.2f}% |\n")
        
        # 전체 통계
        total_outcomes = sum(s['detection_count'] for s in outcome_stats)
        total_studies = len(set(s['study_count'] for s in study_stats))
        total_abbrevs = sum(s['detection_count'] for s in abbrev_stats)
        matched_abbrevs = sum(s['matched_count'] for s in abbrev_stats)
        
        f.write('\n## 4. 전체 통계\n\n')
        f.write(f"- 전체 Measure Code 검출 횟수 (Outcome 기준): {total_outcomes:,}건\n")
        f.write(f"- 사용된 Measure Code 종류: {len(outcome_stats):,}개\n")
        f.write(f"- 전체 약어 검출 횟수: {total_abbrevs:,}건\n")
        f.write(f"- 약어 매칭 성공: {matched_abbrevs:,}건 ({matched_abbrevs/total_abbrevs*100:.2f}%)\n")
        f.write(f"- 약어 매칭 실패: {total_abbrevs - matched_abbrevs:,}건 ({(total_abbrevs - matched_abbrevs)/total_abbrevs*100:.2f}%)\n")
    
    print(f"[OK] 리포트 저장: {report_path}")


def main():
    """메인 함수"""
    print("=" * 80)
    print("[START] Dictionary 빈도수 분석 시작")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        
        # Outcome 기준 measure_code 빈도수
        print("\n[STEP 1] Outcome 기준 measure_code 빈도수 조회 중...")
        outcome_stats = get_measure_code_frequency_by_outcome(conn)
        print(f"  조회 완료: {len(outcome_stats):,}개 measure_code")
        
        # Study 기준 measure_code 빈도수
        print("\n[STEP 2] Study 기준 measure_code 빈도수 조회 중...")
        study_stats = get_measure_code_frequency_by_study(conn)
        print(f"  조회 완료: {len(study_stats):,}개 measure_code")
        
        # 약어 빈도수
        print("\n[STEP 3] 약어 검출 빈도수 조회 중...")
        abbrev_stats = get_abbreviation_frequency(conn)
        print(f"  조회 완료: {len(abbrev_stats):,}개 약어")
        
        # 매칭되지 않은 약어 빈도수
        print("\n[STEP 3-1] 매칭되지 않은 약어 검출 빈도수 조회 중...")
        unmatched_stats = get_unmatched_abbreviation_frequency(conn)
        print(f"  조회 완료: {len(unmatched_stats):,}개 매칭되지 않은 약어")
        
        # 시각화
        print("\n[STEP 4] Outcome 기준 measure_code 빈도수 그래프 생성 중...")
        plot_measure_code_frequency_by_outcome(outcome_stats, top_n=50)
        
        print("\n[STEP 5] Study 기준 measure_code 빈도수 그래프 생성 중...")
        plot_measure_code_frequency_by_study(study_stats, top_n=50)
        
        print("\n[STEP 6] 약어 검출 빈도수 그래프 생성 중...")
        plot_abbreviation_frequency(abbrev_stats, top_n=50)
        
        print("\n[STEP 6-1] 매칭되지 않은 약어 빈도수 그래프 생성 중...")
        plot_unmatched_abbreviation_frequency(unmatched_stats, top_n=50)
        
        print("\n[STEP 7] Domain별 분포 그래프 생성 중...")
        plot_domain_distribution(outcome_stats)
        
        # 리포트 생성
        print("\n[STEP 8] 통계 리포트 생성 중...")
        generate_report(outcome_stats, study_stats, abbrev_stats)
        
        print("\n[STEP 8-1] 매칭되지 않은 약어 리포트 생성 중...")
        generate_unmatched_report(unmatched_stats)
        
        # 통계 요약 출력
        print("\n" + "=" * 80)
        print("[INFO] 통계 요약")
        print("=" * 80)
        print(f"\nOutcome 기준 Top 5 Measure Code:")
        for i, stat in enumerate(outcome_stats[:5], 1):
            print(f"  {i}. {stat['measure_code']}: {stat['detection_count']:,}회 검출 ({stat['study_count']:,}개 Studies)")
        
        print(f"\nStudy 기준 Top 5 Measure Code:")
        for i, stat in enumerate(study_stats[:5], 1):
            print(f"  {i}. {stat['measure_code']}: {stat['study_count']:,}개 Studies")
        
        print(f"\nTop 5 약어:")
        for i, stat in enumerate(abbrev_stats[:5], 1):
            print(f"  {i}. {stat['measure_abbreviation']}: {stat['detection_count']:,}회 검출 (매칭률: {stat['match_rate']:.2f}%)")
        
        print(f"\nTop 5 매칭되지 않은 약어:")
        for i, stat in enumerate(unmatched_stats[:5], 1):
            print(f"  {i}. {stat['measure_abbreviation']}: {stat['detection_count']:,}회 검출 ({stat['study_count']:,}개 Studies)")
        
        print("\n" + "=" * 80)
        print("[OK] Dictionary 빈도수 분석 완료!")
        print("=" * 80)
        print("\n생성된 파일:")
        print("  - visualization/measure_code_frequency_by_outcome_top50.png")
        print("  - visualization/measure_code_frequency_by_study_top50.png")
        print("  - visualization/abbreviation_frequency_top50.png")
        print("  - visualization/unmatched_abbreviation_frequency_top50.png")
        print("  - visualization/domain_distribution.png")
        print("  - reports/dictionary_frequency_report_*.md")
        print("  - reports/unmatched_abbreviation_report_*.md")
        
        conn.close()
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()

