-- ============================================
-- 智能库存管理系统 — 完整数据库初始化脚本
-- ============================================

CREATE DATABASE IF NOT EXISTS inventory_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE inventory_db;

-- ========== 1. 库存核心表 ==========

CREATE TABLE IF NOT EXISTS inventory (
    id INT AUTO_INCREMENT PRIMARY KEY,
    serial_number VARCHAR(50) UNIQUE NOT NULL COMMENT '序号',
    version VARCHAR(50) COMMENT '版本',
    device_id VARCHAR(50) UNIQUE NOT NULL COMMENT '设备号',
    type VARCHAR(100) COMMENT '类型',
    packaging VARCHAR(100) COMMENT '产品包装',
    device_attribute VARCHAR(100) COMMENT '设备属性',
    owner VARCHAR(100) COMMENT '归属人/责任人/甲方',
    borrower VARCHAR(100) COMMENT '领用人',
    sales_person VARCHAR(100) COMMENT '销售',
    iot_card_status VARCHAR(20) COMMENT '物联网卡状态',
    remarks TEXT COMMENT '备注',
    supplementary_info TEXT COMMENT '补充信息记录',
    delivery_date DATE COMMENT '交付/安装时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ========== 2. 借用管理 ==========

CREATE TABLE IF NOT EXISTS borrow_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL COMMENT '设备号',
    borrower VARCHAR(100) NOT NULL COMMENT '借用人',
    borrow_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    expected_return_date DATE COMMENT '预计归还时间',
    actual_return_date DATE COMMENT '实际归还时间',
    purpose TEXT COMMENT '借用目的',
    status VARCHAR(20) DEFAULT 'borrowed' COMMENT 'borrowed/returned/overdue/terminated',
    condition_on_borrow TEXT COMMENT '借出时设备状态',
    condition_on_return TEXT COMMENT '归还时设备状态',
    remarks TEXT COMMENT '备注',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ========== 3. 出库预约 ==========

CREATE TABLE IF NOT EXISTS reservations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    applicant VARCHAR(50) NOT NULL COMMENT '申请人',
    quantity INT NOT NULL COMMENT '需求数量',
    version_req VARCHAR(20) COMMENT '版本要求',
    packaging_req VARCHAR(20) COMMENT '包装要求',
    client_name VARCHAR(100) COMMENT '甲方',
    sales_person VARCHAR(100) COMMENT '销售',
    required_date DATE COMMENT '需求日期',
    purpose TEXT COMMENT '用途说明',
    status VARCHAR(20) DEFAULT 'pending' COMMENT 'pending/approved/fulfilled/rejected',
    admin_username VARCHAR(50) COMMENT '处理人',
    assigned_devices TEXT COMMENT '分配的设备号JSON',
    admin_remarks TEXT COMMENT '管理员备注',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ========== 4. 提醒中心 ==========

CREATE TABLE IF NOT EXISTS reminders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(50) COMMENT '设备号(可选)',
    reminder_type VARCHAR(50) COMMENT '提醒类型',
    due_date DATE COMMENT '到期日期',
    description TEXT COMMENT '描述',
    is_processed BOOLEAN DEFAULT FALSE COMMENT '是否已处理',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========== 5. AI 对话 ==========

CREATE TABLE IF NOT EXISTS ai_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_input TEXT NOT NULL COMMENT '用户输入',
    ai_parsed_action VARCHAR(200) COMMENT 'AI解析的操作',
    affected_records TEXT COMMENT '受影响的记录',
    operation_result TEXT COMMENT '操作结果',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversation_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL COMMENT '用户标识',
    role VARCHAR(20) NOT NULL COMMENT 'user/assistant/system',
    content TEXT NOT NULL COMMENT '对话内容',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========== 6. 系统管理 ==========

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL COMMENT '用户名',
    email VARCHAR(100) COMMENT '邮箱',
    hashed_password VARCHAR(255) NOT NULL COMMENT '密码哈希',
    role VARCHAR(20) DEFAULT 'operator' COMMENT 'admin/operator/viewer',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS operation_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) COMMENT '操作人',
    operation_type VARCHAR(50) NOT NULL COMMENT '操作类型',
    device_id VARCHAR(50) COMMENT '目标设备号',
    details TEXT COMMENT '操作详情JSON',
    ip_address VARCHAR(50) COMMENT '操作IP',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========== 7. 运营平台 — 设备监控 ==========

