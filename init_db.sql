-- 创建数据库
CREATE DATABASE IF NOT EXISTS inventory_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE inventory_db;

-- 创建库存表
CREATE TABLE IF NOT EXISTS inventory (
    id INT AUTO_INCREMENT PRIMARY KEY,
    serial_number VARCHAR(50) UNIQUE NOT NULL COMMENT '序号',
    version VARCHAR(50) COMMENT '版本(WiFi或4G)',
    device_id VARCHAR(50) UNIQUE NOT NULL COMMENT '设备号',
    type VARCHAR(100) COMMENT '类型(睡眠或跌倒)',
    packaging VARCHAR(100) COMMENT '产品包装(简约或精品)',
    device_attribute VARCHAR(100) COMMENT '设备属性',
    owner VARCHAR(100) COMMENT '归属人/责任人/甲方',
    borrower VARCHAR(100) COMMENT '领用人',
    sales_person VARCHAR(100) COMMENT '销售',
    remarks TEXT COMMENT '备注',
    supplementary_info TEXT COMMENT '补充信息记录',
    delivery_date DATE COMMENT '交付/安装时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
);

-- 创建提醒表
CREATE TABLE IF NOT EXISTS reminders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL COMMENT '设备号',
    reminder_type ENUM('trial_period', 'iot_card', 'other') COMMENT '提醒类型',
    due_date DATE COMMENT '到期日期',
    description TEXT COMMENT '描述',
    is_processed BOOLEAN DEFAULT FALSE COMMENT '是否已处理',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
);

-- 创建AI操作日志表
CREATE TABLE IF NOT EXISTS ai_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_input TEXT NOT NULL COMMENT '用户输入',
    ai_parsed_action VARCHAR(200) COMMENT 'AI解析的操作',
    affected_records JSON COMMENT '受影响的记录',
    operation_result TEXT COMMENT '操作结果',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
);

-- 插入示例数据
INSERT INTO inventory (serial_number, version, device_id, type, packaging, device_attribute, owner, borrower, sales_person, remarks) VALUES
('SN001', 'WiFi', 'CAA241100001', '睡眠', '简约', '现有库存', '公司', NULL, NULL, '新入库设备'),
('SN002', '4G', 'CAA241100002', '跌倒', '精品', '现有库存', '公司', NULL, NULL, '新入库设备'),
('SN003', 'WiFi', 'CAA241100003', '睡眠', '简约', '产品演示', '公司', '张三', NULL, '演示设备'),
('SN004', '4G', 'CAA241100004', '跌倒', '精品', '商机试用', '客户A', '李四', '王五', '试用设备'),
('SN005', 'WiFi', 'CAA241100005', '跌倒', '简约', '技术开发/测试', '公司', '赵六', NULL, '测试设备');

-- 插入示例提醒
INSERT INTO reminders (device_id, reminder_type, due_date, description) VALUES
('CAA241100004', 'trial_period', '2024-12-31', '设备试用期即将结束'),
('CAA241100005', 'iot_card', '2024-11-30', '物联网卡即将到期');

COMMIT;