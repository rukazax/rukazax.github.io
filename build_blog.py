#!/usr/bin/env python3
"""Сборка блога rukazax.github.io: src/<slug>.md -> posts/<slug>.html + список статей в index.html.

Без зависимостей: только стандартная библиотека Python 3.8+.
Разметка — подмножество Markdown, которое реально используется в статьях:
заголовки, абзацы, списки, таблицы, цитаты, фенсы кода, mermaid, картинки, ссылки,
жирный/курсив/инлайн-код.

    python build_blog.py            # пересобрать всё
    python build_blog.py --check    # ничего не писать, только сравнить со сборкой на диске
    python build_blog.py --only xio-vpn
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
POSTS_DIR = ROOT / "posts"
INDEX = ROOT / "index.html"
SITE = "https://rukazax.github.io"
NL = "\r\n"

# Метаданные статей. Порядок записей = порядок в блоке «Блог» на главной.
# title/desc/tags/cover/date берутся отсюда; front matter в .md — запасной вариант.
POSTS = [
    {
        "slug": "private-speeddial",
        "title": "Private SpeedDial: закладки, которые принадлежат вам",
        "desc": "Панель быстрого доступа с заметками, папками и синхронизацией в вашем облаке — расширение Chrome и приложение Android.",
        "tags": ["chrome", "android", "privacy"],
        "cover": "private-speeddial.png",
        "date": "2026-10-22",
        "product": True,
        "extra": ["продукт"],
    },
    {
        "slug": "xio-vpn",
        "title": "XIO: VPN, который живёт на вашем сервере",
        "desc": "Свой VPS, свои пользователи, пять протоколов и один интерфейс на Android, Ubuntu и Windows.",
        "tags": ["vpn", "android", "linux"],
        "cover": "xio-vpn.png",
        "date": "2026-10-22",
        "extra": ["gpl"],
    },
    {
        "slug": "x1o-harness",
        "title": "x1o: один харнесс для всех моделей",
        "desc": "Самохостная платформа личных ИИ-ассистентов: единый API, очередь диалогов, биллинг и облачная плоскость для тенантов.",
        "tags": ["llm", "self-hosted", "python"],
        "cover": "x1o-harness.png",
        "date": "2026-10-22",
        "product": True,
        "extra": ["продукт"],
    },
    {
        "slug": "ru-deepseek-harness",
        "title": "Русский язык для DeepSeek Harness: как сообщество сделало локализацию, а я её установил",
        "desc": "Разбираем плагин dsh-russian-lang: откуда в DeepSeek Harness берётся перевод, как он устроен внутри и как включить русский интерфейс за пять минут.",
        "tags": ["deepseek", "i18n", "open-source"],
        "cover": "deepseek-harness.png",
        "date": "2026-10-22",
        "extra": [],
    },
]

FAVICON = (
    "data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22%3E"
    "%3Crect width=%22100%22 height=%22100%22 rx=%2222%22 fill=%22%23fbf237%22/%3E%3C/svg%3E"
)


# --------------------------------------------------------------------------- markdown

def esc(text: str) -> str:
    return html.escape(text, quote=True)


def inline(text: str) -> str:
    """Инлайн-разметка. Инлайн-код прячется в плейсхолдеры, чтобы его не трогали другие правила."""
    codes: list[str] = []

    def keep(m: re.Match) -> str:
        codes.append(m.group(1))
        return "\x00%d\x00" % (len(codes) - 1)

    text = re.sub(r"`([^`]+)`", keep, text)
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img alt="\1" src="\2">', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)

    def restore(m: re.Match) -> str:
        return "<code>%s</code>" % html.escape(codes[int(m.group(1))], quote=False)

    return re.sub(r"\x00(\d+)\x00", restore, text)


def is_block_start(line: str) -> bool:
    s = line.strip()
    return bool(
        s.startswith("```")
        or s == "---"
        or re.match(r"^#{1,3} ", s)
        or s.startswith("|")
        or s.startswith(">")
        or re.match(r"^[-*] ", s)
    )


def table(rows: list[str]) -> str:
    def cells(row: str) -> list[str]:
        row = row.strip()
        if row.startswith("|"):
            row = row[1:]
        if row.endswith("|"):
            row = row[:-1]
        return [c.strip() for c in row.split("|")]

    head = cells(rows[0])
    body = rows[2:] if len(rows) > 2 else []
    out = ['<div class="table-wrap"><table><thead><tr>']
    out += ["<th>%s</th>" % inline(c) for c in head]
    out.append("</tr></thead><tbody>")
    for row in body:
        out.append("<tr>")
        out += ["<td>%s</td>" % inline(c) for c in cells(row)]
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def md_to_html(md: str) -> str:
    lines = md.split("\n")
    out: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        s = lines[i].strip()
        if not s:
            i += 1
            continue

        if s.startswith("```"):
            lang = s[3:].strip()
            i += 1
            buf: list[str] = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i].rstrip("\r"))
                i += 1
            i += 1  # закрывающий фенс
            code = esc("\n".join(buf))
            if lang == "mermaid":
                out.append(
                    '<div class="diagram"><div class="diagram-cap">схема</div>'
                    '<pre class="mermaid">%s</pre></div>' % code
                )
            else:
                out.append('<pre class="code" data-lang="%s"><code>%s</code></pre>' % (lang, code))
            continue

        if s == "---":
            out.append("<hr>")
            i += 1
            continue

        if s.startswith("# "):  # H1 приходит из метаданных шаблона
            i += 1
            continue
        if s.startswith("## "):
            out.append("<h2>%s</h2>" % inline(s[3:].strip()))
            i += 1
            continue
        if s.startswith("### "):
            out.append("<h3>%s</h3>" % inline(s[4:].strip()))
            i += 1
            continue

        if s.startswith("|"):
            rows: list[str] = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            out.append(table(rows))
            continue

        if s.startswith(">"):
            buf: list[str] = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].strip())
                i += 1
            out.append("<blockquote>%s</blockquote>" % inline(" ".join(x for x in buf if x)))
            continue

        if re.match(r"^[-*] ", s):
            items: list[str] = []
            while i < n and re.match(r"^[-*] ", lines[i].strip()):
                item = lines[i].strip()[2:].strip()
                i += 1
                while i < n and lines[i].strip() and lines[i][:1] in (" ", "\t"):
                    item += " " + lines[i].strip()
                    i += 1
                items.append(inline(item))
            out.append("<ul>\n" + "\n".join("<li>%s</li>" % x for x in items) + "\n</ul>")
            continue

        if s.startswith("!["):
            out.append("<p>%s</p>" % inline(s))
            i += 1
            continue

        buf = []
        while i < n:
            t = lines[i].strip()
            if not t or is_block_start(lines[i]):
                break
            buf.append(t)
            i += 1
        out.append("<p>%s</p>" % inline(" ".join(buf)))

    return "\n".join(out)


def strip_front_matter(md: str) -> str:
    if md.startswith("---"):
        parts = md.split("\n")
        if parts and parts[0].strip() == "---":
            for j in range(1, len(parts)):
                if parts[j].strip() == "---":
                    return "\n".join(parts[j + 1:])
    return md


# --------------------------------------------------------------------------- шаблоны

def render_post(meta: dict, body: str) -> str:
    title = esc(meta["title"])
    desc = esc(meta["desc"])
    tags = meta["tags"]
    cover = meta["cover"]
    chips = "".join("<span>%s</span>" % esc(t) for t in tags)
    for t in meta.get("extra", []):
        chips += "<span>%s</span>" % esc(t)
    mermaid = ""
    if '<pre class="mermaid">' in body:
        mermaid = (
            '<script src="../assets/mermaid.min.js"></script>\n'
            '<script>mermaid.initialize({ startOnLoad: true, theme: "dark" });</script>'
        )

    tpl = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — блог rukazax</title>
<meta name="description" content="{desc}">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{site}/assets/covers/{cover}">
<meta property="og:url" content="{site}/posts/{slug}.html">
<meta name="twitter:card" content="summary_large_image">
<link rel="alternate" type="application/rss+xml" title="Блог rukazax" href="../feed.xml">
<link rel="icon" href="{favicon}">
<link rel="stylesheet" href="../assets/site.css">
</head>
<body>
<div class="page">
  <nav class="top">
    <a href="../index.html">← На главную</a>
    <span style="display:flex;gap:12px;align-items:center">
      <a href="../index.html#blog">Все статьи</a><button class="icon-btn" type="button" data-theme-toggle data-theme-title aria-label="Переключить тему"><span data-theme-label>☀</span></button>
    </span>
  </nav>
  <article>
    <img class="cover" src="../assets/covers/{cover}" alt="{title}">
    <h1>{title}</h1>
    <p class="meta">{date} · {tagline}</p>
    <p class="lead">{desc}</p>
{body}
    <div class="tags">{chips}</div>
  </article>
  <footer class="art">
    <p>Константин · <a href="mailto:rukazax@gmail.com">rukazax@gmail.com</a> ·
    <a href="tel:+79998024040">+7 (999) 802-40-40</a></p>
  </footer>
</div>
<script src="../assets/app.js"></script>
{mermaid}
</body>
</html>
"""
    return tpl.format(
        title=title,
        desc=desc,
        site=SITE,
        cover=cover,
        slug=meta["slug"],
        favicon=FAVICON,
        date=meta["date"],
        tagline=", ".join(tags),
        body=body,
        chips=chips,
        mermaid=mermaid,
    )


