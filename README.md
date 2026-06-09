# JoJo's AIED Hub

一个面向教师 AI 研究的香港 AI 教育资料墙。

这个网站用来每天整理：

- 标注发布日期的香港 AI 教育相关新闻
- 教师 AI 培训、讲座、工作坊和报名链接
- AI 教育相关网页的研究摘要

第一版界面采用 Padlet 风格：像资料墙一样浏览新闻、培训和摘要卡片，方便快速发现可追踪的活动、政策变化和潜在研究现场。

## 本地预览

在终端运行：

```bash
cd /Users/zhouxinxin/Documents/Codex/2026-06-09/ai-github
python3 -m http.server 4174 -d docs
```

然后打开：

```text
http://localhost:4174
```

如果要停止本地预览，在终端按：

```text
Control + C
```

## 每天更新资料

运行：

```bash
python3 scripts/update_data.py
```

脚本会整理香港教育局、香港教育城、News.gov.hk、Google News 等公开来源，并写入：

```text
docs/data/content.json
```

LinkedIn 不直接抓取，只通过 Google 发现公开线索。

## Codex 改完后同步到 GitHub

运行：

```bash
./scripts/sync.sh main "update JoJo AIED Hub"
```

这会把 Codex 里的最新版本同步到 GitHub。

## 网站文件

- `docs/index.html`：网页结构
- `docs/styles.css`：Padlet 风格界面
- `docs/app.js`：新闻、培训、摘要卡片显示逻辑
- `docs/data/content.json`：每日更新后的资料
- `scripts/update_data.py`：自动抓取和整理资料
- `scripts/sync.sh`：同步到 GitHub

## GitHub Pages

如果要让它变成公开网址，在 GitHub 仓库中进入：

```text
Settings -> Pages
```

选择：

```text
Branch: main
Folder: /docs
```

保存后，网站会发布到 GitHub Pages。
