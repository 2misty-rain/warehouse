"""
数据库迁移脚本 v2.0
- 修复已有表的列结构，使其与 ORM 模型匹配
- 新增 iot_card_status 字段到 inventory 表
- 修复/创建 operation_logs 表
- 修复/创建 users 表
- 创建 conversation_history 表
- 初始化管理员账号
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from database import engine, SessionLocal
from models import Base, Inventory, OperationLog, User, ConversationHistory
from sqlalchemy import text, inspect
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_columns(table_name):
    """获取表的所有列名"""
    inspector = inspect(engine)
    return [c['name'] for c in inspector.get_columns(table_name)]


def get_existing_tables():
    """获取数据库中所有表名"""
    inspector = inspect(engine)
    return inspector.get_table_names()


def sql_execute(stmt, description=""):
    """执行原始SQL"""
    with engine.connect() as conn:
        conn.execute(text(stmt))
        conn.commit()
    if description:
        print(f"  [OK] {description}")


def fix_inventory_table():
    """修复 inventory 表"""
    print("\n--- inventory 表 ---")
    add_column_if_not_exists('inventory', 'iot_card_status VARCHAR(20) COMMENT "物联网卡状态"')


def fix_users_table():
    """修复 users 表：检查列结构，修复不匹配的列"""
    print("\n--- users 表 ---")
    existing_tables = get_existing_tables()
    if 'users' not in existing_tables:
        # 表不存在，创建
        Base.metadata.tables['users'].create(bind=engine)
        print("  [OK] 创建 users 表")
        return

    columns = get_columns('users')

    # 1. 密码列：password_hash → hashed_password
    if 'password_hash' in columns and 'hashed_password' not in columns:
        sql_execute(
            'ALTER TABLE users RENAME COLUMN password_hash TO hashed_password',
            '重命名 password_hash → hashed_password'
        )
    elif 'hashed_password' not in columns:
        sql_execute(
            'ALTER TABLE users ADD COLUMN hashed_password VARCHAR(255) NOT NULL DEFAULT "changeme"',
            '添加缺失的 hashed_password 列'
        )

    # 2. 确保 role 默认值正确
    if 'role' in columns:
        sql_execute(
            'ALTER TABLE users MODIFY COLUMN role VARCHAR(20) DEFAULT "operator"',
            '修改 role 列默认值'
        )

    # 3. 添加缺失列
    missing = []
    expected_cols = ['id', 'username', 'email', 'hashed_password', 'role', 'is_active', 'created_at', 'updated_at']
    for col in expected_cols:
        if col not in columns:
            missing.append(col)

    if 'updated_at' in missing:
        sql_execute(
            'ALTER TABLE users ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP',
            '添加 updated_at 列'
        )

    # 4. 丢弃旧版多余列（可选，不影响运行）
    extra_cols = set(columns) - set(expected_cols) - {'password_hash'}
    if extra_cols:
        print(f"  [~] 存在旧版多余列: {extra_cols} (保留不动，不影响运行)")

    print("  [OK] users 表修复完成")


def fix_operation_logs_table():
    """修复 operation_logs 表：旧版 schema 完全不同，删表重建"""
    print("\n--- operation_logs 表 ---")
    existing_tables = get_existing_tables()
    columns = get_columns('operation_logs') if 'operation_logs' in existing_tables else []

    # 检查是否有数据
    has_data = False
    if 'operation_logs' in existing_tables:
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM operation_logs"))
                count = result.scalar()
                if count > 0:
                    has_data = True
                    print(f"  [~] operation_logs 表有 {count} 条旧数据，将备份为 operation_logs_backup")
        except:
            pass

    # 新 ORM 期望的列
    expected_cols = {'id', 'username', 'operation_type', 'device_id', 'details', 'ip_address', 'created_at'}
    current_cols = set(columns)

    if current_cols == expected_cols:
        print("  [~] operation_logs 表结构正确，跳过")
        return

    # Schema 不匹配，重建
    if has_data:
        sql_execute('RENAME TABLE operation_logs TO operation_logs_backup', '备份旧 operation_logs 表')
    else:
        sql_execute('DROP TABLE IF EXISTS operation_logs', '删除空的旧 operation_logs 表')

    # 创建新表
    Base.metadata.tables['operation_logs'].create(bind=engine)
    print("  [OK] 创建 operation_logs 表（新 schema）")


def fix_borrow_records_fk():
    """为 borrow_records 添加外键约束"""
    print("\n--- borrow_records 表 ---")

    # 检查是否已有外键
    inspector = inspect(engine)
    fks = inspector.get_foreign_keys('borrow_records')
    fk_columns = []
    for fk in fks:
        fk_columns.extend(fk.get('constrained_columns', []))

    if 'device_id' in fk_columns:
        print("  [~] 外键约束已存在，跳过")
        return

    try:
        sql_execute(
            'ALTER TABLE borrow_records ADD CONSTRAINT fk_borrow_device '
            'FOREIGN KEY (device_id) REFERENCES inventory(device_id) ON DELETE CASCADE',
            '添加外键约束 borrow_records.device_id → inventory.device_id'
        )
    except Exception as e:
        print(f"  [!] 外键添加失败（可能已有不一致数据）: {e}")


def create_missing_tables():
    """创建不存在的新表"""
    existing_tables = get_existing_tables()
    new_tables = ['conversation_history']
    for table_name in new_tables:
        if table_name not in existing_tables:
            Base.metadata.tables[table_name].create(bind=engine)
            print(f"  [OK] 创建表 {table_name}")
        else:
            print(f"  [~] 表 {table_name} 已存在，跳过")


def add_column_if_not_exists(table_name, column_def):
    """如果列不存在则添加"""
    columns = get_columns(table_name)
    column_name = column_def.split()[0].strip('"').strip("'")
    if column_name not in columns:
        sql_execute(
            f'ALTER TABLE {table_name} ADD COLUMN {column_def}',
            f'添加字段 {table_name}.{column_name}'
        )
        return True
    else:
        print(f"  [~] 字段 {table_name}.{column_name} 已存在，跳过")
        return False


def init_admin_user():
    """初始化管理员账号"""
    print("\n--- 管理员账号 ---")
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == 'admin').first()
        if not existing:
            admin = User(
                username='admin',
                email='admin@inventory.local',
                hashed_password=pwd_context.hash('admin123'),
                role='admin',
                is_active=True
            )
            db.add(admin)
            db.commit()
            print("  [OK] 创建管理员账号: admin / admin123")
        else:
            print("  [~] 管理员账号已存在")
            # 重置密码
            existing.hashed_password = pwd_context.hash('admin123')
            db.commit()
            print("  [OK] 管理员密码已重置为: admin123")
    except Exception as e:
        print(f"  [!] 管理员账号处理失败: {e}")
        db.rollback()
    finally:
        db.close()


def run_migration():
    print("=" * 55)
    print("  库存管理系统数据库迁移 v2.0")
    print("=" * 55)

    fix_inventory_table()
    fix_users_table()
    fix_operation_logs_table()
    create_missing_tables()
    fix_borrow_records_fk()
    init_admin_user()

    print("\n" + "=" * 55)
    print("  数据库迁移完成!")
    print("=" * 55)


if __name__ == "__main__":
    run_migration()
