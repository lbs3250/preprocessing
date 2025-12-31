"""
정규화 패턴 정의 및 파싱 함수

timeFrame, measure 등의 정규화를 위한 패턴 정의 및 파싱 로직
"""

import re
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


class TimeFramePatterns:
    """timeFrame 파싱을 위한 정규식 패턴 클래스"""
    
    def __init__(self):
        # 1. Baseline 포함 패턴 (최우선): change_from_baseline_flag = TRUE
        self.baseline = re.compile(r'\bbaseline\b', re.IGNORECASE)
        
        # 2. "At Day/Week/Month N" 패턴
        self.at_day = re.compile(r'\bat\s+(day|days)\s+\d+', re.IGNORECASE)
        self.at_week = re.compile(r'\bat\s+(week|weeks)\s+\d+', re.IGNORECASE)
        self.at_month = re.compile(r'\bat\s+(month|months)\s+\d+', re.IGNORECASE)
        
        # 3. "Day N", "Month N", "Week N" 단독 패턴 (복수형 포함, 하이픈 포함)
        self.day_standalone = re.compile(r'\b(day|days)\s+\d+', re.IGNORECASE)
        self.month_standalone = re.compile(r'\b(month|months)\s+\d+', re.IGNORECASE)
        self.week_standalone = re.compile(r'\b(week|weeks)\s+\d+', re.IGNORECASE)
        
        # 4. "Day N to Day M", "Day N through M" 패턴
        self.day_to = re.compile(r'\bday\s+\d+\s+to\s+day\s+\d+', re.IGNORECASE)
        self.day_through = re.compile(r'\bday\s+\d+\s+through\s+\d+', re.IGNORECASE)
        
        # 5. "For N Months/Weeks/Days/Minutes" 패턴
        self.for_period = re.compile(r'\bfor\s+\d+\s+(month|months|week|weeks|day|days|hour|hours|min|mins|minute|minutes)', re.IGNORECASE)
        
        # 6. "At Months N and M" 패턴
        self.at_months = re.compile(r'\bat\s+months?\s+\d+\s+and\s+\d+', re.IGNORECASE)
        
        # 7. 기존 패턴들
        self.year = re.compile(r'year\s*\d+', re.IGNORECASE)
        self.up_to = re.compile(r'up\s*to\s+\d+', re.IGNORECASE)  # "Upto" (띄어쓰기 없음) 지원
        self.through = re.compile(r'through\s+(study|completion|end)', re.IGNORECASE)
        
        # 8. 텍스트 숫자 패턴 ("Two years", "eight weeks", "thirty minutes" 등)
        self.text_number = re.compile(
            r'\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|'
            r'thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|'
            r'twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)\s+'
            r'(week|weeks|month|months|year|years|day|days|hour|hours|min|mins|minute|minutes)\b',
            re.IGNORECASE
        )
        
        # 9. 숫자+단위 패턴 (하이픈 포함, hr/hrs, min/mins/minute/minutes 단위 포함)
        # 예: "26 weeks", "96-week", "21-months", "48 hr", "30 minutes", "2 min" 등
        self.period = re.compile(r'\d+\s*-?\s*(week|weeks|month|months|year|years|day|days|hour|hours|hr|hrs|min|mins|minute|minutes)', re.IGNORECASE)
        
        # 10. "Up to Day/Week/Month N" 패턴 (단위 포함)
        self.up_to_with_unit = re.compile(r'up\s*to\s+(day|days|week|weeks|month|months|year|years)\s+\d+', re.IGNORECASE)
        
        # 11. 복수 시점 패턴 ("Week 1, Week 14" 등)
        self.multiple_timepoints = re.compile(r'(week|weeks|day|days|month|months)\s+\d+.*?,\s*(week|weeks|day|days|month|months)\s+\d+', re.IGNORECASE)
        
        # 12. 기타 패턴 (분류용)
        self.percent = re.compile(r'%|percent|percentage', re.IGNORECASE)
        self.time = re.compile(r'time\s+to\s+(respond|complete|finish)', re.IGNORECASE)
    
    def classify_timeframe(self, time_frame: str) -> Optional[str]:
        """
        timeFrame을 패턴별로 분류
        
        Returns:
            패턴 타입 문자열 또는 None
        """
        if not time_frame:
            return None
        
        # 우선순위 순서대로 체크
        if self.baseline.search(time_frame):
            return 'baseline'
        elif self.at_day.search(time_frame) or self.at_week.search(time_frame) or self.at_month.search(time_frame):
            return 'at_day_week_month'
        elif self.day_standalone.search(time_frame) or self.month_standalone.search(time_frame) or self.week_standalone.search(time_frame):
            return 'day_month_week_standalone'
        elif self.day_to.search(time_frame) or self.day_through.search(time_frame):
            return 'day_to_through'
        elif self.for_period.search(time_frame):
            return 'for_period'
        elif self.at_months.search(time_frame):
            return 'at_months_and'
        elif self.year.search(time_frame):
            return 'year'
        elif self.up_to_with_unit.search(time_frame):
            return 'upto_with_unit'
        elif self.up_to.search(time_frame):
            return 'upto'
        elif self.multiple_timepoints.search(time_frame):
            return 'multiple_timepoints'
        elif self.through.search(time_frame):
            return 'through'
        elif self.text_number.search(time_frame):
            return 'text_number'
        elif self.period.search(time_frame):
            return 'period'
        elif self.percent.search(time_frame):
            return 'percent'
        elif self.time.search(time_frame):
            return 'time'
        else:
            return 'unparseable'
    
    def get_pattern_code(self, time_frame: str) -> Optional[str]:
        """
        timeFrame에 매칭된 패턴 코드 반환 (패턴1, 패턴2 등)
        
        Returns:
            패턴 코드 문자열 (예: 'PATTERN1', 'PATTERN2') 또는 None
        """
        pattern_type = self.classify_timeframe(time_frame)
        if not pattern_type:
            return None
        
        # 패턴 타입을 패턴 코드로 매핑
        pattern_code_map = {
            'baseline': 'PATTERN1',
            'at_day_week_month': 'PATTERN2',
            'day_month_week_standalone': 'PATTERN3',
            'day_to_through': 'PATTERN4',
            'for_period': 'PATTERN5',
            'at_months_and': 'PATTERN6',
            'year': 'PATTERN7',
            'upto_with_unit': 'PATTERN8',
            'upto': 'PATTERN9',
            'multiple_timepoints': 'PATTERN10',
            'through': 'PATTERN11',
            'text_number': 'PATTERN12',
            'period': 'PATTERN13',
            'percent': 'PATTERN14',
            'time': 'PATTERN15',
            'unparseable': None
        }
        
        return pattern_code_map.get(pattern_type)
    
    def is_parseable(self, time_frame: str) -> bool:
        """timeFrame이 파싱 가능한지 확인"""
        pattern_type = self.classify_timeframe(time_frame)
        parseable_types = [
            'baseline', 'at_day_week_month', 'day_month_week_standalone',
            'day_to_through', 'for_period', 'at_months_and',
            'text_number', 'period', 'year', 'upto', 'upto_with_unit',
            'multiple_timepoints', 'through'
        ]
        return pattern_type in parseable_types if pattern_type else False


