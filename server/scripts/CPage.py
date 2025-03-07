import re

class CPage:
    def __init__(self, name, rules):
        self.name = name
        self.rules = [self.parseRule(r) for r in rules]
        self.transitions = {}

    @staticmethod
    def parseRule(rule):
        # 解析带区域范围的规则 示例："金币[12,0,0,30]"
        match = re.match(r"(.+?)\[([\d,]+)\]$", rule)
        if match:
            text, area = match.groups()
            region = list(map(int, area.split(',')))
            return {'pattern': re.compile(text), 'region': region}
        return {'pattern': re.compile(rule), 'region': None} 