CREATE TABLE IF NOT EXISTS device_status_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL COMMENT '设备号',
    organization VARCHAR(100) COMMENT '归属机构',
    check_time DATETIME NOT NULL COMMENT '检查时间',
    is_online BOOLEAN DEFAULT TRUE COMMENT '是否在线',
    last_heartbeat DATETIME COMMENT '最后心跳时间',
    offline_duration_minutes INT DEFAULT 0 COMMENT '离线时长(分钟)',
    firmware_version VARCHAR(50) COMMENT '固件版本',
    needs_firmware_update BOOLEAN DEFAULT FALSE COMMENT '是否需要固件更新',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS device_groups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '分组名称',
    description TEXT COMMENT '分组描述',
    created_by VARCHAR(50) COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS device_group_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id INT NOT NULL COMMENT '分组ID',
    device_id VARCHAR(50) NOT NULL COMMENT '设备号',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES device_groups(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS offline_incidents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL COMMENT '设备号',
    organization VARCHAR(100) COMMENT '归属机构',
    detected_at DATETIME NOT NULL COMMENT '检测到离线的时间',
    offline_duration INT DEFAULT 0 COMMENT '离线时长(分钟)',
    firmware_version VARCHAR(50) COMMENT '固件版本',
    status VARCHAR(20) DEFAULT '待处理' COMMENT '待处理/已处理/已关闭',
    reason_tag VARCHAR(50) COMMENT '原因标签',
    handled_by VARCHAR(50) COMMENT '处理人',
    handled_at DATETIME COMMENT '处理时间',
    notes TEXT COMMENT '处理备注',
    is_silenced BOOLEAN DEFAULT FALSE COMMENT '是否静默',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS firmware_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    current_normal_version VARCHAR(50) NOT NULL COMMENT '当前正常固件版本',
    updated_by VARCHAR(50) COMMENT '更新人',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ========== 8. 运营平台 — 异常工单 ==========

CREATE TABLE IF NOT EXISTS anomaly_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    record_date DATE NOT NULL COMMENT '异常发生日期',
    institution VARCHAR(100) COMMENT '机构名称',
    room_info VARCHAR(100) COMMENT '房间号',
    device_id VARCHAR(50) COMMENT '设备号',
    person_name VARCHAR(50) COMMENT '老人姓名',
    anomaly_type VARCHAR(50) NOT NULL COMMENT '异常类型',
    anomaly_detail TEXT COMMENT '异常详情描述',
    event_time VARCHAR(100) COMMENT '事件发生时间',
    raw_data JSON COMMENT '原始数据快照',
    status VARCHAR(20) DEFAULT '待处理' COMMENT '待处理/处理中/待回访/已完成/已归档',
    priority VARCHAR(10) DEFAULT '中' COMMENT '高/中/低',
    algorithm_tag VARCHAR(50) COMMENT '算法标记',
    algorithm_notes TEXT COMMENT '算法备注',
    assigned_to VARCHAR(50) COMMENT '处理人',
    resolution TEXT COMMENT '处理结果描述',
    resolved_at DATETIME COMMENT '完成时间',
    prev_status VARCHAR(50) COMMENT '前一天状态',
    current_status VARCHAR(50) COMMENT '当天状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS anomaly_actions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    record_id INT NOT NULL COMMENT '关联工单ID',
    action_by VARCHAR(50) COMMENT '操作人',
    action_type VARCHAR(50) COMMENT '操作类型',
    content TEXT COMMENT '操作内容',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (record_id) REFERENCES anomaly_records(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS data_sync_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sync_date DATE NOT NULL COMMENT '同步日期',
    sync_type VARCHAR(20) DEFAULT 'auto' COMMENT 'auto/manual',
    status VARCHAR(20) DEFAULT 'running' COMMENT 'running/success/failed',
    stats JSON COMMENT '统计信息',
    error_message TEXT COMMENT '错误信息',
    started_at DATETIME COMMENT '开始时间',
    finished_at DATETIME COMMENT '完成时间'
);

-- ========== 9. 运营平台 — 数据报告 ==========

CREATE TABLE IF NOT EXISTS daily_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_date DATE NOT NULL COMMENT '报告日期',
    device_online_rate FLOAT COMMENT '整体在线率',
    total_monitored_devices INT DEFAULT 0 COMMENT '监控设备总数',
    offline_count INT DEFAULT 0 COMMENT '离线设备数',
    new_anomalies INT DEFAULT 0 COMMENT '新增异常数',
    new_offline_incidents INT DEFAULT 0 COMMENT '新增离线事件数',
    resolved_count INT DEFAULT 0 COMMENT '已处理数量',
    summary_text TEXT COMMENT '文字摘要',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS weekly_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    week_start DATE NOT NULL COMMENT '周开始日期',
    week_end DATE NOT NULL COMMENT '周结束日期',
    total_anomalies INT DEFAULT 0 COMMENT '异常总数',
    resolved_count INT DEFAULT 0 COMMENT '已处理数',
    resolution_rate FLOAT COMMENT '处理率',
    top_institutions JSON COMMENT 'TOP机构',
    top_devices JSON COMMENT '高频异常设备',
    report_data JSON COMMENT '完整报告数据',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========== 10. 运营平台 — 企业级扩展 ==========

CREATE TABLE IF NOT EXISTS device_tags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL COMMENT '设备号',
    tag_key VARCHAR(50) NOT NULL COMMENT '标签键',
    tag_value VARCHAR(100) NOT NULL COMMENT '标签值',
    created_by VARCHAR(50) COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS smart_group_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '规则名称',
    description TEXT COMMENT '规则描述',
    rule_type VARCHAR(30) DEFAULT 'smart' COMMENT 'smart/manual',
    conditions JSON NOT NULL COMMENT '筛选条件JSON',
    enabled BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    created_by VARCHAR(50) COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS device_health_scores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL COMMENT '设备号',
    score INT DEFAULT 100 COMMENT '健康度评分 0-100',
    grade VARCHAR(5) DEFAULT 'A' COMMENT 'A/B/C/D',
    online_score INT DEFAULT 100 COMMENT '在线率子分',
    firmware_score INT DEFAULT 100 COMMENT '固件合规子分',
    anomaly_score INT DEFAULT 100 COMMENT '异常频率子分',
    offline_history_score INT DEFAULT 100 COMMENT '离线历史子分',
    details JSON COMMENT '评分详情',
    calculated_at DATETIME COMMENT '计算时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS institution_regions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    institution_name VARCHAR(100) NOT NULL UNIQUE COMMENT '机构名称',
    region VARCHAR(50) COMMENT '大区',
    city VARCHAR(50) COMMENT '城市',
    contact_person VARCHAR(50) COMMENT '联系人',
    contact_phone VARCHAR(20) COMMENT '联系电话',
    notes TEXT COMMENT '备注',
    updated_by VARCHAR(50) COMMENT '更新人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS batch_operations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    operation_type VARCHAR(50) NOT NULL COMMENT '操作类型',
    target_type VARCHAR(20) NOT NULL COMMENT '目标类型',
    target_id VARCHAR(100) COMMENT '目标标识',
    params JSON COMMENT '操作参数',
    affected_count INT DEFAULT 0 COMMENT '影响设备数',
    success_count INT DEFAULT 0 COMMENT '成功数',
    failed_count INT DEFAULT 0 COMMENT '失败数',
    status VARCHAR(20) DEFAULT 'running' COMMENT 'running/success/failed/partial',
    operated_by VARCHAR(50) COMMENT '操作人',
    started_at DATETIME COMMENT '开始时间',
    finished_at DATETIME COMMENT '完成时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========== 11. 插入默认管理员 ==========

-- 密码 admin123 (bcrypt hash)
INSERT IGNORE INTO users (username, email, hashed_password, role, is_active)
VALUES ('admin', 'admin@example.com', '$2b$12$LJ3m4ys3LGyZ0qgFE1SG6e2sRJkjHt4Ny0kUxLkmNrkgxRoPL8mPy', 'admin', TRUE);
