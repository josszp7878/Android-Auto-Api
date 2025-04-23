# import unittest
# import os
# import json
# import shutil
# import threading
# import time
# from unittest.mock import patch, MagicMock
# import sys
# # 添加父目录到sys.path
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# # 导入被测试类
# from CChecker import CChecker_

# class CCheckerTestCase(unittest.TestCase):
#     """CChecker测试用例类"""
    
#     @classmethod
#     def setUpClass(cls):
#         """测试类初始化，创建测试配置文件"""
#         # 创建测试配置目录
#         cls.test_config_dir = os.path.join(os.path.dirname(__file__), "test_config")
#         os.makedirs(cls.test_config_dir, exist_ok=True)
        
#         # 创建测试配置文件
#         cls.test_config_file = os.path.join(cls.test_config_dir, "TestChecks.json")
        
#         # 测试检查器配置
#         cls.test_configs = [
#             {
#                 "name": "test-basic",
#                 "match": "测试文本",
#                 "event": {
#                     "点击这里": "click"
#                 },
#                 "timeout": 3
#             },
#             {
#                 "name": "test-parent",
#                 "match": "父检查器",
#                 "childs": "test-child1,test-child2",
#                 "timeout": 5
#             },
#             {
#                 "name": "test-child1",
#                 "match": "子检查器1",
#                 "event": {
#                     "子动作1": "click"
#                 }
#             },
#             {
#                 "name": "test-child2",
#                 "match": "子检查器2",
#                 "event": {
#                     "子动作2": "click",
#                     "完成$": "exit"
#                 }
#             },
#             {
#                 "name": "test-entry-exit",
#                 "match": "有入口出口",
#                 "entry": {
#                     "开始页面": "{ T.click('开始按钮') }"
#                 },
#                 "exit": "{ T.click('结束按钮') }",
#                 "timeout": 2
#             },
#             {
#                 "name": "test-deamon",
#                 "match": "守护进程",
#                 "type": "deamon",
#                 "interval": 1,
#                 "event": {
#                     "周期性动作": "click"
#                 }
#             },
#             {
#                 "name": "test-complex-match",
#                 "match": "复杂匹配&正则表达式|多条件(x100,y200)",
#                 "event": {
#                     "复杂(.*)按钮": "click"
#                 }
#             }
#         ]
        
#         # 写入测试配置
#         with open(cls.test_config_file, 'w', encoding='utf-8') as f:
#             json.dump(cls.test_configs, f, ensure_ascii=False, indent=2)
    
#     @classmethod
#     def tearDownClass(cls):
#         """测试结束清理"""
#         # 删除测试配置目录
#         if os.path.exists(cls.test_config_dir):
#             shutil.rmtree(cls.test_config_dir)
    
#     def setUp(self):
#         """每个测试用例开始前的准备"""
#         # 创建多个模拟对象，用于替换真实依赖
#         self.g_mock = MagicMock()      # 模拟全局对象g
#         self.log_mock = MagicMock()    # 模拟日志对象
#         self.tools_mock = MagicMock()  # 模拟工具对象
        
#         # 配置模拟对象的行为
#         self.g_mock.Log.return_value = self.log_mock  # g.Log()返回log_mock
#         self.g_mock.CTools.return_value = self.tools_mock  # g.CTools()返回tools_mock
#         self.g_mock.rootDir.return_value = os.path.dirname(self.test_config_dir)  # 设置根目录
        
#         # 设置tools_mock的默认行为
#         self.tools_mock.matchText.return_value = {"t": "测试文本", "x": 100, "y": 200}  # 模拟文本匹配结果
#         self.tools_mock.do.return_value = True  # 模拟do方法返回成功
#         self.tools_mock.click.return_value = True  # 模拟click方法返回成功
        
#         # 使用patch替换CChecker模块中的全局变量
#         self.g_patcher = patch('CChecker.g', self.g_mock)
#         self.log_patcher = patch('CChecker.log', self.log_mock)
#         self.g_patcher.start()  # 启动g的替换
#         self.log_patcher.start()  # 启动log的替换
        
#         # 清理并重置CChecker_的模板和检查器列表
#         CChecker_._templates = None
#         CChecker_._checkers = []
        
#         # 替换loadConfig方法为测试用的模拟方法
#         self.original_loadConfig = CChecker_.loadConfig  # 保存原始方法
#         CChecker_.loadConfig = self._mock_load_config
        
#         # 确保进行了配置加载
#         CChecker_.templates()
    
#     def tearDown(self):
#         """每个测试用例结束后的清理"""
#         # 停止patch
#         self.g_patcher.stop()
#         self.log_patcher.stop()
        
#         # 恢复原始loadConfig方法
#         CChecker_.loadConfig = self.original_loadConfig
        
#         # 清理所有检查器
#         CChecker_.end()  # 停止所有运行中的检查器
#         CChecker_._templates = None  # 清空模板
#         CChecker_._checkers = []  # 清空检查器列表
    
