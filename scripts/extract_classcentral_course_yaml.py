#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import textwrap
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from pathlib import Path


MANIFEST_PATH = Path("/code/data/classcentral-datacamp-pages/manifest.jsonl")
HTML_ROOT = Path("/code/data/classcentral-datacamp-pages")
OUTPUT_ROOT = Path("/code/data/classcentral-datacamp-yaml")
WRAP_WIDTH = 80


class FragmentTextExtractor(HTMLParser):
    def __init__(self, list_mode: bool = False) -> None:
        super().__init__()
        self.list_mode = list_mode
        self.parts: list[str] = []
        self.ignore_depth = 0
        self.in_li = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.ignore_depth += 1
            return
        if self.ignore_depth:
            return
        if tag in {"br"}:
            self.parts.append("\n")
        elif tag in {"p", "div", "section"}:
            self.parts.append("\n\n")
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\n\n")
        elif tag == "li":
            self.in_li = True
            self.parts.append("\n- " if self.list_mode else "\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.ignore_depth:
            self.ignore_depth -= 1
            return
        if self.ignore_depth:
            return
        if tag == "li":
            self.in_li = False
            self.parts.append("\n")
        elif tag in {"p", "div", "section"}:
            self.parts.append("\n\n")
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\n\n")

    def handle_data(self, data: str) -> None:
        if self.ignore_depth:
            return
        self.parts.append(data)

    def get_text(self) -> str:
        text = unescape("".join(self.parts))
        text = text.replace("\xa0", " ")
        text = re.sub(r"[ \t\r\f\v]+", " ", text)
        text = re.sub(r" *\n *", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


class SyllabusParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ul_depth = 0
        self.in_li = False
        self.current_text: list[str] = []
        self.items: list[tuple[int, str]] = []
        self.ignore_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.ignore_depth += 1
            return
        if self.ignore_depth:
            return
        if tag == "ul":
            self.ul_depth += 1
        elif tag == "li":
            self.in_li = True
            self.current_text = []
        elif tag == "br" and self.in_li:
            self.current_text.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.ignore_depth:
            self.ignore_depth -= 1
            return
        if self.ignore_depth:
            return
        if tag == "li" and self.in_li:
            text = unescape("".join(self.current_text))
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                self.items.append((self.ul_depth, text))
            self.in_li = False
            self.current_text = []
        elif tag == "ul" and self.ul_depth:
            self.ul_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.ignore_depth or not self.in_li:
            return
        self.current_text.append(data)


@dataclass
class CourseRecord:
    source_url: str
    final_url: str
    fetched_at: str
    html_file: str
    title: str | None
    provider: str | None
    image: str | None
    summary: str | None
    details: dict[str, str | list[str] | None]
    ratings: dict[str, object]
    subjects: list[str]
    overview: str | None
    syllabus: list[dict[str, str]]


def read_manifest() -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def findall_ld_json(text: str) -> list[object]:
    blocks = re.findall(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
        text,
        flags=re.S,
    )
    parsed: list[object] = []
    for block in blocks:
        block = unescape(block).strip()
        try:
            parsed.append(json.loads(block))
        except json.JSONDecodeError:
            continue
    return parsed


def flatten_json_nodes(node: object) -> list[dict[str, object]]:
    if isinstance(node, dict):
        return [node]
    if isinstance(node, list):
        out: list[dict[str, object]] = []
        for item in node:
            out.extend(flatten_json_nodes(item))
        return out
    return []


def get_product_data(text: str) -> dict[str, object]:
    for payload in findall_ld_json(text):
        for node in flatten_json_nodes(payload):
            if node.get("@type") == "Product":
                return node
    return {}


def clean_fragment(fragment: str, list_mode: bool = False) -> str:
    parser = FragmentTextExtractor(list_mode=list_mode)
    parser.feed(fragment)
    text = parser.get_text()
    paragraphs = []
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        lines = paragraph.splitlines()
        normalized = " ".join(line.strip() for line in lines if line.strip())
        paragraphs.append(normalized)
    return "\n\n".join(paragraphs).strip()


def extract_first(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.S)
    if not match:
        return None
    return unescape(match.group(1)).strip()


def extract_section_fragment(text: str, heading: str) -> str | None:
    pattern = (
        rf"<h[23][^>]*>\s*{re.escape(heading)}\s*</h[23]>"
        r".*?<div[^>]+data-truncatable-id=\"course-content-[^\"]+\"[^>]*>(.*?)</div>"
    )
    return extract_first(text, pattern)


def extract_sidebar(text: str) -> str | None:
    return extract_first(
        text,
        r'id="btnProviderCoursePage".*?<ul class="list-no-style">(.*?)</ul>\s*</div>\s*</div>',
    )


def parse_details(sidebar_html: str | None) -> dict[str, str | list[str] | None]:
    details: dict[str, str | list[str] | None] = {}
    if not sidebar_html:
        return details

    for block in re.findall(r"<li class=\"course-details-item.*?>(.*?)</li>", sidebar_html, re.S):
        label = extract_first(block, r'<span class="medium-up-hidden text-2 color-gray">(.*?)</span>')
        if not label:
            continue
        block = re.sub(r"<button.*?</button>", "", block, flags=re.S)
        value_html = re.sub(r'<div>\s*<i.*?</div>', "", block, flags=re.S)
        value_html = re.sub(
            r'<span class="medium-up-hidden text-2 color-gray">.*?</span>',
            "",
            value_html,
            flags=re.S,
        )
        value = clean_fragment(value_html)
        if value:
            details[label.lower().replace(" & ", "_").replace(" ", "_")] = value
    return details


def parse_subjects(text: str) -> list[str]:
    found_in = extract_first(
        text,
        r'<section id="found-in".*?<div id="found-in-contents"[^>]*>(.*?)</div>\s*</section>',
    )
    if not found_in:
        return []
    subjects = []
    for subject in re.findall(r"<span class=\"\">(.*?)</span>", found_in):
        clean = clean_fragment(subject)
        clean = re.sub(r"\s+Courses$", "", clean)
        if clean and clean not in subjects:
            subjects.append(clean)
    return subjects


def parse_ratings(text: str, product: dict[str, object]) -> dict[str, object]:
    class_central: dict[str, object] = {}
    aggregate = product.get("aggregateRating")
    if isinstance(aggregate, dict):
        class_central = {
            "rating": aggregate.get("ratingValue"),
            "review_count": aggregate.get("reviewCount"),
        }

    provider_match = re.search(
        r"<strong class=\"weight-bold\">([0-9.]+)</strong>\s*rating at "
        r"<strong class=\"weight-bold\">([^<]+)</strong>\s*based on "
        r"<strong class=\"weight-bold\">([0-9,]+)</strong>",
        text,
        flags=re.S,
    )
    provider = None
    if provider_match:
        provider = {
            "rating": provider_match.group(1),
            "provider": provider_match.group(2).strip(),
            "rating_count": provider_match.group(3).replace(",", ""),
        }

    return {"class_central": class_central, "provider": provider}


def parse_syllabus(fragment: str | None) -> list[dict[str, str]]:
    if not fragment:
        return []
    parser = SyllabusParser()
    parser.feed(fragment)
    items = parser.items
    modules: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for depth, text in items:
        if depth <= 1:
            if current:
                modules.append(current)
            current = {"title": text}
        else:
            if current is None:
                current = {"title": text}
            elif "summary" not in current:
                current["summary"] = text
            else:
                current["summary"] += f" {text}"
    if current:
        modules.append(current)
    return modules


def scalar(value: object) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "":
        return '""'
    if re.fullmatch(r"[A-Za-z0-9_./:+-]+", text):
        return text
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def format_block(text: str, indent: int) -> list[str]:
    width = max(20, WRAP_WIDTH - indent)
    lines = []
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if paragraph.startswith("- "):
            for bullet in paragraph.splitlines():
                if not bullet.strip():
                    continue
                wrapped = textwrap.fill(
                    bullet.strip(),
                    width=width,
                    initial_indent=" " * indent,
                    subsequent_indent=" " * indent,
                    break_long_words=False,
                    break_on_hyphens=False,
                )
                lines.append(wrapped)
        else:
            wrapped = textwrap.fill(
                paragraph,
                width=width,
                initial_indent=" " * indent,
                subsequent_indent=" " * indent,
                break_long_words=False,
                break_on_hyphens=False,
            )
            lines.append(wrapped)
        lines.append("")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def emit_yaml(value: object, indent: int = 0) -> list[str]:
    pad = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                if not item:
                    lines.append(f"{pad}{key}: {'{}' if isinstance(item, dict) else '[]'}")
                else:
                    lines.append(f"{pad}{key}:")
                    lines.extend(emit_yaml(item, indent + 2))
            elif isinstance(item, str) and ("\n" in item or len(item) > WRAP_WIDTH - indent - len(key) - 2):
                lines.append(f"{pad}{key}: |-")
                lines.extend(format_block(item, indent + 2))
            else:
                lines.append(f"{pad}{key}: {scalar(item)}")
        return lines
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, dict):
                keys = list(item.keys())
                first_key = keys[0]
                first_value = item[first_key]
                if isinstance(first_value, str) and ("\n" not in first_value) and len(first_value) <= WRAP_WIDTH - indent - len(first_key) - 6:
                    lines.append(f"{pad}- {first_key}: {scalar(first_value)}")
                else:
                    lines.append(f"{pad}- {first_key}: |-")
                    lines.extend(format_block(str(first_value), indent + 4))
                for key in keys[1:]:
                    subvalue = item[key]
                    if isinstance(subvalue, str) and ("\n" in subvalue or len(subvalue) > WRAP_WIDTH - indent - len(key) - 4):
                        lines.append(f"{pad}  {key}: |-")
                        lines.extend(format_block(subvalue, indent + 4))
                    else:
                        lines.append(f"{pad}  {key}: {scalar(subvalue)}")
            elif isinstance(item, str) and len(item) > WRAP_WIDTH - indent - 2:
                lines.append(f"{pad}- |-")
                lines.extend(format_block(item, indent + 4))
            else:
                lines.append(f"{pad}- {scalar(item)}")
        return lines
    return [f"{pad}{scalar(value)}"]


def build_record(entry: dict[str, object]) -> CourseRecord:
    html_rel = str(entry["html_file"])
    html_text = (HTML_ROOT / html_rel).read_text(encoding="utf-8")
    product = get_product_data(html_text)

    title = (
        product.get("name")
        if isinstance(product.get("name"), str)
        else extract_first(html_text, r"<h1[^>]*>(.*?)</h1>")
    )
    provider = None
    offers = product.get("offers")
    if isinstance(offers, dict):
        seller = offers.get("seller")
        if isinstance(seller, dict):
            provider = seller.get("name") if isinstance(seller.get("name"), str) else None
    provider = provider or extract_first(
        html_text,
        r'via <a[^>]*>(.*?)</a>',
    )

    overview_fragment = extract_section_fragment(html_text, "Overview")
    syllabus_fragment = extract_section_fragment(html_text, "Syllabus")
    sidebar_html = extract_sidebar(html_text)

    summary = product.get("description") if isinstance(product.get("description"), str) else None
    image = product.get("image") if isinstance(product.get("image"), str) else None

    return CourseRecord(
        source_url=str(entry["url"]),
        final_url=str(entry["final_url"]),
        fetched_at=str(entry["fetched_at"]),
        html_file=html_rel,
        title=title,
        provider=provider,
        image=image,
        summary=summary.strip() if summary else None,
        details=parse_details(sidebar_html),
        ratings=parse_ratings(html_text, product),
        subjects=parse_subjects(html_text),
        overview=clean_fragment(overview_fragment) if overview_fragment else None,
        syllabus=parse_syllabus(syllabus_fragment),
    )


def record_to_dict(record: CourseRecord) -> dict[str, object]:
    return {
        "source_url": record.source_url,
        "final_url": record.final_url,
        "fetched_at": record.fetched_at,
        "title": record.title,
        "provider": record.provider,
        "summary": record.summary,
        "details": record.details,
        "ratings": record.ratings,
        "subjects": record.subjects,
        "overview": record.overview,
        "syllabus": record.syllabus,
    }


def slug_from_html_path(html_file: str) -> str:
    return Path(html_file).stem + ".yaml"


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = read_manifest()

    for index, entry in enumerate(manifest, start=1):
        record = build_record(entry)
        yaml_text = "\n".join(emit_yaml(record_to_dict(record))) + "\n"
        out_path = OUTPUT_ROOT / slug_from_html_path(record.html_file)
        out_path.write_text(yaml_text, encoding="utf-8")
        if index % 50 == 0 or index == len(manifest):
            print(f"wrote {index}/{len(manifest)} yaml files")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
