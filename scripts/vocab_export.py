#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vocab_export.py - 考研英语核心词汇导出工具
强制执行 ≤30 个上限（超出截断并警告）、清单内部去重、输出供 memo-api 消费的标准格式。
"""

import sys
import os
import json
import argparse

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

MAX_VOCAB_LIMIT = 30

def export_vocab(vocab_list, output_format="markdown"):
    # 清单去重（保留首个出现项，忽略大小写和首尾空格）
    seen = set()
    deduped = []
    for item in vocab_list:
        term = item.get("word", item.get("term", item.get("单词", item.get("词组", "")))).strip()
        if not term:
            continue
        key = term.lower()
        if key not in seen:
            seen.add(key)
            deduped.append({
                "word": term,
                "meaning": item.get("meaning", item.get("definition", item.get("释义", item.get("文中释义", "")))).strip(),
                "tone": item.get("tone", item.get("attitude", item.get("态度", item.get("态度色彩", "")))).strip(),
                "source": item.get("source", item.get("origin", item.get("出处", ""))).strip(),
            })

    total_count = len(deduped)
    if total_count > MAX_VOCAB_LIMIT:
        print(f"[WARNING] 词汇数量 ({total_count}) 超过最大限制 ({MAX_VOCAB_LIMIT})，已自动截断保留前 {MAX_VOCAB_LIMIT} 个词条。", file=sys.stderr)
        deduped = deduped[:MAX_VOCAB_LIMIT]

    if output_format == "json":
        return json.dumps(deduped, ensure_ascii=False, indent=2)

    # 默认标准 Markdown 表格格式
    lines = []
    lines.append(f"### 本篇核心单词与词组清单（共 {len(deduped)} 词，已去重且 ≤30）\n")
    lines.append("| # | 单词 / 词组 | 文中释义 | 态度色彩 | 出处 |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")
    for idx, item in enumerate(deduped, 1):
        word = item['word'].replace('|', '\\|').replace('\n', ' ')
        meaning = item['meaning'].replace('|', '\\|').replace('\n', ' ') if item['meaning'] else "-"
        tone = item['tone'].replace('|', '\\|').replace('\n', ' ') if item['tone'] else "-"
        source = item['source'].replace('|', '\\|').replace('\n', ' ') if item['source'] else "-"
        lines.append(f"| {idx} | {word} | {meaning} | {tone} | {source} |")

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="考研英语核心词汇去重、限额截断与格式化导出工具")
    parser.add_argument("--json", dest="json_input", help="词汇清单 JSON 字符串或文件路径")
    parser.add_argument("--format", dest="output_format", choices=["markdown", "json"], default="markdown", help="输出格式 (markdown 或 json)")
    args = parser.parse_args()

    if args.json_input:
        if os.path.isfile(args.json_input):
            with open(args.json_input, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        else:
            raw_data = json.loads(args.json_input)
    else:
        # Check stdin
        if not sys.stdin.isatty():
            content = sys.stdin.read().strip()
            if content:
                raw_data = json.loads(content)
            else:
                parser.error("未检测到输入内容，请通过 --json 或标准输入传入词汇数据")
        else:
            parser.error("必须通过 --json 或标准输入传入词汇清单 JSON")

    if not isinstance(raw_data, list):
        if isinstance(raw_data, dict) and "words" in raw_data:
            raw_data = raw_data["words"]
        elif isinstance(raw_data, dict) and "vocab" in raw_data:
            raw_data = raw_data["vocab"]
        else:
            print("[ERROR] JSON 输入必须为词汇对象列表", file=sys.stderr)
            sys.exit(1)

    result = export_vocab(raw_data, args.output_format)
    print(result)

if __name__ == "__main__":
    main()
