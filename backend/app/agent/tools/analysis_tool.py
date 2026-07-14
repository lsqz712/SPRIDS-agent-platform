"""
分析工具
提供缺陷数据分析和批次良品率计算功能
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
from app.agent.tools import BaseTool, ToolRegistry
from app.entity.db_models import (
    DetectionResult, DetectionTask, PCBBatch, DefectType, DetectionScene
)
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
class DefectAnalysisTool(BaseTool):
    """缺陷数据分析工具"""
    def __init__(self, db: Session):
        self.db = db
    def get_name(self) -> str:
        return "analyze_defects"
    def get_description(self) -> str:
        return "分析缺陷数据，生成统计报告和维修建议"
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "检测任务 ID"
                },
                "batch_id": {
                    "type": "integer",
                    "description": "PCB 批次 ID（可选）"
                },
                "time_range": {
                    "type": "string",
                    "description": "时间范围，如 'today'/'week'/'month'"
                }
            }
        }
    def execute(self, **kwargs) -> Dict[str, Any]:
        task_id = kwargs.get("task_id")
        batch_id = kwargs.get("batch_id")
        time_range = kwargs.get("time_range")
        query = self.db.query(DetectionResult)
        if task_id:
            query = query.filter(DetectionResult.task_id == task_id)
        elif batch_id:
            tasks = self.db.query(DetectionTask.id).filter(DetectionTask.batch_id == batch_id).subquery()
            query = query.filter(DetectionResult.task_id.in_(tasks))
        elif time_range:
            end_time = datetime.now()
            if time_range == "today":
                start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
            elif time_range == "week":
                start_time = end_time - timedelta(days=7)
            elif time_range == "month":
                start_time = end_time - timedelta(days=30)
            else:
                start_time = end_time - timedelta(days=7)
            tasks = self.db.query(DetectionTask.id).filter(
                DetectionTask.created_at >= start_time
            ).subquery()
            query = query.filter(DetectionResult.task_id.in_(tasks))
        results = query.all()
        if not results:
            return {"error": "未找到检测结果数据"}
        defect_stats = self._calculate_defect_stats(results)
        repair_suggestions = self._generate_repair_suggestions(defect_stats["class_distribution"])
        risk_analysis = self._analyze_risk(defect_stats)
        return {
            "total_defects": defect_stats["total_defects"],
            "total_images": defect_stats["total_images"],
            "defects_per_image": defect_stats["defects_per_image"],
            "class_distribution": defect_stats["class_distribution"],
            "severity_distribution": defect_stats["severity_distribution"],
            "risk_analysis": risk_analysis,
            "repair_suggestions": repair_suggestions,
        }
    def _calculate_defect_stats(self, results: List[DetectionResult]) -> Dict[str, Any]:
        class_distribution = {}
        severity_distribution = {"minor": 0, "major": 0, "critical": 0}
        image_set = set()
        for result in results:
            class_name = result.class_name_cn or result.class_name
            class_distribution[class_name] = class_distribution.get(class_name, 0) + 1
            if result.severity:
                severity_distribution[result.severity.value] += 1
            else:
                severity_distribution["major"] += 1
            image_set.add(result.image_path)
        return {
            "total_defects": len(results),
            "total_images": len(image_set),
            "defects_per_image": round(len(results) / max(len(image_set), 1), 2),
            "class_distribution": class_distribution,
            "severity_distribution": severity_distribution,
        }
    def _generate_repair_suggestions(self, class_distribution: Dict[str, int]) -> List[Dict[str, str]]:
        suggestions = []
        repair_map = {
            "短路": {
                "description": "PCB 上相邻导体之间出现意外导通",
                "suggestion": "1. 检查焊锡量是否过多导致桥连\n2. 检查钢网开口是否过大\n3. 调整焊接温度曲线\n4. 检查 PCB 设计是否存在间距过小问题",
                "severity": "critical",
            },
            "开路": {
                "description": "预期导通的线路断开",
                "suggestion": "1. 检查元件引脚是否氧化\n2. 检查焊锡量是否不足\n3. 检查回流温度是否足够\n4. 检查元件是否虚焊",
                "severity": "critical",
            },
            "缺件": {
                "description": "元件未贴装到 PCB 上",
                "suggestion": "1. 检查贴片机吸嘴是否堵塞\n2. 检查供料器是否正常\n3. 检查元件是否用完\n4. 检查贴装坐标是否正确",
                "severity": "major",
            },
            "偏移": {
                "description": "元件贴装位置偏离",
                "suggestion": "1. 检查贴片机精度\n2. 检查 PCB 定位是否准确\n3. 调整贴装压力\n4. 检查钢网与 PCB 对齐情况",
                "severity": "major",
            },
            "焊点不良": {
                "description": "焊点形状、光泽或质量不符合要求",
                "suggestion": "1. 调整焊接温度曲线\n2. 检查助焊剂是否过期\n3. 检查焊锡品质\n4. 调整回流速度",
                "severity": "minor",
            },
        }
        for defect_name, count in class_distribution.items():
            if defect_name in repair_map:
                suggestions.append({
                    "defect_type": defect_name,
                    "count": count,
                    "description": repair_map[defect_name]["description"],
                    "suggestion": repair_map[defect_name]["suggestion"],
                    "severity": repair_map[defect_name]["severity"],
                })
        return sorted(suggestions, key=lambda x: ["critical", "major", "minor"].index(x["severity"]))
    def _analyze_risk(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        total = stats["total_defects"]
        severity = stats["severity_distribution"]
        risk_level = "low"
        if total == 0:
            risk_level = "low"
        elif severity["critical"] > 0 or total >= 20:
            risk_level = "critical"
        elif severity["major"] >= 5 or total >= 10:
            risk_level = "high"
        elif severity["major"] > 0 or total >= 5:
            risk_level = "medium"
        risk_map = {
            "critical": "高风险：存在致命缺陷，需立即停机排查",
            "high": "较高风险：缺陷数量较多，建议加强抽检",
            "medium": "中等风险：存在少量缺陷，需关注趋势",
            "low": "低风险：质量状况良好",
        }
        return {
            "level": risk_level,
            "description": risk_map[risk_level],
            "critical_count": severity["critical"],
            "major_count": severity["major"],
            "minor_count": severity["minor"],
        }
class PassRateTool(BaseTool):
    """批次良品率计算工具"""
    def __init__(self, db: Session):
        self.db = db
    def get_name(self) -> str:
        return "calculate_pass_rate"
    def get_description(self) -> str:
        return "计算 PCB 批次的良品率"
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "batch_id": {
                    "type": "integer",
                    "description": "PCB 批次 ID"
                }
            },
            "required": ["batch_id"]
        }
    def execute(self, **kwargs) -> Dict[str, Any]:
        batch_id = kwargs.get("batch_id")
        batch = self.db.query(PCBBatch).filter(PCBBatch.id == batch_id).first()
        if not batch:
            return {"error": f"PCB 批次 ID {batch_id} 不存在"}
        tasks = self.db.query(DetectionTask).filter(DetectionTask.batch_id == batch_id).all()
        total_images = sum(task.total_images for task in tasks)
        total_defects = 0
        defect_distribution = {}
        for task in tasks:
            results = self.db.query(DetectionResult).filter(DetectionResult.task_id == task.id).all()
            total_defects += len(results)
            for result in results:
                class_name = result.class_name_cn or result.class_name
                defect_distribution[class_name] = defect_distribution.get(class_name, 0) + 1
        pass_count = max(total_images - total_defects, 0)
        pass_rate = round((pass_count / max(total_images, 1)) * 100, 2)
        return {
            "batch_id": batch.id,
            "batch_no": batch.batch_no,
            "pcb_type": batch.pcb_type,
            "production_line": batch.production_line,
            "total_count": batch.total_count,
            "inspected_count": total_images,
            "pass_count": pass_count,
            "fail_count": total_defects,
            "pass_rate": pass_rate,
            "defect_distribution": defect_distribution,
            "status": batch.status,
            "updated_at": batch.updated_at.isoformat() if batch.updated_at else None,
        }
def register_analysis_tools(registry: ToolRegistry, db: Session):
    registry.register(DefectAnalysisTool(db))
    registry.register(PassRateTool(db))