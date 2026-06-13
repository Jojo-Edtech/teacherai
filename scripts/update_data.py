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
    ("HKU Education News", "https://web.edu.hku.hk/news"),
    ("HKU Education Events", "https://web.edu.hku.hk/upcoming-events"),
    ("HKU INSTEP", "https://web.edu.hku.hk/about-the-faculty/in-service-teacher-education-programme"),
    ("HKU ALiTE", "https://web.edu.hku.hk/about-the-faculty/academy-for-leadership-in-teacher-education"),
    ("HKU CITE", "https://www.cite.hku.hk/"),
    ("HKU CITE Events", "https://www.cite.hku.hk/event/"),
    ("CUHK Faculty of Education ZH", "https://www.fed.cuhk.edu.hk/zh-hant"),
    ("CUHK Faculty of Education Events", "https://www.fed.cuhk.edu.hk/zh-hant/news/events/"),
    ("CUHK CRI", "https://www.fed.cuhk.edu.hk/cri/"),
    ("CUHK CRI Events", "https://www.fed.cuhk.edu.hk/cri/events/"),
    ("CUHK CLST", "https://clst.fed.cuhk.edu.hk/"),
    ("CUHK CLST AI in Education", "https://clst.fed.cuhk.edu.hk/research/ai-in-education3/"),
    ("CUHK CLST Teacher Training", "https://clst.fed.cuhk.edu.hk/professional-development/"),
    ("CUHK CLEAR", "https://www.cuhk.edu.hk/clear/"),
    ("CUHK CLEAR Professional Development", "https://www.cuhk.edu.hk/clear/pointer/prodev.html"),
    ("EdUHK Events", "https://www.eduhk.hk/en/events"),
    ("EdUHK Learning and Teaching", "https://lt.eduhk.hk/"),
    ("EdUHK AEDI Events", "https://aedi.eduhk.hk/news-and-events/events"),
    ("EdUHK AEDI News", "https://aedi.eduhk.hk/news-and-events/news"),
    ("EdUHK AAPSEF", "https://aapsef.eduhk.hk/"),
    ("CUHK Faculty of Education", "https://www.fed.cuhk.edu.hk/"),
]

EVENT_LISTING_SOURCES = {
    "HKU Education Events",
    "HKU CITE Events",
    "CUHK CRI Events",
    "EdUHK AEDI Events",
    "EdUHK Events",
}

UNIVERSITY_EVENT_SOURCE_TOKENS = [
    "hku education events",
    "hku cite",
    "cuhk faculty of education",
    "cuhk cri",
    "cuhk clst",
    "cuhk clear",
    "eduhk",
    "aedi",
    "aapsef",
    "hkust",
    "hku cetl",
    "cityu",
    "polyu",
    "hkbu",
    "lingnan",
]

CUHK_CARD_LISTING_SOURCES = {
    "CUHK Faculty of Education Events",
    "CUHK Faculty of Education ZH",
}

COURSE_LISTING_SOURCES = {
    "CUHK CLST Teacher Training",
}

COMPACT_CARD_SOURCES = {
    "EdUHK AAPSEF",
}

JOURNAL_SOURCES = [
    {"name": "Computers & Education", "issn": "0360-1315", "homepage": "https://www.sciencedirect.com/journal/computers-and-education"},
    {"name": "Teaching and Teacher Education", "issn": "0742-051X", "homepage": "https://www.sciencedirect.com/journal/teaching-and-teacher-education"},
    {"name": "British Journal of Educational Technology", "issn": "1467-8535", "homepage": "https://bera-journals.onlinelibrary.wiley.com/journal/14678535"},
    {"name": "Educational Technology Research and Development", "issn": "1042-1629", "homepage": "https://link.springer.com/journal/11423"},
    {"name": "Internet and Higher Education", "issn": "1096-7516", "homepage": "https://www.sciencedirect.com/journal/the-internet-and-higher-education"},
    {"name": "Learning and Instruction", "issn": "0959-4752", "homepage": "https://www.sciencedirect.com/journal/learning-and-instruction"},
    {"name": "Journal of Computer Assisted Learning", "issn": "1365-2729", "homepage": "https://bera-journals.onlinelibrary.wiley.com/journal/13652729"},
]

