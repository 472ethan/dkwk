import tap from 'tap';
import { parse, parseInline } from '../parser.js';

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

// Normalise whitespace between block elements for fragile comparison.
const squeeze = (s) => s.replace(/\s+/g, ' ').trim();

// ---------------------------------------------------------------------------
// parseInline — basic formatting
// ---------------------------------------------------------------------------

tap.test('inline: bold', (t) => {
  t.equal(parseInline('*hello*'),       '<b>hello</b>');
  t.equal(parseInline('*hello world*'), '<b>hello world</b>');
  t.equal(parseInline('*x*'),           '<b>x</b>', 'single char');
  t.end();
});

tap.test('inline: italic', (t) => {
  t.equal(parseInline('_hello_'),       '<i>hello</i>');
  t.equal(parseInline('_hello world_'), '<i>hello world</i>');
  t.end();
});

tap.test('inline: code — backtick/single-quote', (t) => {
  t.equal(parseInline("`hello'"),        '<code>hello</code>');
  t.equal(parseInline("`hello world'"),  '<code>hello world</code>');
  t.end();
});

tap.test('inline: code — backtick/backtick', (t) => {
  t.equal(parseInline('`hello`'),        '<code>hello</code>');
  t.end();
});

tap.test('inline: code — double delimiters ``…\'\'', (t) => {
  t.equal(parseInline("``hello''"),      '<code>hello</code>');
  t.equal(parseInline("``hello world''"), '<code>hello world</code>');
  t.end();
});

tap.test('inline: code — double delimiters ``…``', (t) => {
  t.equal(parseInline('``hello``'),      '<code>hello</code>');
  t.end();
});

tap.test('inline: math', (t) => {
  t.equal(parseInline('$x^2$'),   '<span class="math-inline">x^2</span>');
  t.equal(parseInline('$a + b$'), '<span class="math-inline">a + b</span>');
  t.end();
});

// ---------------------------------------------------------------------------
// parseInline — space-boundary rule (delimiters must not be space-adjacent)
// ---------------------------------------------------------------------------

tap.test('inline: space-bounded delimiters are literal', (t) => {
  // Opening delimiter followed by space → not markup
  t.equal(parseInline('* hello*'), '* hello*', 'space after *');
  t.equal(parseInline('_ hello_'), '_ hello_', 'space after _');
  // Closing delimiter preceded by space → not markup
  t.equal(parseInline('*hello *'), '*hello *', 'space before closing *');
  t.end();
});

tap.test('inline: unpaired delimiters are literal', (t) => {
  t.equal(parseInline('*no close'),       '*no close');
  t.equal(parseInline('no open*'),        'no open*');
  t.equal(parseInline("no open'"),        "no open'");
  t.end();
});

// ---------------------------------------------------------------------------
// parseInline — backslash escapes
// ---------------------------------------------------------------------------

tap.test('inline: backslash escapes special chars', (t) => {
  t.equal(parseInline('\\*'),    '*',  'escape asterisk');
  t.equal(parseInline('\\_'),    '_',  'escape underscore');
  t.equal(parseInline('\\$'),    '$',  'escape dollar');
  t.equal(parseInline('\\\\'),   '\\', 'escape backslash');
  t.end();
});

tap.test('inline: backslash inside code span prevents inner markup', (t) => {
  // \* is saved as a placeholder before the code-span regex runs,
  // so the asterisk never acts as a bold delimiter.
  // The closing delimiter must be a raw (unescaped) ' or `.
  t.equal(
    parseInline("`escape\\*this'"),   // raw: `escape\*this'
    '<code>escape*this</code>',
    'escaped asterisk in backtick/apostrophe span',
  );
  t.equal(
    parseInline('`escape\\*bold\\*here`'),  // raw: `escape\*bold\*here`
    '<code>escape*bold*here</code>',
    'two escaped asterisks in backtick span',
  );
  t.end();
});

tap.test('inline: backslash escapes backtick inside code span', (t) => {
  // A literal backtick inside a `…' span via backslash escape.
  t.equal(
    parseInline("`back\\`tick'"),
    '<code>back`tick</code>',
  );
  t.end();
});

tap.test('inline: backslash before HTML entities', (t) => {
  t.equal(parseInline('\\<'), '&lt;', 'escape left angle');
  t.equal(parseInline('\\>'), '&gt;', 'escape right angle');
  t.equal(parseInline('\\&'), '&amp;', 'escape ampersand');
  t.end();
});

// ---------------------------------------------------------------------------
// parseInline — HTML passthrough and escaping
// ---------------------------------------------------------------------------

tap.test('inline: <MARK>/<SUP>/<SUB> pass through', (t) => {
  t.equal(parseInline('<MARK>hi</MARK>'), '<mark>hi</mark>');
  t.equal(parseInline('<SUP>2</SUP>'),    '<sup>2</sup>');
  t.equal(parseInline('<SUB>i</SUB>'),    '<sub>i</sub>');
  t.equal(parseInline('<mark>ok</mark>'), '<mark>ok</mark>', 'lowercase also ok');
  t.end();
});

tap.test('inline: other HTML is escaped', (t) => {
  t.equal(parseInline('<b>literal</b>'),   '&lt;b&gt;literal&lt;/b&gt;');
  t.equal(parseInline('<script>xss</script>'), '&lt;script&gt;xss&lt;/script&gt;');
  t.end();
});

