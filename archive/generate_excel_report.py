"""
Excel 리포트 생성 스크립트

diagnosis_data_*.json 파일을 읽어서 Excel 리포트 생성
"""

import json
import glob
import pandas as pd
from datetime import datetime
from pathlib import Path


def load_latest_diagnosis_data():
    """가장 최근 진단 데이터 JSON 파일 로드"""
    json_files = glob.glob("diagnosis_data_*.json")
    if not json_files:
        print("[ERROR] diagnosis_data_*.json 파일을 찾을 수 없습니다.")
        print("먼저 diagnose_all.py를 실행하세요.")
        return None
    
    # 가장 최근 파일 선택
    latest_file = max(json_files, key=Path.stat)
    print(f"📂 데이터 파일 로드: {latest_file}")
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_excel_report(data):
    """Excel 리포트 생성"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_filename = f"diagnosis_report_{timestamp}.xlsx"
    
    with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
        # 1. Summary 시트
        if 'summary' in data:
            summary_df = pd.DataFrame([data['summary']])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # 2. NULL 분석 시트
        if 'null_analysis' in data:
            null_df = pd.DataFrame([data['null_analysis']])
            null_df.to_excel(writer, sheet_name='NULL Analysis', index=False)
        
        # 3. timeFrame 패턴 시트
        if 'timeframe_patterns' in data and data['timeframe_patterns']:
            timeframe_df = pd.DataFrame(data['timeframe_patterns'])
            timeframe_df.to_excel(writer, sheet_name='TimeFrame Patterns', index=False)
        
        # 4. Measure 패턴 시트
        if 'measure_patterns' in data and data['measure_patterns']:
            measure_df = pd.DataFrame(data['measure_patterns'])
            measure_df.to_excel(writer, sheet_name='Top Measures', index=False)
        
        # 5. Description 패턴 시트
        if 'description_patterns' in data:
            desc_df = pd.DataFrame([data['description_patterns']])
            desc_df.to_excel(writer, sheet_name='Description Patterns', index=False)
        
        # 6. Sponsor 분석 시트
        if 'sponsor_analysis' in data and data['sponsor_analysis']:
            sponsor_df = pd.DataFrame(data['sponsor_analysis'])
            sponsor_df.to_excel(writer, sheet_name='Sponsor Analysis', index=False)
        
        # 7. Official 분석 시트
        if 'official_analysis' in data and data['official_analysis']:
            official_df = pd.DataFrame(data['official_analysis'])
            official_df.to_excel(writer, sheet_name='Official Analysis', index=False)
        
        # 8. Sponsor Class 분석 시트
        if 'sponsor_class_analysis' in data and data['sponsor_class_analysis']:
            class_df = pd.DataFrame(data['sponsor_class_analysis'])
            class_df.to_excel(writer, sheet_name='Sponsor Class', index=False)
        
        # 9. 실패율 분석 시트
        if 'failure_rates' in data and data['failure_rates']:
            failure_df = pd.DataFrame(data['failure_rates'])
            failure_df.to_excel(writer, sheet_name='Failure Rates', index=False)
        
        # 10. 정규화 룰 시트
        if 'normalization_rules' in data:
            rules_df = pd.DataFrame([data['normalization_rules']])
            rules_df.to_excel(writer, sheet_name='Normalization Rules', index=False)
        
        # 11. 파싱 가능성 분석 시트
        if 'parseability_analysis' in data:
            parse_df = pd.DataFrame([data['parseability_analysis']])
            parse_df.to_excel(writer, sheet_name='Parseability', index=False)
        
        # 12. 파싱 실패 - 스폰서별 시트
        if 'unparseable_by_sponsor' in data and data['unparseable_by_sponsor']:
            unparse_sponsor_df = pd.DataFrame(data['unparseable_by_sponsor'])
            unparse_sponsor_df.to_excel(writer, sheet_name='Unparseable by Sponsor', index=False)
        
        # 13. 파싱 실패 - 담당자별 시트
        if 'unparseable_by_official' in data and data['unparseable_by_official']:
            unparse_official_df = pd.DataFrame(data['unparseable_by_official'])
            unparse_official_df.to_excel(writer, sheet_name='Unparseable by Official', index=False)
        
        # 14. 기관/담당자 전체 통계 시트
        if 'party_overview' in data:
            party_df = pd.DataFrame([data['party_overview']])
            party_df.to_excel(writer, sheet_name='Party Overview', index=False)
        
        # 15. 기관별 파싱 가능성 상세 시트
        if 'sponsor_parseability' in data and data['sponsor_parseability']:
            sponsor_parse_df = pd.DataFrame(data['sponsor_parseability'])
            sponsor_parse_df.to_excel(writer, sheet_name='Sponsor Parseability', index=False)
        
        # 16. 담당자별 파싱 가능성 상세 시트
        if 'official_parseability' in data and data['official_parseability']:
            official_parse_df = pd.DataFrame(data['official_parseability'])
            official_parse_df.to_excel(writer, sheet_name='Official Parseability', index=False)
        
        # 17. measure 약어 추출 - Study 단위 시트
        if 'measure_by_study' in data:
            measure_study_df = pd.DataFrame([data['measure_by_study']])
            measure_study_df.to_excel(writer, sheet_name='Measure by Study', index=False)
        
        # 18. timeFrame 파싱 - Study 단위 시트
        if 'timeframe_by_study' in data:
            timeframe_study_df = pd.DataFrame([data['timeframe_by_study']])
            timeframe_study_df.to_excel(writer, sheet_name='TimeFrame by Study', index=False)
    
    print(f"\n✅ Excel 리포트 생성 완료: {excel_filename}")
    return excel_filename


def main():
    """메인 함수"""
    print("=" * 80)
    print("📊 Excel 리포트 생성")
    print("=" * 80)
    
    data = load_latest_diagnosis_data()
    if not data:
        return
    
    excel_file = create_excel_report(data)
    
    print(f"\n📋 생성된 시트:")
    print(f"  1. Summary - 전체 요약")
    print(f"  2. NULL Analysis - 컬럼별 누락 건수")
    print(f"  3. Normalization Rules - 정규화 룰 설명")
    print(f"  4. Parseability - 바로 파싱 가능한 건수")
    print(f"  5. Party Overview - 기관/담당자 전체 통계")
    print(f"  6. TimeFrame Patterns - timeFrame 패턴 분석")
    print(f"  7. Top Measures - 상위 measure 목록")
    print(f"  8. Measure by Study - measure 약어 추출 (Study 단위)")
    print(f"  9. TimeFrame by Study - timeFrame 파싱 (Study 단위)")
    print(f"  10. Description Patterns - description 패턴")
    print(f"  11. Sponsor Analysis - 스폰서별 분석")
    print(f"  12. Sponsor Parseability - 기관별 파싱 가능성 상세")
    print(f"  13. Official Analysis - 담당자별 분석")
    print(f"  14. Official Parseability - 담당자별 파싱 가능성 상세")
    print(f"  15. Sponsor Class - 클래스별 분석")
    print(f"  16. Failure Rates - 실패율 분석")
    print(f"  17. Unparseable by Sponsor - 파싱 실패 스폰서별")
    print(f"  18. Unparseable by Official - 파싱 실패 담당자별")


if __name__ == "__main__":
    main()