GOOGLE_QUERIES = [
    ("Google News", "香港 AI 教育 OR 人工智能 教育"),
    ("Google News - 香港01", "site:hk01.com 香港 AI 教育 OR 人工智能 教育"),
    ("Google News - TVB", "site:news.tvb.com 香港 AI 教育 OR 人工智能 教育"),
    ("Google News - EDB Teacher Training", "site:edb.gov.hk/tc/teacher 人工智能 教師 培訓 工作坊 研討會"),
    ("Google News - EdCity", "site:edcity.hk AI 教育 OR 人工智能 教師 培訓"),
    ("Google News - HKU Education", "site:web.edu.hku.hk AI education teacher seminar workshop training"),
    ("Google News - CUHK Education", "site:fed.cuhk.edu.hk AI education teacher seminar workshop training"),
    ("Google News - CUHK CRI", "site:fed.cuhk.edu.hk/cri AI education teacher seminar workshop training"),
    ("Google News - CUHK CLST", "site:clst.fed.cuhk.edu.hk AI education teacher seminar workshop training"),
    ("Google News - EdUHK", "site:eduhk.hk AI education teacher seminar workshop training"),
    ("Google News - EdUHK Learning", "site:lt.eduhk.hk AI teaching learning workshop teacher training"),
    ("Google News - EdUHK AEDI", "site:aedi.eduhk.hk AI education teacher seminar workshop training"),
    ("Google News - EdUHK AAPSEF", "site:aapsef.eduhk.hk AI education teacher seminar workshop training"),
    ("Google News - EdUHK AIDCEC", "site:aidcec.eduhk.hk AI education teacher seminar workshop training"),
    ("Google News - HKUST", "site:hkust.edu.hk AI education teacher seminar workshop training"),
    ("Google News - HKU CITE", "site:cite.hku.hk AI education teacher seminar workshop training"),
    ("Google News - HKU CETL", "site:tl.hku.hk AI teaching learning workshop teacher training"),
    ("Google News - CUHK CLEAR", "site:cuhk.edu.hk/clear AI teaching learning workshop teacher training"),
    ("Google News - HKUST CEI", "site:cei.hkust.edu.hk AI teaching learning workshop teacher training"),
    ("Google News - CityU Teaching", "site:cityu.edu.hk AI teaching learning workshop teacher training"),
    ("Google News - PolyU Teaching", "site:polyu.edu.hk AI teaching learning workshop teacher training"),
    ("Google News - HKBU Teaching", "site:hkbu.edu.hk AI teaching learning workshop teacher training"),
    ("Google News - Lingnan Teaching", "site:ln.edu.hk AI teaching learning workshop teacher training"),
]

LINKEDIN_QUERIES = [
    ("LinkedIn 公开线索 - 香港AI教育", "site:linkedin.com/posts 香港 AI 教育 教師 培訓 OR 講座 OR 工作坊"),
    ("LinkedIn 公开线索 - HK AIED", "site:linkedin.com/posts Hong Kong AI education teacher training workshop seminar"),
    ("LinkedIn 公开线索 - EdTech HK", "site:linkedin.com/posts Hong Kong EdTech AI learning teaching"),
]

AI_KEYWORDS = [
    "人工智能",
    "artificial intelligence",
    "生成式",
    "generative ai",
    "chatgpt",
    "machine learning",
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
    "education",
    "教師",
    "教师",
    "teacher",
    "學校",
    "学校",
    "school",
    "學生",
    "学生",
    "student",
    "教學",
    "教学",
    "learning",
    "teaching",
    "課堂",
    "课堂",
    "培訓",
    "培训",
]

MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

TRAINING_KEYWORDS = ["培訓", "培训", "工作坊", "研討會", "研讨会", "講座", "讲座", "論壇", "论坛", "課程", "课程", "專業發展", "报名", "報名", "seminar", "workshop", "webinar", "training", "course", "conference", "forum", "symposium"]
REGISTRATION_KEYWORDS = ["報名", "报名", "登記", "登记", "截止", "register", "registration", "enrol", "enroll", "apply", "application"]
TRUE_TRAINING_CONTEXT_KEYWORDS = ["教師專業發展", "教师专业发展", "teacher professional development", "teacher professional development courses", "professional development programmes for school teachers", "school teachers", "in-service", "instep", "cpd", "aied", "教師培訓", "教师培训", "teacher training"]
TEACHER_CONTEXT_KEYWORDS = ["教師", "教师", "老師", "老师", "校長", "校长", "學校", "学校", "教學", "教学", "課堂", "课堂", "teacher", "teachers", "school teachers", "teacher education", "professional development"]
POLICY_KEYWORDS = ["政策", "撥款", "拨款", "教育局", "藍圖", "蓝图", "通告", "基金", "qef", "素養", "素养", "資助", "资助"]
EVENT_KEYWORDS = ["活動", "活动", "研討會", "研讨会", "工作坊", "講座", "讲座", "展覽", "展览", "峰會", "峰会", "報名", "报名"]

EXCLUDED_TRAINING_URL_PARTS = [
    "/student-parents/parents-related/ebulletin-for-parents/",
    "/sch-admin/admin/about-sch-staff/employmentflexibility/",
    "/sch-admin/sch-management/imc/",
    "/admin/sch-management/imc/",
    "applications.edb.gov.hk/imc",
    "imc.aspx",
]

EXCLUDED_TRAINING_TEXT_KEYWORDS = [
    "家長智net",
    "家长智net",
    "家長講座",
    "家长讲座",
    "親子同行",
    "亲子同行",
    "法團校董會",
    "法团校董会",
    "校董會登記冊",
    "校董会登记册",
    "incorporated management committee",
]

BAD_REGISTRATION_LINK_PARTS = [
    "applications.edb.gov.hk/imc",
    "imc.aspx",
]

