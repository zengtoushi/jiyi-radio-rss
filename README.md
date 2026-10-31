# Personal Xiaoyuzhou RSS feeds

This repository builds separate RSS feeds for public Xiaoyuzhou podcasts.

## Current feeds

| Podcast | RSS |
|---|---|
| 记意电波 | https://zengtoushi.github.io/jiyi-radio-rss/feed.xml |
| 越位线 | https://zengtoushi.github.io/jiyi-radio-rss/feeds/yueweixian.xml |

- Refresh: every 4 hours through GitHub Actions
- Retention: latest 30 episodes per podcast
- Audio remains hosted by Xiaoyuzhou; this project publishes public episode metadata and audio enclosure links only.

## Add another Xiaoyuzhou podcast

Add one object to the `podcasts` array in `config.json`. Give it a unique `slug`, the public podcast page URL, and unique `state_path`, `feed_path`, and `feed_url` values. The parser reads the public page's embedded `__NEXT_DATA__` podcast episode list.

The workflow updates every configured feed. If any configured show fails to fetch, the run fails rather than committing a partially updated set of feeds.

## Setup

The GitHub Pages source should be set to **GitHub Actions**. Run **Actions → Update podcast RSS and publish Pages → Run workflow** to refresh feeds manually.