def blog_rows(posts: list[dict]) -> str:
    out = []
    for p in posts:
        tags = ", ".join(p["tags"][:2])
        out.append(
            '      <a class="blogrow" href="posts/%s.html">\n'
            '        <div><div class="t">%s</div><div class="d">%s · %s</div></div>\n'
            '        <div class="go">→</div>\n'
            "      </a>" % (p["slug"], esc(p["title"]), esc(p["date"]), esc(tags))
        )
    return "\n".join(out)


def update_index(index_html: str, posts: list[dict]) -> str:
    pattern = re.compile(r'(<div class="bloglist">\n)(.*?)(\n    </div>\s*</section>)', re.S)
    if not pattern.search(index_html):
        raise SystemExit("index.html: не найден блок bloglist")
    return pattern.sub(lambda m: m.group(1) + blog_rows(posts) + m.group(3), index_html, count=1)


# --------------------------------------------------------------------------- sitemap и RSS

SITE_TITLE = "Блог rukazax"
SITE_DESC = "Разборы собственных продуктов: как устроены, какие решения приняты и что не получилось."
SITEMAP = ROOT / "sitemap.xml"
FEED = ROOT / "feed.xml"


def page_urls() -> list[tuple[str, str]]:
    """(url, приоритет) — лендинг, страницы продуктов и статьи."""
    urls = [(SITE + "/", "1.0"), (SITE + "/en.html", "0.9")]
    for app in sorted((ROOT / "apps").glob("*.html")):
        urls.append((f"{SITE}/apps/{app.name}", "0.8"))
    for p in POSTS:
        urls.append((f"{SITE}/posts/{p['slug']}.html", "0.6"))
    return urls