BAD_REGISTRATION_TEXT_KEYWORDS = [
    "登記冊",
    "登记册",
    "法團校董會",
    "法团校董会",
    "校董會",
    "校董会",
    "incorporated management committee",
    "school registration",
]

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
    "about",
    "contact",
    "events",
    "faculty",
    "home",
    "members",
    "people",
    "projects",
    "publications",
    "research",
    "staff",
    "team",
    "teacher training",
    "professional development",
    "training",
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
        print(f"读取 RSS：{source}", file=sys.stderr)
        items.extend(fetch_rss(source, url))
        time.sleep(0.4)

    for source, url in HTML_SOURCES:
        print(f"读取网页：{source}", file=sys.stderr)
        items.extend(fetch_html_links(source, url))
        time.sleep(0.4)

    for source, query in GOOGLE_QUERIES:
        print(f"读取 Google 线索：{source}", file=sys.stderr)
        items.extend(fetch_google_news(source, query))
        time.sleep(0.4)

    for source, query in LINKEDIN_QUERIES:
        print(f"读取 LinkedIn 公开线索：{source}", file=sys.stderr)
        items.extend(fetch_google_news(source, query))
        time.sleep(0.4)
    items.extend(build_linkedin_shortcuts())

    for journal in JOURNAL_SOURCES:
        print(f"读取顶刊文章：{journal['name']}", file=sys.stderr)
        items.extend(fetch_crossref_journal(journal))
        time.sleep(0.4)

    relevant = [enrich(item) for item in items if is_quality(item) and is_relevant(item)]
    merged = merge_previous(relevant, previous)
    merged = fill_missing_images(merged)
    merged = [enrich(item) for item in merged]
    data = build_payload(merged)

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {DATA_PATH} with {len(merged)} unique records")
    return 0


def load_previous() -> dict:
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return {"training": [], "news": [], "policies": [], "events": [], "discoveries": [], "linkedin": [], "journals": []}


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
        raw_summary = text_of(item, "description")
        summary = clean_text(raw_summary)
        date = parse_date(text_of(item, "pubDate") or text_of(item, "date"))
        image = extract_rss_image(item, raw_summary, link)
        if title and link:
            records.append(base_item(source, title, link, date, summary, image))
    return records


def fetch_html_links(source: str, url: str) -> list[dict]:
    try:
        raw = fetch_url(url).decode("utf-8", errors="ignore")
    except Exception as exc:
        print(f"HTML failed: {source} {url}: {exc}", file=sys.stderr)
        return []

    if source in EVENT_LISTING_SOURCES:
        return fetch_event_listing(source, url, raw)
    if source in CUHK_CARD_LISTING_SOURCES:
        return fetch_cuhk_card_listing(source, url, raw)
    if source in COURSE_LISTING_SOURCES:
        return fetch_course_listing(source, url, raw)
    if source in COMPACT_CARD_SOURCES:
        return fetch_compact_card_listing(source, url, raw)

    parser = LinkParser()
    parser.feed(raw)
    records = []
    for link in parser.links:
        absolute = urllib.parse.urljoin(url, link["url"])
        title = link["title"]
        if len(title) < 6:
            continue
        item_date = extract_date(title) or extract_date(raw) or today_iso()
        records.append(base_item(source, title, absolute, item_date, title))
    return records[:80]


def fetch_event_listing(source: str, url: str, raw: str) -> list[dict]:
    parser = LinkParser()
    parser.feed(raw)
    full_text = clean_text(raw)
    records = []
    links = [
        {"title": link["title"], "url": urllib.parse.urljoin(url, link["url"])}
        for link in parser.links
    ]

    for index, link in enumerate(links):
        title = clean_text(link["title"])
        if not is_event_title(title):
            continue
        position = full_text.lower().find(title.lower())
        if position < 0:
            continue
        window = full_text[max(0, position - 140):position + 900]
        event_date = extract_event_date(window) or extract_date(window) or ""
        event_time = extract_event_time(window)
        register_url = find_registration_url(links[index + 1:index + 8])
        if not event_date:
            continue
        item = base_item(source, title, link["url"], event_date, window[:220])
        item["eventDate"] = event_date
        item["date"] = event_date
        if event_time:
            item["eventTime"] = event_time
        if register_url:
            item["registerUrl"] = register_url
        records.append(item)

    return records[:80]


def fetch_cuhk_card_listing(source: str, url: str, raw: str) -> list[dict]:
    parser = LinkParser()
    parser.feed(raw)
    lines = text_lines(raw)
    learn_more_links = [
        urllib.parse.urljoin(url, link["url"])
        for link in parser.links
        if "了解更多" in link["title"] or "learn more" in link["title"].lower()
    ]
    records = []
    learn_index = 0

    for index, line in enumerate(lines):
        item_date = extract_date(line)
        if not item_date:
            continue

        title = ""
        for candidate in reversed(lines[max(0, index - 5):index]):
            if is_listing_title(candidate):
                title = candidate
                break
        if not title:
            continue

        link_url = find_link_by_title(parser.links, title, url)
        if not link_url and learn_index < len(learn_more_links):
            link_url = learn_more_links[learn_index]
            learn_index += 1
        if not link_url:
            link_url = url

        summary = " ".join(lines[index:index + 5])[:240] or title
        item = base_item(source, title, link_url, item_date, summary)
        item["eventDate"] = item_date
        item["date"] = item_date
        records.append(item)

    return records[:80]


