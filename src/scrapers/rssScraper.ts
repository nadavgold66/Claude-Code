import Parser from 'rss-parser';
import { NewsArticle, NewsSource } from '../types';

const parser = new Parser({
  timeout: 10000,
  headers: {
    'User-Agent': 'IsraeliNewsAggregator/1.0',
    'Accept': 'application/rss+xml, application/xml, text/xml',
  },
  customFields: {
    item: [
      ['media:content', 'mediaContent'],
      ['media:thumbnail', 'mediaThumbnail'],
      ['enclosure', 'enclosure'],
    ],
  },
});

function extractImageUrl(item: Record<string, unknown>): string | undefined {
  const mediaContent = item.mediaContent as Record<string, unknown> | undefined;
  if (mediaContent) {
    const attrs = mediaContent.$ as Record<string, string> | undefined;
    if (attrs?.url) return attrs.url;
  }

  const mediaThumbnail = item.mediaThumbnail as Record<string, unknown> | undefined;
  if (mediaThumbnail) {
    const attrs = mediaThumbnail.$ as Record<string, string> | undefined;
    if (attrs?.url) return attrs.url;
  }

  const enclosure = item.enclosure as Record<string, string> | undefined;
  if (enclosure?.url && enclosure.type?.startsWith('image/')) {
    return enclosure.url;
  }

  return undefined;
}

function stripHtml(html: string): string {
  return html.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').trim();
}

export async function scrapeRssFeed(
  source: NewsSource,
  feedUrl: string,
  category?: string
): Promise<NewsArticle[]> {
  const articles: NewsArticle[] = [];
  const now = new Date();

  try {
    const feed = await parser.parseURL(feedUrl);

    for (const item of feed.items) {
      if (!item.title || !item.link) continue;

      const publishedAt = item.pubDate ? new Date(item.pubDate) : now;

      articles.push({
        title: stripHtml(item.title),
        description: item.contentSnippet || (item.content ? stripHtml(item.content).slice(0, 300) : ''),
        url: item.link,
        imageUrl: extractImageUrl(item as unknown as Record<string, unknown>),
        source: source.name,
        category: category || 'General',
        publishedAt,
        scrapedAt: now,
      });
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`Failed to scrape RSS feed ${feedUrl} (${source.name}): ${message}`);
  }

  return articles;
}

export async function scrapeSource(source: NewsSource): Promise<NewsArticle[]> {
  const feedPromises = source.rssFeeds.map((feed) =>
    scrapeRssFeed(source, feed.url, feed.category)
  );

  const results = await Promise.allSettled(feedPromises);
  const articles: NewsArticle[] = [];

  for (const result of results) {
    if (result.status === 'fulfilled') {
      articles.push(...result.value);
    }
  }

  return articles;
}
