#!/usr/bin/env python3
"""
网页数据提取工具 — 获取页面内容并转换为干净的 Markdown/JSON/文本格式。

用法:
    # 获取页面正文（自动提取，去除导航/广告等噪声）
    python scrape.py URL

    # 获取完整 HTML
    python scrape.py URL --mode html

    # 提取所有链接
    python scrape.py URL --mode links

    # 提取所有图片
    python scrape.py URL --mode images

    # 提取结构化数据 (标题 + 正文 + 链接 + 图片)
    python scrape.py URL --mode full

    # 保存到文件
    python scrape.py URL --output result.md

    # 指定 CSS 选择器精确提取
    python scrape.py URL --selector "article .content"

    # 使用自定义 User-Agent
    python scrape.py URL --ua "Mozilla/5.0 ..."
"""

import argparse
import json
import re
import sys
from html import unescape
from urllib.parse import urljoin, urlparse

import httpx

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    from readability import Document
    READABILITY_AVAILABLE = True
except ImportError:
    READABILITY_AVAILABLE = False


DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT = 30


def fetch_page(url, user_agent=None, timeout=DEFAULT_TIMEOUT):
    """获取页面 HTML"""
    headers = {
        "User-Agent": user_agent or DEFAULT_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    response = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    return response.text, str(response.url)


def html_to_markdown(html, base_url=""):
    """将 HTML 转为简单的 Markdown"""
    if not BS4_AVAILABLE:
        # fallback: 简单正则清理
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", "", text)
        text = unescape(text)
        return re.sub(r"\n{3,}", "\n\n", text).strip()

    soup = BeautifulSoup(html, "lxml")

    # 移除噪音元素
    for tag in soup.find_all(["script", "style", "nav", "footer", "noscript", "iframe"]):
        tag.decompose()

    lines = []
    for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote", "pre", "code", "td", "th"]):
        tag_name = el.name
        text = el.get_text(strip=True)
        if not text:
            continue

        if tag_name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag_name[1])
            lines.append(f"\n{'#' * level} {text}\n")
        elif tag_name == "li":
            lines.append(f"- {text}")
        elif tag_name == "blockquote":
            lines.append(f"> {text}")
        elif tag_name in ("pre", "code"):
            lines.append(f"```\n{text}\n```")
        else:
            lines.append(text)

    return "\n".join(lines).strip()


def extract_readable(html, url=""):
    """使用 readability 提取正文"""
    if READABILITY_AVAILABLE:
        doc = Document(html, url=url)
        title = doc.title()
        content_html = doc.summary()
        content_md = html_to_markdown(content_html, url)
        return title, content_md
    else:
        return "", html_to_markdown(html, url)


def extract_links(html, base_url):
    """提取所有链接"""
    if not BS4_AVAILABLE:
        return []
    soup = BeautifulSoup(html, "lxml")
    links = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        text = a.get_text(strip=True)
        if href.startswith("http"):
            links.append({"text": text, "url": href})
    return links


def extract_images(html, base_url):
    """提取所有图片"""
    if not BS4_AVAILABLE:
        return []
    soup = BeautifulSoup(html, "lxml")
    images = []
    for img in soup.find_all("img", src=True):
        src = urljoin(base_url, img["src"])
        alt = img.get("alt", "")
        if src.startswith("http"):
            images.append({"alt": alt, "src": src})
    return images


def extract_by_selector(html, selector, base_url=""):
    """用 CSS 选择器提取内容"""
    if not BS4_AVAILABLE:
        print("❌ 需要 beautifulsoup4 才能使用选择器", file=sys.stderr)
        return ""
    soup = BeautifulSoup(html, "lxml")
    elements = soup.select(selector)
    if not elements:
        return f"⚠️ 未找到匹配 '{selector}' 的元素"
    parts = []
    for el in elements:
        parts.append(html_to_markdown(str(el), base_url))
    return "\n\n---\n\n".join(parts)


def extract_meta(html, url):
    """提取页面元数据"""
    if not BS4_AVAILABLE:
        return {}
    soup = BeautifulSoup(html, "lxml")
    meta = {"url": url}

    title_tag = soup.find("title")
    if title_tag:
        meta["title"] = title_tag.get_text(strip=True)

    for tag in soup.find_all("meta"):
        name = tag.get("name", tag.get("property", "")).lower()
        content = tag.get("content", "")
        if name in ("description", "og:description"):
            meta["description"] = content
        elif name in ("og:title"):
            meta.setdefault("title", content)
        elif name in ("og:image"):
            meta["image"] = content
        elif name in ("keywords"):
            meta["keywords"] = content
    return meta


def main():
    parser = argparse.ArgumentParser(description="网页数据提取工具")
    parser.add_argument("url", help="要抓取的 URL")
    parser.add_argument("--mode", choices=["text", "html", "links", "images", "full", "meta"],
                        default="text", help="提取模式 (默认: text)")
    parser.add_argument("--selector", help="CSS 选择器")
    parser.add_argument("--output", "-o", help="保存到文件")
    parser.add_argument("--ua", help="自定义 User-Agent")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="超时秒数")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")

    args = parser.parse_args()

    try:
        html, final_url = fetch_page(args.url, args.ua, args.timeout)
    except Exception as e:
        print(f"❌ 获取页面失败: {e}", file=sys.stderr)
        sys.exit(1)

    result = ""

    if args.selector:
        result = extract_by_selector(html, args.selector, final_url)

    elif args.mode == "text":
        title, content = extract_readable(html, final_url)
        if title:
            result = f"# {title}\n\n{content}"
        else:
            result = content

    elif args.mode == "html":
        result = html

    elif args.mode == "links":
        links = extract_links(html, final_url)
        if args.json:
            result = json.dumps(links, ensure_ascii=False, indent=2)
        else:
            for link in links:
                result += f"- [{link['text']}]({link['url']})\n"

    elif args.mode == "images":
        images = extract_images(html, final_url)
        if args.json:
            result = json.dumps(images, ensure_ascii=False, indent=2)
        else:
            for img in images:
                result += f"![{img['alt']}]({img['src']})\n"

    elif args.mode == "meta":
        meta = extract_meta(html, final_url)
        result = json.dumps(meta, ensure_ascii=False, indent=2)

    elif args.mode == "full":
        title, content = extract_readable(html, final_url)
        links = extract_links(html, final_url)
        images = extract_images(html, final_url)
        meta = extract_meta(html, final_url)
        full = {
            "meta": meta,
            "title": title,
            "content": content,
            "links_count": len(links),
            "images_count": len(images),
            "links": links[:50],
            "images": images[:20],
        }
        result = json.dumps(full, ensure_ascii=False, indent=2)

    # 输出
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"✅ 已保存到 {args.output} ({len(result)} 字符)")
    else:
        print(result)


if __name__ == "__main__":
    main()
