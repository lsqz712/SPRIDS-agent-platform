"""
种子脚本：创建 PCB 缺陷检测场景 + DatasetVersion 记录。
运行: cd backend && python seed_dataset.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.database.session import SessionLocal
from app.entity.db_models import DetectionScene, DatasetVersion


def seed():
    db = SessionLocal()
    try:
        # 1. 确保场景存在
        scene = db.query(DetectionScene).filter(DetectionScene.name == "pcb_smt").first()
        if not scene:
            scene = DetectionScene(
                name="pcb_smt",
                display_name="PCB SMT 缺陷检测",
                description="PCB 表面贴装工艺缺陷检测，6类：缺孔、鼠咬、开路、短路、毛刺、残铜",
                category="industry",
                class_names=[
                    "missing_hole", "mouse_bite", "open_circuit",
                    "short", "spur", "spurious_copper",
                ],
                class_names_cn={
                    "missing_hole": "缺孔",
                    "mouse_bite": "鼠咬",
                    "open_circuit": "开路",
                    "short": "短路",
                    "spur": "毛刺",
                    "spurious_copper": "残铜",
                },
                is_active=True,
                created_by=1,
            )
            db.add(scene)
            db.commit()
            db.refresh(scene)
            print(f"[OK] 场景 pcb_smt 创建成功 (id={scene.id})")

        # 2. 确保 DatasetVersion 存在
        existing = (
            db.query(DatasetVersion)
            .filter(
                DatasetVersion.scene_id == scene.id,
                DatasetVersion.version == "v1.0.0",
            )
            .first()
        )
        if existing:
            print(f"[SKIP] DatasetVersion v1.0.0 已存在 (id={existing.id})")
            return

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_yaml_path = os.path.join(base_dir, "datasets", "pcb_defect", "data.yaml")

        if not os.path.exists(data_yaml_path):
            print(f"[ERROR] data.yaml 不存在: {data_yaml_path}")
            return

        dataset = DatasetVersion(
            scene_id=scene.id,
            version="v1.0.0",
            name="PCB 缺陷检测数据集 v1",
            description="Roboflow PCB Defect Detection，6类：缺孔、鼠咬、开路、短路、毛刺、残铜",
            storage_path="datasets/pcb_defect",
            data_yaml_path=data_yaml_path,
            image_count=1893,
            class_distribution={
                "missing_hole": "缺孔",
                "mouse_bite": "鼠咬",
                "open_circuit": "开路",
                "short": "短路",
                "spur": "毛刺",
                "spurious_copper": "残铜",
            },
            is_active=True,
            created_by=1,
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        print(f"[OK] DatasetVersion 创建成功 (id={dataset.id})")
        print(f"    data_yaml: {data_yaml_path}")
        print(f"    image_count: 1893 (train: 1511, val: 187, test: 195)")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
