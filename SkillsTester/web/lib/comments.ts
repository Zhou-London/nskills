// Client-safe lexing helpers used by the side-by-side output viewer: they
// split a file into lines whose comment spans are marked, so the viewer can
// tint comments and count how much of each file the agent actually wrote as
// documentation. The scanners are deliberately approximate — they only need
// to be right on ordinary source files, not on every legal edge case.

export type Lang = "c" | "py" | "text";

const C_EXT = new Set([
  "c", "h", "hh", "hpp", "cc", "cpp", "cxx", "cu", "java", "js", "jsx", "ts",
  "tsx", "go", "rs", "swift", "kt", "cs", "scala", "proto",
]);
const PY_EXT = new Set(["py", "pyi", "pyx"]);

/** Comment syntax family for a file name, or "text" when it has none. */
export function langOf(name: string): Lang {
  const ext = name.slice(name.lastIndexOf(".") + 1).toLowerCase();
  if (C_EXT.has(ext)) return "c";
  if (PY_EXT.has(ext)) return "py";
  return "text";
}

/** A run of characters that is either all comment or all code. */
export interface Seg {
  t: string;
  c: boolean;
}

export interface CodeLine {
  n: number;
  segs: Seg[];
  /** The line carries at least one non-blank comment character. */
  hasComment: boolean;
  /** The line carries at least one non-blank character outside a comment. */
  hasCode: boolean;
}

export interface CommentStats {
  lines: number;
  commentLines: number;
  codeLines: number;
  /** Words of comment prose, markers and a leading license header stripped. */
  words: number;
  /** commentLines / (commentLines + codeLines), as a percentage. */
  density: number;
}

/**
 * Marks every character of `src` that belongs to a comment.
 *
 * Tracks string literals so that a `//` or `#` inside a string is not mistaken
 * for a comment. Python triple-quoted strings count as comments, which is what
 * makes docstrings show up as documentation in the viewer.
 */
function commentMask(src: string, lang: Lang): Uint8Array {
  const mask = new Uint8Array(src.length);
  if (lang === "text") return mask;
  let i = 0;
  const n = src.length;
  while (i < n) {
    const ch = src[i];
    const two = src.slice(i, i + 2);
    const three = src.slice(i, i + 3);
    if (lang === "c" && two === "//") {
      while (i < n && src[i] !== "\n") mask[i++] = 1;
      continue;
    }
    if (lang === "c" && two === "/*") {
      const end = src.indexOf("*/", i + 2);
      const stop = end === -1 ? n : end + 2;
      while (i < stop) mask[i++] = 1;
      continue;
    }
    if (lang === "py" && ch === "#") {
      while (i < n && src[i] !== "\n") mask[i++] = 1;
      continue;
    }
    if (lang === "py" && (three === '"""' || three === "'''")) {
      const end = src.indexOf(three, i + 3);
      const stop = end === -1 ? n : end + 3;
      while (i < stop) mask[i++] = 1;
      continue;
    }
    if (ch === '"' || ch === "'") {
      // Skip the literal without marking it, honouring backslash escapes.
      i++;
      while (i < n && src[i] !== ch && src[i] !== "\n") {
        i += src[i] === "\\" ? 2 : 1;
      }
      i++;
      continue;
    }
    i++;
  }
  return mask;
}

/** Splits `content` into lines with their comment spans marked. */
export function analyze(content: string, lang: Lang): CodeLine[] {
  const mask = commentMask(content, lang);
  const out: CodeLine[] = [];
  let start = 0;
  let lineNo = 1;
  const push = (from: number, to: number) => {
    const segs: Seg[] = [];
    let hasComment = false;
    let hasCode = false;
    for (let i = from; i < to; i++) {
      const isC = mask[i] === 1;
      const last = segs[segs.length - 1];
      if (last && last.c === isC) last.t += content[i];
      else segs.push({ t: content[i], c: isC });
      if (content[i].trim() !== "") {
        if (isC) hasComment = true;
        else hasCode = true;
      }
    }
    out.push({ n: lineNo++, segs, hasComment, hasCode });
  };
  for (let i = 0; i < content.length; i++) {
    if (content[i] === "\n") {
      push(start, i);
      start = i + 1;
    }
  }
  if (start < content.length) push(start, content.length);
  return out;
}

const MARKERS = /^[\s/*#"']+|[\s/*"']+$/g;
const CJK = /[㐀-䶿一-鿿豈-﫿぀-ヿ]/g;
const LICENSE =
  /(copyright|licensed under|license at|WITHOUT WARRANTIES|SPDX-|apache\.org\/licenses|all rights reserved)/i;

/**
 * Words of prose, counting each CJK character as one word.
 *
 * Whitespace splitting alone scores a 40-character Chinese sentence as one
 * word, which would make densities incomparable across languages (they are
 * only really comparable *within* one language even so). Mirrored exactly by
 * scripts/metrics.py, which is what writes the recorded density.
 */
export function countWords(text: string): number {
  const cjk = text.match(CJK)?.length ?? 0;
  const latin = text.replace(CJK, " ").split(/\s+/).filter(Boolean).length;
  return cjk + latin;
}

/** Comment prose per line, with a leading license header dropped. */
function proseLines(lines: CodeLine[]): { n: number; text: string }[] {
  const out: { n: number; text: string }[] = [];
  for (const l of lines) {
    if (!l.hasComment) continue;
    const prose = l.segs
      .filter((s) => s.c)
      .map((s) => s.t)
      .join("")
      .replace(MARKERS, "")
      .trim();
    if (prose) out.push({ n: l.n, text: prose });
  }
  // Both skills tell the agent to copy the project's license boilerplate from a
  // neighbouring file, so those ~120 words are not the run's own prose and must
  // not dilute its density.
  if (out.length === 0 || out[0].n > 6) return out;
  let end = 0;
  while (end + 1 < out.length && out[end + 1].n <= out[end].n + 2) end++;
  const block = out.slice(0, end + 1);
  return block.some((l) => LICENSE.test(l.text)) ? out.slice(end + 1) : out;
}

/** Comment volume of an analyzed file — the headline number per column. */
export function statsOf(lines: CodeLine[]): CommentStats {
  let commentLines = 0;
  let codeLines = 0;
  for (const l of lines) {
    if (l.hasComment) commentLines++;
    if (l.hasCode) codeLines++;
  }
  const words = proseLines(lines).reduce((n, l) => n + countWords(l.text), 0);
  const denom = commentLines + codeLines;
  return {
    lines: lines.length,
    commentLines,
    codeLines,
    words,
    density: denom === 0 ? 0 : Math.round((commentLines / denom) * 100),
  };
}
