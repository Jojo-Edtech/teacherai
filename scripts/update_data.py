#!/usr/bin/env python3
"""Fetch Hong Kong AI education sources and write docs/data/content.json."""

from __future__ import annotations

import datetime as dt
import email.utils
import hashlib
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "docs" / "data" / "content.json"

USER_AGENT = "hk-ai-edu-monitor/0.1 (+research summary; contact: GitHub Pages)"

RSS_SOURCES = [
    ("香港教育局 EDB", "http://www.edb.gov.hk/tc/press_release_rss.xml"),
    ("香港教育局 EDB", "http://www.edb.gov.hk/tc/whats_new_rss.xml"),
    ("News.gov.hk", "https://www.news.gov.hk/tc/categories/school_work/html/articlelist.rss.xml"),
]

HTML_SOURCES = [
    ("EdCity 最新消息", "https://www.edcity.hk/home/zh-hant/whatsnew/"),
    ("EdCity AIED", "https://web.edcity.hk/zh-hant/aied/home/"),
    ("EdCity Teacher", "https://teacher.edcity.hk/en/"),
]

GOOGLE_QUERIES = [
    ("Google News", "香港 AI 教育 OR 人工智能 教育"),
    ("Google News - 香港01", "site:hk01.com 香港 AI 教育 OR 人工智能 教育"),
    ("Google News - TVB", "site:news.tvb.com 香港 AI 教育 OR 人工智能 教育"),
    ("Google News - EdCity", "site:edcity.hk AI 教育 OR 人工智能 教師 培訓"),
    ("Google / LinkedIn发现", "site:linkedin.com/posts 香港 AI 教育 教師 培訓"),
]

AI_KEYWORDS = [
    "人工智能",
    "生成式",
    "genai",
    "大語言",
    "大语言",
    "智能",
    "數字教育",
    "数字教育",
    "教育科技",
    "edtech",
    "steam",
]

EDU_KEYWORDS = [
    "教育",
    "教師",
    "教师",
    "學校",
    "学校",
    "學生",
    "学生",
    "教學",
    "教学",
    "課堂",
    "课堂",
    "培訓",
    "培训",
]

TRAINING_KEYWORDS = ["培訓", "培训", "工作坊", "研討會", "研讨会", "講座", "讲座", "課程", "课程", "專業發展", "报名", "報名"]
TEACHER_CONTEXT_KEYWORDS = ["教師", "教师", "老師", "老师", "校長", "校长", "學校", "学校", "教學", "教学", "教育", "課堂", "课堂", "edcity", "edb", "teacher", "aied"]
POLICY_KEYWORDS = ["政策", "撥款", "拨款", "教育局", "藍圖", "蓝图", "通告", "基金", "qef", "素養", "素养", "資助", "资助"]
EVENT_KEYWORDS = ["活動", "活动", "研討會", "研讨会", "工作坊", "講座", "讲座", "展覽", "展览", "峰會", "峰会", "報名", "报名"]

GENERIC_TITLES = {
    "主頁",
    "主页",
    "返回",
    "立即報名",
    "立即报名",
    ">>按此立即報名",
    ">>按此立即报名",
    "按此",
    "title",
    "facebook",
    "linkedin",
    "youtube",
    "電郵",
    "电邮",
}


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._href: Optional[str] = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag.lower() == "a":
            attrs_dict = dict(attrs)
            href = attrs_dict.get("href")
            if href:
                self._href = href
                self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            text = clean_text(" ".join(self._text))
            if text:
                self.links.append({"title": text, "url": self._href})
            self._href = None
            self._text = []


def main() -> int:
    previous = load_previous()
    items: list[dict] = []

    for source, url in RSS_SOURCES:
        items.extend(fetch_rss(source, url))
        time.sleep(0.4)

    for source, url in HTML_SOURCES:
        items.extend(fetch_html_links(source, url))
        time.sleep(0.4)

    for source, query in GOOGLE_QUERIES:
        items.extend(fetch_google_news(source, query))
        time.sleep(0.4)

    relevant = [enrich(item) for item in items if is_quality(item) and is_relevant(item)]
    merged = merge_previous(relevant, previous)
    data = build_payload(merged)

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {DATA_PATH} with {len(merged)} unique records")
    return 0


