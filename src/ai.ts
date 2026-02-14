import Anthropic from '@anthropic-ai/sdk';
import { NewsArticle, AiCategory, AI_CATEGORIES } from './types';

const client = new Anthropic();

const BATCH_SIZE = 20;

interface AiResult {
  summary: string;
  category: AiCategory;
}

function buildPrompt(articles: { index: number; title: string; description: string }[]): string {
  const articlesText = articles
    .map((a) => `[${a.index}] Title: ${a.title}\nDescription: ${a.description}`)
    .join('\n\n');

  return `You are a news analyst. For each article below, provide:
1. A concise 1-sentence summary in Hebrew
2. A category from this exact list: ${AI_CATEGORIES.join(', ')}

Respond ONLY with valid JSON — an array of objects with "index", "summary", and "category" fields.
No markdown, no explanation, just the JSON array.

Articles:
${articlesText}`;
}

function parseAiResponse(text: string, count: number): Map<number, AiResult> {
  const results = new Map<number, AiResult>();

  try {
    // Extract JSON array from response (handle possible markdown wrapping)
    const jsonMatch = text.match(/\[[\s\S]*\]/);
    if (!jsonMatch) return results;

    const parsed = JSON.parse(jsonMatch[0]) as Array<{
      index: number;
      summary: string;
      category: string;
    }>;

    for (const item of parsed) {
      const category = AI_CATEGORIES.includes(item.category as AiCategory)
        ? (item.category as AiCategory)
        : 'General';

      results.set(item.index, {
        summary: item.summary || '',
        category,
      });
    }
  } catch (error) {
    console.error('Failed to parse AI response:', error instanceof Error ? error.message : error);
  }

  return results;
}

async function processBatch(
  articles: NewsArticle[],
  startIndex: number
): Promise<Map<number, AiResult>> {
  const batch = articles.map((a, i) => ({
    index: startIndex + i,
    title: a.title,
    description: (a.description || '').slice(0, 200),
  }));

  try {
    const message = await client.messages.create({
      model: 'claude-sonnet-4-5-20250929',
      max_tokens: 4096,
      messages: [
        {
          role: 'user',
          content: buildPrompt(batch),
        },
      ],
    });

    const responseText =
      message.content[0].type === 'text' ? message.content[0].text : '';

    return parseAiResponse(responseText, articles.length);
  } catch (error) {
    console.error('AI batch processing failed:', error instanceof Error ? error.message : error);
    return new Map();
  }
}

export async function enrichArticlesWithAi(articles: NewsArticle[]): Promise<NewsArticle[]> {
  if (!process.env.ANTHROPIC_API_KEY) {
    console.warn('ANTHROPIC_API_KEY not set — skipping AI enrichment');
    return articles;
  }

  console.log(`Enriching ${articles.length} articles with AI...`);
  const startTime = Date.now();

  const enriched = [...articles];

  // Process in batches
  for (let i = 0; i < enriched.length; i += BATCH_SIZE) {
    const batch = enriched.slice(i, i + BATCH_SIZE);
    const results = await processBatch(batch, i);

    for (const [index, result] of results) {
      if (enriched[index]) {
        enriched[index] = {
          ...enriched[index],
          aiSummary: result.summary,
          aiCategory: result.category,
        };
      }
    }
  }

  const elapsed = Date.now() - startTime;
  const enrichedCount = enriched.filter((a) => a.aiSummary).length;
  console.log(`AI enrichment complete: ${enrichedCount}/${articles.length} articles in ${elapsed}ms`);

  return enriched;
}