class MeasurePatterns:
    """measure 파싱을 위한 정규식 패턴 클래스"""
    
    def __init__(self):
        # 약어 추출 패턴 (괄호 안 약어)
        # 대문자로 시작하는 약어 (슬래시, 소문자 포함)
        # 예: (TMT-A/B), (pharmacodynamics) 등
        self.abbreviation = re.compile(r'\([A-Za-z][A-Za-z0-9\-+\s/]+\)')
        
        # 필터링할 패턴들 (약어로 추출하면 안 되는 것들)
        # 1. 단위 패턴 (ml/d, ng/ml, mg/kg 등)
        self.unit_pattern = re.compile(
            r'\b(ml|mg|g|kg|mcg|μg|µg|iu|units?|d|h|hr|hrs|min|mins|day|days|week|weeks|month|months|year|years)\s*[/]\s*(ml|mg|g|kg|mcg|μg|µg|iu|units?|d|h|hr|hrs|min|mins|day|days|week|weeks|month|months|year|years|d|kg|m2|m\^2)\b',
            re.IGNORECASE
        )
        
        # 2. 시간/파트 관련 패턴 (Week 1, Part 1, Day 1, W0 등)
        self.time_part_pattern = re.compile(
            r'\b(week|day|part|w|d|cohort|arm|aim)\s*[-]?\s*\d+\b',
            re.IGNORECASE
        )
        
        # 3. Arms/Cohorts 관련 패턴 (Arms 1 and 2, Cohorts A and B 등)
        self.arms_cohorts_pattern = re.compile(
            r'\b(arms?|cohorts?)\s+[A-Z0-9]+\s+(and|&|\+)\s+[A-Z0-9]+',
            re.IGNORECASE
        )
        
        # 4. 숫자만 있는 패턴 (screening, participant 등과 함께)
        self.number_only_pattern = re.compile(
            r'^\d+$'
        )
        
        # 5. 기타 의미없는 패턴들
        self.meaningless_patterns = [
            re.compile(r'\b(screening|baseline|participant|persons?)\b', re.IGNORECASE),
            re.compile(r'\b(post[-\s]?study|pre[-\s]?dose|safety\s+assessment)\b', re.IGNORECASE),
            re.compile(r'\b(safety|efficacy|primary|secondary)\s+assessments?\b', re.IGNORECASE),
            re.compile(r'\bend\s+of\s+period\b', re.IGNORECASE),
        ]
    
    def has_abbreviation(self, measure: str) -> bool:
        """measure에 약어가 포함되어 있는지 확인"""
        if not measure:
            return False
        return bool(self.abbreviation.search(measure))
    
    def is_valid_abbreviation(self, abbrev_text: str) -> bool:
        """
        추출된 약어가 유효한 약어인지 확인
        
        Args:
            abbrev_text: 괄호를 제거한 약어 텍스트 (예: "ADAS-Cog-13", "ml/d")
        
        Returns:
            유효한 약어면 True, 필터링해야 하면 False
        """
        if not abbrev_text:
            return False
        
        abbrev_lower = abbrev_text.lower().strip()
        
        # 1. 단위 패턴 체크
        if self.unit_pattern.search(abbrev_text):
            return False
        
        # 2. 시간/파트 관련 패턴 체크
        if self.time_part_pattern.search(abbrev_text):
            return False
        
        # 3. Arms/Cohorts 관련 패턴 체크
        if self.arms_cohorts_pattern.search(abbrev_text):
            return False
        
        # 4. 숫자만 있는 경우 제외
        if self.number_only_pattern.match(abbrev_lower):
            return False
        
        # 5. 기타 의미없는 패턴 체크
        # "assessments" 또는 "assessment"가 포함된 경우 약어가 아님
        if 'assessments' in abbrev_lower or 'assessment' in abbrev_lower:
            return False
        
        # "end of period" 같은 일반 문구는 약어가 아님
        if 'end of period' in abbrev_lower:
            return False
        
        for pattern in self.meaningless_patterns:
            if pattern.search(abbrev_text):
                # 단, "persons with dementia" 같은 경우는 제외하되, 
                # "screening", "baseline" 등만 있는 경우는 제외
                if abbrev_lower in ['screening', 'baseline', 'participant']:
                    return False
                return False
        
        # 6. 너무 짧은 경우 (1-2자) 제외 (단, 알파벳만 있는 경우는 허용)
        if len(abbrev_lower) <= 2 and not re.match(r'^[A-Za-z]{1,2}$', abbrev_text):
            return False
        
        return True


