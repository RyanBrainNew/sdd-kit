"""Pure helpers for SDD-L2 extensions.

This module intentionally owns no state transitions. The authoritative state
machine remains ``sdd/scripts/sdd.py``.
"""

from __future__ import annotations

import ast
import re
from typing import Any, Iterable


FEAT_RE = re.compile(r"^FEAT-\d{3}$")
REVIEW_FINDING_FIELDS = (
    "id",
    "location",
    "evidence",
    "impact",
    "recommendation",
    "authority",
    "severity",
    "verification",
    "blocking",
)
REVIEW_SEVERITIES = {"low", "medium", "high", "critical"}
REVIEW_VERIFICATION_STATES = {
    "open",
    "fixed",
    "verified",
    "closed",
    "resolved",
}
REVIEW_CLOSED_STATES = {"verified", "closed", "resolved"}
KNOWLEDGE_TYPES = {"SRC", "FACT", "BR", "CONFLICT", "GAP"}
KNOWLEDGE_REQUIRED_FIELDS = (
    "id",
    "type",
    "statement",
    "source",
    "version",
    "scope",
    "owner",
    "status",
    "links",
)
KNOWLEDGE_CONFIRMED_STATUSES = {"CONFIRMED", "APPROVED", "ACCEPTED"}
FIX_PATTERN_REQUIRED_FIELDS = (
    "id",
    "symptom",
    "root_cause",
    "trigger",
    "fix",
    "checks",
    "scope",
    "owner",
    "status",
)

