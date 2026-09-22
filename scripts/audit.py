#!/usr/bin/env python3
"""Audit recorded evidence and Markdown; scientific reviews remain explicit."""
import argparse
import json
import re
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from pathlib import Path
from urllib.parse import unquote, urlsplit
from common import STAGES, SCOPES, TASK_STATES, CHECK_STATES, now, location, digest
from common import read_state, render_todo, write_json

BLOCK = re.compile(r"<!--\s*mm:([A-Za-z0-9_.-]+)\s*-->(.*?)<!--\s*/mm:\1\s*-->", re.S)


def json_pointer(obj, pointer):
    if pointer == "":
        return obj
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("JSON pointer必须为空或以/开头")
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(obj, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", token):
                raise ValueError("无效数组索引")
            obj = obj[int(token)]
        elif isinstance(obj, dict):
            obj = obj[token]
        else:
            raise ValueError("JSON pointer越过标量")
    return obj


def display_metric(metric, decimals):
    if not isinstance(metric, dict) or "value" not in metric or "unit" not in metric:
        raise ValueError("指标源必须含value、unit和context")
    value = metric["value"]
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError("value必须是真实数字，布尔值和数字字符串无效")
    if isinstance(decimals, bool) or not isinstance(decimals, int) or not 0 <= decimals <= 12:
        raise ValueError("decimals必须为0到12的整数")
    number = Decimal(str(value))
    if not number.is_finite() or abs(number.adjusted()) > 1000:
        raise ValueError("指标必须为有限且合理可表示的数值")
    unit = metric["unit"]
    if not isinstance(unit, str) or not unit.strip() or "\n" in unit or "<" in unit:
        raise ValueError("unit必须为单行非空文本；无量纲用1")
    with localcontext() as ctx:
        ctx.prec = max(50, len(number.as_tuple().digits) + abs(number.adjusted()) + decimals + 10)
        rounded = number.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
        if rounded == 0:
            rounded = abs(rounded)
        shown = format(rounded, "." + str(decimals) + "f")
    return shown if unit == "1" else shown + " " + unit


def without_fences(text):
    fence = None
    kept = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(chr(96) * 3) or stripped.startswith("~~~"):
            mark = stripped[0]
            length = len(stripped) - len(stripped.lstrip(mark))
            if fence is None:
                fence = (mark, length)
            elif mark == fence[0] and length >= fence[1]:
                fence = None
            continue
        if fence is None:
            kept.append(line)
    return "\n".join(kept), fence is not None


def same_context_value(actual, expected):
    """Compare JSON values without binary-float artifacts or bool/number aliasing."""
    if isinstance(actual, bool) or isinstance(expected, bool):
        return type(actual) is type(expected) and actual == expected
    numbers = (int, float, Decimal)
    if isinstance(actual, numbers) and isinstance(expected, numbers):
        left, right = Decimal(str(actual)), Decimal(str(expected))
        return left.is_finite() and right.is_finite() and left == right
    if isinstance(actual, dict) and isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(
            same_context_value(actual[k], expected[k]) for k in actual)
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(
            same_context_value(a, b) for a, b in zip(actual, expected))
    return type(actual) is type(expected) and actual == expected


class Audit:
    def __init__(self, root, complete=False):
        self.root = Path(root).resolve()
        self.complete = complete
        self.issues = []
        self.tracked = set()
        self.hashed = set()
        self.expected_claims = {}
        self.state = read_state(self.root)

    def issue(self, level, message):
        self.issues.append({"level": level, "message": message})

    def pending(self, message):
        self.issue("INCOMPLETE", message)

    def file(self, relative, label):
        try:
            path = location(self.root, relative)
            if not path.is_file():
                raise ValueError("文件不存在")
            self.tracked.add(path.relative_to(self.root).as_posix())
            return path
        except (ValueError, OSError) as exc:
            self.issue("FAIL", label + ": " + str(relative) + " (" + str(exc) + ")")
            return None

    def fingerprints(self, values, label, required=False):
        if not isinstance(values, dict):
            self.issue("FAIL", label + "必须为路径到SHA256的映射")
            return
        if required and not values:
            self.issue("FAIL", label + "缺少证据快照")
        for relative, expected in values.items():
            path = self.file(relative, label)
            if path:
                self.hashed.add(relative)
                if not isinstance(expected, str) or digest(path) != expected:
                    self.issue("FAIL", label + "证据已改变: " + relative)

    def objects(self, key):
        value = self.state.get(key)
        if not isinstance(value, list):
            self.issue("FAIL", key + "必须为数组")
            return []
        out, seen = [], set()
        for item in value:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
                self.issue("FAIL", key + "含缺少有效ID的记录")
                continue
            if item["id"] in seen:
                self.issue("FAIL", key + "存在重复ID: " + item["id"])
            seen.add(item["id"])
            out.append(item)
        return out

    def evidence_files(self, value, label, required=False):
        if not isinstance(value, list):
            self.issue("FAIL", label + "必须为路径数组")
            return
        if required and not value:
            self.issue("FAIL", label + "已完成但没有证据")
        for p in value:
            self.file(p, label)

    def run(self):
        state = self.state
        for f in ["plan.md", "todo.md", "state.json"]:
            self.file(f, "核心记录")
        scope = state.get("scope")
        if scope not in SCOPES:
            self.issue("FAIL", "未知任务范围")
            active = []
        else:
            active = SCOPES[scope]
        if state.get("mode") not in {"practice", "competition", "unknown"}:
            self.issue("FAIL", "模式必须为practice、competition或unknown")
        tasks = self.objects("tasks")
        requirements = self.objects("requirements")
        checks = self.objects("checks")
        experiments = self.objects("experiments")
        claims = self.objects("claims")
        task_map = {t["id"]: t for t in tasks}
        req_map = {r["id"]: r for r in requirements}
        exp_map = {e["id"]: e for e in experiments}
        checks_map = {c["id"]: c for c in checks}
        active_stages = {"S" + str(n) for n in active}
        if state.get("current_stage") not in {s[0] for s in STAGES}:
            self.issue("FAIL", "当前阶段无效")
        if state.get("requirements_complete") is not True:
            self.pending("尚未确认题目要求已经全部提取")
        if not requirements:
            self.pending("没有登记具体题目要求")
        if not state.get("requirements_source"):
            self.pending("没有登记完整题面来源")
        for n in active:
            cid = "G" + str(n)
            if cid not in checks_map or checks_map[cid].get("required") is not True:
                self.issue("FAIL", "当前范围的必要检查缺失或被取消: " + cid)
            if not any(t.get("stage") == "S" + str(n) and t.get("required") is True for t in tasks):
                self.issue("FAIL", "当前阶段没有必要任务: S" + str(n))
        for task in tasks:
            ident = task["id"]
            status = task.get("status")
            if status not in TASK_STATES:
                self.issue("FAIL", ident + "任务状态无效")
            for field in ["title", "stage", "acceptance", "owner", "priority"]:
                if not isinstance(task.get(field), str) or not task[field].strip():
                    self.issue("FAIL", ident + "缺少任务字段: " + field)
            if task.get("stage") not in {x[0] for x in STAGES}:
                self.issue("FAIL", ident + "阶段无效")
            if task.get("priority") not in {"P0", "P1", "P2"}:
                self.issue("FAIL", ident + "优先级无效")
            if not isinstance(task.get("required"), bool):
                self.issue("FAIL", ident + "required必须为布尔值")
            if status == "SKIPPED" and (task.get("required", True) or not task.get("note")):
                self.issue("FAIL", ident + "必要任务不可跳过，可选跳过必须说明原因")
            if status == "BLOCKED" and not task.get("blocker"):
                self.issue("FAIL", ident + "缺少阻塞原因")
            dependencies = task.get("dependencies", [])
            if not isinstance(dependencies, list):
                self.issue("FAIL", ident + "dependencies必须为数组")
                dependencies = []
            for dep in dependencies:
                other = task_map.get(dep)
                if not other:
                    self.issue("FAIL", ident + "依赖不存在: " + str(dep))
                elif status == "DONE" and not (other.get("status") == "DONE" or
                        (other.get("status") == "SKIPPED" and other.get("required") is False)):
                    self.issue("FAIL", ident + "已完成但上游尚未有效完成: " + str(dep))
            linked = task.get("requirement_ids", [])
            if not isinstance(linked, list):
                self.issue("FAIL", ident + "requirement_ids必须为数组")
                linked = []
            for req in linked:
                if req not in req_map:
                    self.issue("FAIL", ident + "关联要求不存在: " + str(req))
            if task.get("required", True) and status != "DONE":
                self.pending("必要任务未完成: " + ident + " " + str(status))
            if status == "DONE":
                self.evidence_files(task.get("evidence", []), ident, required=True)
                self.evidence_files(task.get("outputs", []), ident + "产出")
        visiting, visited = set(), set()
        def visit(tid):
            if tid in visiting:
                self.issue("FAIL", "任务依赖存在循环: " + tid)
                return
            if tid in visited:
                return
            visiting.add(tid)
            deps = task_map[tid].get("dependencies", [])
            for dep in deps if isinstance(deps, list) else []:
                if dep in task_map:
                    visit(dep)
            visiting.remove(tid)
            visited.add(tid)
        for tid in task_map:
            visit(tid)
        for req in requirements:
            rid = req["id"]
            for field in ["question", "description", "source"]:
                if not isinstance(req.get(field), str) or not req[field].strip():
                    self.issue("FAIL", rid + "缺少字段: " + field)
            if req.get("status") not in TASK_STATES:
                self.issue("FAIL", rid + "要求状态无效")
            if scope == "analysis":
                analysis = req.get("analysis", {})
                if not isinstance(analysis, dict) or analysis.get("status") != "DONE":
                    self.pending("要求的分析工作未完成: " + rid)
                else:
                    self.evidence_files(analysis.get("evidence", []), rid + "分析", required=True)
                    linked = [t for t in tasks if rid in t.get("requirement_ids", [])]
                    if not any(t.get("status") == "DONE" and t.get("stage") in active_stages for t in linked):
                        self.issue("FAIL", rid + "分析已完成但没有当前范围的完成任务")
            elif req.get("status") != "DONE":
                self.pending("要求未完成: " + rid)
            if req.get("status") == "DONE":
                self.evidence_files(req.get("evidence", []), rid, required=True)
                linked = [t for t in tasks if rid in t.get("requirement_ids", [])]
                if not linked or not any(t.get("status") == "DONE" for t in linked):
                    self.issue("FAIL", rid + "已完成但没有对应完成任务")
        for check in checks:
            cid = check["id"]
            status = check.get("status")
            if status not in CHECK_STATES:
                self.issue("FAIL", cid + "检查状态无效")
            if status == "FAIL":
                self.issue("FAIL", cid + "审查记录为FAIL")
            if check.get("required", True) and status != "PASS":
                self.pending("必要检查未通过: " + cid + " " + str(status))
            if status == "NA" and (check.get("required", True) or not check.get("note")):
                self.issue("FAIL", cid + "NA缺少有效不适用理由或仍为必要检查")
            if status == "PASS":
                if not check.get("note"):
                    self.issue("FAIL", cid + "缺少实际检查说明")
                self.fingerprints(check.get("evidence", {}), cid + "审查证据", required=True)
                self.fingerprints(check.get("inputs", {}), cid + "所查输入", required=True)
        for experiment in experiments:
            eid = experiment["id"]
            if experiment.get("retired") is True:
                if not experiment.get("retirement_reason"):
                    self.issue("FAIL", eid + "历史实验退役未说明原因")
                continue
            if experiment.get("status") not in {"SUCCEEDED", "FAILED"}:
                self.issue("FAIL", eid + "运行状态无效")
            if experiment.get("kind") not in {"execution", "derivation"} or not experiment.get("command"):
                self.issue("FAIL", eid + "缺少真实运行/推导记录")
            self.fingerprints(experiment.get("inputs", {}), eid + "输入", required=True)
            self.fingerprints(experiment.get("outputs", {}), eid + "输出",
                              required=experiment.get("status") == "SUCCEEDED")
            self.fingerprints(experiment.get("logs", {}), eid + "日志", required=True)
        paper_name = state.get("paper", "paper/paper.md")
        paper_path = location(self.root, paper_name)
        paper_text = ""
        needs_paper = scope in {"full", "writing"}
        if paper_path.is_file():
            self.tracked.add(paper_name)
            paper_text = paper_path.read_text(encoding="utf-8")
            text, open_fence = without_fences(paper_text)
            if open_fence:
                self.issue("FAIL", "Markdown存在未闭合代码围栏")
            if len(re.findall(r"(?<!\\)\$\$", text)) % 2:
                self.issue("FAIL", "Markdown存在未成对的独立数学公式分隔符")
            if self.complete and re.search(r"\b(?:TODO|TBD|PLACEHOLDER)\b|待补充|待填写|待续写|\[论文标题\]", text):
                self.issue("FAIL", "最终论文仍存在占位内容")
            for req in requirements:
                if needs_paper and req.get("status") == "DONE":
                    anchor = req.get("paper_anchor")
                    if not isinstance(anchor, str) or not anchor or not re.search(
                            r'<a\s+id=["\x27]' + re.escape(anchor) + r'["\x27]\s*>', text):
                        self.issue("FAIL", req["id"] + "缺少论文答题位置锚点")
            self.check_images(paper_path, text)
        elif needs_paper:
            self.pending("尚未生成Markdown论文: " + paper_name)
        self.check_claims(claims, req_map, exp_map, paper_name, paper_text)
        if needs_paper and not claims:
            self.issue("WARN", "没有登记数值绑定；确认是否为无数值结论的理论题，人工检查未绑定数字")
        try:
            if (self.root / "todo.md").read_text(encoding="utf-8") != render_todo(state):
                self.issue("FAIL", "todo.md与state.json不一致；运行project.py sync")
        except (OSError, TypeError, KeyError) as exc:
            self.issue("FAIL", "无法核对todo: " + str(exc))
        for f in state.get("delivery_files", []):
            self.file(f, "交付清单")
        frozen = self.root / "delivery_manifest.json"
        if frozen.exists():
            manifest = json.loads(frozen.read_text(encoding="utf-8"))
            self.fingerprints(manifest.get("files", {}), "冻结交付", required=True)
        hard = any(i["level"] == "FAIL" for i in self.issues)
        pending = any(i["level"] == "INCOMPLETE" for i in self.issues)
        return {
            "checked_at": now(),
            "structural_status": "FAIL" if hard else "PASS",
            "scope_completion": "FAIL" if hard else "INCOMPLETE" if pending else "READY",
            "answer_completion": "RECORDED_COMPLETE" if requirements and all(
                r.get("status") == "DONE" for r in requirements) else "INCOMPLETE",
            "markdown_delivery_ready": bool(not hard and not pending and needs_paper and paper_text),
            "scientific_status": "REQUIRES_DOCUMENTED_REVIEW",
            "scientific_note": "检查脚本不证明数学正确性；PASS检查为已有审查声明及其证据一致性。",
            "official_submission_status": "NOT_ASSESSED",
            "counts": {"tasks": len(tasks), "requirements": len(requirements), "claims": len(claims)},
            "expected_claim_displays": self.expected_claims,
            "issues": self.issues,
        }

    def check_claims(self, claims, req_map, exp_map, paper_name, paper_text):
        visible, _ = without_fences(paper_text)
        blocks = {}
        for cid, body in BLOCK.findall(visible):
            blocks.setdefault(cid, []).append(body)
        known = {c["id"] for c in claims}
        for cid in blocks:
            if cid not in known:
                self.issue("FAIL", "论文数字块没有登记: " + cid)
        open_ids = re.findall(r"<!--\s*mm:([A-Za-z0-9_.-]+)\s*-->", visible)
        close_ids = re.findall(r"<!--\s*/mm:([A-Za-z0-9_.-]+)\s*-->", visible)
        if sorted(open_ids) != sorted(close_ids) or len(open_ids) != sum(map(len, blocks.values())):
            self.issue("FAIL", "论文数值绑定注释未正确配对")
        for claim in claims:
            cid = claim["id"]
            try:
                if not re.fullmatch(r"[A-Za-z0-9_.-]+", cid):
                    raise ValueError("引用ID只能含字母、数字、点、下划线和短横线")
                rid = claim.get("requirement_id")
                if rid not in req_map:
                    raise ValueError("引用的具体要求不存在")
                experiment = exp_map.get(claim.get("experiment_id"))
                if not experiment or experiment.get("retired") or experiment.get("status") != "SUCCEEDED":
                    raise ValueError("源实验不存在、已退役或未成功")
                source = claim.get("result_file")
                if source not in experiment.get("outputs", {}):
                    raise ValueError("结果文件没有登记为该实验输出")
                path = self.file(source, cid + "数值来源")
                if path is None:
                    continue
                data = json.loads(path.read_text(encoding="utf-8"),
                                  parse_float=Decimal, parse_int=Decimal)
                metric = json_pointer(data, claim.get("pointer"))
                expected = display_metric(metric, claim.get("decimals"))
                actual_context = metric.get("context")
                expected_context = claim.get("context")
                if not isinstance(actual_context, dict) or actual_context.get("requirement_id") != rid:
                    raise ValueError("指标所属要求与论文引用不一致")
                if not isinstance(expected_context, dict) or not expected_context:
                    raise ValueError("引用必须声明场景/数据划分/方法等相关context")
                for key, value in expected_context.items():
                    if key not in actual_context or not same_context_value(actual_context[key], value):
                        raise ValueError("指标上下文不一致: " + str(key))
                if claim.get("paper", paper_name) != paper_name:
                    raise ValueError("引用必须指向当前交付论文")
                bodies = blocks.get(cid, [])
                self.expected_claims[cid] = expected
                if len(bodies) != 1:
                    raise ValueError("每个引用ID必须在论文中恰好出现一次")
                if bodies[0] != expected:
                    raise ValueError("数字或单位不一致；应为 " + expected + "，实际为 " + bodies[0])
            except (ValueError, TypeError, KeyError, IndexError, InvalidOperation, OSError) as exc:
                self.issue("FAIL", "数值引用 " + cid + ": " + str(exc))

    def check_images(self, paper_path, text):
        refs = dict((k.strip().lower(), v) for k, v in re.findall(
            r'^\s*\[([^]\n]+)\]:\s*<?([^\s>]+)>?', text, re.M))
        targets = re.findall(r'!\[[^]\n]*\]\(\s*(<[^>]+>|[^\s)]+)', text)
        targets += re.findall(r'<img\b[^>]*\bsrc=["\x27]([^"\x27]+)', text, re.I)
        for alt, key in re.findall(r'!\[([^]\n]*)\]\[([^]\n]*)\]', text):
            label = (key or alt).strip().lower()
            if label not in refs:
                self.issue("FAIL", "图片引用标签没有定义: " + label)
            else:
                targets.append(refs[label])
        for target in targets:
            target = target.strip("<>")
            if urlsplit(target).scheme in {"http", "https", "data"}:
                self.issue("WARN", "外部图片无法通过本地快照保证可用: " + target)
                continue
            rel = unquote(urlsplit(target).path)
            if not rel or Path(rel).is_absolute() or urlsplit(target).scheme:
                self.issue("FAIL", "图片必须使用项目内相对路径: " + target)
                continue
            path = (paper_path.parent / rel).resolve()
            if not path.is_relative_to(self.root):
                self.issue("FAIL", "图片路径超出项目: " + target)
                continue
            self.file(path.relative_to(self.root).as_posix(), "论文图片")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--output", help="项目内审计报告路径，不能覆盖已有证据")
    parser.add_argument("--freeze", action="store_true", help="仅在完整条件满足后生成交付快照")
    args = parser.parse_args()
    try:
        audit = Audit(args.root, args.require_complete or args.freeze)
        report = audit.run()
        if args.output:
            out = location(audit.root, args.output)
            rel = out.relative_to(audit.root).as_posix()
            if rel in audit.hashed or rel in {"state.json", "plan.md", "todo.md", audit.state.get("paper")}:
                raise ValueError("审计输出不得覆盖已登记证据或核心文件")
            if (audit.root / "delivery_manifest.json").exists():
                raise ValueError("已冻结项目不写新报告；省略--output进行只读核验")
            write_json(out, report)
            audit.tracked.add(rel)
        if args.freeze:
            if report["scope_completion"] != "READY":
                raise ValueError("任务范围尚未完整通过，不能冻结；先运行审计查看具体问题")
            manifest = audit.root / "delivery_manifest.json"
            if manifest.exists():
                raise ValueError("已有冻结版本；不能覆盖")
            write_json(manifest, {
                "schema_version": 1, "frozen_at": now(),
                "scope": audit.state["scope"], "paper": audit.state.get("paper"),
                "official_submission_status": "NOT_ASSESSED",
                "files": {p: digest(location(audit.root, p)) for p in sorted(audit.tracked)},
            })
            report["frozen"] = True
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
        if report["structural_status"] != "PASS":
            return 1
        return 2 if (args.require_complete or args.freeze) and report["scope_completion"] != "READY" else 0
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"structural_status": "FAIL", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
