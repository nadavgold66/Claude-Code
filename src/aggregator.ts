import { NewsArticle, AggregatedNews } from './types';
import { NEWS_SOURCES } from './sources';
import { scrapeSource } from './scrapers/rssScraper';
import { scrapeWebPage } from './scrapers/webScraper';
import { enrichArticlesWithAi } from './ai';

let cachedNews: AggregatedNews | null = null;
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

function deduplicateArticles(articles: NewsArticle[]): NewsArticle[] {
  const seen = new Map<string, NewsArticle>();

  for (const article of articles) {
    // Deduplicate by URL
    const normalizedUrl = article.url.replace(/\/$/, '').toLowerCase();
    if (!seen.has(normalizedUrl)) {
      seen.set(normalizedUrl, article);
    }
  }

  return Array.from(seen.values());
}

function sortByDate(articles: NewsArticle[]): NewsArticle[] {
  return articles.sort((a, b) =>
    new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime()
  );
}

export async function aggregateNews(): Promise<AggregatedNews> {
  // Return cached result if still fresh
  if (cachedNews && Date.now() - cachedNews.lastUpdated.getTime() < CACHE_TTL_MS) {
    return cachedNews;
  }

  console.log('Fetching news from all sources...');
  const startTime = Date.now();

  // Scrape all sources in parallel
  const rssPromises = NEWS_SOURCES.map((source) => scrapeSource(source));
  const webPromises = NEWS_SOURCES.map((source) => scrapeWebPage(source));

  const [rssResults, webResults] = await Promise.all([
    Promise.allSettled(rssPromises),
    Promise.allSettled(webPromises),
  ]);

  const allArticles: NewsArticle[] = [];
  let successfulSources = 0;

  for (const result of [...rssResults, ...webResults]) {
    if (result.status === 'fulfilled' && result.value.length > 0) {
      allArticles.push(...result.value);
      successfulSources++;
    }
  }

  const deduplicated = deduplicateArticles(allArticles);
  const sorted = sortByDate(deduplicated);

  const elapsed = Date.now() - startTime;
  console.log(
    `Fetched ${sorted.length} unique articles from ${successfulSources} feeds in ${elapsed}ms`
  );

  // Enrich articles with AI summaries and categories
  const enriched = await enrichArticlesWithAi(sorted);

  cachedNews = {
    articles: enriched,
    lastUpdated: new Date(),
    sourceCount: successfulSources,
  };

  return cachedNews;
}

export function getSourceList() {
  return NEWS_SOURCES.map((s) => ({
    name: s.name,
    nameHe: s.nameHe,
    url: s.url,
    feedCount: s.rssFeeds.length,
  }));
}

export function clearCache(): void {
  cachedNews = null;
}
