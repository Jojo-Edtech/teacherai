const PAGES = ["news", "training", "linkedin", "journals"];

const state = {
  data: null,
  search: "",
  source: "all",
  page: initialPage(),
};

const els = {
  updatedAt: document.querySelector("#updatedAt"),
  itemCount: document.querySelector("#itemCount"),
  sourceFilter: document.querySelector("#sourceFilter"),
  searchInput: document.querySelector("#searchInput"),
  tabButtons: [...document.querySelectorAll("[data-page]")],
  pagePanels: [...document.querySelectorAll("[data-page-panel]")],
  newsList: document.querySelector("#newsList"),
  trainingList: document.querySelector("#trainingList"),
  linkedinList: document.querySelector("#linkedinList"),
  journalList: document.querySelector("#journalList"),
  newsCount: document.querySelector("#newsCount"),
  trainingCount: document.querySelector("#trainingCount"),
  linkedinCount: document.querySelector("#linkedinCount"),
  journalCount: document.querySelector("#journalCount"),
  summaryResult: document.querySelector("#summaryResult"),
  summaryForm: document.querySelector("#summaryForm"),
  urlInput: document.querySelector("#urlInput"),
};

init();

async function init() {
  try {
    const response = await fetch("./data/content.json", { cache: "no-store" });
    state.data = normalizeData(await response.json());
  } catch (error) {
    state.data = fallbackData();
  }

  bindEvents();
  hydrateSources();
  render();
}

function bindEvents() {
  els.searchInput.addEventListener("input", (event) => {
    state.search = event.target.value.trim().toLowerCase();
    render();
  });

  els.sourceFilter.addEventListener("change", (event) => {
    state.source = event.target.value;
    render();
  });

  els.summaryForm.addEventListener("submit", (event) => {
    event.preventDefault();
    renderManualSummary(els.urlInput.value.trim());
  });

  els.tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      setPage(button.dataset.page);
    });
  });

  window.addEventListener("hashchange", () => {
    state.page = initialPage();
    render();
  });
}

function hydrateSources() {
  const sources = [...new Set(allItems().map((item) => item.source))].sort((a, b) => a.localeCompare(b, "zh-Hant"));
  sources.forEach((source) => {
    const option = document.createElement("option");
    option.value = source;
    option.textContent = source;
    els.sourceFilter.append(option);
  });
}

function render() {
  const collections = getCollections();
  const filtered = {
    news: filteredItems(collections.news),
    training: filteredItems(collections.training),
    linkedin: filteredItems(collections.linkedin),
    journals: filteredItems(collections.journals),
  };
  const total = filteredItems(allItems()).length;

  els.updatedAt.textContent = `更新：${formatDateTime(state.data.updatedAt)}`;
  els.itemCount.textContent = `${total} 条资料`;
  els.newsCount.textContent = filtered.news.length;
  els.trainingCount.textContent = filtered.training.length;
  els.linkedinCount.textContent = filtered.linkedin.length;
  els.journalCount.textContent = filtered.journals.length;

  renderTabs();
  renderCardList(els.newsList, filtered.news.slice(0, 48), "news");
  renderCardList(els.trainingList, filtered.training.slice(0, 48), "training");
  renderCardList(els.linkedinList, filtered.linkedin.slice(0, 48), "linkedin");
  renderCardList(els.journalList, filtered.journals.slice(0, 80), "journal");

  if (!els.summaryResult.dataset.ready) {
    const first = filtered.news[0] || filtered.training[0] || filtered.journals[0];
    if (first) renderSummary(first);
  }
}

function renderTabs() {
  els.tabButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.page === state.page);
  });
  els.pagePanels.forEach((panel) => {
    panel.classList.toggle("is-active", panel.dataset.pagePanel === state.page);
  });
}

function renderCardList(container, items, mode) {
  container.innerHTML = items.length ? items.map((item, index) => renderCard(item, mode, index)).join("") : emptyMarkup();
  container.querySelectorAll("[data-summary-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const item = allItems().find((entry) => entry.id === button.dataset.summaryId);
      if (item) renderSummary(item);
      setPage("news");
    });
  });
}

