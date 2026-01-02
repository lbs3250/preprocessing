import re
from typing import Dict, Optional, List

def normalize_unit(unit_str: str) -> str:
    """단위 문자열을 정규화된 형태로 변환"""
    unit_lower = unit_str.lower()
    unit_norm = unit_lower.rstrip('s')  # 복수형 제거
    
    # 약어 정규화
    if unit_norm in ('h', 'hr', 'hrs'):
        unit_norm = 'hour'
    elif unit_norm in ('min', 'mins'):
        unit_norm = 'minute'
    
    return unit_norm

def parse_test(time_frame: str):
    """테스트용 파싱 함수"""
    time_frame_lower = time_frame.lower()
    result = {
        'time_points': [],
        'time_unit_main': None,
        'change_from_baseline_flag': False
    }
    
    # Baseline 체크
    if re.search(r'\bbaseline\b', time_frame_lower):
        result['change_from_baseline_flag'] = True
    
    # 패턴 1: "Week N", "Day N", "Month N" 형태 (단위 + 숫자)
    pattern1 = re.finditer(r'\b(week|weeks|day|days|month|months|year|years|hour|hours|hr|hrs|min|mins|minute|minutes)\s+(\d+(?:\.\d+)?)', time_frame_lower, re.IGNORECASE)
    for match in pattern1:
        unit_str, num_str = match.groups()
        try:
            num = float(num_str)
            if num > 2000:
                continue
            unit_norm = normalize_unit(unit_str)
            point = {'value': int(num) if num.is_integer() else num, 'unit': unit_norm}
            if not any(p.get('value') == point['value'] and p.get('unit') == point['unit'] for p in result['time_points']):
                result['time_points'].append(point)
        except:
            pass
    
    # 패턴 4: "Days N, M, O and P" 형태
    weeks_comma_pattern = re.search(
        r'\b(week|weeks|day|days|month|months|year|years|hour|hours|hr|hrs|min|mins|minute|minutes)\s+\d+(?:\s*,\s*\d+)+(?:\s+and\s+\d+)?',
        time_frame_lower, 
        re.IGNORECASE
    )
    
    print(f"패턴 4 매칭: {weeks_comma_pattern}")
    if weeks_comma_pattern:
        matched_text = weeks_comma_pattern.group(0)
        print(f"매칭된 텍스트: '{matched_text}'")
        unit_match = re.search(r'\b(week|weeks|day|days|month|months|year|years|hour|hours|hr|hrs|min|mins|minute|minutes)', matched_text, re.IGNORECASE)
        if unit_match:
            unit_str = unit_match.group(1)
            unit_norm = normalize_unit(unit_str)
            print(f"단위: {unit_norm}")
            numbers_in_match = re.findall(r'\b(\d+(?:\.\d+)?)\b', matched_text)
            print(f"추출된 숫자: {numbers_in_match}")
            for num_str in numbers_in_match:
                try:
                    num = float(num_str)
                    if num > 2000:
                        continue
                    num_value = int(num) if num.is_integer() else num
                    point = {'value': num_value, 'unit': unit_norm}
                    if not any(p.get('value') == point['value'] and p.get('unit') == point['unit'] for p in result['time_points']):
                        result['time_points'].append(point)
                except:
                    pass
    
    # time_points 정렬 및 필터링
    numeric_points = [p for p in result['time_points'] if p.get('value') is not None]
    numeric_points = [p for p in numeric_points if isinstance(p.get('value'), (int, float)) and p['value'] <= 2000]
    numeric_points.sort(key=lambda x: (x['value'], x['unit']))
    result['time_points'] = numeric_points
    
    # time_value_main과 time_unit_main 설정
    if numeric_points:
        # 단위별로 최대값 찾기
        unit_max_values = {}
        for point in numeric_points:
            unit = point['unit']
            value = point['value']
            if unit not in unit_max_values or value > unit_max_values[unit]['value']:
                unit_max_values[unit] = {'value': value, 'point': point}
        
        print(f"단위별 최대값: {unit_max_values}")
        
        # 단위 변환을 통한 비교
        unit_weights = {
            'minute': 1/60,
            'hour': 1,
            'day': 24,
            'week': 168,
            'month': 730,
            'year': 8760
        }
        
        if unit_max_values:
            max_converted_value = None
            max_point = None
            
            for unit, data in unit_max_values.items():
                value = data['value']
                weight = unit_weights.get(unit, 1)
                converted_value = value * weight
                print(f"  {unit}: {value} * {weight} = {converted_value}")
                
                if max_converted_value is None or converted_value > max_converted_value:
                    max_converted_value = converted_value
                    max_point = data['point']
            
            if max_point:
                result['time_value_main'] = max_point['value']
                result['time_unit_main'] = max_point['unit']
    
    return result

# 테스트
test_case = "Baseline, and pre-dose at Days 84, 169, 253, 421, 505, 589, and 757"
print(f"원본: {test_case}")
print("\n파싱 결과:")
result = parse_test(test_case)
print(f"\ntime_points: {result['time_points']}")
print(f"time_value_main: {result['time_value_main']}")
print(f"time_unit_main: {result['time_unit_main']}")