#     def _mock_load_config(self, cls=None):
#         """模拟加载配置的方法"""
#         CChecker_._templates = []
#         try:
#             for config in self.test_configs:
#                 template = CChecker_(config.get('name', ''), config)
#                 CChecker_._templates.append(template)
#                 print(f"创建模板: {template.name}")  # 添加调试打印
            
#             print(f"总共加载了 {len(CChecker_._templates)} 个模板")  # 添加调试打印
#             self.log_mock.i(f"加载{len(CChecker_._templates)}个checker配置")
#         except Exception as e:
#             print(f"加载配置出错: {e}")  # 添加调试打印
#             self.log_mock.ex(e, "加载Checks.json失败")
#             CChecker_._templates = []
    
#     def test_basic_match(self):
#         """测试基本匹配功能"""
#         # 获取测试检查器，明确指定创建参数
#         checker = CChecker_.get("test-basic", create=True)
#         self.assertIsNotNone(checker, "应该成功创建test-basic检查器")
        
#         # 测试Match方法
#         result = checker.Match()
#         self.assertTrue(result, "Match应该返回True")
        
#         # 验证调用了matchText且参数正确
#         self.tools_mock.matchText.assert_called_with("测试文本")
    
#     def test_event_execution(self):
#         """测试事件执行功能"""
#         # 获取测试检查器
#         checker = CChecker_.get("test-basic")
#         self.assertIsNotNone(checker, "应该成功创建test-basic检查器")
        
#         # 修改模拟返回值，模拟匹配到"点击这里"文本
#         self.tools_mock.matchText.return_value = {"t": "点击这里", "x": 100, "y": 200}
        
#         # 测试Do方法 - 执行匹配到的事件
#         result = checker.Do()
#         self.assertEqual(result, 1, "Do应该返回1表示执行成功")  # 验证返回值
        
#         # 验证调用了click方法
#         self.tools_mock.click.assert_called_with("点击这里")  # 检查是否点击了正确的元素
    
#     def test_parent_child_checkers(self):
#         """测试父子检查器关系"""
#         # 模拟所有检查器的Match方法都返回True
#         with patch.object(CChecker_, 'Match', return_value=True):
#             # 获取父检查器
#             parent = CChecker_.get("test-parent")
#             self.assertIsNotNone(parent, "应该成功创建test-parent检查器")
            
#             # 启动父检查器
#             parent.enabled = True
            
#             # 在单独线程中运行检查器更新方法
#             thread = threading.Thread(target=parent._update)
#             thread.daemon = True  # 设为守护线程，主线程结束时自动结束
#             thread.start()
            
#             # 等待子检查器启动
#             time.sleep(1)
            
#             # 验证子检查器数量
#             self.assertEqual(len(parent.children), 2, "应该有2个子检查器")
            
#             # 停止父检查器
#             parent.enabled = False
#             thread.join(timeout=2)  # 等待线程结束
    
#     def test_entry_exit_logic(self):
#         """测试入口出口逻辑"""
#         # 获取测试检查器
#         checker = CChecker_.get("test-entry-exit")
#         self.assertIsNotNone(checker, "应该成功创建test-entry-exit检查器")
        
#         # 创建模拟页面对象
#         page_mock = MagicMock()
#         page_mock.name = "开始页面"  # 设置页面名称
        
#         # 将检查器的数据设置为模拟页面
#         checker.data = page_mock
        
#         # 测试_enter方法 - 页面进入逻辑
#         result = checker._onEnter()
#         self.assertTrue(result, "_enter应该返回True")
        
#         # 验证调用了click方法
#         self.tools_mock.click.assert_called_with("开始按钮")
        
#         # 测试退出逻辑 - 通过update触发
#         checker._update()
        
#         # 注：这里的注释指出，由于exit逻辑是通过eval执行代码字符串，测试比较复杂
    
#     def test_match_complex_pattern(self):
#         """测试复杂匹配模式"""
#         # 获取测试检查器
#         checker = CChecker_.get("test-complex-match")
#         self.assertIsNotNone(checker, "应该成功创建test-complex-match检查器")
        
#         # 测试匹配属性是否正确设置
#         self.assertEqual(
#             checker.match,
#             "复杂匹配&正则表达式|多条件(x100,y200)",
#             "match属性应该正确设置"
#         )
        
#         # 配置模拟行为
#         self.tools_mock.do.return_value = False  # tools.do返回False
#         self.tools_mock.matchText.return_value = {"t": "复杂匹配", "x": 150, "y": 250}  # 匹配成功
        
#         # 测试Match方法
#         result = checker.Match()
#         self.assertTrue(result, "Match应该返回True")  # 验证匹配成功
    