CHECK_REGISTRY: dict[str, dict[str, Any]] = {
    "G0-01": {
        "gate": "G0",
        "title": "PRD 索引存在且来源模式正确",
        "trigger": "document",
        "level": "required",
        "waivable": False,
        "evidence": "docs/prd-index.md + config.prd_mode",
        "owner": "product-owner",
    },
    "G0-02": {
        "gate": "G0",
        "title": "工作项与 Spec 一致",
        "trigger": "document",
        "level": "required",
        "waivable": False,
        "evidence": "Spec 元数据 + PRD 索引行",
        "owner": "product-owner",
    },
    "G0-03": {
        "gate": "G0",
        "title": "Spec 在 PRD 索引中唯一登记",
        "trigger": "document",
        "level": "required",
        "waivable": False,
        "evidence": "PRD 索引结构化行",
        "owner": "product-owner",
    },
    "G0-04": {
        "gate": "G0",
        "title": "FEAT 一致且唯一",
        "trigger": "document",
        "level": "required",
        "waivable": False,
        "evidence": "Spec FEAT ID + PRD 索引",
        "owner": "product-owner",
    },
    "G0-05": {
        "gate": "G0",
        "title": "澄清标记清零",
        "trigger": "document",
        "level": "required",
        "waivable": False,
        "evidence": "PRD 索引澄清标记",
        "owner": "product-owner",
    },
    "G0-06": {
        "gate": "G0",
        "title": "PRD 来源模式匹配",
        "trigger": "document",
        "level": "required",
        "waivable": False,
        "evidence": "prd-index source 与 config.prd_mode",
        "owner": "platform",
    },
    "G1-01": {
        "gate": "G1",
        "title": "Spec 章节齐备",
        "trigger": "document",
        "level": "required",
        "waivable": False,
        "evidence": "spec.md 核心章节",
        "owner": "planner",
    },
    "G1-02": {
        "gate": "G1",
        "title": "Spec 标识与工作项有效",
        "trigger": "document",
        "level": "required",
        "waivable": False,
        "evidence": "Spec ID + 工作项 ID + FEAT",
        "owner": "planner",
    },
    "G1-03": {
        "gate": "G1",
        "title": "范围边界可判定",
        "trigger": "document",
        "level": "required",
        "waivable": False,
        "evidence": "In-Scope / Out-of-Scope",
        "owner": "planner",
    },
    "G1-04": {
        "gate": "G1",
        "title": "FR/AC 双向映射",
        "trigger": "document",
        "level": "required",
        "waivable": False,
        "evidence": "FR/AC 编号结构",
        "owner": "planner",
    },
    "G1-05": {
        "gate": "G1",
        "title": "AC 可执行",
        "trigger": "document",
        "level": "required",
        "waivable": False,
        "evidence": "Given/When/Then + 执行路径",
        "owner": "planner",
    },
    "G1-06": {
        "gate": "G1",
        "title": "无占位符与澄清残留",
        "trigger": "document",
        "level": "required",
        "waivable": False,
        "evidence": "TODO/占位符/NEEDS CLARIFICATION 扫描",
        "owner": "planner",
    },
    "G1-07": {
        "gate": "G1",
        "title": "FR/AC 定义唯一",
        "trigger": "document",
        "level": "required",
        "waivable": False,
        "evidence": "重复定义扫描",
        "owner": "planner",
    },
    "G2-01": {
        "gate": "G2",
        "title": "Design 章节齐备",
        "trigger": "document",
        "level": "required",
        "waivable": False,
        "evidence": "design.md 章节",
        "owner": "designer",
    },
    "G2-02": {
        "gate": "G2",
        "title": "全部 AC 有设计落点",
        "trigger": "document",
        "level": "required",
        "waivable": False,
        "evidence": "design.md AC 覆盖",
        "owner": "designer",
    },
    "G2-03": {
        "gate": "G2",
        "title": "方案、风险与回滚完整",
        "trigger": "document",
        "level": "required",
        "waivable": False,
        "evidence": "方案概述 + 依赖与风险 + 回滚方案",
        "owner": "designer",
    },
    "G2-04": {
        "gate": "G2",
        "title": "风险责任人与缓解措施完整",
        "trigger": "document",
        "level": "advisory",
        "waivable": False,
        "evidence": "风险表字段",
        "owner": "designer",
    },
    "G3-01": {
        "gate": "G3",
        "title": "Task 字段完整",
        "trigger": "document",
        "level": "required",
        "waivable": False,
        "evidence": "公司任务表",
        "owner": "planner",
    },
    "G3-02": {
        "gate": "G3",
        "title": "AC 全部有 Task",
        "trigger": "document",
        "level": "required",
        "waivable": False,
        "evidence": "AC—Task 映射",
        "owner": "planner",
    },
    "G3-03": {
        "gate": "G3",
        "title": "依赖 DAG 无环",
        "trigger": "document",
        "level": "required",
        "waivable": False,
        "evidence": "依赖图与依赖列",
        "owner": "planner",
    },
    "G3-04": {
        "gate": "G3",
        "title": "Task 测试可定位",
        "trigger": "document",
        "level": "required",
        "waivable": False,
        "evidence": "测试类/方法 + 命令",
        "owner": "planner",
    },
    "G3-05": {
        "gate": "G3",
        "title": "知识索引结构有效",
        "trigger": "document",
        "level": "required",
        "waivable": False,
        "evidence": "docs/knowledge/index.md",
        "owner": "knowledge-owner",
    },
    "G3-06": {
        "gate": "G3",
        "title": "Fix Pattern 可执行闭环",
        "trigger": "document",
        "level": "required",
        "waivable": False,
        "evidence": "docs/knowledge/patterns/FP-*.md",
        "owner": "quality-owner",
    },
    "G4-01": {
        "gate": "G4",
        "title": "全部 Task 完成",
        "trigger": "code",
        "level": "required",
        "waivable": False,
        "evidence": "tasks.md 状态",
        "owner": "implementer",
    },
    "G4-02": {
        "gate": "G4",
        "title": "Task 有验证证据",
        "trigger": "code",
        "level": "required",
        "waivable": False,
        "evidence": "verification.md + events",
        "owner": "implementer",
    },
    "G4-03": {
        "gate": "G4",
        "title": "测试类和方法存在",
        "trigger": "code",
        "level": "required",
        "waivable": False,
        "evidence": "测试文件定位",
        "owner": "implementer",
    },
    "G4-04": {
        "gate": "G4",
        "title": "Review 证据满足风险要求",
        "trigger": "code",
        "level": "required",
        "waivable": False,
        "evidence": "verification.md / review-findings.json",
        "owner": "reviewer",
    },
    "G4-05": {
        "gate": "G4",
        "title": "证据与产物未被篡改",
        "trigger": "code",
        "level": "required",
        "waivable": False,
        "evidence": "哈希与事件链",
        "owner": "reviewer",
    },
    "G5-01": {
        "gate": "G5",
        "title": "验证文档完整",
        "trigger": "ci",
        "level": "required",
        "waivable": False,
        "evidence": "verification.md",
        "owner": "verifier",
    },
    "G5-02": {
        "gate": "G5",
        "title": "全部 AC 有验证覆盖",
        "trigger": "ci",
        "level": "required",
        "waivable": False,
        "evidence": "AC 覆盖表",
        "owner": "verifier",
    },
    "G5-03": {
        "gate": "G5",
        "title": "测试命令真实执行成功",
        "trigger": "ci",
        "level": "required",
        "waivable": False,
        "evidence": "verification-evidence.jsonl",
        "owner": "verifier",
    },
    "G5-04": {
        "gate": "G5",
        "title": "测试定义真实存在",
        "trigger": "ci",
        "level": "required",
        "waivable": False,
        "evidence": "测试文件扫描",
        "owner": "verifier",
    },
    "G5-05": {
        "gate": "G5",
        "title": "独立 Review 结论有效",
        "trigger": "ci",
        "level": "required",
        "waivable": False,
        "evidence": "review findings",
        "owner": "reviewer",
    },
    "G5-06": {
        "gate": "G5",
        "title": "G0–G4 报告齐备",
        "trigger": "ci",
        "level": "required",
        "waivable": False,
        "evidence": "sdd/reports/<spec>/gate*-report.md",
        "owner": "verifier",
    },
    "G5-07": {
        "gate": "G5",
        "title": "Gate 5 结论为 PASS",
        "trigger": "ci",
        "level": "required",
        "waivable": False,
        "evidence": "verification.md",
        "owner": "verifier",
    },
    "G5-08": {
        "gate": "G5",
        "title": "无伪造 AC 标签或测试",
        "trigger": "ci",
        "level": "required",
        "waivable": False,
        "evidence": "测试函数与执行证据",
        "owner": "verifier",
    },
    "G5-09": {
        "gate": "G5",
        "title": "纯文档/配置变更测试豁免",
        "trigger": "ci",
        "level": "required",
        "waivable": True,
        "evidence": "人工豁免记录（范围、原因、审批人、到期时间、证据）",
        "owner": "verifier",
    },
    "G5-10": {
        "gate": "G5",
        "title": "审计事件链可验证",
        "trigger": "ci",
        "level": "required",
        "waivable": False,
        "evidence": "events.jsonl 哈希链",
        "owner": "auditor",
    },
}

