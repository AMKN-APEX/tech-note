import {
  cardsFromDay, normalize, loadState, saveState, enroll, dueCards, grade, exportState, importState,
} from "./review.js";

const ENROLL_DAYS = 30;
const REVIEW_LIMIT = 5;
const $ = (sel, root = document) => root.querySelector(sel);

const storage = (() => {
  try {
    const s = window.localStorage;
    s.getItem("probe");
    return s;
  } catch {
    const m = {};
    return { getItem: (k) => m[k] ?? null, setItem: (k, v) => { m[k] = String(v); } };
  }
})();

const dayCache = new Map();
let terms = {};
let state = loadState(storage);
let queue = [];

async function getJSON(path) {
  const res = await fetch(path, { cache: "no-cache" });
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json();
}

async function getDay(date) {
  if (!dayCache.has(date)) dayCache.set(date, getJSON(`data/days/${date}.json`));
  return dayCache.get(date);
}

function lookupTerm(name) {
  return terms[normalize(name)];
}

// ---------- 今日 ----------
function renderTerm(t) {
  const el = $("#term-tpl").content.firstElementChild.cloneNode(true);
  $(".name", el).textContent = t.name;
  $(".def", el).textContent = t.definition;
  return el;
}

function renderTopic(topic, date) {
  const el = $("#topic-tpl").content.firstElementChild.cloneNode(true);
  $(".field", el).textContent = topic.field;
  $(".title", el).textContent = topic.title;
  $(".question", el).textContent = topic.question;
  const summary = $(".summary", el);
  for (const line of topic.summary) {
    const li = document.createElement("li");
    li.textContent = line;
    summary.append(li);
  }
  $(".mechanism", el).textContent = topic.mechanism;

  const termBox = $(".terms", el);
  const defBox = $(".term-def", el);
  for (const name of topic.terms) {
    const entry = lookupTerm(name);
    const chip = document.createElement("button");
    chip.className = "chip";
    chip.textContent = name;
    if (entry && entry.first_seen < date) {
      const badge = document.createElement("span");
      badge.className = "known";
      badge.textContent = "既習";
      chip.append(badge);
    }
    chip.addEventListener("click", () => {
      defBox.hidden = false;
      defBox.textContent = entry ? `${entry.name}：${entry.definition}` : `${name}：（辞書に未登録）`;
    });
    termBox.append(chip);
  }

  const conns = $(".connections", el);
  for (const c of topic.connections) {
    const li = document.createElement("li");
    li.textContent = `${c.target} — ${c.note}`;
    conns.append(li);
  }
  if (!topic.connections.length) $(".connections-wrap", el).hidden = true;

  const hook = $(".hook", el);
  hook.textContent = topic.hook;
  if (!topic.hook) hook.hidden = true;

  const src = $(".source", el);
  src.href = topic.source_url;
  src.textContent = `出典：${topic.source_title}`;

  $(".reveal", el).addEventListener("click", (e) => {
    $(".answer", el).hidden = false;
    e.currentTarget.hidden = true;
  });
  return el;
}

function renderToday(day) {
  const view = $("#view-today");
  view.replaceChildren();
  $("#date").textContent = day.date;
  if (day.new_terms.length) {
    const h = document.createElement("h2");
    h.textContent = "今日の基礎用語";
    view.append(h, ...day.new_terms.map(renderTerm));
  }
  const h = document.createElement("h2");
  h.textContent = "今日の話題";
  view.append(h, ...day.topics.map((t) => renderTopic(t, day.date)));
}

// ---------- 復習 ----------
async function cardContent(id) {
  if (id.startsWith("term:")) {
    const entry = lookupTerm(id.slice(5));
    return { label: "基礎用語", front: entry ? entry.name : id.slice(5), back: entry ? entry.definition : "（辞書に未登録）" };
  }
  const topicId = id.slice(6);
  const date = topicId.slice(0, 10);
  try {
    const day = await getDay(date);
    const card = cardsFromDay(day).find((c) => c.id === id);
    const topic = day.topics.find((t) => t.id === topicId);
    if (card) return { label: topic.title, front: card.front, back: card.back };
  } catch { /* fall through */ }
  return { label: "話題", front: topicId, back: "（データが見つかりません）" };
}