def fetch_course_listing(source: str, url: str, raw: str) -> list[dict]:
    records = []
    lines = text_lines(raw)
    for index, line in enumerate(lines):
        period_match = re.search(r"\b(20\d{2})\s*[-–]\s*(20\d{2})\b", line)
        if not period_match:
            continue
        period = f"{period_match.group(1)}-{period_match.group(2)}"
        title = clean_text(line[:period_match.start()])
        if not is_listing_title(title):
            title = ""
            for candidate in reversed(lines[max(0, index - 6):index]):
                if is_listing_title(candidate):
                    title = candidate
                    break
        if not is_listing_title(title):
            continue
        item_url = f"{url}#course-{stable_id(title)}"
        item_date = period_start_date(period) or today_iso()
        item = base_item(source, title, item_url, item_date, f"{title}（课程周期：{period}）")
        item["period"] = period
        item["date"] = item_date
        records.append(item)
    return records[:80]


def fetch_compact_card_listing(source: str, url: str, raw: str) -> list[dict]:
    parser = LinkParser()
    parser.feed(raw)
    records = []
    for link in parser.links:
        title = clean_text(link["title"])
        if not is_listing_title(title):
            continue
        item_date = extract_date(title)
        if not item_date:
            continue
        title_without_date = clean_text(re.sub(r"^\d{1,2}\s+[A-Za-z]{3,9}\s+20\d{2}\s*", "", title))
        title_without_date = clean_text(re.sub(r"^20\d{2}[-年/]\d{1,2}[-月/]\d{1,2}\s*", "", title_without_date))
        if not is_listing_title(title_without_date):
            continue
        item = base_item(source, title_without_date, urllib.parse.urljoin(url, link["url"]), item_date, title)
        item["eventDate"] = item_date
        item["date"] = item_date
        records.append(item)
    return records[:80]


def is_event_title(title: str) -> bool:
    lowered = title.lower()
    if len(title) < 8:
        return False
    blocked = ["image", "download poster", "registration", "register now", "learn more", "next", "previous", "home", "search", "reset", "go"]
    if any(blocked_text == lowered or lowered.startswith(blocked_text) for blocked_text in blocked):
        return False
    if lowered in {value.lower() for value in GENERIC_TITLES}:
        return False
    return True


def is_listing_title(value: str) -> bool:
    title = clean_text(value)
    lowered = title.lower()
    if len(title) < 8:
        return False
    if lowered in {value.lower() for value in GENERIC_TITLES}:
        return False
    blocked = [
        "latest news",
        "最新院訊",
        "院訊",
        "即將舉行",
        "最新消息",
        "活動回顧",
        "course title period",
        "funded by edb",
        "events details",
        "news details",
        "gallery details",
        "download poster",
        "registration",
        "learn more",
        "了解更多",
        "view all",
        "all events",
        "all news",
        "filter by",
    ]
    if any(token in lowered for token in blocked):
        return False
    if lowered in {"search", "reset", "dropdown"}:
        return False
    if extract_date(title) == title:
        return False
    if re.fullmatch(r"[\d\s:/.,-]+", title):
        return False
    return True


def find_link_by_title(links: list[dict[str, str]], title: str, page_url: str) -> str:
    normalized = normalize_title(title)
    for link in links:
        link_title = normalize_title(link["title"])
        if normalized and (normalized in link_title or link_title in normalized):
            return urllib.parse.urljoin(page_url, link["url"])
    return ""


def find_registration_url(links: list[dict[str, str]]) -> str:
    for link in links:
        if is_registration_link(link["title"], link["url"]):
            return link["url"]
    return ""


def fetch_google_news(source: str, query: str) -> list[dict]:
    params = urllib.parse.urlencode({"q": query, "hl": "zh-HK", "gl": "HK", "ceid": "HK:zh-Hant"})
    url = f"https://news.google.com/rss/search?{params}"
    return fetch_rss(source, url)


def build_linkedin_shortcuts() -> list[dict]:
    shortcuts = []
    for source, query in LINKEDIN_QUERIES:
        search_url = "https://www.google.com/search?" + urllib.parse.urlencode({"q": query})
        title = source.replace("LinkedIn 公开线索 - ", "LinkedIn 搜索入口：")
        item = base_item("LinkedIn 搜索入口", title, search_url, today_iso(), f"打开 Google 搜索，查看 LinkedIn 上与 {title} 相关的公开线索。")
        item["kind"] = "linkedin-shortcut"
        shortcuts.append(item)
    return shortcuts


