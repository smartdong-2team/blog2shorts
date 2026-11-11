
import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


ALLOWED_HOSTS = {"blog.naver.com", "m.blog.naver.com"}

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


class UnsupportedUrlError(ValueError):
    pass


class ExtractionError(Exception):
    pass


# 본문 속 이미지 자리 표시. N은 image_urls 순서(1부터)
IMAGE_MARKER = re.compile(r"\[이미지 (\d+)\]")


def image_marker(number: int) -> str:
    return f"[이미지 {number}]"


@dataclass
class ExtractedContent:
    blog_id: str
    log_no: str
    url: str
    title: str
    text: str
    image_urls: list[str]


def parse_blog_url(url: str) -> tuple[str, str]:
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise UnsupportedUrlError("HTTP(S) URL만 지원합니다.")

    if parsed.hostname not in ALLOWED_HOSTS:
        raise UnsupportedUrlError("네이버 블로그 URL만 지원합니다.")

    parts = parsed.path.strip("/").split("/")
    query = parse_qs(parsed.query)

    if len(parts) == 2 and all(parts):
        blog_id, log_no = parts
    elif parts == ["PostView.naver"]:
        blog_id = query.get("blogId", [""])[0]
        log_no = query.get("logNo", [""])[0]
    else:
        raise UnsupportedUrlError("지원하지 않는 블로그 URL 형식입니다.")

    if not blog_id or not log_no.isdigit():
        raise UnsupportedUrlError("블로그 ID 또는 글 번호가 올바르지 않습니다.")

    return blog_id, log_no


def validate_host(hostname: str) -> None:
    try:
        addresses = socket.getaddrinfo(
            hostname, 443, type=socket.SOCK_STREAM
        )
    except socket.gaierror as exc:
        raise ExtractionError("호스트 주소를 확인할 수 없습니다.") from exc

    if not addresses or any(
        not ipaddress.ip_address(address[4][0]).is_global
        for address in addresses
    ):
        raise ExtractionError("접근할 수 없는 서버 주소입니다.")


def fetch_html(session: requests.Session, url: str) -> BeautifulSoup:
    parsed = urlparse(url)

    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise UnsupportedUrlError("허용되지 않은 요청 주소입니다.")

    validate_host(parsed.hostname)

    response = session.get(
        url,
        timeout=15,
        allow_redirects=False,
    )

    if response.is_redirect:
        raise ExtractionError("리다이렉트된 페이지는 지원하지 않습니다.")

    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def image_url_of(image, base_url: str) -> str | None:
    src = (
        image.get("data-lazy-src")
        or image.get("data-src")
        or image.get("src")
    )

    if not src:
        return None

    image_url = urljoin(base_url, src)
    parsed = urlparse(image_url)

    if parsed.scheme == "https" and parsed.hostname:
        return image_url
    return None


def extract_image_urls(content, base_url: str) -> list[str]:
    urls = [image_url_of(image, base_url) for image in content.select("img")]
    return list(dict.fromkeys(url for url in urls if url))


def mark_image_positions(content, image_urls: list[str], base_url: str) -> None:
    """본문의 <img> 자리를 "[이미지 N]" 글자로 바꿔 글과 이미지 순서를 남긴다."""
    numbers = {url: index + 1 for index, url in enumerate(image_urls)}

    for image in content.select("img"):
        number = numbers.get(image_url_of(image, base_url) or "")
        if number is None:
            image.decompose()
        else:
            image.replace_with(image_marker(number))


def extract_content(url: str) -> ExtractedContent:
    blog_id, log_no = parse_blog_url(url)

    # URL을 정규화해서 허용된 경로만 요청
    canonical_url = f"https://blog.naver.com/{blog_id}/{log_no}"
    mobile_url = f"https://m.blog.naver.com/{blog_id}/{log_no}"

    with requests.Session() as session:
        session.headers.update(HEADERS)

        try:
            soup = fetch_html(session, mobile_url)

            content = (
                soup.select_one(".se-main-container")
                or soup.select_one("#postViewArea")
            )

            if content is None:
                raise ExtractionError("블로그 본문을 찾을 수 없습니다.")

            title_element = (
                soup.select_one(".se-title-text")
                or soup.select_one(".pcol1 .title")
                or soup.select_one("meta[property='og:title']")
            )

            if title_element is None:
                title = "제목 없음"
            elif title_element.name == "meta":
                title = title_element.get("content", "제목 없음")
            else:
                title = title_element.get_text(" ", strip=True)

            image_urls = extract_image_urls(content, mobile_url)
            mark_image_positions(content, image_urls, mobile_url)
            text = content.get_text("\n", strip=True)

            if not IMAGE_MARKER.sub("", text).strip():
                raise ExtractionError("추출된 본문이 비어 있습니다.")

            return ExtractedContent(
                blog_id=blog_id,
                log_no=log_no,
                url=canonical_url,
                title=title,
                text=text,
                image_urls=image_urls,
            )

        except requests.RequestException as exc:
            raise ExtractionError("블로그 서버 요청에 실패했습니다.") from exc
