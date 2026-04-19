#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const { chromium } = require('/tmp/pw/node_modules/playwright');

const INPUT_PATH = '/code/data/datacamp-course-links-classcentral';
const OUTPUT_DIR = '/code/data/classcentral-datacamp-pages';
const HTML_DIR = path.join(OUTPUT_DIR, 'html');
const MANIFEST_PATH = path.join(OUTPUT_DIR, 'manifest.jsonl');
const FAILURES_PATH = path.join(OUTPUT_DIR, 'failures.jsonl');
const USER_AGENT =
  'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36';
const BASE_DELAY_MS = 2500;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function politeDelayMs() {
  return BASE_DELAY_MS + Math.floor(Math.random() * 1500);
}

function sha1(value) {
  return crypto.createHash('sha1').update(value).digest('hex');
}

function safeSlug(url) {
  const last = url.split('/').pop() || 'page';
  return last.replace(/[^a-zA-Z0-9._-]+/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');
}

async function main() {
  const urls = fs
    .readFileSync(INPUT_PATH, 'utf8')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);

  fs.mkdirSync(HTML_DIR, { recursive: true });
  fs.writeFileSync(MANIFEST_PATH, '');
  fs.writeFileSync(FAILURES_PATH, '');

  const browser = await chromium.launch({
    headless: true,
    executablePath: '/usr/bin/chromium',
  });

  const context = await browser.newContext({
    userAgent: USER_AGENT,
    viewport: { width: 1440, height: 2000 },
    locale: 'en-US',
  });

  await context.route('**/*', async (route) => {
    const resourceType = route.request().resourceType();
    if (['image', 'media', 'font'].includes(resourceType)) {
      await route.abort();
      return;
    }
    await route.continue();
  });

  const page = await context.newPage();

  for (let index = 0; index < urls.length; index += 1) {
    const url = urls[index];
    const startedAt = new Date().toISOString();
    const hash = sha1(url).slice(0, 12);
    const fileName = `${String(index + 1).padStart(4, '0')}-${safeSlug(url)}-${hash}.html`;
    const htmlPath = path.join(HTML_DIR, fileName);

    try {
      const response = await page.goto(url, {
        waitUntil: 'domcontentloaded',
        timeout: 60000,
      });

      await page.waitForTimeout(1200);

      const title = await page.title();
      const finalUrl = page.url();
      const html = await page.content();
      const text = await page.locator('body').innerText().catch(() => '');

      fs.writeFileSync(htmlPath, html);
      fs.appendFileSync(
        MANIFEST_PATH,
        `${JSON.stringify({
          url,
          final_url: finalUrl,
          title,
          status: response ? response.status() : null,
          fetched_at: startedAt,
          html_file: path.relative(OUTPUT_DIR, htmlPath),
          text_length: text.length,
          html_length: html.length,
        })}\n`
      );

      console.error(`saved ${index + 1}/${urls.length}: ${url}`);
    } catch (error) {
      fs.appendFileSync(
        FAILURES_PATH,
        `${JSON.stringify({
          url,
          fetched_at: startedAt,
          error: error && error.message ? error.message : String(error),
        })}\n`
      );
      console.error(`failed ${index + 1}/${urls.length}: ${url}`);
    }

    await page.waitForTimeout(politeDelayMs());
  }

  await context.close();
  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