def fetch_crossref_journal(journal: dict[str, str]) -> list[dict]:
    date_from = (dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date() - dt.timedelta(days=120)).isoformat()
    params = urllib.parse.urlencode({
        "filter": f"from-pub-date:{date_from},type:journal-article",
        "sort": "published",
        "order": "desc",
        "rows": "12",
        "select": "DOI,title,URL,published-print,published-online,issued,container-title,abstract,author,type,created",
    })
    url = f"https://api.crossref.org/journals/{urllib.parse.quote(journal['issn'])}/works?{params}"
    try:
        payload = json.loads(fetch_url(url).decode("utf-8", errors="ignore"))
    except Exception as exc:
        print(f"Journal failed: {journal['name']} {journal['issn']}: {exc}", file=sys.stderr)
        return []

    records = []
    for work in payload.get("message", {}).get("items", []):
        title = clean_text(" ".join(work.get("title") or []))
        if not title:
            continue
        doi = clean_text(work.get("DOI", ""))
        article_url = work.get("URL") or (f"https://doi.org/{doi}" if doi else journal["homepage"])
        date = crossref_date(work) or today_iso()
        abstract = summarize(clean_text(work.get("abstract", "")), 180)
        authors = format_authors(work.get("author", []))
        summary = abstract or (f"作者：{authors}" if authors else f"{journal['name']} 最新文章。")
        item = base_item(f"顶刊：{journal['name']}", title, article_url, date, summary)
        item["kind"] = "journal"
        item["journal"] = journal["name"]
        item["issn"] = journal["issn"]
        item["doi"] = doi
        item["authors"] = authors
        item["publishedDate"] = date
        if abstract:
            item["abstract"] = abstract
        records.append(item)
    return records


def crossref_date(work: dict) -> str:
    for key in ["published-online", "published-print", "issued", "created"]:
        date_parts = work.get(key, {}).get("date-parts")
        if not date_parts:
            continue
        parts = date_parts[0]
        if not parts:
            continue
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        try:
            return dt.date(year, month, day).isoformat()
        except ValueError:
            continue
    return ""


def format_authors(authors: list[dict]) -> str:
    names = []
    for author in authors[:3]:
        name = clean_text(" ".join([author.get("given", ""), author.get("family", "")]))
        if name:
            names.append(name)
    if not names:
        return ""
    suffix = " et al." if len(authors) > 3 else ""
    return ", ".join(names) + suffix


def base_item(source: str, title: str, url: str, date: str, summary: str, image: str = "") -> dict:
    normalized_url = normalize_google_url(url)
    item = {
        "id": stable_id(canonical_url(normalized_url) or title),
        "title": clean_text(title),
        "source": source,
        "date": date or today_iso(),
        "publishedDate": date or today_iso(),
        "url": normalized_url,
        "summary": summarize(summary or title),
    }
    if image:
        item["image"] = image
    return item


def extract_rss_image(item: ET.Element, raw_summary: str, link: str) -> str:
    for node in item.iter():
        tag = node.tag.lower()
        if tag.endswith("thumbnail") or tag.endswith("content"):
            url = node.attrib.get("url", "")
            medium = node.attrib.get("medium", "")
            content_type = node.attrib.get("type", "")
            if url and ("image" in medium or "image" in content_type or tag.endswith("thumbnail")):
                return urllib.parse.urljoin(link, url)
        if tag.endswith("enclosure"):
            url = node.attrib.get("url", "")
            content_type = node.attrib.get("type", "")
            if url and "image" in content_type:
                return urllib.parse.urljoin(link, url)

    match = re.search(r"<img[^>]+src=[\"']([^\"']+)[\"']", raw_summary or "", re.IGNORECASE)
    if match:
        return urllib.parse.urljoin(link, html.unescape(match.group(1)))
    return ""


def enrich(item: dict) -> dict:
    sanitize_item(item)
    text = combined_text(item)
    tags = []
    category = "每日新闻"

    if item.get("kind") == "journal":
        category = "顶刊文章"
        tags.extend(["SSCI", "顶刊文章"])
    elif is_training_candidate(item):
        category = "教师培训"
        tags.append("AI培训与讲座")
        if not item.get("eventDate") and item.get("date") and is_university_event_source_name(item.get("source", "")):
            item["eventDate"] = item.get("date", "")
    if any(keyword in text for keyword in POLICY_KEYWORDS):
        tags.append("政策")
    if any(keyword in text for keyword in EVENT_KEYWORDS):
        tags.append("活动")
    if "linkedin" in item["source"].lower() or "linkedin.com" in item["url"].lower() or item.get("kind") == "linkedin-shortcut":
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

    if "政策" in tags and category not in {"发现", "教师培训", "顶刊文章"}:
        category = "政策"

    item["category"] = category
    item["tags"] = sorted(set(tags))[:6]
    item["researchValue"] = research_value(item)
    item["teacherResearchUse"] = teacher_research_use(item)
    return item


def build_payload(items: list[dict]) -> dict:
    news = sorted([item for item in items if item["category"] == "每日新闻"], key=news_sort_key, reverse=True)
    training = sorted([item for item in items if item["category"] == "教师培训"], key=training_sort_key)
    policies = sorted([item for item in items if item["category"] == "政策"], key=news_sort_key, reverse=True)
    linkedin = sorted([item for item in items if "LinkedIn" in item.get("tags", [])], key=news_sort_key, reverse=True)
    journals = sorted([item for item in items if item["category"] == "顶刊文章"], key=news_sort_key, reverse=True)
    discoveries = sorted(
        [
            item
            for item in items
            if item["category"] == "发现" and "LinkedIn" not in item.get("tags", [])
        ],
        key=news_sort_key,
        reverse=True,
    )
    return {
        "updatedAt": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec="seconds"),
        "training": training[:60],
        "news": news[:80],
        "policies": policies[:60],
        "events": [],
        "discoveries": discoveries[:60],
        "linkedin": linkedin[:60],
        "journals": journals[:100],
    }


