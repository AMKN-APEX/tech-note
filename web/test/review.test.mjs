import { test } from "node:test";
import assert from "node:assert/strict";
import {
  cardsFromDay, loadState, saveState, enroll, dueCards, grade, exportState, importState, KEY,
} from "../review.js";

const memStorage = (init = {}) => {
  const m = { ...init };
  return { getItem: (k) => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = String(v); }, _m: m };
};
const throwing = { getItem() { throw new Error("blocked"); }, setItem() { throw new Error("blocked"); } };

const day = {
  date: "2026-11-25",
  new_terms: [{ name: "焼却炉", definition: "ごみを燃やす設備。", field: "環境" }],
  topics: [1, 2].map((n) => ({
    id: `2026-11-25-${n}`, title: `話題${n}`, question: `問い${n}`,
    summary: ["一", "二", "三"], mechanism: "仕組み", terms: [], connections: [], hook: "", field: "",
  })),
};
const now = new Date("2026-11-25T07:00:00+09:00");

test("cardsFromDay makes term and topic cards", () => {
  const cards = cardsFromDay(day);
  assert.deepEqual(cards.map((c) => c.id), ["term:焼却炉", "topic:2026-11-25-1", "topic:2026-11-25-2"]);
  assert.equal(cards[1].front, "問い1");
});

test("loadState returns empty on corrupt json", () => {
  assert.deepEqual(loadState(memStorage({ [KEY]: "{" })), { version: 1, cards: {} });
});

test("loadState returns empty on throwing storage, saveState swallows", () => {
  assert.deepEqual(loadState(throwing), { version: 1, cards: {} });
  assert.doesNotThrow(() => saveState(throwing, { version: 1, cards: {} }));
});

test("enroll then dueCards returns new cards up to limit 5", () => {
  const many = { ...day, new_terms: Array.from({ length: 6 }, (_, i) => ({ name: `t${i}`, definition: "d", field: "" })) };
  let s = enroll({ version: 1, cards: {} }, cardsFromDay(many), now);
  assert.equal(Object.keys(s.cards).length, 8);
  assert.equal(dueCards(s, now).length, 5);
  s = enroll(s, cardsFromDay(many), now); // re-enroll keeps existing
  assert.equal(Object.keys(s.cards).length, 8);
});

test("grade Good pushes due into future", () => {
  let s = enroll({ version: 1, cards: {} }, cardsFromDay(day), now);
  s = grade(s, "term:焼却炉", 3, now);
  assert.ok(new Date(s.cards["term:焼却炉"].due) > now);
  assert.ok(!dueCards(s, now).includes("term:焼却炉"));
});

test("state survives save/load and export/import roundtrip", () => {
  let s = enroll({ version: 1, cards: {} }, cardsFromDay(day), now);
  s = grade(s, "term:焼却炉", 3, now);
  const st = memStorage();
  saveState(st, s);
  const loaded = loadState(st);
  assert.deepEqual(importState(exportState(loaded)), loaded);
  assert.doesNotThrow(() => grade(loaded, "term:焼却炉", 3, new Date("2026-12-10T07:00:00+09:00")));
});

test("importState rejects garbage", () => {
  assert.throws(() => importState("nope"));
  assert.throws(() => importState('{"version":1}'));
});
