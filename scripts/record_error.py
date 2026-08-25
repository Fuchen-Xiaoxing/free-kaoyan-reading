#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
record_error.py - 考研英语阅读错题记录脚本
将错题以 YAML frontmatter + 正文格式只追加写入错题本.md
支持单条与批量 (JSON 数组) 追加、ID 自动去重递增与 12 类错误枚举/能力短板校验。
"""

import sys
import os
import re
import json
import argparse

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# 12 类错误类型封闭枚举
ERROR_TYPES = [
    "定位错误",
    "无对应内容",
    "过度推理",
    "偷换概念/嫁接",
    "因果倒置",
    "态度背离",
    "细节背离主旨",
    "绝对化误选",
    "审题不清",
    "比较/时态偷换",
    "词义误解",
    "长难句误读"
]

# 能力短板封闭集合
ABILITY_SHORTBOARDS = ["词汇", "语法", "主旨"]

DEFAULT_FILE = "错题本.md"

def get_existing_ids(file_path):
    if not os.path.exists(file_path):
        return set()
    ids = set()
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^id:\s*(.+)$", line.strip())
            if m:
                ids.add(m.group(1).strip())
    return ids

def generate_unique_id(base_id, existing_ids):
    if base_id not in existing_ids:
        return base_id
    index = 2
    while f"{base_id}-{index}" in existing_ids:
        index += 1
    return f"{base_id}-{index}"

def format_error_entry(data, existing_ids):
    # 校验错误类型
    error_type = data.get("error_type", data.get("错误类型", "")).strip()
    if error_type not in ERROR_TYPES:
        print(f"[ERROR] 非法错误类型: '{error_type}'。必须严格属于 12 类封闭枚举之一：\n{', '.join(ERROR_TYPES)}", file=sys.stderr)
        sys.exit(1)

    # 校验能力短板
    shortboard = data.get("ability_shortboard", data.get("能力短板", "")).strip()
    if shortboard not in ABILITY_SHORTBOARDS:
        print(f"[ERROR] 非法能力短板: '{shortboard}'。必须属于 {ABILITY_SHORTBOARDS} 之一", file=sys.stderr)
        sys.exit(1)

    base_id = data.get("id", data.get("ID", "UNKNOWN-Q0")).strip()
    entry_id = generate_unique_id(base_id, existing_ids)
    existing_ids.add(entry_id)

    q_type = data.get("question_type", data.get("题型", "细节题")).strip()
    keyword = data.get("keyword", data.get("解题关键词", "")).strip()
    location = data.get("location", data.get("原文定位", "")).strip()
    restore = data.get("restore", data.get("错误还原", "")).strip()
    attribution = data.get("attribution", data.get("方法论归因", "")).strip()
    lesson = data.get("lesson", data.get("教训金句", "")).strip()
    analysis = data.get("analysis", data.get("正文", "")).strip()
    if not analysis:
        analysis = f"错误还原：{restore}\n方法论归因：{attribution}\n教训金句：{lesson}"

    entry_content = f"""
---
id: {entry_id}
题型: {q_type}
error_type: {error_type}
能力短板: {shortboard}
解题关键词: {keyword}
原文定位: {location}
错误还原: {restore}
方法论归因: {attribution}
教训金句: {lesson}
---

### {entry_id}

{analysis}
"""
    return entry_id, entry_content

def append_errors(file_path, items):
    if not items:
        print("[WARNING] 没有待追加的错题条目。", file=sys.stderr)
        return []

    existing_ids = get_existing_ids(file_path)
    added_ids = []
    contents = []

    for item in items:
        if not isinstance(item, dict):
            continue
        entry_id, content = format_error_entry(item, existing_ids)
        added_ids.append(entry_id)
        contents.append(content)

    if not added_ids:
        print("[ERROR] 未解析到有效错题数据。", file=sys.stderr)
        sys.exit(1)

    parent_dir = os.path.dirname(os.path.abspath(file_path))
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    if not os.path.exists(file_path):
        header = "# 错题本\n\n本文件存放考研英语阅读错题，由 FREE考研英语阅读理解 (free-kaoyan-reading) skill 维护。\n\n## 错题列表\n"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(header)

    with open(file_path, "a", encoding="utf-8") as f:
        f.write("".join(contents))

    if len(added_ids) == 1:
        print(f"[SUCCESS] 错题已成功追加至错题本，条目 ID: {added_ids[0]}")
    else:
        print(f"[SUCCESS] 成功批量追加 {len(added_ids)} 条错题至错题本: {', '.join(added_ids)}")

    return added_ids

def main():
    parser = argparse.ArgumentParser(description="考研英语阅读错题批量/单条追加记录工具")
    parser.add_argument("--file", default=DEFAULT_FILE, help="错题本文件路径（默认: 错题本.md）")
    parser.add_argument("--json", dest="json_input", help="以 JSON 字符串或 JSON 文件路径传入完整参数（支持单个对象或对象数组）")
    parser.add_argument("--id", help="题目唯一 ID (如 2009-T4-Q21)")
    parser.add_argument("--type", "--question-type", dest="question_type", default="细节题", help="题型")
    parser.add_argument("--error-type", dest="error_type", help="12 类错误类型之一")
    parser.add_argument("--shortboard", "--ability-shortboard", dest="ability_shortboard", help="能力短板 (词汇/语法/主旨)")
    parser.add_argument("--keyword", default="", help="解题关键词")
    parser.add_argument("--location", default="", help="原文定位")
    parser.add_argument("--restore", default="", help="错误还原思路")
    parser.add_argument("--attribution", default="", help="方法论归因")
    parser.add_argument("--lesson", default="", help="教训金句")
    parser.add_argument("--analysis", default="", help="详细复盘正文")

    args = parser.parse_args()

    items = []
    if args.json_input:
        if os.path.isfile(args.json_input):
            with open(args.json_input, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        else:
            raw_data = json.loads(args.json_input)

        if isinstance(raw_data, list):
            items = raw_data
        elif isinstance(raw_data, dict):
            if "errors" in raw_data and isinstance(raw_data["errors"], list):
                items = raw_data["errors"]
            elif "questions" in raw_data and isinstance(raw_data["questions"], list):
                items = raw_data["questions"]
            else:
                items = [raw_data]
    else:
        # Check stdin
        if not sys.stdin.isatty():
            content = sys.stdin.read().strip()
            if content:
                raw_data = json.loads(content)
                if isinstance(raw_data, list):
                    items = raw_data
                elif isinstance(raw_data, dict):
                    if "errors" in raw_data and isinstance(raw_data["errors"], list):
                        items = raw_data["errors"]
                    else:
                        items = [raw_data]
        if not items:
            if not args.error_type or not args.ability_shortboard or not args.id:
                parser.error("必须提供 --id, --error-type, --shortboard 或通过 --json / stdin 提供完整参数")
            items = [{
                "id": args.id,
                "question_type": args.question_type,
                "error_type": args.error_type,
                "ability_shortboard": args.ability_shortboard,
                "keyword": args.keyword,
                "location": args.location,
                "restore": args.restore,
                "attribution": args.attribution,
                "lesson": args.lesson,
                "analysis": args.analysis
            }]

    append_errors(args.file, items)

if __name__ == "__main__":
    main()