def merge_previous(new_items: list[dict], previous: dict) -> list[dict]:
    combined = []
    for key in ["training", "news", "policies", "events", "discoveries", "linkedin", "journals"]:
        combined.extend(previous.get(key, []))
    combined.extend(new_items)

    seen: set[str] = set()
    merged: list[dict] = []
    for item in sorted(combined, key=lambda entry: entry.get("date", ""), reverse=True):
        if not is_quality(item) or not is_relevant(item):
            continue
        item = enrich(item)
        signature = item_signature(item)
        if signature in seen:
            continue
        seen.add(signature)
        merged.append(item)
    return merged


def fill_missing_images(items: list[dict]) -> list[dict]:
    checked = 0
    for item in items:
        if checked >= 80:
            break
        url = item.get("url", "")
        if not should_fetch_page_details(item):
            continue
        checked += 1
        details = fetch_page_details(url)
        for key, value in details.items():
            if value and (key != "image" or not item.get("image")):
                item[key] = value
        if item.get("eventDate") or item.get("deadlineDate"):
            item["date"] = item.get("deadlineDate") or item.get("eventDate") or item.get("date")
        elif item.get("period"):
            item["date"] = period_start_date(item.get("period", "")) or item.get("date")
        time.sleep(0.2)
    return items


def should_fetch_page_details(item: dict) -> bool:
    url = item.get("url", "").lower()
    source = item.get("source", "").lower()
    if not url.startswith("http"):
        return False
    if "news.google.com" in url or "linkedin.com" in url:
        return False
    return any(token in url or token in source for token in [
        "edcity",
        "edb.gov.hk",
        "news.gov.hk",
        "hk01",
        "tvb",
        "web.edu.hku.hk",
        "cite.hku.hk",
        "fed.cuhk.edu.hk",
        "clst.fed.cuhk.edu.hk",
        "cuhk.edu.hk/clear",
        "eduhk",
        "lt.eduhk.hk",
        "aedi.eduhk.hk",
        "aapsef.eduhk.hk",
        "hkust",
        "cityu.edu.hk",
        "polyu.edu.hk",
        "hkbu.edu.hk",
        "ln.edu.hk",
    ])


def fetch_page_details(url: str) -> dict[str, str]:
    try:
        raw = fetch_url(url).decode("utf-8", errors="ignore")
    except Exception:
        return {}
    text = clean_text(raw)
    image = extract_meta_image(raw) or extract_first_image(raw)
    details = {
        "image": urllib.parse.urljoin(url, image) if image else "",
        "publishedDate": extract_published_date(raw) or extract_date(text),
        "eventDate": extract_event_date(text),
        "deadlineDate": extract_deadline_date(text),
        "period": extract_period(text),
        "eventTime": extract_event_time(text),
        "registerUrl": extract_registration_url(raw, url),
    }
    return {key: value for key, value in details.items() if value}


def extract_meta_image(raw: str) -> str:
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            return html.unescape(match.group(1))
    return ""


def extract_first_image(raw: str) -> str:
    for match in re.finditer(r"<img[^>]+src=[\"']([^\"']+)[\"']", raw or "", re.IGNORECASE):
        src = html.unescape(match.group(1))
        lowered = src.lower()
        if not src.startswith("data:") and not is_bad_image_url(lowered):
            return src
    return ""


def extract_registration_url(raw: str, page_url: str) -> str:
    parser = LinkParser()
    parser.feed(raw)
    for link in parser.links:
        href = link["url"]
        if is_registration_link(link["title"], href):
            return urllib.parse.urljoin(page_url, href)
    return ""


def sanitize_item(item: dict) -> None:
    register_url = item.get("registerUrl", "")
    if register_url and not is_registration_link("register", register_url):
        item.pop("registerUrl", None)
    image = item.get("image", "")
    if image and is_bad_image_url(image.lower()):
        item.pop("image", None)


def is_registration_link(title: str, href: str) -> bool:
    lowered_title = clean_text(title).lower()
    lowered_href = (href or "").lower()
    if any(part in lowered_href for part in BAD_REGISTRATION_LINK_PARTS):
        return False
    if any(keyword in lowered_title for keyword in BAD_REGISTRATION_TEXT_KEYWORDS):
        return False
    return any(keyword in lowered_title or keyword in lowered_href for keyword in [
        "報名",
        "报名",
        "register",
        "registration",
        "enrol",
        "enroll",
        "apply",
        "application",
    ])


def is_bad_image_url(value: str) -> bool:
    return any(token in value for token in ["logo", "icon", "sprite", "search_grey", "search.svg", "print", "share"])


