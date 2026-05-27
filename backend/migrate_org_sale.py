"""
数据库迁移: 将 device_attribute 从 "组织售卖" 改为 "商机交付"
"""
from database import SessionLocal
from models import Inventory

def migrate():
    db = SessionLocal()
    try:
        count = db.query(Inventory).filter(
            Inventory.device_attribute == '组织售卖'
        ).count()
        print(f"找到 {count} 台 '组织售卖' 设备")

        if count > 0:
            updated = db.query(Inventory).filter(
                Inventory.device_attribute == '组织售卖'
            ).update({"device_attribute": "商机交付"}, synchronize_session=False)
            db.commit()
            print(f"已更新 {updated} 台设备: '组织售卖' → '商机交付'")
        else:
            print("无需迁移")

        # 验证
        after = db.query(Inventory).filter(
            Inventory.device_attribute == '商机交付'
        ).count()
        print(f"验证: 当前 '商机交付' 设备数 = {after}")
    except Exception as e:
        db.rollback()
        print(f"迁移失败: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
    print("迁移完成")