SECURITY_CHECK_IDS = frozenset(
    {
        "G0-02",
        "G0-03",
        "G0-04",
        "G4-03",
        "G4-05",
        "G5-03",
        "G5-04",
        "G5-08",
    }
)

_ERROR_HINTS = {
    "G0-01": ("缺少 PRD", "prd-index.md 头部", "source="),
    "G0-02": ("工作项不一致", "没有登记工作项", "重复登记工作项"),
    "G0-03": ("没有登记 Spec", "重复登记 Spec"),
    "G0-04": ("FEAT",),
    "G0-05": ("澄清", "CLARIFICATION"),
    "G0-06": ("prd_mode", "source="),
    "G1-01": ("缺少章节",),
    "G1-02": ("Spec ID", "工作项 ID", "FEAT ID"),
    "G1-03": ("In-Scope", "Out-of-Scope", "范围声明"),
    "G1-04": ("没有对应 AC", "没有对应的 FR", "没有 FR"),
    "G1-05": ("Given", "When", "Then", "执行路径"),
    "G1-06": ("TODO", "占位符", "CLARIFICATION"),
    "G1-07": ("重复 FR", "重复 AC", "重复定义"),
    "G2-01": ("design.md 缺少章节", "轻量设计章节"),
    "G2-02": ("没有覆盖以下 AC",),
    "G2-03": ("方案概述", "依赖与风险", "回滚方案"),
    "G2-04": ("负责人", "缓解"),
    "G3-01": (
        "没有任务",
        "没有任务描述",
        "没有明确验收标准",
        "没有具体单元测试",
        "没有单 Task 测试命令",
        "并行标识",
        "状态必须",
    ),
    "G3-02": ("没有关联 AC", "没有关联 FR", "没有对应任务", "不存在的 AC"),
    "G3-03": ("依赖", "存在环"),
    "G3-04": ("测试类", "测试命令"),
    "G3-05": ("知识记录", "知识索引"),
    "G3-06": ("Fix Pattern", "CHK-", "check_command"),
    "G4-01": ("Task 全部完成", "未完成的 task"),
    "G4-02": ("验证证据",),
    "G4-03": ("测试类/方法", "测试名", "测试定义"),
    "G4-04": ("独立审查", "Review", "finding"),
    "G4-05": ("哈希", "篡改", "证据"),
    "G5-01": ("verification.md 缺少章节", "“命令”", "“结果”"),
    "G5-02": ("没有覆盖以下 AC",),
    "G5-03": ("测试命令", "成功退出码", "未执行", "退出码"),
    "G5-04": ("测试文件", "没有关联以下 AC"),
    "G5-05": ("独立审查", "Review", "finding", "阻断"),
    "G5-06": ("Gate 报告", "G0–G4"),
    "G5-07": ("Gate 5 结论", "PASS/通过"),
    "G5-08": ("伪造", "标签", "测试名"),
    "G5-09": ("纯文档", "纯配置", "人工豁免", "G5-09"),
    "G5-10": ("事件链", "event_sha256", "prev_sha256"),
}


