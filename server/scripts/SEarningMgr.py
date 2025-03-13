from datetime import datetime
import json
from SModels import db, EarningRecord
import _Log
import re

class SEarningMgr_:
    """收益记录管理类"""
    
    # 关键文本的正则表达式
    PATTERNS = {
        'coin_section': r'金[币幣]明细?',  # 金币明细区域开始
        'cash_section': r'现金明细?',      # 现金明细区域开始
        'date': r'\d{4}[\.-]\d{1,2}[\.-]\d{1,2}',  # 日期格式
        'amount': r'[+-]?\d+(?:,\d{3})*(?:\.\d+)?金[币幣]?'  # 金额格式
    }
    
    @staticmethod
    def Add(deviceId: str, appName: str, earnType: str, amount: float, time: datetime = None) -> bool:
        """添加收益记录
        Args:
            deviceId: 设备ID
            appName: 应用名称
            earnType: 收益类型(score/cash)
            amount: 收益数量
            time: 收益时间,默认为当前时间
        Returns:
            bool: 是否添加成功
        """
        try:
            if time is None:
                time = datetime.now()
                
            record = EarningRecord(
                deviceId=deviceId,
                appName=appName,
                earnType=earnType,
                amount=amount,
                time=time
            )
            
            db.session.add(record)
            db.session.commit()
            
            _Log._Log_.i(f"添加收益记录: {deviceId}-{appName} {earnType}={amount}")
            return True
            
        except Exception as e:
            _Log._Log_.ex(e, "添加收益记录失败")
            return False
    
    @staticmethod        
    def Load(appName: str, content: str) -> bool:
        """从OCR结果加载收益记录"""
        try:
            # 检查关键字
            if not (re.search(SEarningMgr_.PATTERNS['coin_section'], content) or 
                   re.search(SEarningMgr_.PATTERNS['cash_section'], content)):
                _Log._Log_.e("内容格式错误: 缺少必要的关键字")
                return False
                
            # 解析记录
            records = SEarningMgr_._parse_records(content)
            if not records:
                _Log._Log_.e("未找到有效的收益记录")
                return False
                
            # 获取设备ID
            from SDeviceMgr import deviceMgr
            device_id = deviceMgr.curDeviceID
            if not device_id:
                _Log._Log_.e("未选择设备")
                return False
                
            # 导入记录
            success_count = 0
            for record in records:
                try:
                    # 转换日期格式
                    date = datetime.strptime(
                        record['date'].replace('.', '-'),
                        '%Y-%m-%d'
                    )
                    
                    # 添加记录
                    if SEarningMgr_.Add(
                        deviceId=device_id,
                        appName=appName,
                        earnType='score',
                        amount=record['amount'],
                        time=date
                    ):
                        success_count += 1
                        
                except Exception as e:
                    _Log._Log_.ex(e, f"导入记录失败: {record}")
                    
            total = len(records)
            _Log._Log_.i(f"导入完成: 成功{success_count}/{total}")
            return success_count == total
            
        except Exception as e:
            _Log._Log_.ex(e, "导入收益记录失败")
            return False
    
    @staticmethod
    def _parse_records(content: str) -> list:
        """解析OCR识别的文本内容
        Args:
            content: OCR识别的JSON内容
        Returns:
            list: 解析后的记录列表 [{
                date: str,
                type: str,
                amount: float
            }]
        """
        try:
            # 解析JSON
            items = json.loads(content)
            if not isinstance(items, list):
                return []
                
            # 按y坐标排序
            items.sort(key=lambda x: [int(i) for i in x['b'].split(',')][1])
            
            # 初始化结果
            records = []
            current_date = None
            current_type = None
            
            # 遍历文本项
            for i, item in enumerate(items):
                text = item['t']
                y = int(item['b'].split(',')[1])
                
                # 检查是否是日期
                date_match = re.search(SEarningMgr_.PATTERNS['date'], text)
                if date_match:
                    current_date = date_match.group()
                    continue
                    
                # 检查是否是金额
                amount_match = re.search(SEarningMgr_.PATTERNS['amount'], text)
                if amount_match and current_date:
                    # 获取上一行的文本作为类型描述
                    if i > 0:
                        prev_y = int(items[i-1]['b'].split(',')[1])
                        # 如果y坐标接近(差距小于50)，认为是同一条记录
                        if abs(y - prev_y) < 50:
                            current_type = items[i-1]['t']
                    
                    # 提取金额
                    amount_str = amount_match.group()
                    amount = float(re.sub(r'[^\d.-]', '', amount_str))
                    
                    # 添加记录
                    if current_type:
                        records.append({
                            'date': current_date,
                            'type': current_type,
                            'amount': amount
                        })
                        
                    current_type = None
                    
            return records
            
        except Exception as e:
            _Log._Log_.ex(e, "解析收益记录失败")
            return []
    
    def GetEarnings(self, deviceId: str, appName: str, start_date: datetime, end_date: datetime, earnType: str) -> float:
        """获取指定设备在指定时间范围内的收益记录
        
        Args:
            deviceId: 设备ID
            appName: 应用名称
            earnType: 收益类型(score/cash)  
            start_date: 开始日期
            end_date: 结束日期
        Returns:
            float: 总收益
        """
        try:
            # 构建查询条件
            query = db.session.query(
                EarningRecord.time,
                EarningRecord.amount,
                EarningRecord.earnType
            ).filter(
                EarningRecord.deviceId == deviceId,
                EarningRecord.appName == appName,
                EarningRecord.earnType == earnType,
                EarningRecord.time >= start_date,
                EarningRecord.time <= end_date
            )   
            
            # 执行查询
            earnings = query.all()
            
            # 计算总收益
            total_earnings = sum(earning.amount for earning in earnings)
            
            return total_earnings
            
        except Exception as e:
            _Log._Log_.ex(e, "获取收益记录失败")
            return 0    
