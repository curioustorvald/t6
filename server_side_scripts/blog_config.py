# blog_config.py — environment settings for Torvald's Tech Tales
#
# Edit this file when moving the blog to a different server or URL path,
# then recompile to regenerate all static pages:
#
#   python3 /srv/www/cgi-bin/blog_compile.py
#
# ── Paths ──────────────────────────────────────────────────────────────────

# Absolute filesystem path to the blog source tree.
# Contains: template.html, panels.json, articles/, CSS files.
# Compiled pages are also written here.
# Recompile when changed.
BLOG_ROOT = '/srv/www/htdocs/blog'

# ── URLs ───────────────────────────────────────────────────────────────────

# URL prefix under which the blog is served, with trailing slash.
# Examples:
#   '/blog/'          → https://example.com/blog/
#   '/'               → https://example.com/          (served at domain root)
#   '/~user/blog/'    → https://example.com/~user/blog/
# Recompile when changed.
BLOG_URL_BASE = '/blog/'
