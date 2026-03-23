# X/Twitter 搜索语法速查

## 基础搜索

- `关键词` — 基本搜索
- `"exact phrase"` — 精确短语匹配
- `keyword1 OR keyword2` — 任一匹配
- `keyword1 -keyword2` — 排除关键词
- `#hashtag` — 话题标签搜索
- `$TICKER` — 股票代码（如 $AAPL）

## 用户相关

- `from:username` — 某用户发的帖子
- `to:username` — 回复某用户的帖子
- `@username` — 提及某用户
- `list:listid` — 某列表内的帖子

## 时间过滤

- `since:2026-03-22` — 某日期之后
- `until:2026-03-24` — 某日期之前
- `since:2026-03-23 until:2026-03-24` — 当天帖子

## 内容过滤

- `filter:links` — 包含链接
- `filter:images` — 包含图片
- `filter:videos` — 包含视频
- `filter:media` — 包含媒体
- `filter:replies` — 仅回复
- `-filter:replies` — 排除回复
- `filter:nativeretweets` — 仅转推
- `-filter:retweets` — 排除转推

## 互动量过滤

- `min_retweets:100` — 最少转推数
- `min_faves:500` — 最少点赞数
- `min_replies:50` — 最少回复数

## 语言过滤

- `lang:en` — 英文
- `lang:zh` — 中文
- `lang:ja` — 日文

## 组合示例

搜集某主题当天高质量英文帖子：
```
"artificial intelligence" since:2026-03-23 min_faves:100 lang:en -filter:retweets
```

搜集某领域 KOL 的帖子：
```
(from:elonmusk OR from:sama OR from:kaborris) AI since:2026-03-22
```

## X 搜索页面标签页

搜索结果页有多个标签页可切换：
- **Top** — 热门结果（默认）
- **Latest** — 最新结果（按时间排序，适合获取当天新帖）
- **People** — 相关用户（用于发现 KOL）
- **Media** — 包含媒体的帖子
- **Lists** — 相关列表

**重要**：搜集当天新信息时，务必切换到 **Latest** 标签页。
