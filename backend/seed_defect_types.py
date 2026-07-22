"""种子脚本：插入 6 种 PCB 缺陷类型"""
from app.database.session import SessionLocal
from app.entity.db_models import DefectType

DEFECTS = [
    {"code": "MH", "name": "missing_hole", "name_cn": "缺孔",
     "severity": "major", "description": "PCB 上缺少应有的孔位", "is_active": True},
    {"code": "MB", "name": "mouse_bite", "name_cn": "鼠咬",
     "severity": "major", "description": "PCB 边缘出现类似鼠咬的缺口", "is_active": True},
    {"code": "OC", "name": "open_circuit", "name_cn": "开路",
     "severity": "critical", "description": "电路导线断裂导致开路", "is_active": True},
    {"code": "SC", "name": "short", "name_cn": "短路",
     "severity": "critical", "description": "不应连接的导线发生短路", "is_active": True},
    {"code": "SP", "name": "spur", "name_cn": "毛刺",
     "severity": "minor", "description": "蚀刻残留导致的铜箔毛刺", "is_active": True},
    {"code": "SPC", "name": "spurious_copper", "name_cn": "残铜",
     "severity": "minor", "description": "PCB 表面残留的多余铜箔", "is_active": True},
]

db = SessionLocal()
count = 0
for d in DEFECTS:
    existing = db.query(DefectType).filter(DefectType.code == d["code"]).first()
    if not existing:
        db.add(DefectType(**d))
        count += 1
db.commit()
db.close()
print(f"Inserted {count} new defect types (already existed: {6 - count})")
