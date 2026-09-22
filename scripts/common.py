"""Shared, standard-library-only project records. No model execution."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

STAGES = [
    ("S0", "接收与规划", "reports/intake.md", "范围、材料、规则、资源与预算已核实"),
    ("S1", "选题与拆解", "reports/requirements.md", "全部问题及具体要求均登记，有原文定位"),
    ("S2", "数据与假设检查", "reports/data_assumptions.md", "输入含义明确，关键歧义已处理或条件化"),
    ("S3", "建模与验证设计", "reports/modeling.md", "模型可实现，验证、接口及停止条件明确"),
    ("S4", "基础实现", "reports/baseline_check.md", "实际运行基础流程，约束与小实例检查通过"),
    ("S5", "改进与验证", "reports/results.md", "主要结论有相应对照、误差或理论证据"),
    ("S6", "Markdown论文", "paper/paper.md", "逐项答题，结论、图表和数值与证据一致"),
    ("S7", "最终验收", "reports/review.md", "必要数学、实现、覆盖与表达检查通过"),
    ("S8", "交付归档", "reports/delivery.md", "Markdown与支持材料齐全，交付状态真实"),
]
SCOPES = {
    "full": list(range(9)),
    "analysis": [0, 1, 2, 3],
    "coding": [0, 1, 2, 3, 4, 5, 7],
    "writing": [0, 1, 6, 7, 8],
    "review": [0, 1, 7],
}
TASK_STATES = {"TODO", "DOING", "BLOCKED", "DONE", "SKIPPED", "STALE"}
CHECK_STATES = {"PASS", "FAIL", "NOT_RUN", "BLOCKED", "NA"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def location(root, relative):
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError("路径必须为非空的项目相对路径")
    if Path(relative).is_absolute():
        raise ValueError("需要项目相对路径: " + relative)
    root = Path(root).resolve()
    p = (root / relative).resolve()
    if not p.is_relative_to(root):
        raise ValueError("路径超出项目目录: " + relative)
    return p


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(root, paths):
    out = {}
    for item in paths:
        path = location(root, item)
        if not path.is_file():
            raise ValueError("证据文件不存在: " + item)
        relative = path.relative_to(Path(root).resolve()).as_posix()
        if relative in {"state.json", "todo.md", "delivery_manifest.json"}:
            raise ValueError("不要把易变状态/待办/冻结清单用作科学证据: " + relative)
        out[relative] = digest(path)
    return out


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp-" + str(os.getpid()))
    try:
        temp.write_text(text, encoding="utf-8")
        temp.replace(path)
    finally:
        if temp.exists():
            temp.unlink()


def write_json(path, obj):
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def read_state(root):
    with (Path(root) / "state.json").open(encoding="utf-8") as stream:
        state = json.load(stream)
    if not isinstance(state, dict) or state.get("schema_version") != 1:
        raise ValueError("不支持的state.json结构")
    return state


def ensure_unfrozen(root):
    if (Path(root) / "delivery_manifest.json").exists():
        raise ValueError("项目已冻结；为新修改复制新版本，并保留旧交付清单，不能静默覆盖")


def cell(value):
    if value is None:
        return "未知"
    if isinstance(value, list):
        value = "、".join(str(v) for v in value) or "—"
    return str(value).replace("|", "／").replace("\n", "；")


def render_todo(state):
    out = [
        "# 待办事项", "",
        "依据 state.json 生成。修改结构化任务后运行 project.py sync；勾选代表有证据的完成。",
        "", "当前阶段：" + str(state.get("current_stage", "未知")),
        "任务范围：" + str(state.get("scope", "未知")),
        "", "状态：TODO 待做；DOING 正在做；BLOCKED 受阻；DONE 有证据完成；SKIPPED 有理由跳过可选项；STALE 需重新核验。",
        "", "## 下一步与阻塞", "",
    ]
    tasks = state.get("tasks", [])
    done = {t["id"] for t in tasks if t.get("status") == "DONE" or
            (t.get("status") == "SKIPPED" and not t.get("required", True))}
    ready = [t for t in tasks if t.get("status") in {"TODO", "DOING", "STALE"}
             and set(t.get("dependencies", [])).issubset(done)]
    rank = {"P0": 0, "P1": 1, "P2": 2}
    for t in sorted(ready, key=lambda t: (rank.get(t.get("priority"), 9), t["id"]))[:8]:
        out.append("- " + t["id"] + "：" + t["title"] + "；通过标准：" + t.get("acceptance", "待定义"))
    if not ready:
        out.append("- 无依赖已满足的未完成任务；检查是否完成、受阻或需要拆解新任务。")
    for t in tasks:
        if t.get("status") == "BLOCKED":
            out.append("- 受阻 " + t["id"] + "：" + t.get("blocker", "未说明原因"))
    for sid, name, _, _ in STAGES:
        rows = [t for t in tasks if t.get("stage") == sid]
        if not rows:
            continue
        out += ["", "## " + sid + " " + name, "",
                "| 完成 | ID / 状态 | 任务 / 对应要求 | 优先级 / 责任人 / 预算 | 依赖 | 产出 | 完成标准 | 证据 / 阻塞 / 备注 |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        for t in rows:
            mark = "[x]" if t.get("status") == "DONE" else "[ ]"
            budget = t.get("estimate_minutes")
            columns = [
                mark, t["id"] + " / " + t.get("status", "TODO"),
                t["title"] + "；" + cell(t.get("requirement_ids", [])),
                t.get("priority", "P1") + " / " + t.get("owner", "执行者") +
                " / " + (str(budget) + "分钟" if budget is not None else "待估"),
                t.get("dependencies", []), t.get("outputs", []), t.get("acceptance", ""),
                cell(t.get("evidence", [])) + "；" + t.get("blocker", "") + "；" + t.get("note", ""),
            ]
            out.append("| " + " | ".join(cell(x) for x in columns) + " |")
    out += ["", "## 逐项要求覆盖", "",
            "| ID | 顶层问题 | 具体要求 | 来源 | 解题状态 | 完成证据 | 论文锚点 |",
            "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in state.get("requirements", []):
        out.append("| " + " | ".join(cell(r.get(k, "")) for k in
                   ["id", "question", "description", "source", "status", "evidence", "paper_anchor"]) + " |")
    if not state.get("requirements"):
        out.append("| — | — | 等待读题后逐项登记，不能判定答题完整 | — | TODO | — | — |")
    if state.get("scope") == "analysis":
        out += ["", "## 当前分析范围覆盖", "",
                "分析完成不代表预测、求解或论文已完成。", "",
                "| 要求 | 分析状态 | 分析证据 |", "| --- | --- | --- |"]
        for r in state.get("requirements", []):
            a = r.get("analysis", {})
            out.append("| " + " | ".join(cell(x) for x in
                       [r["id"], a.get("status", "TODO"), a.get("evidence", [])]) + " |")
    out += ["", "## 阶段检查", "", "| 检查 | 状态 | 说明 | 证据 |", "| --- | --- | --- | --- |"]
    for c in state.get("checks", []):
        out.append("| " + " | ".join(cell(x) for x in
                   [c["id"], c.get("status"), c.get("note", ""), list(c.get("evidence", {}))]) + " |")
    return "\n".join(out) + "\n"
