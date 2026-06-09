const state = {
  data: null,
  search: "",
  source: "all",
};

const els = {
  updatedAt: document.querySelector("#updatedAt"),
  itemCount: document.querySelector("#itemCount"),
  sourceFilter: document.querySelector("#sourceFilter"),
  searchInput: document.querySelector("#searchInput"),
  trainingList: document.querySelector("#trainingList"),
  newsList: document.querySelector("#newsList"),
  summaryList: document.querySelector("#summaryList"),
  summaryResult: document.querySelector("#summaryResult"),
  summaryForm: document.querySelector("#summaryForm"),
  urlInput: document.querySelector("#urlInput"),
};

init();

async function init() {
  try {
    const response = await fetch("./data/content.json", { cache: "no-store" });
    state.data = await response.json();
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
  const data = state.data;
  const news = filteredItems(data.news).slice(0, 28);
  const training = filteredItems(data.training).slice(0, 24);
  const summaryCandidates = filteredItems([...data.news, ...data.discoveries]).slice(0, 14);
  const total = filteredItems(allItems()).length;

  els.updatedAt.textContent = `更新：${formatDateTime(data.updatedAt)}`;
  els.itemCount.textContent = `${total} 条资料`;

  renderCardList(els.newsList, news, "news");
  renderCardList(els.trainingList, training, "training");
  renderCardList(els.summaryList, summaryCandidates, "summary");

  if (!els.summaryResult.dataset.ready) {
    const first = summaryCandidates[0] || news[0] || training[0];
    if (first) renderSummary(first);
  }
}

function renderCardList(container, items, mode) {
  container.innerHTML = items.length ? items.map((item, index) => renderCard(item, mode, index)).join("") : emptyMarkup();
  container.querySelectorAll("[data-summary-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const item = allItems().find((entry) => entry.id === button.dataset.summaryId);
      if (item) renderSummary(item);
    });
  });
}

function renderCard(item, mode, index) {
  const tilt = ["tilt-left", "tilt-right", "tilt-none"][index % 3];
  const image = item.image ? `
    <img class="card-image" src="${escapeAttr(item.image)}" alt="${escapeAttr(item.title)}" loading="lazy" />
  ` : `
    <div class="card-image image-fallback ${sourceClass(item)}">
      <span>${escapeHtml(shortSource(item.source))}</span>
    </div>
  `;

  return `
    <article class="padlet-card ${tilt}">
      ${image}
      <div class="card-body">
        <div class="card-topline">
          <span class="date-pill">发布日期：${escapeHtml(formatDate(item.date))}</span>
          <span>${escapeHtml(item.source)}</span>
        </div>
        <h3>${escapeHtml(cleanTitle(item.title))}</h3>
        <p>${escapeHtml(item.summary)}</p>
        <div class="tags">${(item.tags || []).slice(0, 4).map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}</div>
        <div class="card-actions">
          <a href="${escapeAttr(item.url)}" target="_blank" rel="noopener">${mode === "training" ? "查看报名/详情" : "打开原文"}</a>
          ${mode === "summary" || mode === "news" ? `<button type="button" data-summary-id="${escapeAttr(item.id)}">生成总结</button>` : ""}
        </div>
      </div>
    </article>
  `;
}

function renderSummary(item) {
  els.summaryResult.dataset.ready = "true";
  els.summaryResult.innerHTML = `
    <h3>${escapeHtml(cleanTitle(item.title))}</h3>
    <p><strong>一句话总结：</strong>${escapeHtml(item.summary)}</p>
    <p><strong>重点内容：</strong>${escapeHtml(item.researchValue || "这条资料可作为香港 AI 教育发展、教师培训或政策环境的研究线索。")}</p>
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
    <p><strong>和教师 AI 研究的关系：</strong>建议先确认网页是否包含教师培训、AI教学实践、政策或学校案例。</p>
    <a href="${escapeAttr(url)}" target="_blank" rel="noopener">打开网页</a>
  `;
}

function filteredItems(items) {
  return items.filter((item) => {
    const sourceMatch = state.source === "all" || item.source === state.source;
    const haystack = [item.title, item.summary, item.source, ...(item.tags || [])].join(" ").toLowerCase();
    const searchMatch = !state.search || haystack.includes(state.search);
    return sourceMatch && searchMatch;
  });
}

function allItems() {
  const data = state.data || fallbackData();
  const merged = [...data.training, ...data.news, ...data.policies, ...data.events, ...data.discoveries];
  return [...new Map(merged.map((item) => [item.id, item])).values()].sort(sortByDateDesc);
}

function sortByDateDesc(a, b) {
  return new Date(b.date || 0) - new Date(a.date || 0);
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
  if (source.includes("EdCity")) return "EdCity";
  if (source.includes("Google")) return "Google News";
  if (source.includes("EDB")) return "EDB";
  if (source.includes("News.gov")) return "Gov News";
  return source.split(" ")[0];
}

function sourceClass(item) {
  const source = `${item.source || ""} ${item.category || ""}`.toLowerCase();
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
  };
}