class DescriptionPatterns:
    """description 파싱을 위한 정규식 패턴 클래스"""
    
    def __init__(self):
        # change from baseline 패턴
        self.change_from_baseline = re.compile(
            r'change\s+(from|of)\s+baseline|difference\s+from\s+baseline',
            re.IGNORECASE
        )
    
    def has_change_from_baseline(self, description: str) -> bool:
        """description에 change from baseline 패턴이 있는지 확인"""
        if not description:
            return False
        return bool(self.change_from_baseline.search(description))


# 전역 인스턴스
timeframe_patterns = TimeFramePatterns()
measure_patterns = MeasurePatterns()
description_patterns = DescriptionPatterns()


def get_sql_parseable_conditions() -> Dict[str, str]:
    """
    SQL 쿼리에서 사용할 파싱 가능 조건 반환
    
    Returns:
        파싱 가능한 패턴의 SQL 조건 딕셔너리
    """
    return {
        'baseline': r"(^|[^a-z])baseline([^a-z]|$)",
        'at_day_week_month': r"\bat\s+(day|days|week|weeks|month|months)\s+\d+",
        'day_month_week_standalone': r"\b(day|days|month|months|week|weeks)\s+\d+",
        'day_to_through': r"\bday\s+\d+\s+(to|through)\s+(day\s+)?\d+",
        'for_period': r"\bfor\s+\d+\s+(month|months|week|weeks|day|days)",
        'at_months_and': r"\bat\s+months?\s+\d+\s+and\s+\d+",
        'text_number': r"(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)\s+(week|weeks|month|months|year|years|day|days|hour|hours)",
        'period': r"\d+\s*-?\s*(week|weeks|month|months|year|years|day|days|hour|hours|hr|hrs)",
        'year': r"year\s*\d+",
        'upto': r"up\s*to\s+\d+",
        'upto_with_unit': r"up\s*to\s+(day|days|week|weeks|month|months|year|years)\s+\d+",
        'multiple_timepoints': r"(week|weeks|day|days|month|months)\s+\d+.*?,\s*(week|weeks|day|days|month|months)\s+\d+",
        'through': r"through.*completion.*\d+\s*(week|weeks|month|months|year|years)"
    }


def get_sql_unparseable_condition() -> str:
    """
    SQL 쿼리에서 사용할 파싱 불가능 조건 반환
    
    Returns:
        파싱 불가능한 패턴을 제외하는 SQL 조건 문자열
    """
    conditions = get_sql_parseable_conditions()
    
    # 모든 파싱 가능한 패턴을 NOT 조건으로 결합
    not_conditions = []
    for pattern_name, pattern_regex in conditions.items():
        not_conditions.append(f"NOT (o.time_frame_raw ~* '{pattern_regex}')")
    
    return " AND ".join(not_conditions)

