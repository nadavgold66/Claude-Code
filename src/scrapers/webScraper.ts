import axios from 'axios';
import * as cheerio from 'cheerio';
import { NewsArticle, NewsSource } from '../types';

const HTTP_TIMEOUT = 10000;

const SCRAPER_CONFIGS: Record<string, {
  articleSelector: string;
  titleSelector: string;
  linkSelector: string;
  descriptionSelector?: string;
  imageSelector?: string;
}> = {
  'Ynet': {
    articleSelector: '.slotView',
    titleSelector: '.slotTitle',
    linkSelector: 'a',
    descriptionSelector: '.slotSubTitle',
    imageSelector: 'img',
  },
  'Walla': {
    articleSelector: '.css-item, article',
    titleSelector: 'h2, .title',
    linkSelector: 'a',
    descriptionSelector: '.subtitle, .description',
    imageSelector: 'img',
  },
  'Israel Hayom': {
    articleSelector: '.post-item, article',
    titleSelector: 'h2, h3, .title',
    linkSelector: 'a',
    descriptionSelector: '.excerpt, .description',
    imageSelector: 'img',
  },
};

function resolveUrl(base: string, relative: string): string {
  try {
    return new URL(relative, base).href;
  } catch {
    return relative;
  }
}

export async function scrapeWebPage(source: NewsSource): Promise<NewsArticle[]> {
  const config = SCRAPER_CONFIGS[source.name];
  if (!config) return [];

  const articles: NewsArticle[] = [];
  const now = new Date();

  try {
    const response = await axios.get(source.url, {
      timeout: HTTP_TIMEOUT,
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; IsraeliNewsAggregator/1.0)',
        'Accept-Language': 'he-IL,he;q=0.9,en;q=0.8',
      },
    });

    const $ = cheerio.load(response.data);

    $(config.articleSelector).each((_, element) => {
      const $el = $(element);
      const title = $el.find(config.titleSelector).first().text().trim();
      const linkEl = $el.find(config.linkSelector).first();
      const href = linkEl.attr('href');

      if (!title || !href) return;

      const url = resolveUrl(source.url, href);
      const description = config.descriptionSelector
        ? $el.find(config.descriptionSelector).first().text().trim()
        : '';
      const imageUrl = config.imageSelector
        ? $el.find(config.imageSelector).first().attr('src')
        : undefined;

      articles.push({
        title,
        description,
        url,
        imageUrl: imageUrl ? resolveUrl(source.url, imageUrl) : undefined,
        source: source.name,
        category: 'General',
        publishedAt: now,
        scrapedAt: now,
      });
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`Failed to scrape web page ${source.url} (${source.name}): ${message}`);
  }

  return articles;
}
