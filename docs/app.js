const state = {
  data: null,
  view: "overview",
  search: "",
  source: "all",
};

const els = {
  updatedAt: document.querySelector("#updatedAt"),
  itemCount: document.querySelector("#itemCount"),
  sourceFilter: document.querySelector("#sourceFilter"),
  searchInput: document.querySelector("#searchInput"),
  trainingCount: document.querySelector("#trainingCount"),
  newsCount: document.querySelector("#newsCount"),
  policyCount: document.querySelector("#policyCount"),
  discoveryCount: document.querySelector("#discoveryCount"),
  overviewGrid: document.querySelector("#overviewGrid"),
  trainingList: document.querySelector("#trainingList"),
  newsList: document.querySelector("#newsList"),
  summaryList: document.querySelector("#summaryList"),
  summaryResult: document.querySelector("#summaryResult"),
  policyTimeline: document.querySelector("#policyTimeline"),
  calendarList: document.querySelector("#calendarList"),
  discoveryList: document.querySelector("#discoveryList"),
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
  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => {
      state.view = button.dataset.view;
      document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("is-active", tab === button));
      document.querySelectorAll(".view").forEach((view) => view.classList.remove("is-visible"));
      document.querySelector(`#view-${state.view}`).classList.add("is-visible");
    });
  });

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
  const items = filteredItems(allItems());
  const training = filteredItems(data.training);
  const news = filteredItems(data.news);
  const policies = filteredItems(data.policies);
  const events = filteredItems(data.events);
  const discoveries = filteredItems(data.discoveries);

  els.updatedAt.textContent = `更新：${formatDateTime(data.updatedAt)}`;
  els.itemCount.textContent = `${items.length} 条记录`;
  els.trainingCount.textContent = training.length;
  els.newsCount.textContent = news.length;
  els.policyCount.textContent = policies.length;
  els.discoveryCount.textContent = discoveries.length;

  renderOverview(training, news, policies, discoveries);
  renderCardList(els.trainingList, training, "training");
  renderCardList(els.newsList, news, "news");
  renderCardList(els.summaryList, news.slice(0, 8), "summary");
  renderTimeline(policies);
  renderCalendar(events);
  renderCardList(els.discoveryList, discoveries, "discovery");

  if (!els.summaryResult.dataset.ready) {
    const first = news[0] || training[0] || policies[0];
    if (first) renderSummary(first);
  }
}

function renderOverview(training, news, policies, discoveries) {
  const panels = [
    ["AI教师培训", training.slice(0, 4)],
    ["香港AI教育每日新闻", news.slice(0, 4)],
    ["政策追踪", policies.slice(0, 4)],
    ["Google / LinkedIn发现", discoveries.slice(0, 4)],
  ];

  els.overviewGrid.innerHTML = panels
    .map(([title, list]) => `
      <article class="dashboard-panel">
        <h3>${escapeHtml(title)}</h3>
        ${list.length ? `<div class="mini-list">${list.map(renderMiniItem).join("")}</div>` : emptyMarkup()}
      </article>
    `)
    .join("");
}

function renderMiniItem(item) {
  return `
    <a class="mini-item" href="${escapeAttr(item.url)}" target="_blank" rel="noopener">
      <strong>${escapeHtml(item.title)}</strong>
      <span>${escapeHtml(item.source)} · ${escapeHtml(formatDate(item.date))}</span>
    </a>
  `;
}

function renderCardList(container, items, mode) {
  container.innerHTML = items.length ? items.map((item) => renderCard(item, mode)).join("") : emptyMarkup();
  container.querySelectorAll("[data-summary-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const item = allItems().find((entry) => entry.id === button.dataset.summaryId);
      if (item) renderSummary(item);
      state.view = "summaries";
      document.querySelector('[data-view="summaries"]').click();
    });
  });
}

function renderCard(item, mode) {
  const badgeClass = item.category === "政策" ? "policy" : item.category === "教师培训" ? "training" : "";
  return `
    <article class="news-card">
      <div class="card-topline">
        <span class="badge ${badgeClass}">${escapeHtml(item.category || "资料")}</span>
        <span>${escapeHtml(item.source)}</span>
        <span>${escapeHtml(formatDate(item.date))}</span>
      </div>
      <h3>${escapeHtml(item.title)}</h3>
      <p>${escapeHtml(item.summary)}</p>
      <div class="tags">${(item.tags || []).map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}</div>
      <div class="card-actions">
        <a href="${escapeAttr(item.url)}" target="_blank" rel="noopener">打开原文</a>
        ${mode === "summary" ? `<button type="button" data-summary-id="${escapeAttr(item.id)}">查看总结</button>` : ""}
      </div>
    </article>
  `;
}

function renderSummary(item) {
  els.summaryResult.dataset.ready = "true";
  els.summaryResult.innerHTML = `
    <h3>${escapeHtml(item.title)}</h3>
    <p><strong>一句话总结：</strong>${escapeHtml(item.summary)}</p>
    <p><strong>重点内容：</strong>${escapeHtml(item.researchValue || "这条资料可作为香港 AI 教育发展、教师培训或政策环境的研究线索。")}</p>
    <p><strong>与教师 AI 研究的关系：</strong>${escapeHtml(item.teacherResearchUse || "可用于追踪教师专业发展、AI素养培训、学校采纳教育科技的背景变化。")}</p>
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
    <p><strong>重点内容：</strong>每日更新脚本可在后续版本中加入该来源，或把它作为手动研究记录保存。</p>
    <p><strong>与教师 AI 研究的关系：</strong>建议先确认网页是否包含教师培训、AI教学实践、政策或学校案例。</p>
    <a href="${escapeAttr(url)}" target="_blank" rel="noopener">打开网页</a>
  `;
}

function renderTimeline(items) {
  els.policyTimeline.innerHTML = items.length
    ? items.map((item) => `
      <article class="timeline-item">
        <div class="timeline-date">${escapeHtml(formatDate(item.date))}</div>
        <div>
          <h3>${escapeHtml(item.title)}</h3>
          <p>${escapeHtml(item.summary)}</p>
          <a href="${escapeAttr(item.url)}" target="_blank" rel="noopener">${escapeHtml(item.source)}</a>
        </div>
      </article>
    `).join("")
    : emptyMarkup();
}

function renderCalendar(items) {
  els.calendarList.innerHTML = items.length
    ? items.map((item) => `
      <article class="calendar-item">
        <span class="calendar-date">${escapeHtml(formatDate(item.date))}</span>
        <h3>${escapeHtml(item.title)}</h3>
        <p>${escapeHtml(item.summary)}</p>
        <a href="${escapeAttr(item.url)}" target="_blank" rel="noopener">${escapeHtml(item.source)}</a>
      </article>
    `).join("")
    : emptyMarkup();
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

function formatDate(value) {
  if (!value) return "日期待定";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-Hant-HK", { year: "numeric", month: "short", day: "numeric" }).format(date);
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
