// Runs a saved workflow script under stubbed runtime hooks, so its control flow
// (validation, blinding, ordering, clamping, halting) is tested without
// spawning a single model call.
//
// The workflow runtime wraps the script body in an async function and injects
// agent, parallel, pipeline, phase, log, args, budget, and workflow. This does
// the same, and additionally shadows Date and Math so a script that calls
// Date.now(), new Date(), or Math.random() fails here the way it would break
// resume in the real runtime.

import { readFileSync } from "node:fs";

const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

export function readWorkflow(path) {
  const src = readFileSync(path, "utf8");
  if (!src.startsWith("export const meta = {")) {
    throw new Error(`${path}: a workflow must begin with "export const meta = {"`);
  }
  return src;
}

/** The meta literal, evaluated in an empty scope: any identifier reference throws. */
export function extractMeta(src) {
  const start = src.indexOf("{");
  let depth = 0;
  let end = -1;
  let quote = null;
  for (let i = start; i < src.length; i++) {
    const ch = src[i];
    if (quote) {
      if (ch === "\\") i++;
      else if (ch === quote) quote = null;
      continue;
    }
    if (ch === "'" || ch === '"' || ch === "`") quote = ch;
    else if (ch === "{") depth++;
    else if (ch === "}") {
      depth--;
      if (depth === 0) {
        end = i;
        break;
      }
    }
  }
  const literal = src.slice(start, end + 1);
  if (/[`]|\.\.\./.test(literal)) throw new Error("meta must be a pure literal: no template strings or spreads");
  return { literal, value: new Function(`"use strict"; return (${literal});`)() };
}

function forbiddenDate(...a) {
  if (a.length === 0) throw new Error("new Date() without arguments is unavailable in workflows");
  return new Date(...a);
}
forbiddenDate.now = () => {
  throw new Error("Date.now() is unavailable in workflows");
};

const safeMath = Object.create(Math);
safeMath.random = () => {
  throw new Error("Math.random() is unavailable in workflows");
};

// Every other road to wall-clock time or randomness is closed too: a script
// that reaches for globalThis.Date, crypto, performance, or process fails here.
function forbidden(name) {
  return new Proxy({}, {
    get() {
      throw new Error(`${name} is unavailable in workflows`);
    },
  });
}
const BLOCKED_GLOBALS = { crypto: forbidden("crypto"), performance: forbidden("performance"), process: forbidden("process") };
const safeGlobal = new Proxy(globalThis, {
  get(target, key) {
    if (key === "Date") return forbiddenDate;
    if (key === "Math") return safeMath;
    if (key in BLOCKED_GLOBALS) return BLOCKED_GLOBALS[key];
    return Reflect.get(target, key);
  },
});

/**
 * Run a workflow script. `respond(prompt, opts, index)` supplies each agent's
 * return value (return null to simulate a skipped or dead agent).
 */
export async function runWorkflow(src, args, respond) {
  const body = src.replace(/^export const meta =/, "const meta =");
  const fn = new AsyncFunction(
    "agent", "parallel", "pipeline", "phase", "log", "args", "budget", "workflow", "Date", "Math",
    "globalThis", "crypto", "performance", "process",
    body,
  );
  const calls = [];
  const phases = [];
  const logs = [];
  const agent = async (prompt, opts = {}) => {
    const index = calls.length;
    calls.push({ prompt, opts });
    return respond(prompt, opts, index);
  };
  const parallel = async (thunks) =>
    Promise.all(thunks.map((t) => Promise.resolve().then(t).catch(() => null)));
  const pipeline = async (items, ...stages) =>
    Promise.all(items.map(async (item, i) => {
      let value = item;
      for (const stage of stages) {
        try {
          value = await stage(value, item, i);
        } catch {
          return null;
        }
      }
      return value;
    }));
  const budget = { total: null, spent: () => 0, remaining: () => Infinity };
  const workflow = async () => {
    throw new Error("nested workflow() is not stubbed");
  };
  const result = await fn(
    agent, parallel, pipeline, (t) => phases.push(t), (m) => logs.push(m), args, budget, workflow,
    forbiddenDate, safeMath,
    safeGlobal, BLOCKED_GLOBALS.crypto, BLOCKED_GLOBALS.performance, BLOCKED_GLOBALS.process,
  );
  return { result, calls, phases, logs };
}
