"""
Riftbound(playriftbound.com) 한국어 새 소식 페이지를 확인해서
새로 올라온 글이 있으면 디스코드 웹훅으로 전송하는 스크립트.

GitHub Actions에서 주기적으로(예: 15분마다) 실행되도록 설계되었습니다.
- 이미 본 글의 URL은 data/seen_news.json 에 저장해 중복 알림을 막습니다.
- 스크립트를 처음 실행할 때는 기존 글들을 모두 "본 것"으로 기록만 하고
  디스코드에는 올리지 않습니다. (처음부터 과거 글이 우르르 올라오는 걸 방지)
"""

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

NEWS_URL = "https://playriftbound.com/ko-kr/news/"
BASE_URL = "https://playriftbound.com"
SEEN_FILE = Path(__file__).resolve().parent.parent / "data" / "seen_news.json"
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
TEST_LATEST = os.environ.get("TEST_LATEST", "false").lower() == "true"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 RiftboundNewsBot/1.0"
    )
}


def load_seen() -> set:
    if SEEN_FILE.exists():
        try:
            return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))
        except Exception:
            return set()
    return set()


def save_seen(seen: set) -> None:
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    # 파일이 무한정 커지지 않도록 최근 300개만 유지
    trimmed = list(seen)[-300:]
    SEEN_FILE.write_text(
        json.dumps(trimmed, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fetch_news_items():
    resp = requests.get(NEWS_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = []
    seen_urls = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/news/" not in href:
            continue
        if href.rstrip("/").endswith("/news"):
            continue  # 목록 페이지 자체로 가는 링크는 제외

        full_url = urljoin(BASE_URL, href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        title, description, date_text = _extract_fields(a)
        if not title:
            continue

        items.append(
            {
                "url": full_url,
                "title": title,
                "description": description,
                "date": date_text,
            }
        )

    return items


def _extract_fields(a_tag):
    # 1) 우선 구조화된 태그(제목 헤딩, time 태그)로 추출을 시도
    time_tag = a_tag.find("time")
    date_text = time_tag.get("datetime") if time_tag else None

    heading = a_tag.find(["h1", "h2", "h3", "h4"])
    if heading:
        title = heading.get_text(strip=True)
        if title:
            desc_tag = heading.find_next("p")
            description = desc_tag.get_text(strip=True) if desc_tag else ""
            return title, description, date_text

    # 2) 실패하면, 링크 전체 텍스트에서 ISO 날짜를 기준으로 분리
    #    (예: "공지2026-09-02T16:00:00.000Z9월 18일, ...열립니다설명문")
    raw_text = a_tag.get_text(separator="", strip=True)
    match = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", raw_text)
    if match:
        date_text = date_text or match.group(0)
        remainder = raw_text[match.end():]
    else:
        remainder = raw_text

    return remainder.strip(), "", date_text


def post_to_discord(item):
    if not WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URL 환경변수가 없어 전송을 건너뜁니다.", file=sys.stderr)
        return

    title = item["title"][:250] if item["title"] else "리프트바운드 새 소식"
    description = item["description"][:500] if item["description"] else ""

    payload = {
        "username": "Riftbound 새 소식",
        "embeds": [
            {
                "title": title,
                "url": item["url"],
                "description": description,
                "color": 0x1E90FF,
                "footer": {"text": "playriftbound.com"},
            }
        ],
    }
    resp = requests.post(WEBHOOK_URL, json=payload, timeout=15)
    resp.raise_for_status()


def main():
    first_run = not SEEN_FILE.exists()
    seen = load_seen()
    items = fetch_news_items()

    if not items:
        print(
            "새 소식 페이지에서 글을 찾지 못했습니다. "
            "사이트 구조가 바뀌었을 수 있어요.",
            file=sys.stderr,
        )
        sys.exit(1)

    if TEST_LATEST:
        # 테스트용: seen 목록/첫 실행 여부와 상관없이 가장 최신 글 1개를 강제 전송.
        # seen 목록은 건드리지 않으므로, 실제 자동 감지 흐름에는 영향이 없습니다.
        latest = items[0]
        print(f"[테스트 모드] 최신 글 강제 전송: {latest['title']} ({latest['url']})")
        post_to_discord(latest)
        return

    if first_run:
        print(f"첫 실행 감지: 현재 글 {len(items)}개를 기준선으로 저장만 하고 전송은 하지 않습니다.")
        for item in items:
            seen.add(item["url"])
        save_seen(seen)
        return

    new_items = [item for item in items if item["url"] not in seen]

    if not new_items:
        print("새 글 없음.")
        return

    # 오래된 글부터 순서대로 올려서 디스코드에서 시간순으로 보이게 함
    for item in reversed(new_items):
        print(f"새 글 발견 → 전송: {item['title']} ({item['url']})")
        post_to_discord(item)
        seen.add(item["url"])

    # 현재 페이지에 있는 모든 글을 본 것으로 기록
    for item in items:
        seen.add(item["url"])

    save_seen(seen)


if __name__ == "__main__":
    main()
