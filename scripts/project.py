#!/usr/bin/env python3
"""Create project records, render todo, and record evidence after real work."""
import argparse
import json
import sys
from pathlib import Path
from common import STAGES, SCOPES, CHECK_STATES, now, read_state, write_text, write_json
from common import ensure_unfrozen, render_todo, snapshot


def init(args):
    root = Path(args.root).resolve()
    for name in ("state.json", "plan.md", "todo.md", "delivery_manifest.json"):
        if (root / name).exists():
            raise ValueError("已存在 " + name + "；请续接项目，不重新初始化")
    active = SCOPES[args.scope]
    tasks, checks = [], []
    previous = None
    for index in active:
        sid, name, output, acceptance = STAGES[index]
        tid = sid + ".T01"
        tasks.append({
            "id": tid, "stage": sid, "title": "细化并完成" + name,
            "requirement_ids": [], "dependencies": [previous] if previous else [],
            "priority": "P0" if index < 3 else "P1", "estimate_minutes": None,
            "owner": "执行者", "outputs": [output], "acceptance": acceptance,
            "status": "TODO", "evidence": [], "required": True, "blocker": "",
            "note": "读题后替换为可验收的具体任务，保留真实依赖",
        })
        checks.append({"id": "G" + str(index), "stage": sid, "status": "NOT_RUN",
                       "required": True, "note": "", "evidence": {}, "inputs": {}})
        previous = tid
    state = {
        "schema_version": 1, "title": args.title, "mode": args.mode, "scope": args.scope,
        "created_at": now(), "updated_at": now(), "current_stage": "S0",
        "competition": {"name": "华为杯中国研究生数学建模竞赛", "year": None,
                        "deadline": None, "timezone": None, "rules_sources": []},
        "requirements_complete": False, "requirements_source": "",
        "tasks": tasks, "requirements": [], "checks": checks,
        "experiments": [], "claims": [], "paper": "paper/paper.md",
        "delivery_files": [], "official_submission_status": "NOT_ASSESSED",
    }
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "state.json", state)
    write_text(root / "todo.md", render_todo(state))
    lines = [
        "# " + args.title + "：阶段计划", "",
        "## 目标与交付", "",
        "- 当前范围：" + args.scope,
        "- 模式：" + args.mode + "；年份、题号、截止时间与剩余预算待核实。",
        "- 论文交付：Markdown；不使用论文模板或排版引擎。",
        "- 已定用户偏好与限制：待根据会话和输入填写。",
        "", "## 当前进度与材料", "",
        "记录题面、附件、原文定位、已有成果和最新版本；关键未知项明确标注。",
        "", "## 总体建模路线", "",
        "读题后说明每问目标、数据依赖、基线、主方案、备选和选择理由。",
        "", "## 阶段计划", "",
        "| 阶段 | 输入 | 行动与产物 | 通过条件 | 预算 / 状态 | 失败回退 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for i in active:
        sid, name, output, acceptance = STAGES[i]
        lines.append("| " + sid + " " + name + " | 读题后具体化 | " + output +
                     " | G" + str(i) + "：" + acceptance + " | 待估 / TODO | 按题意、数据、模型或实现原因定位 |")
    lines += [
        "", "## 里程碑与资源预算", "",
        "填写首次有效结果、全问基础覆盖、结果定稿、论文定稿和交付缓冲。按实际剩余时间安排；注明获准资源、单次运行预算和停止条件。",
        "", "## 实验与选择协议", "",
        "填写主指标、基线、数据划分、参数选择、对照条件、随机性处理、必要检验和结果选择方法。",
        "", "## 决策与变更记录", "",
        "| 时间 | 决策 / 变更 | 依据 | 影响任务与文件 | 需要重验的内容 |",
        "| --- | --- | --- | --- | --- |",
        "", "## 阻塞、备选与恢复", "",
        "| 缺口 / 风险 | 阻塞要求 | 可继续任务 | 解除或转向条件 |",
        "| --- | --- | --- | --- |",
        "", "## 当前下一步", "",
        "读取题面和附件，细化requirements与任务，核实范围和预算。",
    ]
    write_text(root / "plan.md", "\n".join(lines) + "\n")
    print("已建立 plan.md、todo.md、state.json；所有完成状态均未预先判定。")


def save(root, state):
    state["updated_at"] = now()
    write_json(Path(root) / "state.json", state)
    write_text(Path(root) / "todo.md", render_todo(state))


def run_record(args):
    ensure_unfrozen(args.root)
    state = read_state(args.root)
    if any(x.get("id") == args.id for x in state["experiments"]):
        raise ValueError("实验ID已存在；使用新ID保留历史")
    inputs = snapshot(args.root, args.input)
    outputs = snapshot(args.root, args.output)
    logs = snapshot(args.root, [args.log])
    if not inputs or (args.status == "SUCCEEDED" and not outputs):
        raise ValueError("必须有输入；成功运行必须有实际输出")
    record = {
        "id": args.id, "kind": args.kind, "status": args.status, "command": args.command,
        "recorded_at": now(), "inputs": inputs, "outputs": outputs, "logs": logs,
        "retired": False, "retirement_reason": "",
    }
    state["experiments"].append(record)
    save(args.root, state)
    print("已登记证据快照 " + args.id + "；此命令本身没有执行或验证模型。")


def check_record(args):
    ensure_unfrozen(args.root)
    state = read_state(args.root)
    match = next((x for x in state["checks"] if x.get("id") == args.id), None)
    if match is None:
        raise ValueError("检查ID不存在；按当前范围在state中明确定义检查")
    if not args.note.strip():
        raise ValueError("需要具体检查结论或受阻/不适用原因")
    evidence = snapshot(args.root, args.evidence)
    inputs = snapshot(args.root, args.input)
    if args.status == "PASS" and (not evidence or not inputs):
        raise ValueError("PASS必须提供实际审查证据与所审查输入")
    if args.status == "NA" and match.get("required", True):
        raise ValueError("必要检查不可直接记NA；先根据任务范围明确调整必要性")
    if match.get("status") != "NOT_RUN":
        state.setdefault("check_history", []).append(dict(match))
    match.update(status=args.status, note=args.note, evidence=evidence, inputs=inputs,
                 reviewed_at=now())
    save(args.root, state)
    print("已记录 " + args.id + " " + args.status + "；审查声明必须与实际工作一致。")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("init")
    p.add_argument("--root", required=True)
    p.add_argument("--title", default="数学建模项目")
    p.add_argument("--mode", choices=["practice", "competition", "unknown"], default="unknown")
    p.add_argument("--scope", choices=list(SCOPES), default="full")
    p = sub.add_parser("sync")
    p.add_argument("--root", required=True)
    p = sub.add_parser("record-run")
    p.add_argument("--root", required=True)
    p.add_argument("--id", required=True)
    p.add_argument("--status", choices=["SUCCEEDED", "FAILED"], required=True)
    p.add_argument("--kind", choices=["execution", "derivation"], default="execution")
    p.add_argument("--command", required=True)
    p.add_argument("--input", action="append", default=[])
    p.add_argument("--output", action="append", default=[])
    p.add_argument("--log", required=True)
    p = sub.add_parser("record-check")
    p.add_argument("--root", required=True)
    p.add_argument("--id", required=True)
    p.add_argument("--status", choices=sorted(CHECK_STATES), required=True)
    p.add_argument("--note", required=True)
    p.add_argument("--evidence", action="append", default=[])
    p.add_argument("--input", action="append", default=[])
    args = parser.parse_args()
    try:
        if args.action == "init":
            init(args)
        elif args.action == "sync":
            ensure_unfrozen(args.root)
            state = read_state(args.root)
            write_text(Path(args.root) / "todo.md", render_todo(state))
            print("todo.md已与state.json一致；plan.md保持原有内容。")
        elif args.action == "record-run":
            run_record(args)
        else:
            check_record(args)
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
