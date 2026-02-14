import express from 'express';
import path from 'path';
import { aggregateNews, getSourceList, clearCache } from './aggregator';

const app = express();
const PORT = process.env.PORT || 3000;

// Serve static frontend files
app.use(express.static(path.join(__dirname, 'public')));

// API: Get aggregated news
app.get('/api/news', async (_req, res) => {
  try {
    const news = await aggregateNews();
    res.json(news);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    res.status(500).json({ error: 'Failed to fetch news', details: message });
  }
});

// API: Get news filtered by source
app.get('/api/news/source/:source', async (req, res) => {
  try {
    const news = await aggregateNews();
    const filtered = news.articles.filter(
      (a) => a.source.toLowerCase() === req.params.source.toLowerCase()
    );
    res.json({ ...news, articles: filtered });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    res.status(500).json({ error: 'Failed to fetch news', details: message });
  }
});

// API: Get news filtered by category
app.get('/api/news/category/:category', async (req, res) => {
  try {
    const news = await aggregateNews();
    const filtered = news.articles.filter(
      (a) => a.category?.toLowerCase() === req.params.category.toLowerCase()
    );
    res.json({ ...news, articles: filtered });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    res.status(500).json({ error: 'Failed to fetch news', details: message });
  }
});

// API: List all sources
app.get('/api/sources', (_req, res) => {
  res.json(getSourceList());
});

// API: Force refresh cache
app.post('/api/refresh', async (_req, res) => {
  clearCache();
  try {
    const news = await aggregateNews();
    res.json({ message: 'Cache refreshed', articleCount: news.articles.length });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    res.status(500).json({ error: 'Failed to refresh', details: message });
  }
});

// Serve frontend for all non-API routes
app.get('*', (_req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Israeli News Aggregator running at http://localhost:${PORT}`);
  console.log(`API endpoints:`);
  console.log(`  GET  /api/news                - All articles`);
  console.log(`  GET  /api/news/source/:name    - Filter by source`);
  console.log(`  GET  /api/news/category/:cat   - Filter by category`);
  console.log(`  GET  /api/sources              - List sources`);
  console.log(`  POST /api/refresh              - Force refresh`);
});
