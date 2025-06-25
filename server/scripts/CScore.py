import re
import time
import _G
import os
import json
from datetime import datetime
from typing import List

class CScore_:
   
    # 关键文本的正则表达式
    PATTERNS = {
            'coin_section': r'金[币幣]明细?',  # 金币明细区域开始
            'cash_section': r'现金明细?',      # 现金明细区域开始
            'date': r'\d{4}[\.-]\d{1,2}[\.-]\d{1,2}',  # 日期格式
            'amount': r'[+-]?\d+(?:,\d{3})*(?:\.\d+)?金[币幣]?'  # 金额格式
        }
    
    @classmethod
    def loadScore(cls, content: str, filterDate: datetime = None) -> List[dict]:
        """解析OCR识别的文本内容"""
        if not content:
            return []
        
        log = _G._G_.Log()
        try:
            if not cls._validateContent(content, log):
                return []            
            items = json.loads(content)
            if not isinstance(items, list):
                return []    
            # 过滤掉无效的OCR项目
            valids = cls._filterValidItems(items)
            # 分类识别日期、金额和名字项目
            dates, amounts, names = cls._classifyItems(valids)
            # 为每个金额项目匹配对应的日期和名字, 并过滤掉非filterDate的记录
            records = cls._matchItemsToRecords(amounts, dates, names, filterDate, log)            
            # 合并相同名字的记录
            return cls._mergeRecords(records, log)
            
        except Exception as e:
            log.ex(e, "解析收益记录失败")
            return []

    @classmethod
    def _validateContent(cls, content: str, log) -> bool:
        """验证内容是否包含必要的关键字"""
        if not (re.search(cls.PATTERNS['coin_section'], content) or 
               re.search(cls.PATTERNS['cash_section'], content)):
            log.e("内容格式错误: 缺少必要的关键字")
            return False
        return True

    @classmethod
    def _filterValidItems(cls, items: list, line_height: int = 80) -> list:
        """过滤有效的OCR项目"""
        valid_items = []
        for item in items:
            try:
                coords = [int(x) for x in item['b'].split(',')]
                x1, y1, x2, y2 = coords
                height = y2 - y1
                
                if height <= line_height:
                    item.update({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'height': height})
                    valid_items.append(item)
            except:
                continue
        return valid_items

    @classmethod
    def _classifyItems(cls, items: list) -> tuple:
        """分类识别日期、金额和名字项目"""
        date_items, amount_items, name_items = [], [], []
        
        for item in items:
            text = item['t']
            
            date_match = re.search(cls.PATTERNS['date'], text)
            if date_match:
                item['date_str'] = date_match.group()
                date_items.append(item)
                continue
                
            amount_match = re.search(cls.PATTERNS['amount'], text)
            if amount_match:
                item['amount_str'] = amount_match.group()
                amount_items.append(item)
                continue
            
            if len(text.strip()) > 1 and not text.isdigit():
                name_items.append(item)
        
        return date_items, amount_items, name_items

    @classmethod
    def _findClosestDate(cls, amount_item: dict, date_items: list) -> dict:
        """为金额项目找到最近的日期"""
        closest_date = None
        min_distance = float('inf')
        
        for date_item in date_items:
            dx = abs(amount_item['x1'] - date_item['x1'])
            dy = abs(amount_item['y1'] - date_item['y1'])
            distance = dx + dy * 0.5
            
            if date_item['y1'] <= amount_item['y1'] + 200 and distance < min_distance:
                closest_date = date_item
                min_distance = distance
        
        return closest_date

    @classmethod
    def _findClosestName(cls, amount_item: dict, name_items: list) -> dict:
        """为金额项目找到最近的名字"""
        closest_name = None
        min_distance = float('inf')
        
        # 优先找同行左方的名字
        for name_item in name_items:
            if not cls._isValidNameText(name_item['t']):
                continue
                
            if abs(name_item['y1'] - amount_item['y1']) <= 50:
                dx = amount_item['x1'] - name_item['x1']
                if 0 < dx < 800 and dx < min_distance:
                    closest_name = name_item
                    min_distance = dx
        
        # 如果没找到同行的，找上方的名字
        if not closest_name:
            for name_item in name_items:
                if not cls._isValidNameText(name_item['t']):
                    continue
                    
                dx = abs(amount_item['x1'] - name_item['x1'])
                dy = amount_item['y1'] - name_item['y1']
                
                if 0 < dy <= 200:
                    distance = dx + dy * 0.5
                    if distance < min_distance:
                        closest_name = name_item
                        min_distance = distance
        
        return closest_name

    @classmethod
    def _isValidNameText(cls, text: str) -> bool:
        """检查文本是否是有效的名字"""
        text = text.strip()
        return len(text) >= 3 and re.search(r'[\u4e00-\u9fff\w]', text)

    @classmethod
    def _cleanName(cls, name: str) -> str:
        """清理名字：移除标点符号，转换为小写"""
        name = re.sub(r'[^\w\u4e00-\u9fff]', '', name)
        return name.lower()
    
    @classmethod
    def _matchItemsToRecords(cls, amounts: list, dates: list, names: list, filterDate: datetime, log) -> list:
        """为每个金额项目匹配对应的日期和名字, 并过滤掉非filterDate的记录
        
        Args:
            amounts: 金额列表
            dates: 日期列表
            names: 名字列表
            filterDate: 过滤日期
            log: 日志对象
        Returns:
            records: 匹配到的记录列表
        """
        records = []
        
        for amount in amounts:
            closest_date = cls._findClosestDate(amount, dates)
            if not closest_date:
                continue
                
            closest_name = cls._findClosestName(amount, names)
            if not closest_name:
                continue
            
            try:
                date_obj = _G.DateHelper.toDate(closest_date['date_str'].replace('.', '-'))
                amount_value = float(re.sub(r'[^\d.-]', '', amount['amount_str']))
                name = cls._cleanName(closest_name['t'])
                
                if not filterDate or date_obj.date() == filterDate.date():
                    record = {
                        'date': date_obj.strftime('%Y-%m-%d'),
                        'name': name,
                        'amount': amount_value
                    }
                    records.append(record)
                    # log.d(f"找到收益记录: {name} {amount_value} {record['date']}")                    
            except Exception as e:
                log.ex(e, f"解析数据失败: 日期={closest_date.get('date_str')}, 金额={amount.get('amount_str')}")
                continue
        
        return records

    @classmethod
    def _mergeRecords(cls, records: list, log) -> list:
        """使用OCR比较合并相同名字的记录"""
        mergeds = []
        g = _G._G_
        
        for record in records:
            found_similar = False
            for merged_record in mergeds:
                if g.ocrCompare(record['name'], merged_record['name']):
                    merged_record['amount'] += record['amount']
                    found_similar = True
                    # log.d(f"合并记录: {record['name']} -> {merged_record['name']}, 累计金额: {merged_record['amount']}")
                    break
            
            if not found_similar:
                mergeds.append(record.copy())
        
        return mergeds