function renderCard(item, mode, index) {
  const tilt = ["tilt-left", "tilt-right", "tilt-none"][index % 3];
  const actionUrl = mode === "training" ? (item.registerUrl || item.url) : item.url;
  const image = item.image ? `
    <img class="card-image" src="${escapeAttr(item.image)}" alt="${escapeAttr(item.title)}" loading="lazy" />
  ` : `
    <div class="card-image image-fallback ${sourceClass(item)}">
      <span>${escapeHtml(shortSource(item.source))}</span>
    </div>
  `;
  const canSummarize = ["news", "linkedin", "journal"].includes(mode);

  return `
    <article class="padlet-card ${tilt}">
      ${image}
      <div class="card-body">
        <div class="card-topline">
          <span class="date-pill">${escapeHtml(dateLabel(item, mode))}</span>
          <span>${escapeHtml(item.source)}</span>
        </div>
        <h3>${escapeHtml(cleanTitle(item.title))}</h3>
        <p>${escapeHtml(item.summary)}</p>
        ${mode === "training" ? renderTrainingDetails(item) : ""}
        ${mode === "journal" ? renderJournalDetails(item) : ""}
        <div class="tags">${(item.tags || []).slice(0, 5).map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}</div>
        <div class="card-actions">
          <a href="${escapeAttr(actionUrl)}" target="_blank" rel="noopener">${actionLabel(item, mode)}</a>
          ${canSummarize ? `<button type="button" data-summary-id="${escapeAttr(item.id)}">生成总结</button>` : ""}
        </div>
      </div>
    </article>
  `;
}

function renderTrainingDetails(item) {
  const details = [];
  if (item.eventDate) details.push(`活动日期：${formatDate(item.eventDate)}`);
  if (item.eventTime) details.push(`时间：${item.eventTime}`);
  if (item.deadlineDate) details.push(`报名截止：${formatDate(item.deadlineDate)}`);
  if (item.period) details.push(`课程周期：${item.period}`);
  if (!details.length) return "";
  return `<div class="training-details">${details.map((detail) => `<span>${escapeHtml(detail)}</span>`).join("")}</div>`;
}

function renderJournalDetails(item) {
  const details = [];
  if (item.journal) details.push(`期刊：${item.journal}`);
  if (item.authors) details.push(`作者：${item.authors}`);
  if (item.doi) details.push(`DOI：${item.doi}`);
  if (!details.length) return "";
  return `<div class="training-details journal-details">${details.map((detail) => `<span>${escapeHtml(detail)}</span>`).join("")}</div>`;
}

function dateLabel(item, mode) {
  if (mode === "training") {
    if (item.deadlineDate) return `报名截止：${formatDate(item.deadlineDate)}`;
    if (item.eventDate) return `活动日期：${formatDate(item.eventDate)}`;
    if (item.period) return `课程周期：${item.period}`;
    return "日期待核对";
  }
  if (mode === "journal") return `发表日期：${formatDate(item.publishedDate || item.date)}`;
  if (mode === "linkedin") return `发现日期：${formatDate(item.publishedDate || item.date)}`;
  return `发布日期：${formatDate(item.publishedDate || item.date)}`;
}

function actionLabel(item, mode) {
  if (mode === "training") return item.registerUrl ? "打开报名链接" : "查看详情";
  if (mode === "journal") return item.doi ? "打开论文/DOI" : "打开文章";
  if (mode === "linkedin") return "打开线索";
  return "打开原文";
}

function renderSummary(item) {
  els.summaryResult.dataset.ready = "true";
  els.summaryResult.innerHTML = `
    <h3>${escapeHtml(cleanTitle(item.title))}</h3>
    <p><strong>一句话总结：</strong>${escapeHtml(item.summary)}</p>
    <p><strong>重点内容：</strong>${escapeHtml(item.researchValue || "这条资料可作为香港 AI 教育发展、教师培训、文献追踪或政策环境的研究线索。")}</p>
    <p><strong>和教师 AI 研究的关系：</strong>${escapeHtml(item.teacherResearchUse || "可用于追踪教师专业发展、AI素养培训、学校采纳教育科技的背景变化。")}</p>
    <a href="${escapeAttr(item.url)}" target="_blank" rel="noopener">查看原文链接</a>
  `;
}

function renderManualSummary(url) {
  if (!url) return;
  const match = allItems().find((item) => item.url === url);
  if (match) {
    renderSummary(match);
    return;
  }

  els.summaryResult.dataset.ready = "true";
  els.summaryResult.innerHTML = `
    <h3>待整理网页</h3>
    <p><strong>一句话总结：</strong>这个链接尚未进入资料库。</p>
    <p><strong>重点内容：</strong>之后可以把这个来源加入每日更新脚本，或作为手动研究记录保存。</p>
    <p><strong>和教师 AI 研究的关系：</strong>建议先确认网页是否包含教师培训、AI教学实践、政策、学校案例或研究文章。</p>
    <a href="${escapeAttr(url)}" target="_blank" rel="noopener">打开网页</a>
  `;
}

