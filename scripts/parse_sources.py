"""Parse read-only public source files into Task 02 JSON artifacts.

This script intentionally uses only the Python standard library. It reads the
source DOCX/XLSX files as ZIP/XML containers and writes generated JSON into
data/processed/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "示范景区公开资料包"
OUTPUT_DIR = ROOT / "data" / "processed"

STRUCTURED_DOCX = "灵山胜境 景点结构化数据集.docx"
GUIDE_DOCX = "灵山胜境：历史、文化、景点特色与个性化游览指南.docx"
BEHAVIOR_XLSX = "景点景区旅游数据行为分析数据.xlsx"

WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
SHEET_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

STRUCTURED_HEADERS = [
    "景区名称",
    "景点ID",
    "景点名称",
    "具体位置",
    "建筑/景观参数",
    "核心功能",
    "文化内涵",
    "详细介绍",
    "游玩亮点",
    "演艺/开放信息",
    "备注",
]


@dataclass
class SourceFile:
    path: Path
    name: str
    sha256: str
    size_bytes: int
    modified_ns: int


def ensure_workspace_path(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise RuntimeError(f"Refusing to access outside workspace: {resolved}")
    return resolved


def source_info(path: Path) -> SourceFile:
    path = ensure_workspace_path(path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    stat = path.stat()
    return SourceFile(
        path=path,
        name=path.name,
        sha256=digest.hexdigest(),
        size_bytes=stat.st_size,
        modified_ns=stat.st_mtime_ns,
    )


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def split_cn_items(text: str, *, max_items: int = 8) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    parts = re.split(r"[；;。]\s*", text)
    items = [clean_text(part) for part in parts if clean_text(part)]
    return items[:max_items] or [text]


def compact_summary(text: str, limit: int = 150) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip("，。；; ") + "。"


def word_cell_text(cell: ET.Element) -> str:
    return clean_text("".join(node.text or "" for node in cell.findall(".//w:t", WORD_NS)))


def docx_tables(path: Path) -> list[list[list[str]]]:
    path = ensure_workspace_path(path)
    with zipfile.ZipFile(path) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))

    tables: list[list[list[str]]] = []
    for table in document.findall(".//w:tbl", WORD_NS):
        rows = []
        for row in table.findall("./w:tr", WORD_NS):
            rows.append([word_cell_text(cell) for cell in row.findall("./w:tc", WORD_NS)])
        tables.append(rows)
    return tables


def docx_blocks(path: Path) -> list[dict[str, Any]]:
    path = ensure_workspace_path(path)
    with zipfile.ZipFile(path) as archive:
        body = ET.fromstring(archive.read("word/document.xml")).find(".//w:body", WORD_NS)

    blocks: list[dict[str, Any]] = []
    if body is None:
        return blocks

    for child in list(body):
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            text = clean_text("".join(node.text or "" for node in child.findall(".//w:t", WORD_NS)))
            if text:
                blocks.append({"type": "paragraph", "text": text})
        elif tag == "tbl":
            rows = []
            for row in child.findall("./w:tr", WORD_NS):
                rows.append([word_cell_text(cell) for cell in row.findall("./w:tc", WORD_NS)])
            if rows:
                blocks.append({"type": "table", "rows": rows})
    return blocks


def scenic_slug(scenic_area: str) -> str:
    if "拈花湾" in scenic_area:
        return "nianhuawan"
    return "lingshan"


def infer_category(row: dict[str, str]) -> str:
    text = " ".join([row.get("核心功能", ""), row.get("文化内涵", ""), row.get("详细介绍", "")])
    name = row.get("景点名称", "")
    if any(word in text for word in ["演艺", "表演", "动态", "舞台"]):
        return "演艺互动"
    if any(word in text for word in ["商业", "文创", "美食", "消费"]):
        return "禅意商业"
    if any(word in text for word in ["自然", "花海", "水景", "休闲", "漫步"]):
        return "自然休闲"
    if any(word in text for word in ["朝圣", "祈福", "佛教", "禅寺", "坛城"]) or any(
        word in name for word in ["佛", "寺", "坛", "宫", "塔", "掌", "门"]
    ):
        return "佛教文化"
    if any(word in text for word in ["入口", "门户", "集散"]):
        return "门户集散"
    return "文化景观"


def infer_tags(row: dict[str, str]) -> list[str]:
    text = " ".join(row.values())
    tag_rules = {
        "佛教文化": ["佛", "禅", "朝圣", "祈福"],
        "亲子友好": ["亲子", "孩子", "儿童"],
        "拍照打卡": ["打卡", "拍摄", "合影", "花海"],
        "演艺提醒": ["演出", "表演", "舞台", "动态"],
        "路线节点": ["必经", "中轴线", "连接"],
        "休闲漫步": ["休闲", "漫步", "步道", "小镇"],
        "历史文化": ["历史", "赵朴初", "玄奘", "文化"],
        "夜游": ["夜间", "灯光", "夜景"],
    }
    tags = [tag for tag, needles in tag_rules.items() if any(needle in text for needle in needles)]
    if not tags:
        tags.append(infer_category(row))
    return tags[:8]


def parse_attractions(source: SourceFile) -> list[dict[str, Any]]:
    tables = docx_tables(source.path)
    attractions: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for table_index, rows in enumerate(tables, start=1):
        if not rows or rows[0] != STRUCTURED_HEADERS:
            continue
        for row_index, values in enumerate(rows[1:], start=2):
            if len(values) < len(STRUCTURED_HEADERS):
                continue
            row = dict(zip(STRUCTURED_HEADERS, values, strict=True))
            attraction_id = row["景点ID"].strip()
            if not attraction_id or attraction_id in seen_ids:
                continue
            seen_ids.add(attraction_id)

            scenic_area = row["景区名称"]
            tags = infer_tags(row)
            category = infer_category(row)
            description = (
                row["详细介绍"]
                or row["核心功能"]
                or row["文化内涵"]
                or row["游玩亮点"]
                or "。".join(value for value in [row["具体位置"], row["建筑/景观参数"]] if value)
            )
            attractions.append(
                {
                    "id": f"{scenic_slug(scenic_area)}-{attraction_id.lower()}",
                    "attraction_id": attraction_id,
                    "scenic_area": scenic_area,
                    "name": row["景点名称"],
                    "category": category,
                    "summary": compact_summary(description, 180),
                    "description": description,
                    "location": row["具体位置"],
                    "parameters": row["建筑/景观参数"],
                    "core_function": row["核心功能"],
                    "culture_points": split_cn_items(row["文化内涵"], max_items=6),
                    "history_points": [item for item in split_cn_items(row["文化内涵"], max_items=6) if any(key in item for key in ["历史", "唐", "宋", "赵朴初", "玄奘", "佛"])],
                    "visitor_tips": split_cn_items("；".join([row["游玩亮点"], row["演艺/开放信息"], row["备注"]]), max_items=8),
                    "opening_info": row["演艺/开放信息"],
                    "notes": row["备注"],
                    "tags": tags,
                    "source_file": source.name,
                    "source_table": table_index,
                    "source_row": row_index,
                    "metadata": {
                        "source_sha256": source.sha256,
                        "raw_fields": row,
                    },
                }
            )

    return attractions


def attraction_lookup(attractions: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    entries = []
    for attraction in attractions:
        entries.append((attraction["name"], attraction["id"], attraction["attraction_id"]))
    entries.sort(key=lambda item: len(item[0]), reverse=True)
    return entries


def find_attraction_id(text: str, lookup: list[tuple[str, str, str]]) -> str | None:
    for name, stable_id, legacy_id in lookup:
        if name and name in text:
            return stable_id
        if legacy_id and legacy_id in text:
            return stable_id
    return None


def make_chunk(
    *,
    chunk_id: str,
    source_file: SourceFile,
    source_section: str,
    attraction_id: str | None,
    title: str,
    content: str,
    tags: list[str],
    chunk_type: str,
    priority: int,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": chunk_id,
        "source_file": source_file.name,
        "source_section": source_section,
        "attraction_id": attraction_id,
        "title": title,
        "content": clean_text(content),
        "tags": tags,
        "chunk_type": chunk_type,
        "priority": priority,
        "metadata": {
            "source_sha256": source_file.sha256,
            **(metadata or {}),
        },
    }


def structured_chunks(source: SourceFile, attractions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for attraction in attractions:
        base = attraction["id"]
        culture_content = "；".join(attraction["culture_points"]) or (
            f"{attraction['name']}资料行未提供单独文化内涵字段；可引用基础介绍：{attraction['description']}"
        )
        visitor_content = "；".join(tip for tip in attraction["visitor_tips"] if tip.strip("；;。 ")) or (
            f"{attraction['name']}资料行未提供单独游览建议字段；位置：{attraction['location']}。开放信息：{attraction['opening_info'] or '待后续资料补充'}。"
        )
        chunks.append(
            make_chunk(
                chunk_id=f"{base}::overview",
                source_file=source,
                source_section=f"{attraction['scenic_area']} 景点数据集",
                attraction_id=base,
                title=f"{attraction['name']} 基础信息",
                content=(
                    f"{attraction['name']}位于{attraction['location']}。"
                    f"建筑/景观参数：{attraction['parameters']}。"
                    f"核心功能：{attraction['core_function']}。"
                    f"详细介绍：{attraction['description']}"
                ),
                tags=attraction["tags"],
                chunk_type="attraction_overview",
                priority=95,
                metadata={"attraction_name": attraction["name"]},
            )
        )
        chunks.append(
            make_chunk(
                chunk_id=f"{base}::culture",
                source_file=source,
                source_section=f"{attraction['scenic_area']} 景点数据集",
                attraction_id=base,
                title=f"{attraction['name']} 文化内涵",
                content=culture_content,
                tags=list(dict.fromkeys([*attraction["tags"], "文化讲解"])),
                chunk_type="culture",
                priority=92,
                metadata={"attraction_name": attraction["name"]},
            )
        )
        chunks.append(
            make_chunk(
                chunk_id=f"{base}::visitor-advice",
                source_file=source,
                source_section=f"{attraction['scenic_area']} 景点数据集",
                attraction_id=base,
                title=f"{attraction['name']} 游览建议",
                content=(
                    f"游玩亮点：{visitor_content}。"
                    f"开放/演艺信息：{attraction['opening_info']}。备注：{attraction['notes']}"
                ),
                tags=list(dict.fromkeys([*attraction["tags"], "游览建议"])),
                chunk_type="visitor_advice",
                priority=90,
                metadata={"attraction_name": attraction["name"]},
            )
        )
    return chunks


def is_section_heading(text: str) -> bool:
    if len(text) > 44:
        return False
    if text.endswith(("。", "；", "，", ".", "：")):
        return False
    return any(
        key in text
        for key in [
            "概况",
            "历史",
            "文化",
            "特色",
            "详解",
            "大佛",
            "梵宫",
            "九龙灌浴",
            "五印坛城",
            "祥符禅寺",
            "推荐路线",
            "游览",
            "票务",
        ]
    )


def guide_chunks(source: SourceFile, attractions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    lookup = attraction_lookup(attractions)
    current_section = "文档开头"
    paragraph_index = 0
    table_index = 0

    for block in docx_blocks(source.path):
        if block["type"] == "paragraph":
            text = block["text"]
            if is_section_heading(text):
                current_section = text
                continue
            if len(text) < 35:
                continue
            paragraph_index += 1
            attraction_id = find_attraction_id(f"{current_section} {text}", lookup)
            chunks.append(
                make_chunk(
                    chunk_id=f"guide::p{paragraph_index:03d}",
                    source_file=source,
                    source_section=current_section,
                    attraction_id=attraction_id,
                    title=current_section,
                    content=text,
                    tags=["历史文化", "导览讲解"] if attraction_id else ["景区概览", "导览讲解"],
                    chunk_type="guide_paragraph",
                    priority=82 if attraction_id else 70,
                    metadata={"block_index": paragraph_index},
                )
            )
        elif block["type"] == "table":
            rows = block["rows"]
            if len(rows) < 2:
                continue
            table_index += 1
            headers = rows[0]
            for row_number, row in enumerate(rows[1:], start=2):
                if not any(row):
                    continue
                row_title = row[0] if row else f"表格第 {row_number} 行"
                paired = []
                if len(headers) == len(row):
                    paired = [f"{header}：{value}" for header, value in zip(headers, row, strict=True)]
                else:
                    paired = row
                content = "；".join(clean_text(value) for value in paired if clean_text(value))
                attraction_id = find_attraction_id(f"{current_section} {content}", lookup)
                chunks.append(
                    make_chunk(
                        chunk_id=f"guide::t{table_index:02d}r{row_number:02d}",
                        source_file=source,
                        source_section=current_section,
                        attraction_id=attraction_id,
                        title=f"{current_section} - {row_title}",
                        content=content,
                        tags=["表格资料", "事实信息"],
                        chunk_type="guide_table_row",
                        priority=86 if attraction_id else 72,
                        metadata={"table_index": table_index, "row_number": row_number},
                    )
                )
    return chunks


def col_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    result = 0
    for ch in letters:
        result = result * 26 + ord(ch.upper()) - ord("A") + 1
    return result - 1


def read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return ["".join(node.text or "" for node in item.iter(f"{SHEET_NS}t")) for item in root.findall(f"{SHEET_NS}si")]


def cell_value(cell: ET.Element, shared: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return clean_text("".join(node.text or "" for node in cell.iter(f"{SHEET_NS}t")))
    node = cell.find(f"{SHEET_NS}v")
    if node is None or node.text is None:
        return ""
    raw = node.text
    if cell_type == "s" and raw.isdigit():
        return shared[int(raw)]
    return raw


def iter_xlsx_rows(path: Path) -> Iterable[list[str]]:
    path = ensure_workspace_path(path)
    with zipfile.ZipFile(path) as archive:
        shared = read_shared_strings(archive)
        with archive.open("xl/worksheets/sheet1.xml") as sheet:
            for _event, row in ET.iterparse(sheet, events=("end",)):
                if row.tag != f"{SHEET_NS}row":
                    continue
                cells: dict[int, str] = {}
                max_col = -1
                for cell in row.findall(f"{SHEET_NS}c"):
                    index = col_index(cell.attrib.get("r", "A1"))
                    max_col = max(max_col, index)
                    cells[index] = cell_value(cell, shared)
                yield [cells.get(index, "") for index in range(max_col + 1)]
                row.clear()


def excel_date_to_iso(value: str) -> str | None:
    try:
        serial = float(value)
    except ValueError:
        return None
    if serial <= 0:
        return None
    return (datetime(1899, 12, 30) + timedelta(days=serial)).date().isoformat()


def numeric(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def top_counter(counter: Counter[str], limit: int = 12) -> list[dict[str, Any]]:
    return [{"value": key, "count": count} for key, count in counter.most_common(limit)]


def average(total: float, count: int) -> float | None:
    if count == 0:
        return None
    return round(total / count, 2)


def age_bucket(age: float | None) -> str:
    if age is None:
        return "未知"
    if age <= 17:
        return "0-17"
    if age <= 25:
        return "18-25"
    if age <= 35:
        return "26-35"
    if age <= 45:
        return "36-45"
    if age <= 60:
        return "46-60"
    return "60+"


def parse_behavior(source: SourceFile) -> dict[str, Any]:
    rows = iter_xlsx_rows(source.path)
    headers = next(rows)
    index = {name: position for position, name in enumerate(headers)}

    counters = {
        "gender": Counter(),
        "attraction_type": Counter(),
        "satisfaction": Counter(),
        "age_group": Counter(),
        "group_size": Counter(),
        "top_attractions": Counter(),
    }
    type_stats: dict[str, dict[str, float | int]] = defaultdict(lambda: {"count": 0, "satisfaction_total": 0.0, "stay_total": 0.0, "total_cost": 0.0})
    cost_fields = ["ticket_cost", "food_cost", "shopping_cost", "transport_cost", "entertainment_cost", "total_cost"]
    cost_totals = {field: 0.0 for field in cost_fields}
    cost_counts = {field: 0 for field in cost_fields}
    stay_total = 0.0
    stay_count = 0
    satisfaction_total = 0.0
    satisfaction_count = 0
    min_date: str | None = None
    max_date: str | None = None
    total_rows = 0

    for row in rows:
        total_rows += 1

        def get(field: str) -> str:
            pos = index[field]
            return row[pos] if pos < len(row) else ""

        gender = get("gender") or "未知"
        attraction_type = get("attraction_type") or "未知"
        attraction_name = get("attraction_name") or "未知"
        satisfaction = numeric(get("satisfaction"))
        stay = numeric(get("stay_duration"))
        age = numeric(get("age"))
        group_size = get("group_size") or "未知"
        visit_date = excel_date_to_iso(get("visit_date"))

        counters["gender"][gender] += 1
        counters["attraction_type"][attraction_type] += 1
        counters["age_group"][age_bucket(age)] += 1
        counters["group_size"][group_size] += 1
        counters["top_attractions"][attraction_name] += 1
        if satisfaction is not None:
            counters["satisfaction"][str(int(satisfaction)) if satisfaction.is_integer() else str(satisfaction)] += 1
            satisfaction_total += satisfaction
            satisfaction_count += 1
        if stay is not None:
            stay_total += stay
            stay_count += 1
        if visit_date:
            min_date = visit_date if min_date is None else min(min_date, visit_date)
            max_date = visit_date if max_date is None else max(max_date, visit_date)

        stat = type_stats[attraction_type]
        stat["count"] = int(stat["count"]) + 1
        if satisfaction is not None:
            stat["satisfaction_total"] = float(stat["satisfaction_total"]) + satisfaction
        if stay is not None:
            stat["stay_total"] = float(stat["stay_total"]) + stay
        total_cost = numeric(get("total_cost"))
        if total_cost is not None:
            stat["total_cost"] = float(stat["total_cost"]) + total_cost

        for field in cost_fields:
            value = numeric(get(field))
            if value is not None:
                cost_totals[field] += value
                cost_counts[field] += 1

    by_type = []
    for key, stat in sorted(type_stats.items(), key=lambda item: int(item[1]["count"]), reverse=True):
        count = int(stat["count"])
        by_type.append(
            {
                "attraction_type": key,
                "count": count,
                "avg_satisfaction": average(float(stat["satisfaction_total"]), count),
                "avg_stay_duration": average(float(stat["stay_total"]), count),
                "avg_total_cost": average(float(stat["total_cost"]), count),
            }
        )

    return {
        "source_file": source.name,
        "source_sha256": source.sha256,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "caveat": "该 xlsx 为公开样例游客行为数据/行业画像数据，包含多景区样本；不能声称为灵山胜境或拈花湾真实运营数据。",
        "row_count": total_rows,
        "fields": headers,
        "date_range": {"start": min_date, "end": max_date},
        "distributions": {
            "gender": top_counter(counters["gender"]),
            "age_group": top_counter(counters["age_group"]),
            "attraction_type": top_counter(counters["attraction_type"]),
            "satisfaction": top_counter(counters["satisfaction"]),
            "group_size": top_counter(counters["group_size"]),
        },
        "top_attractions": top_counter(counters["top_attractions"], limit=20),
        "averages": {
            "stay_duration": average(stay_total, stay_count),
            "satisfaction": average(satisfaction_total, satisfaction_count),
            **{field: average(cost_totals[field], cost_counts[field]) for field in cost_fields},
        },
        "by_attraction_type": by_type[:20],
        "metadata": {
            "source_size_bytes": source.size_bytes,
            "source_modified_ns": source.modified_ns,
            "parser": "scripts/parse_sources.py",
        },
    }


def write_json(path: Path, payload: Any) -> None:
    path = ensure_workspace_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_all() -> dict[str, int]:
    sources = {
        "structured": source_info(SOURCE_DIR / STRUCTURED_DOCX),
        "guide": source_info(SOURCE_DIR / GUIDE_DOCX),
        "behavior": source_info(SOURCE_DIR / BEHAVIOR_XLSX),
    }

    attractions = parse_attractions(sources["structured"])
    chunks = [
        *structured_chunks(sources["structured"], attractions),
        *guide_chunks(sources["guide"], attractions),
    ]
    behavior_summary = parse_behavior(sources["behavior"])

    write_json(OUTPUT_DIR / "attractions.json", attractions)
    write_json(OUTPUT_DIR / "knowledge_chunks.json", chunks)
    write_json(OUTPUT_DIR / "behavior_summary.json", behavior_summary)

    return {
        "attractions": len(attractions),
        "knowledge_chunks": len(chunks),
        "behavior_rows": behavior_summary["row_count"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse Task 02 source materials into processed JSON.")
    parser.add_argument("--summary-only", action="store_true", help="Print counts without extra prose.")
    args = parser.parse_args()
    counts = parse_all()
    if args.summary_only:
        print(json.dumps(counts, ensure_ascii=False, sort_keys=True))
    else:
        print(f"Wrote {OUTPUT_DIR / 'attractions.json'} ({counts['attractions']} attractions)")
        print(f"Wrote {OUTPUT_DIR / 'knowledge_chunks.json'} ({counts['knowledge_chunks']} chunks)")
        print(f"Wrote {OUTPUT_DIR / 'behavior_summary.json'} ({counts['behavior_rows']} behavior rows)")


if __name__ == "__main__":
    main()
