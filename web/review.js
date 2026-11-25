// Review scheduling (FSRS). DOM-independent so it can be tested with node --test.
import { fsrs, createEmptyCard, TypeConvert } from "./vendor/ts-fsrs.mjs";

export const KEY = "tech-trivia-review-v1";
const scheduler = fsrs();
const empty = () => ({ version: 1, cards: {} });

// Must match normalize_term() in generator/store.py.
export const normalize = (s) => s.normalize("NFKC").replace(/\s+/g, "").toLowerCase();

export function cardsFromDay(day) {
  const terms = (day.new_terms || []).map((t) => ({
    id: `term:${normalize(t.name)}`, kind: "term", front: t.name, back: t.definition,
  }));
  const topics = (day.topics || []).map((t) => ({
    id: `topic:${t.id}`, kind: "topic", front: t.question,
    back: [...t.summary, "", t.mechanism].join("\n"),
  }));
  return [...topics, ...terms];
}

function isState(s) {
  return s && typeof s === "object" && s.version === 1 && s.cards && typeof s.cards === "object";
}

export function loadState(storage) {
  try {
    const s = JSON.parse(storage.getItem(KEY));
    return isState(s) ? s : empty();
  } catch {
    return empty();
  }
}

export function saveState(storage, state) {
  try {
    storage.setItem(KEY, JSON.stringify(state));
  } catch {
    /* storage unavailable: keep working in memory */
  }
}

const localDate = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

// Introduce at most maxNew unseen cards per local day so the review load stays
// within the daily budget; the rest are picked up on later days.
export function enroll(state, cards, now, maxNew = 5) {
  const today = localDate(now);
  const next = { ...state, cards: { ...state.cards }, newByDay: { [today]: state.newByDay?.[today] ?? 0 } };
  for (const c of cards) {
    if (next.cards[c.id]) continue;
    if (next.newByDay[today] >= maxNew) break;
    next.cards[c.id] = JSON.parse(JSON.stringify(createEmptyCard(now)));
    next.newByDay[today] += 1;
  }
  return next;
}

export function dueCards(state, now, limit = 5) {
  return Object.entries(state.cards)
    .filter(([, c]) => new Date(c.due) <= now)
    .sort(([, a], [, b]) => new Date(a.due) - new Date(b.due))
    .slice(0, limit)
    .map(([id]) => id);
}

export function grade(state, id, rating, now) {
  const card = TypeConvert.card(state.cards[id]);
  const { card: updated } = scheduler.next(card, now, rating);
  return { ...state, cards: { ...state.cards, [id]: JSON.parse(JSON.stringify(updated)) } };
}

export function exportState(state) {
  return JSON.stringify(state);
}

export function importState(text) {
  const s = JSON.parse(text);
  if (!isState(s)) throw new Error("復習データの形式が正しくありません");
  return s;
}

export function videoSearchUrl(topic) {
  return `https://www.youtube.com/results?search_query=${encodeURIComponent(topic.video_query || topic.title)}`;
}
