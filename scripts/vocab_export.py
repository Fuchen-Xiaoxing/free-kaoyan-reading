#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vocab_export.py - 考研英语核心词汇导出校验工具

职责是"校验"而非"排版"：清单去重（忽略大小写）、强制执行 ≤30 个上限（超出截断）、
字段归一化。默认 --format check 输出紧凑校验简报（不重复输出整张 Markdown 表格），
Markdown 表格由调用方 AI 按校验后的最终清单直接在正文中渲染，避免同一张表进两遍上下文。
如需完整表格（调试/存档），显式传 --format markdown。

输出格式：
- check（默认）   ：紧凑校验简报。有修正（去重/截断/无效条目）时附最终词序清单，供 AI 按此渲染。
- markdown        ：标准 Markdown 表格（表头：| # | 单词 / 词组 | 文中释义 | 态度色彩 | 出处 |）。
- json            ：归一化后的 JSON 数组（供 memo_import.py 消费）。
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


def normalize_vocab(vocab_list):
    """
    去重（保留首个出现项，忽略大小写和首尾空格）、字段归一化、剔除无效条目。
    返回 (deduped, duplicates, invalid)：
      deduped    : 归一化后的词条列表（未截断）
      duplicates : 被去重移除的重复词（按出现顺序）
      invalid    : 被剔除的无效条目（缺少 word 字段）
    """
    seen = set()
    deduped = []
    duplicates = []
    invalid = []
    for item in vocab_list:
        if not isinstance(item, dict):
            invalid.append(item)
            continue
        raw_word = item.get("word", item.get("term", item.get("单词", item.get("词组", ""))))
        term = raw_word.strip() if isinstance(raw_word, str) else ""
        if not term:
            invalid.append(item)
            continue
        key = term.lower()
        if key in seen:
            duplicates.append(term)
            continue
        seen.add(key)
        deduped.append({
            "word": term,
            "meaning": (item.get("meaning", item.get("definition", item.get("释义", item.get("文中释义", "")))) or "").strip(),
            "tone": (item.get("tone", item.get("attitude", item.get("态度", item.get("态度色彩", "")))) or "").strip(),
            "source": (item.get("source", item.get("origin", item.get("出处", ""))) or "").strip(),
        })
    return deduped, duplicates, invalid


def export_vocab(vocab_list, output_format="check"):
    """
    按指定格式输出校验/导出结果。
    """
    deduped, duplicates, invalid = normalize_vocab(vocab_list)

    total_count = len(deduped)
    truncated = []
    if total_count > MAX_VOCAB_LIMIT:
        print(f"[WARNING] 词汇数量 ({total_count}) 超过最大限制 ({MAX_VOCAB_LIMIT})，已自动截断保留前 {MAX_VOCAB_LIMIT} 个词条。", file=sys.stderr)
        truncated = deduped[MAX_VOCAB_LIMIT:]
        deduped = deduped[:MAX_VOCAB_LIMIT]

    if output_format == "json":
        return json.dumps(deduped, ensure_ascii=False, indent=2)

    if output_format == "markdown":
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

    # 默认：check 紧凑校验简报
    lines = []
    if total_count == 0:
        lines.append("❌ 校验失败：清单为空（全部条目无效或无词条）。")
        return "\n".join(lines)

    has_corrections = bool(duplicates or truncated or invalid)
    if has_corrections:
        lines.append(f"⚠️ 校验修正：最终 {len(deduped)} 词（去重 {len(duplicates)} | 截断 {len(truncated)} | 无效条目 {len(invalid)}）")
        if duplicates:
            lines.append(f"  移除重复: {', '.join(duplicates)}")
        if truncated:
            lines.append(f"  截断移除: {', '.join(t['word'] for t in truncated)}")
        if invalid:
            lines.append(f"  无效条目（缺 word 字段）: {len(invalid)} 个")
        lines.append(f"\n最终清单（共 {len(deduped)} 词，请严格按此清单与词序在正文渲染 Markdown 表格）:")
        lines.append(", ".join(item['word'] for item in deduped))
    else:
        lines.append(f"✅ 校验通过：共 {total_count} 词，无重复、未超限、无无效条目。请在正文中按原清单渲染 Markdown 表格。")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="考研英语核心词汇去重、限额截断与格式化校验工具")
    parser.add_argument("--json", dest="json_input", help="词汇清单 JSON 字符串或文件路径")
    parser.add_argument("--format", dest="output_format", choices=["check", "markdown", "json"], default="check",
                        help="输出格式：check=紧凑校验简报（默认），markdown=完整表格，json=归一化 JSON")
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
