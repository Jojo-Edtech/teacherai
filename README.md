# Jojo Teacher AI Hub

一个面向教师 AI 研究的香港 AI 教育资料墙。

这个网站用来每天整理：

- 香港 AI 教育相关新闻与网页摘要（标注发布日期）
- AI 相关培训、讲座、工作坊、研讨会和报名链接（优先标注活动日期/报名截止）
- LinkedIn 公开线索入口
- 教育类 SSCI 顶刊最新文章
- 每张卡片会显示一段简体中文简介，说明这条新闻、培训或文章主要写了什么

界面采用简洁资料库风格，并拆成四个顶部选项卡：新闻与网页摘要、AI培训与讲座、LinkedIn线索、SSCI顶刊文章。这样之后可以继续增加新功能。

目前已经加入两层去重：

- 自动更新脚本会按 URL、DOI 和标题合并重复资料。
- 网页显示时会再做一次去重，避免同一条资料从不同来源重复出现。

## 本地预览

在终端运行：

```bash
cd /Users/zhouxinxin/Documents/Codex/2026-06-09/ai-github
python3 -m http.server 4177 --bind 127.0.0.1 -d docs
```

然后打开：

```text
http://127.0.0.1:4177
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

脚本会整理香港教育局、香港教育城、News.gov.hk、Google News、LinkedIn 公开线索入口、教育类顶刊 Crossref 资料，以及更多大学公开来源，并写入：

```text
docs/data/content.json
```

目前已加入的大学/教育技术相关来源包括：

- 港大教育学院、HKU CITE、HKU INSTEP、HKU ALiTE
- 港中文教育学院、CUHK CRI、CUHK CLST、CUHK CLEAR
- 香港教育大学 Events、Learning and Teaching、AEDI、AAPSEF
- 其他大学教学发展/教育科技网页会通过 Google News 线索补充发现

AI培训与讲座区会优先使用活动日期、报名截止日期或课程周期，避免把“网页更新时间”误当成“培训时间”。

LinkedIn 不直接抓取，只通过 Google 发现公开线索。

顶刊文章区使用 Crossref 公开 API，目前追踪：

- Computers & Education
- Teaching and Teacher Education
- British Journal of Educational Technology
- Educational Technology Research and Development
- Internet and Higher Education
- Learning and Instruction
- Journal of Computer Assisted Learning

## Codex 改完后同步到 GitHub

运行：

```bash
./scripts/sync.sh main "update Jojo Teacher AI Hub"
```

这会把 Codex 里的最新版本同步到 GitHub。

## 网站文件

- `docs/index.html`：网页结构
- `docs/styles.css`：简洁资料库风格界面
- `docs/app.js`：选项卡、新闻、培训讲座、LinkedIn、顶刊文章显示逻辑
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
Source: GitHub Actions
```

保存后，仓库里的 `Deploy GitHub Pages` workflow 会把 `docs` 文件夹发布到 GitHub Pages。
