import { NewsSource } from './types';

export const NEWS_SOURCES: NewsSource[] = [
  {
    name: 'Ynet',
    nameHe: 'ידיעות אחרונות',
    url: 'https://www.ynet.co.il',
    rssFeeds: [
      { url: 'https://www.ynet.co.il/Integration/StoryRss2.xml', category: 'General' },
      { url: 'https://www.ynet.co.il/Integration/StoryRss1854.xml', category: 'Breaking' },
    ],
  },
  {
    name: 'Haaretz',
    nameHe: 'הארץ',
    url: 'https://www.haaretz.co.il',
    rssFeeds: [
      { url: 'https://www.haaretz.co.il/cmlink/1.1617539', category: 'General' },
    ],
  },
  {
    name: 'Maariv',
    nameHe: 'מעריב',
    url: 'https://www.maariv.co.il',
    rssFeeds: [
      { url: 'https://www.maariv.co.il/Rss/RssFeedsBreakingNews', category: 'Breaking' },
      { url: 'https://www.maariv.co.il/Rss/RssFeedsMivzakiNews', category: 'General' },
    ],
  },
  {
    name: 'Walla',
    nameHe: 'וואלה',
    url: 'https://www.walla.co.il',
    rssFeeds: [
      { url: 'https://rss.walla.co.il/feed/1', category: 'General' },
      { url: 'https://rss.walla.co.il/feed/2', category: 'Breaking' },
    ],
  },
  {
    name: 'Israel Hayom',
    nameHe: 'ישראל היום',
    url: 'https://www.israelhayom.co.il',
    rssFeeds: [
      { url: 'https://www.israelhayom.co.il/rss.xml', category: 'General' },
    ],
  },
  {
    name: 'Kan News',
    nameHe: 'כאן חדשות',
    url: 'https://www.kan.org.il',
    rssFeeds: [
      { url: 'https://www.kan.org.il/Rss/', category: 'General' },
    ],
  },
  {
    name: 'Channel 12 News',
    nameHe: 'חדשות 12',
    url: 'https://www.mako.co.il/news',
    rssFeeds: [
      { url: 'https://rcs.mako.co.il/rss/31750a2610f26110VgnVCM1000004801000aRCRD.xml', category: 'General' },
    ],
  },
  {
    name: 'Channel 13 News',
    nameHe: 'חדשות 13',
    url: 'https://13tv.co.il',
    rssFeeds: [
      { url: 'https://13tv.co.il/feed/', category: 'General' },
    ],
  },
  {
    name: 'Globes',
    nameHe: 'גלובס',
    url: 'https://www.globes.co.il',
    rssFeeds: [
      { url: 'https://www.globes.co.il/webservice/rss/rssfeeder.asmx/FeederNode?iID=585', category: 'Business' },
    ],
  },
  {
    name: 'Calcalist',
    nameHe: 'כלכליסט',
    url: 'https://www.calcalist.co.il',
    rssFeeds: [
      { url: 'https://www.calcalist.co.il/Integration/StoryRss2.xml', category: 'Business' },
    ],
  },
];
