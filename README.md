# 记意电波 — Personal RSS

This repository builds a personal RSS feed for the public Xiaoyuzhou podcast **记意电波**.

- Source: https://www.xiaoyuzhoufm.com/podcast/64341d0ec21112da279464c6
- Published feed: `docs/feed.xml`
- Retention: latest 30 episodes
- Refresh: every 4 hours through GitHub Actions
- Audio remains hosted by Xiaoyuzhou; this project publishes episode metadata and public audio enclosure links only.

## One-time setup

1. Open **Settings → Pages**.
2. Under **Build and deployment**, choose **Deploy from a branch**.
3. Select branch **main** and folder **/docs**, then save.
4. Open **Actions → Update podcast RSS → Run workflow** to run the first fetch.
5. When the workflow succeeds and Pages finishes publishing, subscribe to:

`https://zengtoushi.github.io/jiyi-radio-rss/feed.xml`

The workflow keeps the newest 30 episodes. It preserves the existing feed if Xiaoyuzhou's page structure changes or a fetch returns no usable episodes.

## Important

The initial run is also a compatibility test: Xiaoyuzhou may change its public page data format or restrict automated requests. If the run fails, open the failed run under **Actions** and share the error log; the parser will need adjustment before Pocket Casts can use the feed.