function updateBadge() {
  const n = dueCards(state, new Date(), Infinity).length;
  const badge = $("#due-badge");
  badge.hidden = n === 0;
  badge.textContent = String(n);
}

function startReview() {
  queue = dueCards(state, new Date(), REVIEW_LIMIT);
  showNext(queue.length);
}

async function showNext(total) {
  const view = $("#view-review");
  view.replaceChildren();
  if (!queue.length) {
    const done = document.createElement("div");
    done.className = "card progress";
    const p = document.createElement("p");
    p.textContent = total ? "今日の復習は完了！" : "今は復習するカードがありません。";
    done.append(p);
    if (dueCards(state, new Date(), 1).length) {
      const more = document.createElement("button");
      more.className = "btn secondary";
      more.textContent = "もう少しやる";
      more.addEventListener("click", startReview);
      done.append(more);
    }
    view.append(done);
    return;
  }
  const id = queue[0];
  const c = await cardContent(id);
  const card = document.createElement("article");
  card.className = "card";
  const progress = document.createElement("div");
  progress.className = "label";
  progress.textContent = `${total - queue.length + 1} / ${total} ・ ${c.label}`;
  const front = document.createElement("p");
  front.className = "review-front";
  front.textContent = c.front;
  const reveal = document.createElement("button");
  reveal.className = "btn";
  reveal.textContent = "答えを見る";
  const back = document.createElement("div");
  back.className = "review-back";
  back.textContent = c.back;
  back.hidden = true;
  const grades = document.createElement("div");
  grades.className = "grades";
  grades.hidden = true;
  [["もう一度", 1], ["難しい", 2], ["できた", 3], ["簡単", 4]].forEach(([label, rating]) => {
    const b = document.createElement("button");
    b.textContent = label;
    b.addEventListener("click", () => {
      state = grade(state, id, rating, new Date());
      saveState(storage, state);
      queue.shift();
      updateBadge();
      showNext(total);
    });
    grades.append(b);
  });
  reveal.addEventListener("click", () => {
    back.hidden = false;
    grades.hidden = false;
    reveal.hidden = true;
  });
  card.append(progress, front, reveal, back, grades);
  view.append(card);
}

// ---------- 設定 ----------
function setupSettings() {
  const msg = $("#settings-msg");
  $("#export").addEventListener("click", () => {
    $("#backup").value = exportState(state);
    msg.textContent = "上の文字列をコピーして保存してください。";
  });
  $("#import").addEventListener("click", () => {
    try {
      state = importState($("#backup").value);
      saveState(storage, state);
      updateBadge();
      msg.textContent = "インポートしました。";
    } catch (e) {
      msg.textContent = `インポートできませんでした：${e.message}`;
    }
  });
}

// ---------- タブ ----------
const TITLES = { today: "今日", review: "復習", settings: "設定" };
function show(view) {
  for (const b of document.querySelectorAll(".tabs button")) b.classList.toggle("active", b.dataset.view === view);
  for (const v of Object.keys(TITLES)) $(`#view-${v}`).hidden = v !== view;
  $("#heading").textContent = TITLES[view];
  $("#date").hidden = view !== "today";
  if (view === "review") startReview();
}

async function init() {
  setupSettings();
  for (const b of document.querySelectorAll(".tabs button")) b.addEventListener("click", () => show(b.dataset.view));
  try {
    const [index, termData] = await Promise.all([getJSON("data/index.json"), getJSON("data/terms.json")]);
    terms = termData;
    if (!index.days.length) throw new Error("まだデータがありません");
    const recent = index.days.slice(0, ENROLL_DAYS);
    const days = await Promise.all(recent.map((d) => getDay(d).catch(() => null)));
    const now = new Date();
    for (const day of days.filter(Boolean).reverse()) state = enroll(state, cardsFromDay(day), now);
    saveState(storage, state);
    if (days[0]) renderToday(days[0]);
    updateBadge();
  } catch (e) {
    const p = document.createElement("p");
    p.className = "card";
    p.textContent = `データを読み込めませんでした：${e.message}`;
    $("#view-today").replaceChildren(p);
  }
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
}

init();