def is_training_candidate(item: dict) -> bool:
    text = combined_text(item)
    source = item.get("source", "").lower()
    has_ai = has_ai_signal(text)
    has_event = any(keyword in text for keyword in TRAINING_KEYWORDS)
    has_teacher_context = any(keyword in text for keyword in TEACHER_CONTEXT_KEYWORDS)
    has_registration = has_valid_registration(item) or any(keyword in text for keyword in REGISTRATION_KEYWORDS)
    has_true_training_context = any(keyword in text for keyword in TRUE_TRAINING_CONTEXT_KEYWORDS)
    has_event_date = bool(item.get("eventDate") or item.get("deadlineDate") or item.get("period"))
    is_known_teacher_source = any(token in source for token in [
        "edcity teacher",
        "edcity aied",
        "hku instep",
        "hku alite",
        "cuhk clst teacher training",
    ])
    is_university_event_source = is_university_event_source_name(source)

    if is_excluded_training_item(item):
        return False
    if not has_ai:
        return False
    if is_known_teacher_source and has_event and (has_event_date or has_registration or has_true_training_context):
        return True
    if has_true_training_context and has_event and (has_event_date or has_registration):
        return True
    if has_registration and has_event and has_teacher_context:
        return True
    if is_university_event_source and has_event and has_ai and (has_event_date or item.get("date") or item.get("publishedDate")):
        return True
    if is_university_event_source and has_event and has_event_date and has_ai:
        return True
    if is_university_event_source and has_event and has_event_date and (has_registration or has_teacher_context):
        return True
    return False


def is_university_event_source_name(source: str) -> bool:
    lowered = (source or "").lower()
    return any(token in lowered for token in UNIVERSITY_EVENT_SOURCE_TOKENS)


def has_valid_registration(item: dict) -> bool:
    register_url = item.get("registerUrl", "")
    return bool(register_url and is_registration_link("register", register_url))


def is_excluded_training_item(item: dict) -> bool:
    text = combined_text(item)
    url = item.get("url", "").lower()
    register_url = item.get("registerUrl", "").lower()
    if any(part in url or part in register_url for part in EXCLUDED_TRAINING_URL_PARTS):
        return True
    return any(keyword in text for keyword in EXCLUDED_TRAINING_TEXT_KEYWORDS)


def news_sort_key(item: dict) -> str:
    return item.get("publishedDate") or item.get("date") or ""


def training_sort_key(item: dict) -> tuple[int, str]:
    candidate = item.get("deadlineDate") or item.get("eventDate") or period_end_date(item.get("period", ""))
    if not candidate:
        return (1, "")
    today = today_iso()
    return (0 if candidate >= today else 2, candidate)


def is_relevant(item: dict) -> bool:
    text = combined_text(item)
    if item.get("kind") in {"journal", "linkedin-shortcut"}:
        return True
    if "linkedin.com" in item.get("url", "").lower():
        return has_ai_signal(text) and any(keyword in text for keyword in EDU_KEYWORDS)
    has_ai = has_ai_signal(text)
    has_edu = any(keyword in text for keyword in EDU_KEYWORDS)
    source = item.get("source", "").lower()
    if any(token in source for token in [
        "edcity",
        "edb",
        "news.gov.hk",
        "hku education",
        "hku cite",
        "cuhk faculty",
        "cuhk cri",
        "cuhk clst",
        "cuhk clear",
        "eduhk",
        "aedi",
        "aapsef",
        "hkust",
    ]):
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
    if item["category"] == "顶刊文章":
        return "可用于追踪教育技术、教师教育与学习科学顶刊的新研究，并筛选与 AI 教育相关的论文。"
    if item["category"] == "教师培训":
        return "可作为追踪 AI 培训、讲者、主办机构、大学公开讲座和潜在研究现场的资料。"
    if item["category"] == "政策":
        return "可用于建立香港 AI 教育政策时间线，并分析政策如何影响教师专业发展。"
    if item["category"] == "发现":
        return "这是补充发现线索，适合人工点开核对后再纳入正式资料库。"
    return "可作为香港 AI 教育发展、学校应用和教育科技趋势的新闻线索。"


def teacher_research_use(item: dict) -> str:
    if item["category"] == "顶刊文章":
        return "适合为教师 AI 研究补充理论、方法、量表、实验设计和文献综述线索。"
    if item["category"] == "教师培训":
        return "适合记录活动对象、活动形式、AI应用议题，以及可联系或观察的研究场景。"
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