def render_sitemap() -> str:
    rows = "\n".join(
        "  <url>\n    <loc>%s</loc>\n    <changefreq>monthly</changefreq>\n    <priority>%s</priority>\n  </url>"
        % (esc(url), prio)
        for url, prio in page_urls()
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + rows
        + "\n</urlset>\n"
    )


def rfc822(date: str) -> str:
    from datetime import datetime, timedelta, timezone

    dt = datetime.strptime(date, "%Y-%m-%d").replace(hour=9, tzinfo=timezone(timedelta(hours=3)))
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")


def render_feed() -> str:
    items = []
    for p in POSTS:
        url = f"{SITE}/posts/{p['slug']}.html"
        items.append(
            "    <item>\n"
            "      <title>%s</title>\n"
            "      <link>%s</link>\n"
            '      <guid isPermaLink="true">%s</guid>\n'
            "      <pubDate>%s</pubDate>\n"
            "      <description>%s</description>\n"
            "    </item>" % (esc(p["title"]), url, url, rfc822(p["date"]), esc(p["desc"]))
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        "    <title>%s</title>\n"
        "    <link>%s/</link>\n"
        "    <description>%s</description>\n"
        "    <language>ru</language>\n"
        "    <lastBuildDate>%s</lastBuildDate>\n"
        '    <atom:link href="%s/feed.xml" rel="self" type="application/rss+xml"/>\n'
        "%s\n"
        "  </channel>\n"
        "</rss>\n"
        % (SITE_TITLE, SITE, SITE_DESC, rfc822(POSTS[0]["date"]), SITE, "\n".join(items))
    )


# --------------------------------------------------------------------------- сборка

def build(only: list[str] | None = None, check: bool = False) -> int:
    posts = POSTS if not only else [p for p in POSTS if p["slug"] in only]
    if only and not posts:
        print("нет таких статей:", ", ".join(only))
        return 2

    changed = 0
    for meta in posts:
        src = SRC / (meta["slug"] + ".md")
        if not src.exists():
            raise SystemExit("нет исходника: %s" % src)
        body = md_to_html(strip_front_matter(src.read_text(encoding="utf-8-sig")))
        page = render_post(meta, body)
        dst = POSTS_DIR / (meta["slug"] + ".html")
        old = dst.read_text(encoding="utf-8") if dst.exists() else None
        same = old == page
        if check:
            print(("ok   " if same else "DIFF ") + str(dst.relative_to(ROOT)))
            changed += 0 if same else 1
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            with open(dst, "w", encoding="utf-8", newline=NL) as fh:
                fh.write(page)
            print(("same " if same else "write") + " " + str(dst.relative_to(ROOT)))

    if not only:
        index = INDEX.read_text(encoding="utf-8")
        new_index = update_index(index, POSTS)
        same = new_index == index
        if check:
            print(("ok   " if same else "DIFF ") + "index.html")
            changed += 0 if same else 1
        else:
            if not same:
                with open(INDEX, "w", encoding="utf-8", newline=NL) as fh:
                    fh.write(new_index)
                print("write index.html")
            else:
                print("same  index.html")

        for path, payload in ((SITEMAP, render_sitemap()), (FEED, render_feed())):
            old = path.read_text(encoding="utf-8") if path.exists() else None
            if check:
                print(("ok   " if old == payload else "DIFF ") + path.name)
                changed += 0 if old == payload else 1
            elif old != payload:
                with open(path, "w", encoding="utf-8", newline=NL) as fh:
                    fh.write(payload)
                print("write " + path.name)
            else:
                print("same  " + path.name)

    if check:
        print("итог:", "сборка совпадает" if changed == 0 else "есть расхождения: %d" % changed)
        return 0 if changed == 0 else 1
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Сборка блога rukazax.github.io")
    ap.add_argument("--check", action="store_true", help="только сравнить, ничего не писать")
    ap.add_argument("--only", action="append", metavar="SLUG", help="собрать только указанные статьи")
    args = ap.parse_args(argv)
    return build(args.only, args.check)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
