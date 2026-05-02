/**
 * DK-Wiki Markup Parser
 *
 * Block-level syntax:
 *   <!-- ... -->          comment (-- may appear inside)
 *   = Heading =           h1 through h6 (trailing ='s optional)
 *   <SP/HT>text           verbatim block (<pre>); continues while indent matches
 *   (everything else)     paragraph
 *
 * Inline syntax (delimiter must not be space-adjacent on the inside):
 *   \X                    escaped literal X
 *   *text*                bold
 *   _text_                italic
 *   `text'  `text`        fixed-width (code)
 *   ``text''  ``text``    fixed-width (code, double delimiters)
 *   $text$                inline math (render separately, e.g. with KaTeX)
 *   <MARK>  <SUP>  <SUB>  passed through as lowercase HTML
 *
 * Verbatim blocks are not inline-parsed; backslashes inside are literal.
 */

function esc(s) {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/**
 * Parse inline markup within a text segment.
 * Returns an HTML string safe for innerHTML assignment.
 */
export function parseInline(src) {
  /*
   * Strategy:
   *   1. Save backslash escapes first, then whitelisted HTML tags, as opaque
   *      placeholders so they survive the HTML-escaping step.
   *      (Backslashes processed before tags so \<MARK> escapes the bracket.)
   *   2. HTML-escape the remaining characters.
   *   3. Apply delimiter-pair regexes.
   *      Opening delimiter: must be followed by a non-space char ((?=\S)).
   *      Closing delimiter: must be preceded by a non-space char (\S before closer).
   *      Lazy [\s\S]*? finds the shortest match.
   *   4. Restore placeholders.
   */
  const saved = [];
  const save = (raw) => { saved.push(raw); return `\x01${saved.length - 1}\x01`; };

  /* Step 1a – backslash escapes (processed first so \<TAG> escapes the bracket). */
  src = src.replace(/\\([\s\S])/g, (_, ch) => save(esc(ch)));

  /* Step 1b – whitelisted HTML tags (tag name only, no attributes). */
  src = src.replace(/<\/?(MARK|SUP|SUB)>/gi, (m) => save(m.toLowerCase()));

  /* Step 2 – HTML-escape the rest. */
  src = esc(src);

  /* Step 3 – inline markup.  Double delimiters matched before single ones. */
  src = src.replace(/``(?=\S)([\s\S]*?\S)''/g, '<code>$1</code>');
  src = src.replace(/``(?=\S)([\s\S]*?\S)``/g, '<code>$1</code>');
  src = src.replace(/`(?=\S)([\s\S]*?\S)'/g,   '<code>$1</code>');
  src = src.replace(/`(?=\S)([\s\S]*?\S)`/g,   '<code>$1</code>');
  src = src.replace(/\*(?=\S)([\s\S]*?\S)\*/g,  '<b>$1</b>');
  src = src.replace(/_(?=\S)([\s\S]*?\S)_/g,    '<i>$1</i>');
  src = src.replace(/\$(?=\S)([\s\S]*?\S)\$/g,  '<span class="math-inline">$1</span>');

  /* Step 4 – restore placeholders. */
  src = src.replace(/\x01(\d+)\x01/g, (_, i) => saved[+i]);

  return src;
}

/**
 * Parse a full DK-Wiki markup document.
 * Returns an HTML string.
 */
export function parse(src) {
  /* Strip comments (-- is allowed inside, unlike standard XML). */
  src = src.replace(/<!--[\s\S]*?-->/g, '');

  const lines = src.split('\n');
  const out   = [];
  let   i     = 0;

  while (i < lines.length) {
    const line = lines[i];

    /* Blank line – paragraph separator. */
    if (/^\s*$/.test(line)) { i++; continue; }

    /* Heading – one to six leading '=' followed by whitespace.
       Trailing ='s are decorative; only the leading count sets the level. */
    const hm = line.match(/^(={1,6})\s+(.+?)(?:\s+=+)?\s*$/);
    if (hm) {
      const lvl = hm[1].length;
      out.push(`<h${lvl}>${parseInline(hm[2])}</h${lvl}>`);
      i++;
      continue;
    }

    /* Verbatim block – line starts with SP or HT.
       Collect subsequent lines that begin with the same indent.
       Content is not parsed for inline markup; backslashes are literal. */
    if (/^[ \t]/.test(line)) {
      const indent = line.match(/^([ \t]+)/)[1];
      const vlines = [];
      while (i < lines.length && lines[i].startsWith(indent)) {
        vlines.push(lines[i].slice(indent.length));
        i++;
      }
      while (vlines.length && /^\s*$/.test(vlines[vlines.length - 1])) vlines.pop();
      out.push(`<pre>${esc(vlines.join('\n'))}</pre>`);
      continue;
    }

    /* Paragraph – consecutive non-blank, non-heading, non-verbatim lines. */
    const plines = [];
    while (
      i < lines.length &&
      !/^\s*$/.test(lines[i]) &&
      !/^={1,6}\s/.test(lines[i]) &&
      !/^[ \t]/.test(lines[i])
    ) {
      plines.push(lines[i]);
      i++;
    }
    out.push(`<p>${parseInline(plines.join('\n'))}</p>`);
  }

  return out.join('\n');
}
