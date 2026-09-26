#!/usr/bin/env node
// Copy and wall scan for any file, including the ones the Flutter suite never
// reads (index.html, web/, docs, the agent layer).
//
// The rules are NOT restated here. They are read at runtime from the Dart
// tests that own them, so this tool can never drift from the suite:
//   test/copy/walled_repo_test.dart     internal names and filing identifiers
//                                       (stored base64 there; decoded only in
//                                       memory here and never printed)
//   test/copy/product_language_test.dart recruiting vocabulary (--copy only)
// The typography rule (no em or en dashes) is the house rule from
// test/copy/no_em_dash_test.dart.
//
// Usage:  node .claude/tools/scan-copy.mjs [--copy] <file>...
// Exit:   0 clean, 1 findings, 2 could not run (a rule source is missing or
//         unreadable). Fail closed: a scan that could not load its rules
//         never reports clean.

import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");

const WALLED_SOURCE = "test/copy/walled_repo_test.dart";
const LANGUAGE_SOURCE = "test/copy/product_language_test.dart";

// Built from code points so this file never contains the characters it bans.
const DASHES = [
  { char: String.fromCharCode(0x2014), name: "em dash" },
  { char: String.fromCharCode(0x2013), name: "en dash" },
];

export class RuleSourceError extends Error {}

function readRuleSource(relPath, root) {
  try {
    return readFileSync(join(root, relPath), "utf8");
  } catch (err) {
    throw new RuleSourceError(`cannot read rule source ${relPath}: ${err.code ?? err.message}`);
  }
}

/** Decoded walled terms, upper-cased, exactly as the Dart guard compares them. */
export function loadWalledTerms(root = REPO_ROOT) {
  const src = readRuleSource(WALLED_SOURCE, root);
  const open = src.indexOf("_banned = <String>[");
  const close = open === -1 ? -1 : src.indexOf("]", open);
  if (open === -1 || close === -1) {
    throw new RuleSourceError(`${WALLED_SOURCE}: banned list not found`);
  }
  const encoded = [...src.slice(open, close).matchAll(/["']([A-Za-z0-9+/=]{4,})["']/g)].map((m) => m[1]);
  if (encoded.length === 0) {
    throw new RuleSourceError(`${WALLED_SOURCE}: banned list is empty`);
  }
  return encoded.map((e) => Buffer.from(e, "base64").toString("utf8").toUpperCase());
}

/** The recruiting vocabulary list from the product-language test. */
export function loadRecruitingWords(root = REPO_ROOT) {
  const src = readRuleSource(LANGUAGE_SOURCE, root);
  const open = src.indexOf("_bannedWords = <String>[");
  const close = open === -1 ? -1 : src.indexOf("];", open);
  if (open === -1 || close === -1) {
    throw new RuleSourceError(`${LANGUAGE_SOURCE}: banned word list not found`);
  }
  const words = [...src.slice(open, close).matchAll(/"([a-z]+)"/g)].map((m) => m[1]);
  if (words.length === 0) {
    throw new RuleSourceError(`${LANGUAGE_SOURCE}: banned word list is empty`);
  }
  return words;
}

// Embedded images are base64 noise; a word boundary inside one is not copy.
const DATA_URI = /data:[^"')\s]+/g;

/**
 * Scan text. Returns findings as {line, rule, detail}. Walled terms are
 * reported by index only; the decoded term never leaves memory.
 */
export function scanText(text, { path = "", walled = [], recruiting = null } = {}) {
  const findings = [];
  const upperPath = path.toUpperCase();
  walled.forEach((term, i) => {
    if (upperPath.includes(term)) {
      findings.push({ line: 0, rule: "walled-term", detail: `walled term #${i + 1} in file path` });
    }
  });
  const lines = text.split(/\r?\n/);
  lines.forEach((raw, idx) => {
    const line = idx + 1;
    for (const d of DASHES) {
      if (raw.includes(d.char)) findings.push({ line, rule: "dash", detail: d.name });
    }
    const upper = raw.toUpperCase();
    walled.forEach((term, i) => {
      if (upper.includes(term)) {
        findings.push({ line, rule: "walled-term", detail: `walled term #${i + 1}` });
      }
    });
    if (recruiting) {
      const visible = raw.replace(DATA_URI, "");
      for (const word of recruiting) {
        if (new RegExp(`\\b${word}\\b`, "i").test(visible)) {
          findings.push({ line, rule: "recruiting-vocabulary", detail: `"${word}"` });
        }
      }
    }
  });
  return findings;
}

export function scanFiles(paths, { copy = false, root = REPO_ROOT } = {}) {
  const walled = loadWalledTerms(root);
  const recruiting = copy ? loadRecruitingWords(root) : null;
  const results = [];
  for (const p of paths) {
    let text;
    try {
      text = readFileSync(resolve(root, p), "utf8");
    } catch (err) {
      results.push({ path: p, line: 0, rule: "unreadable", detail: err.code ?? err.message });
      continue;
    }
    for (const f of scanText(text, { path: p, walled, recruiting })) results.push({ path: p, ...f });
  }
  return results;
}

function main(argv) {
  const copy = argv.includes("--copy");
  const paths = argv.filter((a) => a !== "--copy");
  if (paths.length === 0) {
    console.error("usage: node .claude/tools/scan-copy.mjs [--copy] <file>...");
    return 2;
  }
  let results;
  try {
    results = scanFiles(paths, { copy });
  } catch (err) {
    if (err instanceof RuleSourceError) {
      console.error(`SCAN NOT RUN: ${err.message}`);
      return 2;
    }
    throw err;
  }
  for (const r of results) console.log(`${r.path}:${r.line}  ${r.rule}  ${r.detail}`);
  const unreadable = results.some((r) => r.rule === "unreadable");
  console.log(results.length === 0 ? `CLEAN: ${paths.length} file(s)` : `FINDINGS: ${results.length}`);
  if (unreadable) return 2;
  return results.length === 0 ? 0 : 1;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = main(process.argv.slice(2));
}
