import pymysql
from sqlalchemy import create_engine, text
from database import settings
from models import Base

def init_mysql_db():
    """初始化MySQL数据库"""
    try:
        # 首先连接到MySQL服务器（不指定数据库）
        temp_url = settings.database_url.rsplit('/', 1)[0] + '/mysql'
        temp_engine = create_engine(temp_url)
        
        with temp_engine.connect() as conn:
            # 创建数据库（如果不存在）
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS inventory_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            conn.commit()
        
        temp_engine.dispose()
        
        # 使用正确的数据库URL连接到inventory_db
        engine = create_engine(settings.database_url, echo=True)
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("MySQL数据库表创建成功!")
        
        # 检查表是否已创建
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"当前数据库中的表: {tables}")
        
        # 插入示例数据
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # 检查是否有数据
        result = db.execute(text("SELECT COUNT(*) FROM inventory")).fetchone()[0]
        if result == 0:
            # 插入示例数据
            sample_data = [
                ("SN001", "WiFi", "CAA241100001", "睡眠", "简约", "现有库存", "公司", None, None, "新入库设备"),
                ("SN002", "4G", "CAA241100002", "跌倒", "精品", "现有库存", "公司", None, None, "新入库设备"),
                ("SN003", "WiFi", "CAA241100003", "睡眠", "简约", "产品演示", "公司", "张三", None, "演示设备"),
                ("SN004", "4G", "CAA241100004", "跌倒", "精品", "商机试用", "客户A", "李四", "王五", "试用设备"),
                ("SN005", "WiFi", "CAA241100005", "跌倒", "简约", "技术开发/测试", "公司", "赵六", None, "测试设备"),
            ]
            
            insert_sql = """
            INSERT INTO inventory 
            (serial_number, version, device_id, type, packaging, device_attribute, owner, borrower, sales_person, remarks) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            for data in sample_data:
                db.execute(text(insert_sql), data)
            
            db.commit()
            print("示例数据插入成功!")
        else:
            print(f"inventory表中已有 {result} 条记录")
        
        # 检查DAA2512开头的设备
        result = db.execute(text("SELECT COUNT(*) FROM inventory WHERE device_id LIKE 'DAA2512%'")).fetchone()[0]
        print(f"DAA2512开头的设备数量: {result}")
        
        db.close()
        print("MySQL数据库初始化完成!")
        
    except Exception as e:
        print(f"MySQL数据库初始化过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    init_mysql_db()