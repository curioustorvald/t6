"""Shared rendering library for Torvald's Tech Tales static site compiler."""

import html
import json
import re
from pathlib import Path

from blog_config import BLOG_URL_BASE

try:
    from markdown_it import MarkdownIt as _MarkdownIt
    _md = _MarkdownIt('commonmark', {'html': True})
    _render_markdown = _md.render
except ImportError:
    def _render_markdown(text):
        raise RuntimeError(
            "markdown-it-py is required for Markdown support. "
            "Install with: pip install markdown-it-py"
        )


# ── Utilities ──────────────────────────────────────────────────────────────

def filename_to_slug(f):
    """Strip 12-digit timestamp prefix + underscore from a filename stem.
    '202202041337_terrarum_lighting1' → 'terrarum_lighting1'
    """
    return f[13:]


def timestamp_to_readable(stamp):
    """'202202041337' → '2022-02-04 13:37'"""
    return f'{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]} {stamp[8:10]}:{stamp[10:12]}'


def strip_html_tags(s):
    """Remove HTML tags and normalise whitespace to a single space."""
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s)).strip()


def make_description(body_html, max_len=160):
    """Extract a short plain-text description for a <meta> description tag."""
    text = html.unescape(strip_html_tags(body_html))
    if len(text) > max_len:
        text = text[:max_len].rsplit(' ', 1)[0] + '\u2026'
    return html.escape(text, quote=True)


# ── Config Loading ─────────────────────────────────────────────────────────

def load_config(blog_root):
    """Load all site configuration from blog_root.

    Returns a dict:
      blog_root, panels, alts, template, articles_by_cat
    """
    blog_root = Path(blog_root)

    with open(blog_root / 'panels.json', encoding='utf-8') as f:
        panels = json.load(f)

    alts = {}
    alts_path = blog_root / 'articles' / 'alts.json'
    if alts_path.exists():
        with open(alts_path, encoding='utf-8') as f:
            for entry in json.load(f):
                alts.update(entry)

    with open(blog_root / 'template.html', encoding='utf-8') as f:
        template = f.read()

    articles_by_cat = {}
    for panel_id, panel in panels.items():
        if panel.get('schema') == 'LIST':
            p = blog_root / 'articles' / f'articles_{panel_id}.json'
            articles_by_cat[panel_id] = json.loads(p.read_text('utf-8')) if p.exists() else []

    return dict(
        blog_root=blog_root,
        panels=panels,
        alts=alts,
        template=template,
        articles_by_cat=articles_by_cat,
    )


def find_source_file(blog_root, f):
    """Return Path to article source for stem f, preferring .html over .md."""
    for ext in ('.html', '.md'):
        p = Path(blog_root) / 'articles' / f'{f}{ext}'
        if p.exists():
            return p
    return None


def render_source(filepath):
    """Read an article source file (.html or .md) and return HTML string."""
    filepath = Path(filepath)
    text = filepath.read_text(encoding='utf-8')
    return _render_markdown(text) if filepath.suffix == '.md' else text


# ── Template Helpers ───────────────────────────────────────────────────────

def _replace_inner(page, tag, content):
    """Replace inner content of the first <tag>…</tag> occurrence."""
    pat = re.compile(
        rf'(<{re.escape(tag)}(?:\s[^>]*)?>)(.*?)(</{re.escape(tag)}>)',
        re.IGNORECASE | re.DOTALL,
    )
    return pat.sub(lambda m: m.group(1) + content + m.group(3), page, count=1)


def _remove_tag(page, tag):
    """Remove the first <tag>…</tag> block (including preceding whitespace)."""
    pat = re.compile(
        rf'[ \t]*\n?[ \t]*<{re.escape(tag)}(?:\s[^>]*)?>.*?</{re.escape(tag)}>',
        re.IGNORECASE | re.DOTALL,
    )
    return pat.sub('', page, count=1)


# ── HTML Builders ──────────────────────────────────────────────────────────

def build_nav_html(panels, current_page_id, articles_by_cat):
    """Build navigation HTML; LIST entries with no articles are omitted."""
    items = []
    for panel_id, panel in panels.items():
        schema = panel.get('schema', '')
        label  = panel.get('label', panel_id)
        css    = 'sub_link selected' if panel_id == current_page_id else 'sub_link'

        if schema == 'HOME':
            href = BLOG_URL_BASE
        elif schema == 'HREF':
            href = panel.get('source', '#')
        elif schema == 'LIST':
            if not articles_by_cat.get(panel_id):
                continue   # skip empty categories
            href = f'{BLOG_URL_BASE}cat_{panel_id}.html'
        else:
            continue

        items.append(
            f'<li class="columngap"><a href="{href}" class="{css}">{label}</a></li>'
        )

    return (
        '<div class="sub_content"><ul class="sub_menu">'
        + ''.join(items)
        + '</ul></div>'
    )


