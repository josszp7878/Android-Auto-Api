from datetime import datetime
import json
from typing import List, Dict
from .models import db, EarningRecord
from scripts.logger import Log
from sqlalchemy import func
from .SAppMgr import appMgr  # 添加导入

class SEarningMgr:
    """收益记录管理类"""
    
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
            
            Log.i(f"添加收益记录: {deviceId}-{appName} {earnType}={amount}")
            return True
            
        except Exception as e:
            Log.ex(e, "添加收益记录失败")
            return False
    
    @staticmethod        
    def Load(json_str: str) -> bool:
        """从JSON字符串加载收益记录
        Args:
            json_str: JSON格式的收益记录列表
                格式: [{
                    "deviceId": "设备ID",
                    "appName": "应用名称",
                    "earnType": "score/cash",
                    "amount": 数量,
                    "time": "时间字符串(可选)"
                }, ...]
        Returns:
            bool: 是否成功导入所有记录
        """
        try:
            # 解析JSON
            records = json.loads(json_str)
            if not isinstance(records, list):
                Log.e("JSON格式错误: 应为数组")
                return False
                
            success_count = 0
            for record in records:
                try:
                    # 解析时间
                    time = None
                    if 'time' in record:
                        try:
                            time = datetime.strptime(
                                record['time'],
                                '%Y-%m-%d %H:%M:%S'
                            )
                        except ValueError:
                            time = None
                    
                    
                    # 获取金额
                    amount = float(record['amount'])
                    appName = record['appName']
                    # 根据金额正负判断类型
                    if amount < 0:
                        # 负数表示积分转现金,使用应用配置的换算比例
                        earnType = 'cash'
                        ratio = appMgr.getRatio(appName)
                        amount = abs(amount) / ratio
                    else:
                        earnType = 'score'
                    
                    # 添加记录
                    if SEarningMgr.Add(
                        deviceId=record['deviceId'],
                        appName=appName,
                        earnType=earnType,
                        amount=amount,
                        time=time
                    ):
                        success_count += 1
                        
                except KeyError as e:
                    Log.e(f"记录缺少必要字段: {e}")
                except ValueError as e:
                    Log.e(f"数据格式错误: {e}")
                except Exception as e:
                    Log.ex(e, "处理单条记录失败")
            
            total = len(records)
            Log.i(f"导入完成: 成功{success_count}/{total}")
            return success_count == total
            
        except json.JSONDecodeError as e:
            Log.e(f"JSON解析失败: {e}")
            return False
        except Exception as e:
            Log.ex(e, "导入收益记录失败")
            return False 
        
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
            Log.ex(e, "获取收益记录失败")
            return 0    