def load_previous() -> dict:
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return {"training": [], "news": [], "policies": [], "events": [], "discoveries": []}


def fetch_url(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def fetch_rss(source: str, url: str) -> list[dict]:
    try:
        raw = fetch_url(url)
        root = ET.fromstring(raw)
    except Exception as exc:
        print(f"RSS failed: {source} {url}: {exc}", file=sys.stderr)
        return []

    records = []
    for item in root.findall(".//item"):
        title = text_of(item, "title")
        link = text_of(item, "link")
        summary = clean_text(text_of(item, "description"))
        date = parse_date(text_of(item, "pubDate") or text_of(item, "date"))
        if title and link:
            records.append(base_item(source, title, link, date, summary))
    return records


def fetch_html_links(source: str, url: str) -> list[dict]:
    try:
        raw = fetch_url(url).decode("utf-8", errors="ignore")
    except Exception as exc:
        print(f"HTML failed: {source} {url}: {exc}", file=sys.stderr)
        return []

    parser = LinkParser()
    parser.feed(raw)
    records = []
    for link in parser.links:
        absolute = urllib.parse.urljoin(url, link["url"])
        title = link["title"]
        if len(title) < 6:
            continue
        records.append(base_item(source, title, absolute, extract_date(raw) or today_iso(), title))
    return records[:80]


def fetch_google_news(source: str, query: str) -> list[dict]:
    params = urllib.parse.urlencode({"q": query, "hl": "zh-HK", "gl": "HK", "ceid": "HK:zh-Hant"})
    url = f"https://news.google.com/rss/search?{params}"
    return fetch_rss(source, url)


def base_item(source: str, title: str, url: str, date: str, summary: str) -> dict:
    return {
        "id": stable_id(url or title),
        "title": clean_text(title),
        "source": source,
        "date": date or today_iso(),
        "url": normalize_google_url(url),
        "summary": summarize(summary or title),
    }


def enrich(item: dict) -> dict:
    text = combined_text(item)
    tags = []
    category = "每日新闻"

    has_training = any(keyword in text for keyword in TRAINING_KEYWORDS)
    has_teacher_context = any(keyword in text for keyword in TEACHER_CONTEXT_KEYWORDS)

    if has_training and has_teacher_context:
        category = "教师培训"
        tags.append("教师培训")
    if any(keyword in text for keyword in POLICY_KEYWORDS):
        tags.append("政策")
    if any(keyword in text for keyword in EVENT_KEYWORDS):
        tags.append("活动")
    if "linkedin" in item["source"].lower() or "linkedin.com" in item["url"].lower():
        category = "发现"
        tags.append("LinkedIn")
    elif "google" in item["source"].lower():
        tags.append("Google发现")

    if has_ai_signal(text):
        tags.append("AI教育")
    if "數字教育" in text or "数字教育" in text:
        tags.append("数字教育")
    if "撥款" in text or "拨款" in text or "基金" in text:
        tags.append("拨款")

    if "政策" in tags and category != "发现":
        category = "政策" if not any(keyword in text for keyword in TRAINING_KEYWORDS) else category

    item["category"] = category
    item["tags"] = sorted(set(tags))[:6]
    item["researchValue"] = research_value(item)
    item["teacherResearchUse"] = teacher_research_use(item)
    return item


def build_payload(items: list[dict]) -> dict:
    items = sorted(items, key=lambda item: item.get("date", ""), reverse=True)[:160]
    return {
        "updatedAt": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec="seconds"),
        "training": [item for item in items if item["category"] == "教师培训"][:60],
        "news": [item for item in items if item["category"] == "每日新闻"][:80],
        "policies": [item for item in items if item["category"] == "政策"][:60],
        "events": [item for item in items if item["category"] in {"教师培训", "政策"} or "活动" in item.get("tags", [])][:60],
        "discoveries": [item for item in items if item["category"] == "发现" or "Google发现" in item.get("tags", [])][:60],
    }