function getCollections() {
  const data = state.data || fallbackData();
  const news = dedupeItems([...(data.news || []), ...(data.policies || []), ...(data.discoveries || []).filter((item) => !isLinkedInItem(item))]).sort(sortByDateDesc);
  const linkedin = dedupeItems([...(data.linkedin || []), ...(data.discoveries || []).filter(isLinkedInItem)]).sort(sortByDateDesc);
  return {
    news,
    training: dedupeItems(data.training || []).sort(sortByTrainingDate),
    linkedin,
    journals: dedupeItems(data.journals || []).sort(sortByDateDesc),
  };
}

function filteredItems(items) {
  return items.filter((item) => {
    const sourceMatch = state.source === "all" || item.source === state.source;
    const haystack = [item.title, item.summary, item.source, item.journal, item.authors, item.doi, ...(item.tags || [])].join(" ").toLowerCase();
    const searchMatch = !state.search || haystack.includes(state.search);
    return sourceMatch && searchMatch;
  });
}

function allItems() {
  const data = state.data || fallbackData();
  const merged = [
    ...(data.training || []),
    ...(data.news || []),
    ...(data.policies || []),
    ...(data.events || []),
    ...(data.discoveries || []),
    ...(data.linkedin || []),
    ...(data.journals || []),
  ];
  return dedupeItems(merged).sort(sortByDateDesc);
}

function dedupeItems(items) {
  return [...new Map(items.map((item) => [item.id, item])).values()];
}

function sortByDateDesc(a, b) {
  return new Date(b.publishedDate || b.date || 0) - new Date(a.publishedDate || a.date || 0);
}

function sortByTrainingDate(a, b) {
  const aDate = a.deadlineDate || a.eventDate || a.date || "";
  const bDate = b.deadlineDate || b.eventDate || b.date || "";
  return new Date(aDate || 0) - new Date(bDate || 0);
}

function isLinkedInItem(item) {
  const text = `${item.source || ""} ${item.url || ""} ${(item.tags || []).join(" ")}`.toLowerCase();
  return text.includes("linkedin");
}

function setPage(page, updateHash = true) {
  if (!PAGES.includes(page)) return;
  state.page = page;
  if (updateHash) {
    window.location.hash = page;
  }
  render();
}

function initialPage() {
  const page = window.location.hash.replace("#", "");
  return PAGES.includes(page) ? page : "news";
}

function normalizeData(data) {
  return {
    ...fallbackData(),
    ...data,
    training: data.training || [],
    news: data.news || [],
    policies: data.policies || [],
    events: data.events || [],
    discoveries: data.discoveries || [],
    linkedin: data.linkedin || [],
    journals: data.journals || [],
  };
}

function cleanTitle(title) {
  return String(title || "")
    .replace(/\s+-\s+香港文匯網\s+-?\s*香港文匯網/g, "")
    .replace(/\s+-\s+Google News/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function shortSource(source) {
  if (!source) return "AIED";
  if (source.includes("顶刊")) return "Journal";
  if (source.includes("LinkedIn")) return "LinkedIn";
  if (source.includes("EdCity")) return "EdCity";
  if (source.includes("Google")) return "Google";
  if (source.includes("EDB")) return "EDB";
  if (source.includes("News.gov")) return "Gov News";
  return source.split(" ")[0];
}

function sourceClass(item) {
  const source = `${item.source || ""} ${item.category || ""} ${item.kind || ""}`.toLowerCase();
  if (source.includes("journal") || source.includes("顶刊")) return "image-journal";
  if (source.includes("linkedin")) return "image-linkedin";
  if (source.includes("edcity") || source.includes("教师培训")) return "image-training";
  if (source.includes("google")) return "image-google";
  if (source.includes("edb") || source.includes("news.gov")) return "image-gov";
  return "image-news";
}

function formatDate(value) {
  if (!value) return "日期待定";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-Hant-HK", { year: "numeric", month: "long", day: "numeric" }).format(date);
}

function formatDateTime(value) {
  if (!value) return "尚未更新";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-Hant-HK", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function emptyMarkup() {
  return `<div class="empty">暂无符合条件的记录。</div>`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[char]));
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, "&#096;");
}

function fallbackData() {
  return {
    updatedAt: new Date().toISOString(),
    training: [],
    news: [],
    policies: [],
    events: [],
    discoveries: [],
    linkedin: [],
    journals: [],
  };
}
