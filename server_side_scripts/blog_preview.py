#!/usr/bin/python3
"""Torvald's Tech Tales – dev preview CGI.

Renders any blog page dynamically without writing to disk.

Query parameters:
  ?article=<stem>   Preview a specific article or alt-language version
                    e.g. ?article=202202041337_terrarum_lighting1
                         ?article=202603242007_human_slops_ai_edition_ko
  ?page=index       Preview the index page
  ?page=cat_<id>    Preview a category listing page  (e.g. ?page=cat_cg)
  (no params)       Show a menu of available preview links
"""

import os
import re
import sys
import traceback
import urllib.parse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blog_common
from blog_config import BLOG_ROOT

BLOG_ROOT = Path(BLOG_ROOT)

_LINK_CSS_RE = re.compile(
    r'<link\b[^>]*\brel=["\']stylesheet["\'][^>]*/?>',
    re.IGNORECASE,
)
_HREF_RE = re.compile(r'\bhref=["\']([^"\']+)["\']', re.IGNORECASE)


def _inline_css(html_str, blog_root):
    """Replace local <link rel="stylesheet"> tags with inlined <style> blocks."""
    def _replace(m):
        tag = m.group(0)
        href_m = _HREF_RE.search(tag)
        if not href_m:
            return tag
        href = href_m.group(1)
        if href.startswith(('http://', 'https://', '//')):
            return tag
        css_path = Path(blog_root) / href
        if not css_path.exists():
            return tag
        return f'<style>\n{css_path.read_text(encoding="utf-8")}\n</style>'

    return _LINK_CSS_RE.sub(_replace, html_str)


def _find_article_info(config, stem):
    """Locate an article or alt-language version by filename stem.

    Returns a dict suitable for render_article_page, or None if not found.
    """
    alts = config['alts']
    for cat_id, articles in config['articles_by_cat'].items():
        for rec in articles:
            # Base article
            if rec['f'] == stem:
                return dict(article_f=rec['f'], cat_id=cat_id, title=rec['t'])
            # Alt-language version
            if rec['f'] in alts:
                for alt in alts[rec['f']].get('alts', []):
                    alt_f = f'{rec["f"]}_{alt["s"]}'
                    if alt_f == stem:
                        return dict(
                            article_f=rec['f'],
                            cat_id=cat_id,
                            title=alt.get('t', rec['t']),
                            lang=alt['s'],
                            alt_f=alt_f,
                        )
    return None


def _preview_menu(config):
    """Return an HTML page listing all available preview links."""
    panels          = config['panels']
    articles_by_cat = config['articles_by_cat']
    alts            = config['alts']

    lines = [
        '<!DOCTYPE html><html><head><meta charset="UTF-8">',
        '<title>Blog Preview</title>',
        '<style>'
        'body{font-family:sans-serif;max-width:800px;margin:2em auto}'
        'h2{margin-top:1.8em}ul{line-height:2.2}small{color:#666}'
        '</style>',
        '</head><body>',
        '<h1>Blog Preview</h1>',
        '<p><a href="?page=index">&#127968; Index page</a></p>',
    ]
    for cat_id, articles in articles_by_cat.items():
        if not articles:
            continue
        cat_label = panels.get(cat_id, {}).get('label', cat_id)
        lines.append(
            f'<h2>{cat_label}'
            f' <small>&ensp;<a href="?page=cat_{cat_id}">category page</a></small>'
            f'</h2><ul>'
        )
        for rec in reversed(articles):
            line = f'<li><a href="?article={rec["f"]}">{rec["t"]}</a>'
            if rec['f'] in alts:
                for alt in alts[rec['f']].get('alts', []):
                    alt_f = f'{rec["f"]}_{alt["s"]}'
                    line += f' &middot; <a href="?article={alt_f}">{alt["l"]}</a>'
            line += '</li>'
            lines.append(line)
        lines.append('</ul>')
    lines.append('</body></html>')
    return '\n'.join(lines)


def main():
    print('Content-Type: text/html\n')

    params = dict(urllib.parse.parse_qsl(os.environ.get('QUERY_STRING', '')))

    try:
        config        = blog_common.load_config(BLOG_ROOT)
        article_param = params.get('article')
        page_param    = params.get('page')

        blog_root = config['blog_root']

        if article_param:
            info = _find_article_info(config, article_param)
            if info is None:
                print(f'<p>Article not found: <code>{article_param}</code></p>')
                return
            print(_inline_css(blog_common.render_article_page(
                config,
                info['article_f'],
                info['cat_id'],
                info['title'],
                lang=info.get('lang', 'en'),
                alt_f=info.get('alt_f'),
            ), blog_root))

        elif page_param == 'index':
            print(_inline_css(blog_common.render_index_page(config), blog_root))

        elif page_param and page_param.startswith('cat_'):
            print(_inline_css(blog_common.render_category_page(config, page_param[4:]), blog_root))

        else:
            print(_preview_menu(config))

    except Exception:
        print(
            '<pre style="color:red;font-family:monospace">'
            + traceback.format_exc()
            + '</pre>'
        )


if __name__ == '__main__':
    main()