def build_alts_html(base_f, alts, current_file):
    """Build the alt-language switcher HTML. Returns '' if no alts exist."""
    if base_f not in alts:
        return ''

    entry = alts[base_f]
    versions = [{'label': entry['default'], 'slug': filename_to_slug(base_f), 'file': base_f}]
    for alt in entry.get('alts', []):
        alt_f = f'{base_f}_{alt["s"]}'
        versions.append({'label': alt['l'], 'slug': filename_to_slug(alt_f), 'file': alt_f})

    parts = []
    for v in versions:
        if v['file'] == current_file:
            parts.append(f'<strong>{v["label"]}</strong>')
        else:
            parts.append(f'<a href="{BLOG_URL_BASE}{v["slug"]}.html">{v["label"]}</a>')
    return ' &middot; '.join(parts)


def build_share_html():
    """Share button using navigator.clipboard (no external JS needed)."""
    return (
        "<a href=\"#\""
        " onclick=\"navigator.clipboard.writeText(window.location.href)"
        ".then(()=>alert('Link Copied'));return false\">"
        "Share This Article</a>"
    )


# ── Template Filling ───────────────────────────────────────────────────────

def fill_template(template_str, *, lang, title, nav_html, article_title_html,
                  timestamp_str, share_html, alts_html, body_html,
                  goback_html, description, is_index=False):
    """Return a fully-rendered HTML page from the template.

    Pass timestamp_str='' for non-article pages (index, category lists) —
    this removes article_toolbox entirely.  Pass goback_html='' to remove
    article_goback.
    """
    p = template_str

    # Language
    p = p.replace('<html lang="en">', f'<html lang="{lang}">', 1)

    # Page <title>
    page_title = ("Torvald's Tech Tales"
                  if is_index else
                  f"{title} \u2013 Torvald's Tech Tales")
    p = p.replace("<title>Torvald's Tech Tales</title>",
                  f'<title>{page_title}</title>', 1)

    # Site header: wrap in link to index
    p = _replace_inner(
        p, 'siteheader',
        f'<a href="{BLOG_URL_BASE}"><h1 class="site_header">Torvald\'s Tech&nbsp;Tales</h1></a>',
    )

    # Navigation
    p = _replace_inner(p, 'panelnavwrapper', nav_html)

    # Article title
    p = _replace_inner(p, 'article_title', article_title_html)

    # Toolbox — omit entirely on index / category pages
    if timestamp_str:
        p = _replace_inner(p, 'article_timestamp', timestamp_str)
        p = _replace_inner(p, 'article_share',     share_html)
        p = _replace_inner(p, 'article_alts',      alts_html)
    else:
        p = _remove_tag(p, 'article_toolbox')

    # Body
    p = _replace_inner(p, 'article_body', body_html)

    # Go-back link — omit on index / category pages
    if goback_html:
        p = _replace_inner(p, 'article_goback', goback_html)
    else:
        p = _remove_tag(p, 'article_goback')

    # Meta description
    p = p.replace('</head>',
                  f'    <meta name="description" content="{description}">\n</head>', 1)

    return p


# ── Page Renderers ─────────────────────────────────────────────────────────

def render_article_page(config, article_f, category_id, title,
                        lang='en', alt_f=None):
    """Compile one article page.

    article_f    — base filename stem (always the timestamped base article)
    category_id  — which nav category to highlight
    title        — display title (may be the alt-language title)
    lang         — HTML lang attribute value
    alt_f        — alt-language filename stem (if rendering an alt version)
    """
    current_f = alt_f or article_f
    src = find_source_file(config['blog_root'], current_f)
    if src is None:
        raise FileNotFoundError(f'Source file not found: {current_f}')

    body_html  = render_source(src)
    timestamp  = article_f.split('_', 1)[0]
    cat_label  = config['panels'].get(category_id, {}).get('label', category_id)

    return fill_template(
        config['template'],
        lang=lang,
        title=title,
        nav_html=build_nav_html(config['panels'], category_id, config['articles_by_cat']),
        article_title_html=f'<h2>{title}</h2>',
        timestamp_str=timestamp_to_readable(timestamp),
        share_html=build_share_html(),
        alts_html=build_alts_html(article_f, config['alts'], current_f),
        body_html=body_html,
        goback_html=(
            f'<a href="{BLOG_URL_BASE}cat_{category_id}.html">'
            f'<sym>🖘</sym>&ensp;Go Back to {cat_label}</a>'
        ),
        description=make_description(body_html),
    )


