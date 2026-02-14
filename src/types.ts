export interface NewsArticle {
  title: string;
  description: string;
  url: string;
  imageUrl?: string;
  source: string;
  sourceLogoUrl?: string;
  category?: string;
  publishedAt: Date;
  scrapedAt: Date;
}

export interface NewsSource {
  name: string;
  nameHe: string;
  url: string;
  rssFeeds: RssFeed[];
  logoUrl?: string;
}

export interface RssFeed {
  url: string;
  category?: string;
}

export interface AggregatedNews {
  articles: NewsArticle[];
  lastUpdated: Date;
  sourceCount: number;
}
