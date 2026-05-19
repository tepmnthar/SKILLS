# Sarna.net URL Reference

## Base Domain

- Wiki base: `https://www.sarna.net/wiki/`
- News base: `https://www.sarna.net/news/`

## Mode URLs

### News (RSS)

- News page: `https://www.sarna.net/news/`
  - Contains recent news articles with dates and summaries

### Search

- Search URL template: `https://www.sarna.net/wiki/index.php?title=Special%3ASearch&search={query}&fulltext=Search`
  - Replace `{query}` with user's search term (URL-encode spaces as `+` or `%20`)
  - Results contain links to wiki pages matching the query

### Random

- Random page: `https://www.sarna.net/wiki/Special:Random`
  - Redirects to a random wiki article

## Sitemap

- Sitemap: `https://www.sarna.net/news/sitemap.xml.gz`
  - Compressed XML sitemap for the news section
  - Can be used for URL validation or discovery

## Valid Cascade Links

During search cascade, only follow links matching these patterns:

- `https://www.sarna.net/wiki/*` — main wiki articles
- Exclude: `/wiki/Special:*`, `/wiki/Help:*`, `/wiki/MediaWiki:*`
- Exclude: links to categories (`/wiki/Category:*`) unless directly relevant to search query

## URL Encoding

When constructing search URLs, encode the query:
- Spaces → `+` or `%20`
- Special characters → percent-encoded