#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
memo_import.py - 考研英语核心词汇墨墨背单词自动化导入脚本

功能说明：
1. 接收与 vocab_export.py 兼容的词汇清单 JSON（支持文件、字符串与标准输入）。
2. 批量解析词条的 voc_id，词组优先按原形整体查询。
3. 未在墨墨直接收录的词组自动拆分为单个独立单词，二次兜底查询解析。
4. 查询学习记录，自动状态分流：
   - 不在学习计划 -> 调用 /study/add_words 添加至待背队列 (advance=false)；
   - 已在学习计划 -> 调用 /study/advance_study 设置为提前复习。
5. 结束后输出分类报告（新加待背 / 提前复习 / 词组拆出的单词 / 无法识别）。
6. 支持 --dry-run 预览模式；Token 缺失或接口异常清晰报错退出，不静默失败。
"""

import sys
import os
import json
import argparse
import re
import urllib.request
import urllib.error

# Windows 控制台 UTF-8 编码重配置
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_URL = "https://open.maimemo.com/open/api/v1"
TIMEOUT_SECONDS = 15


class MaiMemoAPIError(Exception):
    """墨墨 API 调用异常"""
    pass


def make_api_request(endpoint: str, data: dict = None, token: str = "") -> dict:
    """
    发送 API 请求并返回解析后的 JSON 响应
    """
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "free-kaoyan-reading-importer/1.0"
    }

    req_data = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=req_data, headers=headers, method="POST" if data is not None else "GET")

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
            try:
                res_json = json.loads(body)
            except Exception as e:
                raise MaiMemoAPIError(f"API 响应 JSON 解析失败: {e} (原始内容: {body[:200]})")

            if not res_json.get("success", False):
                errors = res_json.get("errors", [])
                err_msgs = [f"[{err.get('code', 'UNKNOWN')}] {err.get('msg', '')}" for err in errors]
                err_str = "; ".join(err_msgs) if err_msgs else "未知业务错误"
                raise MaiMemoAPIError(f"API 返回错误: {err_str}")

            return res_json

    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8", errors="replace")
            err_json = json.loads(err_body)
            errors = err_json.get("errors", [])
            err_msgs = [f"[{err.get('code', 'HTTP_' + str(e.code))}] {err.get('msg', '')}" for err in errors]
            err_str = "; ".join(err_msgs) if err_msgs else err_body
        except Exception:
            err_str = err_body if err_body else str(e.reason)
        raise MaiMemoAPIError(f"HTTP {e.code} 请求失败 ({endpoint}): {err_str}")
    except urllib.error.URLError as e:
        raise MaiMemoAPIError(f"网络连接失败 ({endpoint}): {e.reason}")
    except TimeoutError:
        raise MaiMemoAPIError(f"请求超时 ({endpoint}, >{TIMEOUT_SECONDS}s)")


def parse_input_vocab(raw_input) -> list:
    """
    解析并提取词汇清单列表
    """
    if isinstance(raw_input, dict):
        if "words" in raw_input and isinstance(raw_input["words"], list):
            raw_input = raw_input["words"]
        elif "vocab" in raw_input and isinstance(raw_input["vocab"], list):
            raw_input = raw_input["vocab"]
        else:
            raw_input = [raw_input]

    if not isinstance(raw_input, list):
        raise ValueError("输入数据必须为词汇列表或包含 words/vocab 列表的对象")

    terms = []
    seen = set()
    for item in raw_input:
        if isinstance(item, str):
            term = item.strip()
        elif isinstance(item, dict):
            term = item.get("word", item.get("term", item.get("单词", item.get("词组", ""))))
            if isinstance(term, str):
                term = term.strip()
            else:
                term = ""
        else:
            term = ""

        if not term:
            continue

        key = term.lower()
        if key not in seen:
            seen.add(key)
            terms.append(term)

    return terms


def split_phrase_into_words(phrase: str) -> list:
    """
    将未直接收录的短语拆解为单个单词（过滤标点符号）
    """
    words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", phrase)
    cleaned = []
    seen = set()
    for w in words:
        w_clean = w.strip()
        if w_clean and w_clean.lower() not in seen:
            seen.add(w_clean.lower())
            cleaned.append(w_clean)
    return cleaned


def resolve_vocabularies(terms: list, token: str) -> tuple:
    """
    批量查询词汇 ID，包含整词查询和短语拆分兜底
    返回:
      direct_matches: {term: voc_id}
      phrase_splits: {phrase: [word1, word2, ...]}
      split_matches: {word: voc_id}
      unrecognized: [unmatched_single_words or failed_split_words]
    """
    direct_matches = {}
    phrase_splits = {}
    split_matches = {}
    unrecognized = []

    if not terms:
        return direct_matches, phrase_splits, split_matches, unrecognized

    # 1. 批量查询第一批（所有原形词条，包含整句短语）
    # 同时提交原形和全小写以提升命中率
    spelling_query_set = set()
    for t in terms:
        spelling_query_set.add(t)
        if t.lower() != t:
            spelling_query_set.add(t.lower())

    res = make_api_request("/vocabulary/query", {"spellings": list(spelling_query_set)}, token=token)
    voc_list = res.get("data", {}).get("voc", [])
    
    # 建立 spelling.lower() -> voc_id 映射
    lookup_map = {}
    for item in voc_list:
        lookup_map[item["spelling"].lower()] = (item["id"], item["spelling"])

    unmatched_terms = []
    for t in terms:
        t_key = t.lower()
        if t_key in lookup_map:
            direct_matches[t] = lookup_map[t_key][0]
        else:
            unmatched_terms.append(t)

    # 2. 对未命中的词条进行分类：是短语则拆分，是单字则归入无法识别
    words_to_query = set()
    for t in unmatched_terms:
        # 判断是否包含多个单词
        words = split_phrase_into_words(t)
        if len(words) > 1:
            phrase_splits[t] = words
            for w in words:
                w_key = w.lower()
                if w_key in lookup_map:
                    split_matches[w] = lookup_map[w_key][0]
                else:
                    words_to_query.add(w)
                    if w.lower() != w:
                        words_to_query.add(w.lower())
        else:
            unrecognized.append(t)

    # 3. 针对未在之前查询中命中的拆分单词进行二次查询
    if words_to_query:
        res_split = make_api_request("/vocabulary/query", {"spellings": list(words_to_query)}, token=token)
        split_voc_list = res_split.get("data", {}).get("voc", [])
        for item in split_voc_list:
            lookup_map[item["spelling"].lower()] = (item["id"], item["spelling"])

        # 检查拆分单词是否全部解析
        for phrase, words in phrase_splits.items():
            for w in words:
                w_key = w.lower()
                if w_key in lookup_map:
                    split_matches[w] = lookup_map[w_key][0]
                else:
                    if w not in unrecognized:
                        unrecognized.append(w)

    return direct_matches, phrase_splits, split_matches, unrecognized


def partition_and_import(direct_matches: dict, phrase_splits: dict, split_matches: dict, token: str, dry_run: bool = False) -> dict:
    """
    查询学习状态分流并执行导入
    """
    # 汇总所有需要处理的 voc_id
    all_voc_ids = set()
    voc_to_term = {}

    for term, vid in direct_matches.items():
        all_voc_ids.add(vid)
        voc_to_term.setdefault(vid, []).append(term)

    for word, vid in split_matches.items():
        all_voc_ids.add(vid)
        voc_to_term.setdefault(vid, []).append(word)

    if not all_voc_ids:
        return {
            "existing_voc_ids": set(),
            "new_add_voc_ids": set(),
            "advance_voc_ids": set(),
            "added_count": 0,
            "advanced_count": 0
        }

    # 批量查询已有学习记录
    rec_res = make_api_request("/study/query_study_records", {"voc_ids": list(all_voc_ids)}, token=token)
    records = rec_res.get("data", {}).get("records", [])
    existing_voc_ids = {rec["voc_id"] for rec in records if "voc_id" in rec}

    new_add_voc_ids = all_voc_ids - existing_voc_ids
    advance_voc_ids = all_voc_ids & existing_voc_ids

    added_count = 0
    advanced_count = 0

    if not dry_run:
        # 1. 新词添加至待背 (advance=false)
        if new_add_voc_ids:
            words_payload = [{"id": vid} for vid in new_add_voc_ids]
            add_res = make_api_request("/study/add_words", {"words": words_payload, "advance": False}, token=token)
            added_count = add_res.get("data", {}).get("added_count", len(new_add_voc_ids))

        # 2. 已有词提升为提前复习
        if advance_voc_ids:
            adv_res = make_api_request("/study/advance_study", {"voc_ids": list(advance_voc_ids)}, token=token)
            advanced_count = adv_res.get("data", {}).get("advanced_count", len(advance_voc_ids))
    else:
        added_count = len(new_add_voc_ids)
        advanced_count = len(advance_voc_ids)

    return {
        "existing_voc_ids": existing_voc_ids,
        "new_add_voc_ids": new_add_voc_ids,
        "advance_voc_ids": advance_voc_ids,
        "added_count": added_count,
        "advanced_count": advanced_count
    }


def format_report_text(direct_matches: dict, phrase_splits: dict, split_matches: dict, 
                       unrecognized: list, result: dict, dry_run: bool) -> str:
    """
    格式化生成清晰的控制台 Markdown/文本分类报告
    """
    new_add_vids = result["new_add_voc_ids"]
    advance_vids = result["advance_voc_ids"]

    # 分类直接词条
    direct_new = []
    direct_advance = []
    for term, vid in direct_matches.items():
        if vid in new_add_vids:
            direct_new.append(term)
        elif vid in advance_vids:
            direct_advance.append(term)

    # 分类拆分出来的词条（去重汇总）
    split_new = []
    split_advance = []
    for word, vid in split_matches.items():
        if vid in new_add_vids:
            split_new.append(word)
        elif vid in advance_vids:
            split_advance.append(word)

    lines = []
    lines.append("=" * 46)
    if dry_run:
        lines.append("🔍 墨墨背单词导入报告 【预览模式 - 未实际写入】")
    else:
        lines.append("🚀 墨墨背单词导入完成")
    lines.append("=" * 46)

    # 1. 新加待背
    total_new = len(direct_new) + len(split_new)
    lines.append(f"\n📌 新加待背 ({total_new} 个):")
    if direct_new:
        for t in direct_new:
            lines.append(f"  • {t}")
    if split_new:
        for w in split_new:
            lines.append(f"  • {w} (来自词组拆分)")
    if total_new == 0:
        lines.append("  (无)")

    # 2. 提前复习
    total_advance = len(direct_advance) + len(split_advance)
    lines.append(f"\n🔄 提前复习 ({total_advance} 个):")
    if direct_advance:
        for t in direct_advance:
            lines.append(f"  • {t}")
    if split_advance:
        for w in split_advance:
            lines.append(f"  • {w} (来自词组拆分)")
    if total_advance == 0:
        lines.append("  (无)")

    # 3. 词组拆分明细
    if phrase_splits:
        lines.append(f"\n✂️ 词组拆出的单词 ({len(phrase_splits)} 个词组):")
        for phrase, words in phrase_splits.items():
            breakdowns = []
            for w in words:
                vid = split_matches.get(w)
                if vid in new_add_vids:
                    st = "待背"
                elif vid in advance_vids:
                    st = "提前复习"
                else:
                    st = "未识别"
                breakdowns.append(f"{w} [{st}]")
            lines.append(f"  • \"{phrase}\" (未整句收录) → 拆分解析: {', '.join(breakdowns)}")

    # 4. 无法识别
    lines.append(f"\n❌ 无法识别 ({len(unrecognized)} 个):")
    if unrecognized:
        for u in unrecognized:
            lines.append(f"  • {u}")
    else:
        lines.append("  (无)")

    # 汇总条
    lines.append("\n" + "-" * 46)
    lines.append(f"📊 汇总统计: 新加待背 {total_new} | 提前复习 {total_advance} | 拆分词组 {len(phrase_splits)} | 无法识别 {len(unrecognized)}")
    lines.append("=" * 46)

    return "\n".join(lines)


def format_report_json(direct_matches: dict, phrase_splits: dict, split_matches: dict, 
                       unrecognized: list, result: dict, dry_run: bool) -> str:
    """
    格式化生成 JSON 结构化分类报告
    """
    new_add_vids = result["new_add_voc_ids"]
    advance_vids = result["advance_voc_ids"]

    direct_new = [t for t, vid in direct_matches.items() if vid in new_add_vids]
    direct_advance = [t for t, vid in direct_matches.items() if vid in advance_vids]
    split_new = [w for w, vid in split_matches.items() if vid in new_add_vids]
    split_advance = [w for w, vid in split_matches.items() if vid in advance_vids]

    phrase_detail = []
    for phrase, words in phrase_splits.items():
        w_list = []
        for w in words:
            vid = split_matches.get(w)
            if vid in new_add_vids:
                st = "new_added"
            elif vid in advance_vids:
                st = "advance_review"
            else:
                st = "unrecognized"
            w_list.append({"word": w, "status": st, "voc_id": vid})
        phrase_detail.append({"phrase": phrase, "words": w_list})

    out = {
        "dry_run": dry_run,
        "summary": {
            "new_added_count": len(direct_new) + len(split_new),
            "advance_review_count": len(direct_advance) + len(split_advance),
            "phrase_splits_count": len(phrase_splits),
            "unrecognized_count": len(unrecognized)
        },
        "new_added": {
            "direct": direct_new,
            "from_phrases": split_new
        },
        "advance_review": {
            "direct": direct_advance,
            "from_phrases": split_advance
        },
        "phrase_splits": phrase_detail,
        "unrecognized": unrecognized
    }
    return json.dumps(out, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="考研英语篇末词汇墨墨背单词自动化导入工具")
    parser.add_argument("--json", dest="json_input", help="词汇清单 JSON 字符串或文件路径")
    parser.add_argument("--token", dest="token", help="墨墨 API Token (若不指定则读取 MAIMEMOTOKEN 或 MAIMEMO_TOKEN 环境变量)")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="预览模式，仅查询与分流，不执行写入操作")
    parser.add_argument("--format", dest="output_format", choices=["text", "json"], default="text", help="报告输出格式 (text 或 json)")

    args = parser.parse_args()

    # 1. 检查并获取 Token
    token = args.token or os.environ.get("MAIMEMOTOKEN") or os.environ.get("MAIMEMO_TOKEN")
    if not token:
        print("[ERROR] 缺少墨墨背单词 API Token。请在环境变量中设置 MAIMEMOTOKEN 或通过 --token 参数传入。", file=sys.stderr)
        sys.exit(1)

    # 2. 读取与解析输入 JSON
    if args.json_input:
        if os.path.isfile(args.json_input):
            try:
                with open(args.json_input, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
            except Exception as e:
                print(f"[ERROR] 读取输入 JSON 文件失败: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            try:
                raw_data = json.loads(args.json_input)
            except Exception as e:
                print(f"[ERROR] 解析 --json 参数字符串失败: {e}", file=sys.stderr)
                sys.exit(1)
    else:
        if not sys.stdin.isatty():
            content = sys.stdin.read().strip()
            if content:
                try:
                    raw_data = json.loads(content)
                except Exception as e:
                    print(f"[ERROR] 解析标准输入 JSON 失败: {e}", file=sys.stderr)
                    sys.exit(1)
            else:
                print("[ERROR] 未检测到标准输入内容，请通过 --json 或标准输入传入词汇清单 JSON。", file=sys.stderr)
                sys.exit(1)
        else:
            parser.error("必须通过 --json 或标准输入传入词汇清单 JSON")

    try:
        terms = parse_input_vocab(raw_data)
    except Exception as e:
        print(f"[ERROR] 词汇清单格式错误: {e}", file=sys.stderr)
        sys.exit(1)

    if not terms:
        print("[WARNING] 输入词汇列表为空，无词条需要导入。", file=sys.stderr)
        sys.exit(0)

    # 3. 词汇查询与短语拆分兜底
    try:
        direct_matches, phrase_splits, split_matches, unrecognized = resolve_vocabularies(terms, token)
    except MaiMemoAPIError as e:
        print(f"[ERROR] 墨墨词汇解析失败: {e}", file=sys.stderr)
        sys.exit(1)

    # 4. 学习记录状态分流与写入
    try:
        result = partition_and_import(direct_matches, phrase_splits, split_matches, token, dry_run=args.dry_run)
    except MaiMemoAPIError as e:
        print(f"[ERROR] 墨墨学习记录分流/写入失败: {e}", file=sys.stderr)
        sys.exit(1)

    # 5. 输出报告
    if args.output_format == "json":
        report = format_report_json(direct_matches, phrase_splits, split_matches, unrecognized, result, args.dry_run)
    else:
        report = format_report_text(direct_matches, phrase_splits, split_matches, unrecognized, result, args.dry_run)

    print(report)


if __name__ == "__main__":
    main()