tap.test('inline: & < > are always escaped', (t) => {
  t.equal(parseInline('a & b'),     'a &amp; b');
  t.equal(parseInline('a < b'),     'a &lt; b');
  t.equal(parseInline('a > b'),     'a &gt; b');
  t.equal(parseInline('1 < 2 > 0'), '1 &lt; 2 &gt; 0');
  t.end();
});

// ---------------------------------------------------------------------------
// parseInline — apostrophes don't accidentally close code spans
// ---------------------------------------------------------------------------

tap.test("inline: apostrophe in prose doesn't close code span", (t) => {
  // "don't" contains a ' but there's no preceding ` so no code span forms.
  t.equal(parseInline("don't"), "don't");
  // After a code span is closed, remaining apostrophes are literal.
  t.equal(
    parseInline("`code' and don't"),
    "<code>code</code> and don't",
  );
  t.end();
});

// ---------------------------------------------------------------------------
// parse — comments
// ---------------------------------------------------------------------------

tap.test('block: comments are stripped', (t) => {
  t.equal(parse('<!-- removed -->'), '');
  t.equal(parse('<!-- a -- b -->'),  '', '-- inside comment');
  // Inline comment on the same prose line is removed in place.
  t.equal(
    parse('before <!-- gone --> after'),
    '<p>before  after</p>',
    'inline comment leaves surrounding text',
  );
  // A comment on its own line strips to blank → paragraph break.
  t.equal(
    squeeze(parse('before\n<!-- gone -->\nafter')),
    '<p>before</p> <p>after</p>',
    'standalone comment line becomes paragraph separator',
  );
  t.end();
});

// ---------------------------------------------------------------------------
// parse — headings
// ---------------------------------------------------------------------------

tap.test('block: headings h1–h6', (t) => {
  for (let n = 1; n <= 6; n++) {
    const eq = '='.repeat(n);
    t.equal(parse(`${eq} Title`), `<h${n}>Title</h${n}>`, `h${n}`);
  }
  t.end();
});

tap.test('block: trailing equals signs on headings are decorative', (t) => {
  t.equal(parse('= Title ='),   '<h1>Title</h1>');
  t.equal(parse('== Title =='), '<h2>Title</h2>');
  t.equal(parse('= Title ==='), '<h1>Title</h1>', 'mismatched trailing');
  t.end();
});

tap.test('block: inline markup inside headings', (t) => {
  t.equal(parse('= *bold* heading ='), '<h1><b>bold</b> heading</h1>');
  t.end();
});

// ---------------------------------------------------------------------------
// parse — verbatim blocks
// ---------------------------------------------------------------------------

tap.test('block: verbatim — basic indented block', (t) => {
  const src = '  line one\n  line two';
  t.equal(parse(src), '<pre>line one\nline two</pre>');
  t.end();
});

tap.test('block: verbatim — tab indent', (t) => {
  t.equal(parse('\tcode here'), '<pre>code here</pre>');
  t.end();
});

tap.test('block: verbatim — backslashes are literal (no escape processing)', (t) => {
  // \* inside a verbatim block is NOT an escape; it's two literal chars.
  t.equal(parse('  \\*not bold\\*'), '<pre>\\*not bold\\*</pre>');
  t.equal(parse('  back\\slash'),   '<pre>back\\slash</pre>');
  t.end();
});

tap.test('block: verbatim — HTML chars escaped, no inline markup', (t) => {
  t.equal(parse('  <b>literal</b>'), '<pre>&lt;b&gt;literal&lt;/b&gt;</pre>');
  t.equal(parse('  *not bold*'),     '<pre>*not bold*</pre>');
  t.end();
});

tap.test('block: verbatim — trailing blank lines trimmed', (t) => {
  t.equal(parse('  line\n  \n  '), '<pre>line</pre>');
  t.end();
});

tap.test('block: verbatim — deeper indent continues the block', (t) => {
  // A line with more indent than the first is still part of the block.
  const src = '  top\n    deeper\n  back';
  t.equal(parse(src), '<pre>top\n  deeper\nback</pre>');
  t.end();
});

tap.test('block: verbatim — backtick/quote spans are not parsed', (t) => {
  // `hello' inside a verbatim block should appear literally.
  t.equal(parse("  `hello'"), "<pre>`hello'</pre>");
  t.end();
});

// ---------------------------------------------------------------------------
// parse — paragraphs
// ---------------------------------------------------------------------------

tap.test('block: paragraph wraps prose lines', (t) => {
  t.equal(parse('hello world'), '<p>hello world</p>');
  t.end();
});

tap.test('block: consecutive lines join into one paragraph', (t) => {
  t.equal(parse('line one\nline two'), '<p>line one\nline two</p>');
  t.end();
});

tap.test('block: blank line separates paragraphs', (t) => {
  t.equal(parse('a\n\nb'), '<p>a</p>\n<p>b</p>');
  t.end();
});

tap.test('block: inline markup in paragraphs', (t) => {
  t.equal(parse('*bold* and _italic_'),
          '<p><b>bold</b> and <i>italic</i></p>');
  t.end();
});

// ---------------------------------------------------------------------------
// parse — mixed blocks
// ---------------------------------------------------------------------------

tap.test('block: heading followed by paragraph', (t) => {
  const src = '= Title =\n\nSome text.';
  t.equal(squeeze(parse(src)), '<h1>Title</h1> <p>Some text.</p>');
  t.end();
});

tap.test('block: verbatim between paragraphs', (t) => {
  const src = 'intro\n\n  code here\n\noutro';
  t.equal(squeeze(parse(src)), '<p>intro</p> <pre>code here</pre> <p>outro</p>');
  t.end();
});
