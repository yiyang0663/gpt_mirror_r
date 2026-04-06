const escapeHtml = (value: string) => {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
};

const escapeAttribute = (value: string) => {
  return escapeHtml(value).replace(/`/g, '&#96;');
};

const normalizeUrl = (value: string) => {
  const trimmed = value.trim();
  if (/^https?:\/\//i.test(trimmed)) {
    return trimmed;
  }
  return '';
};

const renderInline = (value: string) => {
  let output = escapeHtml(value);

  output = output.replace(/`([^`\n]+)`/g, '<code>$1</code>');
  output = output.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  output = output.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');
  output = output.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_match, label: string, href: string) => {
    const normalizedHref = normalizeUrl(href);
    if (!normalizedHref) {
      return escapeHtml(label);
    }
    return `<a href="${escapeAttribute(normalizedHref)}" target="_blank" rel="noreferrer noopener">${escapeHtml(label)}</a>`;
  });

  return output;
};

const renderCodeBlock = (value: string, language = '') => {
  const label = language.trim().toLowerCase();
  return `<pre class="chat-code-block"><div class="chat-code-head"><span>${escapeHtml(label || 'code')}</span></div><code>${escapeHtml(
    value.replace(/\n$/, ''),
  )}</code></pre>`;
};

const flushParagraph = (paragraph: string[], chunks: string[]) => {
  if (!paragraph.length) {
    return;
  }
  chunks.push(`<p>${paragraph.map((item) => renderInline(item)).join('<br />')}</p>`);
  paragraph.length = 0;
};

const flushList = (items: string[], ordered: boolean, chunks: string[]) => {
  if (!items.length) {
    return;
  }
  const tag = ordered ? 'ol' : 'ul';
  chunks.push(`<${tag}>${items.map((item) => `<li>${renderInline(item)}</li>`).join('')}</${tag}>`);
  items.length = 0;
};

const flushQuote = (quote: string[], chunks: string[]) => {
  if (!quote.length) {
    return;
  }
  chunks.push(`<blockquote>${quote.map((item) => `<p>${renderInline(item)}</p>`).join('')}</blockquote>`);
  quote.length = 0;
};

const renderPlainMarkdown = (value: string) => {
  const lines = value.split('\n');
  const chunks: string[] = [];
  const paragraph: string[] = [];
  const bulletItems: string[] = [];
  const orderedItems: string[] = [];
  const quoteLines: string[] = [];

  const flushAll = () => {
    flushParagraph(paragraph, chunks);
    flushList(bulletItems, false, chunks);
    flushList(orderedItems, true, chunks);
    flushQuote(quoteLines, chunks);
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    const trimmed = line.trim();

    if (!trimmed) {
      flushAll();
      continue;
    }

    const headingMatch = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (headingMatch) {
      flushAll();
      const level = Math.min(headingMatch[1].length, 3);
      chunks.push(`<h${level}>${renderInline(headingMatch[2])}</h${level}>`);
      continue;
    }

    const bulletMatch = trimmed.match(/^[-*+]\s+(.+)$/);
    if (bulletMatch) {
      flushParagraph(paragraph, chunks);
      flushList(orderedItems, true, chunks);
      flushQuote(quoteLines, chunks);
      bulletItems.push(bulletMatch[1]);
      continue;
    }

    const orderedMatch = trimmed.match(/^\d+\.\s+(.+)$/);
    if (orderedMatch) {
      flushParagraph(paragraph, chunks);
      flushList(bulletItems, false, chunks);
      flushQuote(quoteLines, chunks);
      orderedItems.push(orderedMatch[1]);
      continue;
    }

    const quoteMatch = trimmed.match(/^>\s?(.+)$/);
    if (quoteMatch) {
      flushParagraph(paragraph, chunks);
      flushList(bulletItems, false, chunks);
      flushList(orderedItems, true, chunks);
      quoteLines.push(quoteMatch[1]);
      continue;
    }

    flushList(bulletItems, false, chunks);
    flushList(orderedItems, true, chunks);
    flushQuote(quoteLines, chunks);
    paragraph.push(trimmed);
  }

  flushAll();
  return chunks.join('');
};

export const renderChatMarkdown = (value: string) => {
  const normalized = String(value || '').replace(/\r\n/g, '\n').trim();
  if (!normalized) {
    return '<p></p>';
  }

  const blocks: Array<{ type: 'code' | 'text'; content: string; language?: string }> = [];
  const codeBlockRegex = /```([\w-]*)\n([\s\S]*?)```/g;
  let cursor = 0;
  let match: RegExpExecArray | null;

  while ((match = codeBlockRegex.exec(normalized))) {
    if (match.index > cursor) {
      blocks.push({
        type: 'text',
        content: normalized.slice(cursor, match.index),
      });
    }

    blocks.push({
      type: 'code',
      language: match[1] || '',
      content: match[2] || '',
    });

    cursor = match.index + match[0].length;
  }

  if (cursor < normalized.length) {
    blocks.push({
      type: 'text',
      content: normalized.slice(cursor),
    });
  }

  return blocks
    .map((block) => {
      if (block.type === 'code') {
        return renderCodeBlock(block.content, block.language);
      }
      return renderPlainMarkdown(block.content);
    })
    .join('');
};
