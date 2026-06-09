# 香港 AI 教育资料站

一个面向教师 AI 研究的静态资料站，聚合香港 AI 教育新闻、教师培训、政策追踪、活动日历，以及 Google / LinkedIn 公开线索发现区。

## 本地预览

```bash
python3 -m http.server 4173 -d docs
```

然后打开 `http://localhost:4173`。

## 更新数据

```bash
python3 scripts/update_data.py
```

脚本会抓取教育局 RSS、News.gov.hk RSS、EdCity 页面和 Google News RSS 查询结果，并写入 `docs/data/content.json`。

LinkedIn 不会被直接抓取；脚本只通过 Google News 搜索公开线索并保留原始链接。

## 在 Codex 修改后同步到 GitHub

### 方式一：先拉新、改、提交、推送（手工流程）

```bash
cd /Users/zhouxinxin/Documents/Codex/2026-06-09/ai-github
git pull --rebase origin main
git add .
git commit -m "update content"
git push origin main
```

先 `pull` 后改再推送，可以避免和 GitHub Action 自动更新同一文件时出现冲突。

### 方式二：一键同步（推荐）

```bash
./scripts/sync.sh
```

默认会执行：
1. `git pull --rebase origin main`
2. `git add .`
3. 生成带时间的 commit message（如 `chore: sync from codex 2026-06-09 14:30`）
4. `git push origin main`

> 建议把该脚本放在每次改完页面/数据后的最后一步：先更新 `docs/data/content.json`，再运行同步脚本。

### 连接方式（首次）

如果你用 SSH：`git@github.com:你的用户名/仓库名.git`  
如果你用 HTTPS：`https://github.com/你的用户名/仓库名.git`

首次提交前执行：

```bash
git init
git remote add origin git@github.com:你的用户名/仓库名.git  # 或 HTTPS
git branch -M main
git push -u origin main
```

## 部署建议

- GitHub Pages：将 Pages 来源设置为 `main` 分支的 `/docs` 文件夹。
- 阿里云：第一版建议使用中国香港 OSS 静态网站托管，或中国香港 ECS + Nginx。
- 域名：不是第一步必须购买。网站确认后再绑定自定义域名更稳。
