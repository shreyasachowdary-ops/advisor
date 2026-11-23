/**
 * Minimal, safe Markdown parser for advisor answers (DECISIONS.md DEC-032).
 * Supports paragraphs, line breaks, "-"/"*" and "1." lists, "#" headings,
 * **bold** and _italic_. Returns plain data; MarkdownText renders it as React
 * elements, so no HTML string is ever injected (no XSS risk from model output).
 */

const LIST_BULLET = /^\s*[-*•]\s+(.*)$/;
const LIST_NUMBER = /^\s*\d{1,2}[.)]\s+(.*)$/;
const HEADING = /^\s*#{1,6}\s+(.*)$/;
// Single _ or * only counts as italic at word edges, so "4_years" stays as-is.
const INLINE = /(\*\*[^*]+\*\*|(?<!\w)__[^_]+__(?!\w)|(?<!\w)_[^_\s][^_]*_(?!\w)|(?<![\w*])\*[^*\s][^*]*\*(?![\w*]))/g;

export function parseInline(text) {
  const parts = [];
  let last = 0;
  for (const match of text.matchAll(INLINE)) {
    if (match.index > last) parts.push({ text: text.slice(last, match.index) });
    const token = match[0];
    if (token.startsWith("**") || token.startsWith("__")) {
      parts.push({ text: token.slice(2, -2), bold: true });
    } else {
      parts.push({ text: token.slice(1, -1), italic: true });
    }
    last = match.index + token.length;
  }
  if (last < text.length) parts.push({ text: text.slice(last) });
  return parts;
}

export function parseMarkdown(source) {
  const blocks = [];
  let paragraph = null;
  let list = null;

  const flush = () => {
    if (paragraph) blocks.push(paragraph);
    if (list) blocks.push(list);
    paragraph = null;
    list = null;
  };

  for (const rawLine of String(source || "").replace(/\r\n/g, "\n").split("\n")) {
    const line = rawLine.trimEnd();
    if (!line.trim()) {
      flush();
      continue;
    }
    const heading = line.match(HEADING);
    const bullet = line.match(LIST_BULLET);
    const number = line.match(LIST_NUMBER);
    if (heading) {
      flush();
      blocks.push({ type: "heading", inlines: parseInline(heading[1]) });
    } else if (bullet || number) {
      const type = number ? "ol" : "ul";
      if (paragraph) {
        blocks.push(paragraph);
        paragraph = null;
      }
      if (!list || list.type !== type) {
        if (list) blocks.push(list);
        list = { type, items: [] };
      }
      list.items.push(parseInline((number || bullet)[1]));
    } else {
      if (list) {
        blocks.push(list);
        list = null;
      }
      if (!paragraph) paragraph = { type: "paragraph", lines: [] };
      paragraph.lines.push(parseInline(line.trim()));
    }
  }
  flush();
  return blocks;
}