def check_ids_for_gate(gate: str) -> list[str]:
    return [
        check_id
        for check_id, definition in CHECK_REGISTRY.items()
        if definition["gate"] == gate
    ]


def check_id_for_error(gate: str, error: str) -> str:
    explicit = re.match(r"^\s*(G\d-\d{2})\b", str(error))
    if explicit and explicit.group(1) in CHECK_REGISTRY:
        return explicit.group(1)
    for check_id in check_ids_for_gate(gate):
        for hint in _ERROR_HINTS.get(check_id, ()):
            if hint.lower() in error.lower():
                return check_id
    return f"{gate}-99"


def build_check_results(
    gate: str,
    errors: Iterable[str],
    selected: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    error_list = [str(error) for error in errors]
    allowed = set(selected) if selected is not None else set(check_ids_for_gate(gate))
    results: list[dict[str, Any]] = []
    for check_id in check_ids_for_gate(gate):
        if check_id not in allowed:
            continue
        definition = CHECK_REGISTRY[check_id]
        failures = [
            error
            for error in error_list
            if check_id_for_error(gate, error) == check_id
        ]
        if failures:
            result = "warn" if definition["level"] == "advisory" else "block"
        else:
            result = "pass"
        results.append(
            {
                "id": check_id,
                "gate": gate,
                "title": definition["title"],
                "trigger": definition["trigger"],
                "level": definition["level"],
                "waivable": bool(definition["waivable"]),
                "evidence": definition["evidence"],
                "owner": definition["owner"],
                "result": result,
                "detail": " / ".join(failures) if failures else "检查通过",
            }
        )
    unclassified = [
        error
        for error in error_list
        if check_id_for_error(gate, error).endswith("-99")
    ]
    if unclassified:
        results.append(
            {
                "id": f"{gate}-99",
                "gate": gate,
                "title": "未分类检查",
                "trigger": "document",
                "level": "required",
                "waivable": False,
                "evidence": "错误详情",
                "owner": "platform",
                "result": "block",
                "detail": " / ".join(unclassified),
            }
        )
    return results


def blocking_errors(
    gate: str,
    errors: Iterable[str],
    selected: Iterable[str] | None = None,
) -> list[str]:
    results = build_check_results(gate, errors, selected)
    blocked_ids = {
        item["id"]
        for item in results
        if item["result"] == "block"
    }
    return [
        str(error)
        for error in errors
        if check_id_for_error(gate, str(error)) in blocked_ids
    ]


def next_feat_number(prd_text: str) -> int:
    numbers = [
        int(match.group(1))
        for match in re.finditer(r"\bFEAT-([0-9]{3})\b", prd_text)
    ]
    return max(numbers, default=0) + 1


def normalize_row(row: dict[str, str], *names: str) -> str:
    for name in names:
        value = row.get(name)
        if value is not None:
            return str(value).strip()
    return ""


def extract_backtick_paths(text: str) -> list[str]:
    paths: list[str] = []
    for match in re.finditer(r"`([^`\n]+)`", text):
        value = match.group(1).strip().replace("\\", "/")
        if not value or "://" in value or value.startswith("-"):
            continue
        if (
            "/" in value
            or re.search(r"\.[A-Za-z0-9]{1,8}$", value)
            or value.startswith(".")
        ):
            paths.append(value)
    return list(dict.fromkeys(paths))


def parse_front_matter(text: str) -> dict[str, Any]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    data: dict[str, Any] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        raw = value.strip()
        if not key:
            continue
        if "," in raw:
            data[key] = [item.strip() for item in raw.split(",") if item.strip()]
        elif raw.startswith("[") and raw.endswith("]"):
            data[key] = [
                item.strip().strip("'\"")
                for item in raw[1:-1].split(",")
                if item.strip()
            ]
        else:
            data[key] = raw.strip("'\"")
    return data


def review_required_for(
    workflow: dict[str, Any],
    state: dict[str, Any],
) -> bool:
    if workflow.get("review_required") is True:
        return True
    policy = workflow.get("review_policy")
    required_for = {"medium", "high"}
    if isinstance(policy, dict):
        for item in policy.get("required_for_risk", []) or []:
            required_for.add(str(item).lower())
    return str(state.get("risk") or "low").lower() in required_for


def validate_review_findings(
    payload: Any,
) -> tuple[list[str], list[str]]:
    if not isinstance(payload, list):
        return ["review-findings.json 必须是 finding 数组"], []
    errors: list[str] = []
    unresolved: list[str] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            errors.append(f"review finding #{index} 必须是对象")
            continue
        finding_id = str(item.get("id") or "").strip()
        label = finding_id or f"#{index}"
        missing = [
            field
            for field in REVIEW_FINDING_FIELDS
            if field not in item or item.get(field) in (None, "")
        ]
        if missing:
            errors.append(
                f"Review finding {label} 缺少字段：" + ", ".join(missing)
            )
        unknown = sorted(set(item) - set(REVIEW_FINDING_FIELDS))
        if unknown:
            errors.append(
                f"Review finding {label} 包含未知字段：" + ", ".join(unknown)
            )
        if finding_id:
            if finding_id in seen_ids:
                errors.append(f"Review finding ID 重复：{finding_id}")
            seen_ids.add(finding_id)
        severity = str(item.get("severity") or "").strip().lower()
        if severity and severity not in REVIEW_SEVERITIES:
            errors.append(
                f"Review finding {label} 的 severity 必须是 "
                + "/".join(sorted(REVIEW_SEVERITIES))
            )
        verification = str(item.get("verification") or "").strip().lower()
        if (
            verification
            and verification not in REVIEW_VERIFICATION_STATES
        ):
            errors.append(
                f"Review finding {label} 的 verification 必须是 "
                + "/".join(sorted(REVIEW_VERIFICATION_STATES))
            )
        blocking = item.get("blocking")
        if not isinstance(blocking, bool):
            errors.append(
                f"Review finding {label} 的 blocking 必须是布尔值"
            )
        elif blocking and verification not in REVIEW_CLOSED_STATES:
            unresolved.append(label)
    return errors, unresolved


def _missing_record_fields(
    record: dict[str, Any],
    required: Iterable[str],
) -> list[str]:
    return [
        field
        for field in required
        if field not in record
        or record.get(field) in (None, "")
        or (
            isinstance(record.get(field), list)
            and not record.get(field)
        )
    ]


def knowledge_record_errors(record: dict[str, Any]) -> list[str]:
    record_id = str(record.get("id") or "").strip()
    label = record_id or "knowledge record"
    errors: list[str] = []
    missing = _missing_record_fields(record, KNOWLEDGE_REQUIRED_FIELDS)
    if missing:
        errors.append(
            f"知识记录 {label} 缺少字段：" + ", ".join(missing)
        )
    record_type = str(record.get("type") or "").strip().upper()
    if record_type and record_type not in KNOWLEDGE_TYPES:
        errors.append(
            f"知识记录 {label} 的 type 必须是 "
            + "/".join(sorted(KNOWLEDGE_TYPES))
        )
    if record_id and record_type:
        prefix = record_id.split("-", 1)[0].upper()
        if prefix != record_type:
            errors.append(
                f"知识记录 {label} 的 ID 前缀必须与 type {record_type} 一致"
            )
    links = str(record.get("links") or "")
    if links and not re.search(
        r"\b(?:FEAT|FR|AC)-\d",
        links,
    ):
        errors.append(
            f"知识记录 {label} 的 links 必须关联 FEAT/FR/AC"
        )
    source = str(record.get("source") or "").strip()
    status = str(record.get("status") or "").strip().upper()
    if (
        status in KNOWLEDGE_CONFIRMED_STATUSES
        and source.lower() in {"", "n/a", "na", "none", "unknown", "待补充", "tbd"}
    ):
        errors.append(
            f"知识记录 {label} 没有权威来源，不能标记为 {status}"
        )
    return errors


def fix_pattern_errors(record: dict[str, Any]) -> list[str]:
    pattern_id = str(record.get("id") or "").strip()
    label = pattern_id or "Fix Pattern"
    errors: list[str] = []
    missing = _missing_record_fields(record, FIX_PATTERN_REQUIRED_FIELDS)
    if missing:
        errors.append(
            f"{label} 缺少字段：" + ", ".join(missing)
        )
    if pattern_id and not re.fullmatch(r"FP-\d{3}", pattern_id):
        errors.append(f"{label} 的 ID 必须符合 FP-xxx")
    raw_checks = record.get("checks") or record.get("check") or []
    checks = raw_checks if isinstance(raw_checks, list) else [raw_checks]
    check_ids = [
        str(item)
        for item in checks
        if re.fullmatch(r"CHK-\d{3}", str(item).strip())
    ]
    if not check_ids:
        errors.append(f"{label} 必须关联至少一个 CHK-xxx 可执行检查")
    if not str(record.get("check_command") or "").strip():
        errors.append(f"{label} 必须记录 check_command")
    return errors


def pattern_applies(pattern: dict[str, Any], paths: Iterable[str]) -> bool:
    raw = pattern.get("applies_to") or pattern.get("scope") or ""
    values = raw if isinstance(raw, list) else [str(raw)]
    normalized = [str(path).replace("\\", "/") for path in paths]
    for value in values:
        value = str(value).replace("\\", "/").strip()
        if not value or value == "*":
            return True
        if value.endswith("/") and any(path.startswith(value) for path in normalized):
            return True
        if value in normalized:
            return True
        if "*" in value:
            regex = "^" + re.escape(value).replace(r"\*", ".*") + "$"
            if any(re.match(regex, path) for path in normalized):
                return True
    return False


def traceability_errors(
    rows: Iterable[dict[str, str]],
    *,
    spec_id: str,
    work_item: str,
    spec_feat: str,
    require_feat: bool,
    clarification_count: int,
    clarification_marker: bool,
) -> list[str]:
    """Validate the structured work item -> FEAT -> Spec chain."""
    errors: list[str] = []
    row_list = list(rows)
    current = [
        row
        for row in row_list
        if normalize_row(row, "specid", "spec_id") == spec_id
    ]
    if not current:
        errors.append(f"G0-03 docs/prd-index.md 没有登记 Spec {spec_id}")
    elif len(current) > 1:
        errors.append(
            f"G0-03 docs/prd-index.md 重复登记 Spec {spec_id}，共 {len(current)} 行"
        )

    work_rows = [
        row
        for row in row_list
        if normalize_row(row, "工作项id", "workitemid") == work_item
    ]
    if not work_rows:
        errors.append(f"G0-02 docs/prd-index.md 没有登记工作项 {work_item}")
    elif len(work_rows) > 1:
        errors.append(
            f"G0-02 docs/prd-index.md 重复登记工作项 {work_item}，共 {len(work_rows)} 行"
        )

    row = current[0] if len(current) == 1 else None
    row_feat = normalize_row(row or {}, "feat", "featid") if row else ""
    if require_feat:
        if not FEAT_RE.fullmatch(spec_feat):
            errors.append(
                f"G0-04 spec.md 缺少有效 FEAT ID（当前 {spec_feat or '空'}）"
            )
        if not FEAT_RE.fullmatch(row_feat):
            errors.append(
                f"G0-04 docs/prd-index.md 中 {spec_id} 的 FEAT 为空或格式错误"
            )
        if spec_feat and row_feat and spec_feat != row_feat:
            errors.append(
                f"G0-04 FEAT 与 Spec 不一致：spec.md={spec_feat}，"
                f"prd-index={row_feat}"
            )

    if row and work_item:
        row_work = normalize_row(row, "工作项id", "workitemid")
        if row_work != work_item:
            errors.append(
                f"G0-02 工作项不一致：Spec={work_item}，prd-index={row_work}"
            )

    feat_owners: dict[str, list[str]] = {}
    for item in row_list:
        feat = normalize_row(item, "feat", "featid")
        item_spec = normalize_row(item, "specid", "spec_id")
        if FEAT_RE.fullmatch(feat):
            feat_owners.setdefault(feat, []).append(item_spec)
    for feat, owners in sorted(feat_owners.items()):
        if len(owners) > 1:
            errors.append(
                f"G0-04 FEAT 重复：{feat} 同时关联 "
                + ", ".join(owner or "(空 Spec)" for owner in owners)
            )

    if clarification_marker:
        errors.append("G0-05 docs/prd-index.md 还有 [NEEDS CLARIFICATION] 标记")
    if clarification_count:
        errors.append(
            f"G0-05 工作项 {work_item} 仍有 {clarification_count} 个澄清标记"
        )
    return errors


CODE_EXTENSIONS = (
    ".py",
    ".java",
    ".kt",
    ".go",
    ".rs",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".vue",
    ".cs",
    ".rb",
    ".php",
    ".scala",
    ".swift",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".sql",
)

TEST_PATH_RE = re.compile(
    r"(^|/)(tests?|__tests__|specs?)/"
    r"|(^|/)test_[^/]+$"
    r"|(^|/)[^/]+_(test|spec)\.[A-Za-z0-9]+$"
    r"|(^|/)[^/]+Test\.[A-Za-z0-9]+$",
    re.IGNORECASE,
)

AC_ID_RE = re.compile(r"\bAC-\d{3}-[1-9]\d*\b")


def is_code_path(path: str) -> bool:
    normalized = path.replace("\\", "/").strip()
    if not normalized or normalized.startswith("docs/"):
        return False
    if TEST_PATH_RE.search(normalized):
        return False
    return normalized.lower().endswith(CODE_EXTENSIONS)


def declared_code_paths(text: str) -> list[str]:
    return [
        path
        for path in extract_backtick_paths(text)
        if is_code_path(path)
    ]


def normalize_test_name(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _strip_docstrings(body: str) -> str:
    return re.sub(
        r"(?s)\"\"\".*?\"\"\"|'''.*?'''",
        "",
        body,
    )


def _has_executable_assertion(body: str) -> bool:
    code = _strip_docstrings(body)
    code = re.sub(r"(?m)#.*$", "", code)
    return bool(
        re.search(
            r"(?m)(^|\s)(assert\b|assert\w+|self\.assert\w+|self\.fail\b"
            r"|pytest\.raises|self\.assertRaises|raise\s+\w+)",
            code,
        )
    )


def scan_test_definitions(
    files: Iterable[tuple[str, str]],
) -> dict[str, dict[str, Any]]:
    """Locate real test definitions and the AC ids they execute.

    Only methods inside a ``TestCase`` subclass, or module-level pytest-style
    functions, count. A tag in a docstring/comment attached to a body without
    an executable assertion does not count as coverage.
    """
    source_files = list(files)
    python_files = [
        (relative, text)
        for relative, text in source_files
        if relative.lower().endswith(".py")
    ]
    other_files = [
        (relative, text)
        for relative, text in source_files
        if not relative.lower().endswith(".py")
    ]

    definitions: dict[str, dict[str, Any]] = {}
    parsed: list[tuple[str, str, ast.AST]] = []
    class_bases: dict[str, list[str]] = {}
    for relative, text in python_files:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        parsed.append((relative, text, tree))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            bases: list[str] = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(base.attr)
            class_bases[node.name] = bases

    testcase_cache: dict[str, bool] = {}

    def is_python_testcase(name: str, seen: set[str]) -> bool:
        if name in testcase_cache:
            return testcase_cache[name]
        if name.endswith("TestCase") or name in {"TestCase", "TransactionTestCase"}:
            testcase_cache[name] = True
            return True
        if name in seen:
            return False
        seen = {*seen, name}
        result = any(is_python_testcase(base, seen) for base in class_bases.get(name, []))
        testcase_cache[name] = result
        return result

    for relative, text, tree in parsed:
        def visit(node: ast.AST, classes: list[str]) -> None:
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    visit(child, [*classes, node.name])
                return
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("test"):
                    return
                owner = classes[-1] if classes else None
                if owner is not None and not is_python_testcase(owner, set()):
                    return
                source = ast.get_source_segment(text, node) or ""
                if not _has_executable_assertion(source):
                    return
                record = {
                    "name": node.name,
                    "normalized": normalize_test_name(node.name),
                    "class": owner,
                    "path": relative,
                    "acs": sorted(set(AC_ID_RE.findall(source))),
                }
                definitions[node.name] = record
                definitions.setdefault(record["normalized"], record)
                return
            for child in ast.iter_child_nodes(node):
                visit(child, classes)

        visit(tree, [])

    if not other_files:
        return definitions

    file_lines: list[tuple[str, list[str]]] = []
    class_index: dict[str, list[tuple[str, list[str], int]]] = {}
    for relative, text in other_files:
        lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
        file_lines.append((relative, lines))
        for index, line in enumerate(lines):
            match = re.match(
                r"^(\s*)class\s+([A-Za-z_]\w*)\s*(?:\(([^)]*)\))?\s*:",
                line,
            )
            if not match:
                continue
            indent = len(match.group(1))
            name = match.group(2)
            bases = [
                item.strip().split(".")[-1]
                for item in re.split(r",", match.group(3) or "")
                if item.strip()
            ]
            class_index.setdefault(name, []).append(
                (relative, bases, index)
            )

    testcase_cache: dict[str, bool] = {}

    def is_testcase(name: str, seen: set[str]) -> bool:
        if name in testcase_cache:
            return testcase_cache[name]
        if name.endswith("TestCase") or name in {"TestCase", "TransactionTestCase"}:
            testcase_cache[name] = True
            return True
        if name in seen:
            return False
        seen = {*seen, name}
        entries = class_index.get(name, [])
        result = False
        for _relative, bases, _index in entries:
            if any(
                base.endswith("TestCase")
                or base in {"TransactionTestCase"}
                or is_testcase(base, seen)
                for base in bases
            ):
                result = True
                break
        testcase_cache[name] = result
        return result

    for relative, lines in file_lines:
        classes = [
            (index, len(match.group(1)), match.group(2))
            for index, line in enumerate(lines)
            if (
                match := re.match(
                    r"^(\s*)class\s+([A-Za-z_]\w*)\s*(?:\([^)]*\))?\s*:",
                    line,
                )
            )
        ]
        for index, line in enumerate(lines):
            match = re.match(
                r"^(\s*)(?:async\s+)?def\s+(test[A-Za-z0-9_]*)\s*\(",
                line,
            )
            if not match:
                continue
            def_indent = len(match.group(1))
            method = match.group(2)
            owner = None
            for class_index_line, class_indent, class_name in classes:
                if class_index_line >= index:
                    break
                if class_indent < def_indent:
                    owner = class_name
            if owner is not None and not is_testcase(owner, set()):
                continue
            body_lines: list[str] = []
            for following in lines[index + 1 :]:
                if following.strip() and len(following) - len(following.lstrip()) <= def_indent:
                    break
                body_lines.append(following)
            body = "\n".join(body_lines)
            if not _has_executable_assertion(body):
                continue
            record = {
                "name": method,
                "normalized": normalize_test_name(method),
                "class": owner,
                "path": relative,
                "acs": sorted(set(AC_ID_RE.findall(body))),
            }
            definitions[method] = record
            definitions.setdefault(record["normalized"], record)
    return definitions


def test_reference_errors(
    tasks_text: str,
    definitions: dict[str, dict[str, Any]],
    test_files_present: bool = False,
) -> list[str]:
    if not definitions and not test_files_present:
        return []
    references = list(
        dict.fromkeys(
            re.findall(
                r"\b([A-Za-z_]\w*)#(test[A-Za-z0-9_]*)\b",
                tasks_text,
            )
        )
    )
    errors: list[str] = []
    for owner, method in references:
        if method in definitions or normalize_test_name(method) in definitions:
            continue
        errors.append(
            f"G4-03 任务表引用的测试 {owner}#{method} 在测试文件中不存在"
        )
    return errors