#     def test_batch_run(self):
#         """测试批量执行功能"""
#         # 获取测试检查器
#         checker = CChecker_.get("test-basic")
#         self.assertIsNotNone(checker, "应该成功创建test-basic检查器")
        
#         # 创建批量执行策略 - 执行3次，间隔0.1秒
#         policy = {
#             "times": 3,
#             "interval": 0.1
#         }
        
#         # 启动批量执行
#         thread = checker.batchRun(policy)  # 返回执行线程
        
#         # 等待执行完成
#         thread.join(timeout=2)
        
#         # 验证至少调用了3次matchText方法
#         self.assertGreaterEqual(
#             self.tools_mock.matchText.call_count, 
#             3, 
#             "批量执行应该至少调用3次matchText"
#         )
    
#     def test_deamon_mode(self):
#         """测试守护进程模式"""
#         # 获取测试检查器
#         checker = CChecker_.get("test-deamon")
#         self.assertIsNotNone(checker, "应该成功创建test-deamon检查器")
        
#         # 验证配置参数
#         self.assertEqual(checker.type, "deamon", "type应该设置为deamon")
#         self.assertEqual(checker.interval, 1, "interval应该设置为1")
        
#         # 启动检查器
#         checker.enabled = True
        
#         # 创建线程运行update方法
#         thread = threading.Thread(target=checker._update)
#         thread.daemon = True
#         thread.start()
        
#         # 等待2.5秒（覆盖多个周期）
#         time.sleep(2.5)
        
#         # 停止检查器
#         checker.enabled = False
#         thread.join(timeout=1)
        
#         # 验证至少执行了2次matchText
#         self.assertGreaterEqual(
#             self.tools_mock.matchText.call_count, 
#             2, 
#             "守护进程模式应该至少执行2次matchText"
#         )
    
#     def test_add_remove_property(self):
#         """测试添加和删除属性"""
#         # 获取测试检查器
#         checker = CChecker_.get("test-basic")
#         self.assertIsNotNone(checker, "应该成功创建test-basic检查器")
        
#         # 测试添加match属性
#         result = checker.addProp("match", "新匹配文本")
#         self.assertTrue(result, "添加match属性应该成功")
#         self.assertEqual(checker._match, "&新匹配文本", "match属性应该被正确更新")
        
#         # 测试添加childs属性
#         result = checker.addProp("childs", "test-child1")
#         self.assertTrue(result, "添加childs属性应该成功")
#         self.assertEqual(checker._childs, "test-child1", "childs属性应该被正确设置")
        
#         # 测试添加event属性
#         result = checker.addProp("event", "新按钮", "新动作")
#         self.assertTrue(result, "添加event属性应该成功")
#         self.assertEqual(checker.event["新按钮"], "新动作", "event属性应该被正确设置")
        
#         # 测试删除match属性
#         result = checker.removeProp("match", "新匹配文本")
#         self.assertTrue(result, "删除match属性应该成功")
#         # 注释指出由于删除正则表达式的复杂性，不严格验证结果值
        
#         # 测试删除childs属性
#         result = checker.removeProp("childs", "test-child1")
#         self.assertTrue(result, "删除childs属性应该成功")
#         self.assertEqual(checker._childs, "", "childs属性应该被正确清空")
        
#         # 测试删除event属性
#         result = checker.removeProp("event", "新按钮")
#         self.assertTrue(result, "删除event属性应该成功")
#         self.assertNotIn("新按钮", checker.event, "event属性应该被正确删除")
    
#     def test_checker_lifecycle(self):
#         """测试检查器生命周期"""
#         # 获取测试检查器并强制创建
#         checker = CChecker_.get("test-basic", create=True)
#         self.assertIsNotNone(checker, "应该成功创建test-basic检查器")
        
#         # 验证检查器在活跃列表中
#         self.assertIn(checker, CChecker_._checkers, "检查器应该在活跃列表中")
        
#         # 删除检查器
#         CChecker_.remove(checker)
        
#         # 验证检查器已被移除
#         self.assertNotIn(checker, CChecker_._checkers, "检查器应该被从活跃列表中移除")
        
#         # 再次创建检查器
#         checker = CChecker_.get("test-basic", create=True)
#         self.assertIsNotNone(checker, "应该成功重新创建test-basic检查器")
        
#         # 通过类方法结束所有检查器
#         CChecker_.end()
        
#         # 验证所有检查器都已停止
#         self.assertEqual(len(CChecker_._checkers), 0, "所有检查器应该被停止")

# def run_test(test_name):
#     """运行指定的测试用例或全部测试"""
#     if test_name == "all":
#         unittest.main()
#     else:
#         suite = unittest.TestSuite()
#         suite.addTest(CCheckerTestCase(test_name))
#         unittest.TextTestRunner().run(suite)

# if __name__ == "__main__":
#     # 运行单个测试，可以修改这里的参数来切换测试
#     run_test("test_basic_match")
#     # 或者运行所有测试
#     # run_test("all")