def merge_previous(new_items: list[dict], previous: dict) -> list[dict]:
    combined = []
    for key in ["training", "news", "policies", "events", "discoveries"]:
        combined.extend(previous.get(key, []))
    combined.extend(new_items)

    seen: set[str] = set()
    merged: list[dict] = []
    for item in sorted(combined, key=lambda entry: entry.get("date", ""), reverse=True):
        if not is_quality(item) or not is_relevant(item):
            continue
        item = enrich(item)
        signature = item.get("url") or normalize_title(item.get("title", ""))
        if signature in seen:
            continue
        seen.add(signature)
        merged.append(item)
    return merged


def is_relevant(item: dict) -> bool:
    text = combined_text(item)
    if "linkedin.com" in item.get("url", "").lower():
        return has_ai_signal(text) and any(keyword in text for keyword in EDU_KEYWORDS)
    has_ai = has_ai_signal(text)
    has_edu = any(keyword in text for keyword in EDU_KEYWORDS)
    source = item.get("source", "").lower()
    if "edcity" in source or "edb" in source or "news.gov.hk" in source:
        return has_ai or ("數字教育" in text or "数字教育" in text)
    return has_ai and has_edu


def has_ai_signal(text: str) -> bool:
    lowered = text.lower()
    if re.search(r"(?<![a-z])ai(?![a-z])", lowered):
        return True
    return any(keyword in lowered for keyword in AI_KEYWORDS)


def is_quality(item: dict) -> bool:
    title = clean_text(item.get("title", ""))
    normalized = title.strip().lower()
    if len(title) < 6:
        return False
    if "@" in title:
        return False
    if normalized in GENERIC_TITLES:
        return False
    if title.startswith(("<<", ">>")):
        return False
    if re.fullmatch(r"[\W_]+", title):
        return False
    if ("按此" in title or "立即" in title) and len(title) < 16:
        return False
    return True


def research_value(item: dict) -> str:
    if item["category"] == "教师培训":
        return "可作为追踪教师 AI 培训、讲者、主办机构和潜在研究场景的资料。"
    if item["category"] == "政策":
        return "可用于建立香港 AI 教育政策时间线，并分析政策如何影响教师专业发展。"
    if item["category"] == "发现":
        return "这是补充发现线索，适合人工点开核对后再纳入正式资料库。"
    return "可作为香港 AI 教育发展、学校应用和教育科技趋势的新闻线索。"


def teacher_research_use(item: dict) -> str:
    if item["category"] == "教师培训":
        return "适合记录培训对象、活动形式与教师可能面对的 AI 应用议题。"
    if item["category"] == "政策":
        return "适合分析教师培训需求、学校执行压力和 AI 素养框架的形成。"
    return "适合观察教师 AI 使用环境、学校案例和社会讨论如何变化。"


def text_of(node: ET.Element, tag: str) -> str:
    child = node.find(tag)
    return clean_text(child.text if child is not None and child.text else "")


def clean_text(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def summarize(value: str, limit: int = 110) -> str:
    text = clean_text(value)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip("，。；,.; ") + "..."


def combined_text(item: dict) -> str:
    return f"{item.get('title', '')} {item.get('summary', '')} {item.get('source', '')}".lower()


def parse_date(value: str) -> str:
    if not value:
        return today_iso()
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        return parsed.date().isoformat()
    except Exception:
        pass
    match = re.search(r"(20\d{2})[-年/](\d{1,2})[-月/](\d{1,2})", value)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return today_iso()


def extract_date(raw: str) -> Optional[str]:
    match = re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日", raw)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return None


def normalize_google_url(url: str) -> str:
    return url.strip()


def normalize_title(title: str) -> str:
    return re.sub(r"\W+", "", title.lower())


def stable_id(value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
    return f"item-{digest}"


def today_iso() -> str:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date().isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
