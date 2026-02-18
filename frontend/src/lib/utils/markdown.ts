/**
 * Simple Markdown-to-HTML converter for LLM-generated advice text.
 * Supports: headings (##), bold (**), unordered lists (*), paragraphs, line breaks.
 * No external dependencies — regex-based line-by-line processing.
 */
export function simpleMarkdownToHtml(text: string): string {
	if (!text) return '';

	// 1. HTML escape (XSS prevention — must be first)
	let escaped = text
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;');

	const lines = escaped.split('\n');
	const blocks: string[] = [];
	let currentLines: string[] = [];
	let inList = false;
	let listItems: string[] = [];

	function flushParagraph() {
		if (currentLines.length > 0) {
			const content = currentLines.join('<br>');
			blocks.push(`<p>${content}</p>`);
			currentLines = [];
		}
	}

	function flushList() {
		if (listItems.length > 0) {
			blocks.push('<ul>' + listItems.map((li) => `<li>${li}</li>`).join('') + '</ul>');
			listItems = [];
			inList = false;
		}
	}

	for (const rawLine of lines) {
		const line = rawLine.trim();

		// Empty line → flush current block
		if (line === '') {
			if (inList) flushList();
			flushParagraph();
			continue;
		}

		// ## Heading
		const headingMatch = line.match(/^##\s+(.+)$/);
		if (headingMatch) {
			if (inList) flushList();
			flushParagraph();
			blocks.push(`<h4>${applyInline(headingMatch[1])}</h4>`);
			continue;
		}

		// * List item (also - list item)
		const listMatch = line.match(/^[*\-]\s+(.+)$/);
		if (listMatch) {
			flushParagraph();
			inList = true;
			listItems.push(applyInline(listMatch[1]));
			continue;
		}

		// Regular line
		if (inList) flushList();
		currentLines.push(applyInline(line));
	}

	// Flush remaining
	if (inList) flushList();
	flushParagraph();

	return blocks.join('');
}

/** Apply inline formatting: **bold** and 【】headings pattern */
function applyInline(text: string): string {
	// **bold**
	let result = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
	// 【見出し】 as emphasis (when not already inside <strong>)
	result = result.replace(/【(.+?)】/g, '<strong>【$1】</strong>');
	return result;
}
