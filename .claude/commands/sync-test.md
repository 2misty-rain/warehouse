---
name: sync-test
description: 完整的端到端测试 —— 重启服务、配置生产库、刷新设备状态、测试异常工单流转
---

# 完整端到端测试

执行以下完整测试流程（会重启服务，但不修改代码）：

## 第一步：重启服务
```bash
taskkill //F //IM python.exe 2>/dev/null; sleep 2
cd backend && python main.py > /dev/null 2>&1 & sleep 8
```
确认启动成功：
```bash
curl -s http://localhost:8000/
```

## 第二步：保存生产库配置
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -s -X POST http://localhost:8000/operations/production-db/config -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"host":"localhost","port":3306,"database":"wechat_idc","username":"root","password":"123456","device_table":"operation_device","device_id_column":"device_id","online_status_column":"status","last_heartbeat_column":"last_online_time","firmware_version_column":"version"}'
```

## 第三步：刷新设备状态
```bash
curl -s -X POST http://localhost:8000/operations/device-status/refresh -H "Authorization: Bearer $TOKEN"
```

## 第四步：验证设备状态
- 总览：检查在线率和机构数量
- 明细：检查在线/离线设备数
- 离线事件：检查待处理数量

## 第五步：异常工单流转测试
- 获取一条待处理工单
- 执行算法标记（需要回访）
- 执行售后处理（完成）
- 验证时间线

## 第六步：其他模块抽查
- 工具箱机构列表
- 智能分组
- 健康度评分
- 指挥中心

## 输出格式
- 每步标注 [OK] 或 [FAIL]
- 末尾汇总：X 项通过 / Y 项失败
- 列出失败项的具体原因和修复建议
