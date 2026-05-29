---
name: check
description: 快速健康检查 —— 验证后端导入、前端编译、登录是否正常
---

# 快速健康检查

请按顺序执行以下检查（只读操作，不做任何修改）：

## 1. 后端导入验证
```bash
cd backend && python -c "from models import *; from crud import *; from schemas import *; from routers.operations import router; print(f'Routes: {len(router.routes)}')" 2>&1
```

## 2. 前端编译验证
```bash
cd frontend && npx vite build 2>&1 | grep -E "✓|error|Error"
```

## 3. 服务器状态
检查是否在运行：
```bash
curl -s http://localhost:8000/ 2>&1 || echo "服务器未启动"
```

## 4. 登录验证
如果服务器在运行，测试登录：
```bash
curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}' | python -c "import sys,json; d=json.load(sys.stdin); print('Login OK' if 'access_token' in d else f'Login FAIL: {d}')" 2>&1
```

## 5. 核心 API 快速抽查
如果登录成功，测试 6 个核心端点：
- 仪表盘 stats
- 异常工单 stats
- 设备状态 overview
- 固件配置
- 机构列表
- 指挥中心

## 输出格式
每个检查项标注 [OK] 或 [FAIL]，最后汇总通过/失败数量。
如有失败，说明具体原因。
