#!/usr/bin/python3
"""Torvald's Tech Tales – static site compiler.

Runs as a CGI script (via Apache) or directly from the command line:

  python3 blog_compile.py                       # compile everything
  python3 blog_compile.py --article=terrarum_lighting1   # one slug only

Via CGI:
  GET /cgi-bin/blog_compile.py
  GET /cgi-bin/blog_compile.py?article=terrarum_lighting1
"""

import os
import sys
from pathlib import Path

# Allow importing blog_common and blog_config from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blog_common
from blog_config import BLOG_ROOT, BLOG_URL_BASE

BLOG_ROOT = Path(BLOG_ROOT)


def compile_all(specific_slug=None):
    """Compile all pages (or one specific slug).

    Returns list of (slug, 'OK'|'ERROR', error_or_None).
    """
    config = blog_common.load_config(BLOG_ROOT)
    tasks  = blog_common.build_compile_tasks(config)
    results = []

    for slug, render_fn in tasks:
        if specific_slug and slug != specific_slug:
            continue
        try:
            html = render_fn()
            (BLOG_ROOT / f'{slug}.html').write_text(html, encoding='utf-8')
            results.append((slug, 'OK', None))
        except Exception as exc:
            results.append((slug, 'ERROR', str(exc)))

    return results


def _html_report(results):
    ok     = [(s, e) for s, st, e in results if st == 'OK']
    errors = [(s, e) for s, st, e in results if st == 'ERROR']
    lines  = [
        '<!DOCTYPE html><html lang="en"><head>',
        '<meta charset="UTF-8"><title>Blog Compiler</title>',
        '<style>'
        'body{font-family:sans-serif;max-width:800px;margin:2em auto;line-height:1.6}'
        '.ok{color:#060}.err{color:#c00}ul{font-family:monospace}'
        '</style>',
        '</head><body>',
        '<h1>Blog Compiler</h1>',
        f'<p>Compiled <strong>{len(ok)}</strong> page(s)'
        + (f', <strong class="err">{len(errors)} error(s)</strong>' if errors else '')
        + '.</p>',
    ]
    if ok:
        lines += ['<h2>Generated</h2><ul>']
        for slug, _ in ok:
            lines.append(
                f'<li class="ok"><a href="{BLOG_URL_BASE}{slug}.html">{slug}.html</a></li>'
            )
        lines.append('</ul>')
    if errors:
        lines += ['<h2 class="err">Errors</h2><ul>']
        for slug, err in errors:
            lines.append(f'<li class="err"><code>{slug}</code>: {err}</li>')
        lines.append('</ul>')
    lines.append('</body></html>')
    return '\n'.join(lines)


def main():
    is_cgi = 'GATEWAY_INTERFACE' in os.environ

    specific_slug = None
    if is_cgi:
        import urllib.parse
        params = dict(urllib.parse.parse_qsl(os.environ.get('QUERY_STRING', '')))
        specific_slug = params.get('article')
        print('Content-Type: text/html\n')
    else:
        for arg in sys.argv[1:]:
            if arg.startswith('--article='):
                specific_slug = arg[len('--article='):]

    results = compile_all(specific_slug=specific_slug)

    if is_cgi:
        print(_html_report(results))
    else:
        for slug, status, err in results:
            mark = '\u2713' if status == 'OK' else '\u2717'
            line = f'  {mark}  {slug}.html'
            if err:
                line += f'  \u2192  {err}'
            print(line)
        n_ok  = sum(1 for _, st, _ in results if st == 'OK')
        n_err = sum(1 for _, st, _ in results if st == 'ERROR')
        print(f'\nDone: {n_ok} compiled, {n_err} error(s).')


if __name__ == '__main__':
    main()