def _article_list_html(articles):
    """Return <article_list_container> HTML for a list of article records."""
    if not articles:
        return '<article_list_container></article_list_container>'
    items = []
    for rec in reversed(articles):
        slug = filename_to_slug(rec['f'])
        date = timestamp_to_readable(rec['f'].split('_', 1)[0])[:10]
        items.append(
            f'<article_list>'
            f'<a href="{BLOG_URL_BASE}{slug}.html">{rec["t"]}</a>'
            f'<span class="article_date">{date}</span>'
            f'</article_list>'
        )
    return '<article_list_container>' + ''.join(items) + '</article_list_container>'


def render_category_page(config, category_id):
    """Compile a category article-listing page."""
    cat_label = config['panels'].get(category_id, {}).get('label', category_id)
    articles  = config['articles_by_cat'].get(category_id, [])

    return fill_template(
        config['template'],
        lang='en',
        title=f'Articles: {cat_label}',
        nav_html=build_nav_html(config['panels'], category_id, config['articles_by_cat']),
        article_title_html=f'<h2>Articles with {cat_label} Topic:</h2>',
        timestamp_str='',
        share_html='',
        alts_html='',
        body_html=_article_list_html(articles),
        goback_html='',
        description=f"Articles about {cat_label} on Torvald's Tech Tales.",
    )


def render_index_page(config):
    """Compile the blog index page."""
    panels          = config['panels']
    articles_by_cat = config['articles_by_cat']

    intro = (
        '<p>This is a blog where I post technical articles about the projects I work on'
        ' &mdash; primarily graphics programming, colour science, logic systems,'
        ' and other curiosities.</p>'
    )

    sections = [intro]
    for panel_id, panel in panels.items():
        if panel.get('schema') != 'LIST':
            continue
        articles = articles_by_cat.get(panel_id, [])
        if not articles:
            continue
        cat_label = panel.get('label', panel_id)
        sections.append(f'<h3>{cat_label}</h3>')
        sections.append(_article_list_html(articles))

    return fill_template(
        config['template'],
        lang='en',
        title="Torvald's Tech Tales",
        nav_html=build_nav_html(panels, 'index', articles_by_cat),
        article_title_html='<h2>Welcome</h2>',
        timestamp_str='',
        share_html='',
        alts_html='',
        body_html=''.join(sections),
        goback_html='',
        description=(
            "Technical blog by CuriousTorvald covering graphics programming, "
            "colour science, logic systems, and other curiosities."
        ),
        is_index=True,
    )


# ── Task Builder (for compiler) ────────────────────────────────────────────

def build_compile_tasks(config):
    """Return list of (output_slug, render_fn) for every page to compile."""
    alts            = config['alts']
    articles_by_cat = config['articles_by_cat']
    tasks           = []

    # Index page
    tasks.append(('index', lambda c=config: render_index_page(c)))

    # Category listing pages (non-empty only)
    for cat_id, articles in articles_by_cat.items():
        if articles:
            tasks.append((
                f'cat_{cat_id}',
                lambda c=config, cid=cat_id: render_category_page(c, cid),
            ))

    # Individual article pages
    for cat_id, articles in articles_by_cat.items():
        for rec in articles:
            f, t = rec['f'], rec['t']
            slug  = filename_to_slug(f)
            tasks.append((
                slug,
                lambda c=config, af=f, cid=cat_id, ti=t:
                    render_article_page(c, af, cid, ti),
            ))
            # Alt-language versions
            if f in alts:
                for alt in alts[f].get('alts', []):
                    alt_f     = f'{f}_{alt["s"]}'
                    alt_title = alt.get('t', t)
                    alt_lang  = alt['s']
                    alt_slug  = filename_to_slug(alt_f)
                    tasks.append((
                        alt_slug,
                        lambda c=config, af=f, cid=cat_id, at=alt_title,
                               al=alt_lang, alf=alt_f:
                            render_article_page(c, af, cid, at, lang=al, alt_f=alf),
                    ))

    return tasks