def text_lines(raw: str) -> list[str]:
    text = html.unescape(raw or "")
    text = re.sub(r"<\s*br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</\s*(?:p|div|li|tr|td|th|h[1-6]|article|section|a)\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    lines = []
    for line in text.splitlines():
        cleaned = clean_text(line)
        if cleaned:
            lines.append(cleaned)
    return lines


def summarize(value: str, limit: int = 110) -> str:
    text = clean_text(value)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip("，。；,.; ") + "..."


def combined_text(item: dict) -> str:
    return " ".join([
        item.get("title", ""),
        item.get("summary", ""),
        item.get("source", ""),
        item.get("url", ""),
        item.get("eventDate", ""),
        item.get("deadlineDate", ""),
        item.get("eventTime", ""),
        item.get("period", ""),
        item.get("journal", ""),
        item.get("doi", ""),
        item.get("authors", ""),
        item.get("abstract", ""),
    ]).lower()


def parse_date(value: str) -> str:
    if not value:
        return today_iso()
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        return parsed.date().isoformat()
    except Exception:
        pass
    match = re.search(r"(20\d{2})\s*[-年/]\s*(\d{1,2})\s*[-月/]\s*(\d{1,2})", value)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    extracted = extract_date(value)
    if extracted:
        return extracted
    return today_iso()


def extract_date(raw: str) -> Optional[str]:
    value = clean_text(raw)
    match = re.search(r"(20\d{2})\s*[-年/]\s*(\d{1,2})\s*[-月/]\s*(\d{1,2})", value)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    match = re.search(r"\b([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(20\d{2})\b", value)
    if match:
        month_name, day, year = match.groups()
        month = MONTHS.get(month_name.lower())
        if month:
            return f"{int(year):04d}-{month:02d}-{int(day):02d}"
    match = re.search(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\s+(20\d{2})\b", value)
    if match:
        day, month_name, year = match.groups()
        month = MONTHS.get(month_name.lower())
        if month:
            return f"{int(year):04d}-{month:02d}-{int(day):02d}"
    return None


def extract_published_date(raw: str) -> str:
    patterns = [
        r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']date["\'][^>]+content=["\']([^"\']+)["\']',
        r'"datePublished"\s*:\s*"([^"]+)"',
        r'"dateCreated"\s*:\s*"([^"]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            parsed = parse_date(match.group(1))
            if parsed:
                return parsed
    return ""


def extract_event_date(text: str) -> str:
    patterns = [
        r"Event date\s+([A-Za-z]{3,9}\s+\d{1,2},?\s+20\d{2})",
        r"活動日期[:：]?\s*(20\d{2}[年/-]\d{1,2}[月/-]\d{1,2})",
        r"活动日期[:：]?\s*(20\d{2}[年/-]\d{1,2}[月/-]\d{1,2})",
        r"日期[:：]?\s*(20\d{2}[年/-]\d{1,2}[月/-]\d{1,2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date = extract_date(match.group(1))
            if date:
                return date
    return ""


def extract_deadline_date(text: str) -> str:
    patterns = [
        r"(?:報名截止|报名截止|截止報名|截止报名|截止日期|申請截止|申请截止)[:：]?\s*([^。；;\n]{0,50})",
        r"(?:registration deadline|application deadline|deadline)[:：]?\s*([^.;\n]{0,70})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date = extract_date(match.group(1))
            if date:
                return date
    return ""


def extract_period(text: str) -> str:
    value = clean_text(text)
    match = re.search(r"\b(20\d{2})\s*[-–]\s*(20\d{2})\b", value)
    if match:
        window = value[max(0, match.start() - 120):match.end() + 120].lower()
        if not any(keyword in window for keyword in [
            "course",
            "programme",
            "program",
            "professional development",
            "training",
            "teacher",
            "school teachers",
            "課程",
            "课程",
            "培訓",
            "培训",
            "教師專業發展",
            "教师专业发展",
        ]):
            return ""
        return f"{match.group(1)}-{match.group(2)}"
    return ""


def period_start_date(period: str) -> str:
    match = re.match(r"(20\d{2})-20\d{2}", period or "")
    if match:
        return f"{int(match.group(1)):04d}-01-01"
    return ""


def period_end_date(period: str) -> str:
    match = re.match(r"20\d{2}-(20\d{2})", period or "")
    if match:
        return f"{int(match.group(1)):04d}-12-31"
    return ""


def extract_event_time(text: str) -> str:
    match = re.search(r"Event time\s+([0-9:\sAPMapm.-]+)", text)
    if match:
        return clean_text(match.group(1))[:40]
    match = re.search(r"(?:時間|时间)[:：]?\s*([0-9:\sAPMapm上午下午至到.-]+)", text)
    if match:
        return clean_text(match.group(1))[:40]
    return ""


def normalize_google_url(url: str) -> str:
    return url.strip()


def canonical_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""

    parsed = urllib.parse.urlsplit(raw)
    if not parsed.scheme or not parsed.netloc:
        return raw.split("#", 1)[0].rstrip("/").lower()

    query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    filtered_query = [
        (key, value)
        for key, value in query_pairs
        if key.lower()
        not in {
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "fbclid",
            "gclid",
        }
    ]
    query = urllib.parse.urlencode(filtered_query, doseq=True)
    path = parsed.path.rstrip("/").lower()
    return urllib.parse.urlunsplit(("", parsed.netloc.lower(), path, query, ""))


def normalize_doi(doi: str) -> str:
    value = (doi or "").strip().lower()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value)
    value = re.sub(r"^doi:\s*", "", value)
    return value


def item_signature(item: dict) -> str:
    doi = normalize_doi(item.get("doi", ""))
    if doi:
        return f"doi:{doi}"

    url = canonical_url(item.get("url", ""))
    if url:
        return f"url:{url}"

    title = normalize_title(item.get("title", ""))
    source = normalize_title(item.get("source", ""))
    return f"title:{title}:source:{source}"


def normalize_title(title: str) -> str:
    return re.sub(r"\W+", "", title.lower())


def stable_id(value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
    return f"item-{digest}"


def today_iso() -> str:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date().isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
