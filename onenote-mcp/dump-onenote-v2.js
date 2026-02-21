#!/usr/bin/env node

// Zero-dependency OneNote dump script (native fetch only, works on Node.js v18+)
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const tokenFilePath = path.join(__dirname, '.access-token.txt');
const outputPath = path.join(__dirname, 'onenote-dump.json');
const GRAPH = 'https://graph.microsoft.com/v1.0';

function getAccessToken() {
  const tokenData = fs.readFileSync(tokenFilePath, 'utf8');
  try {
    return JSON.parse(tokenData).token;
  } catch {
    return tokenData.trim();
  }
}

function extractReadableText(html) {
  // Simple HTML to text without JSDOM
  return html
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<h[1-6][^>]*>([\s\S]*?)<\/h[1-6]>/gi, '\n## $1\n')
    .replace(/<li[^>]*>([\s\S]*?)<\/li>/gi, '  - $1\n')
    .replace(/<td[^>]*>([\s\S]*?)<\/td>/gi, '$1 | ')
    .replace(/<tr[^>]*>([\s\S]*?)<\/tr>/gi, '| $1\n')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<p[^>]*>([\s\S]*?)<\/p>/gi, '$1\n\n')
    .replace(/<div[^>]*>([\s\S]*?)<\/div>/gi, '$1\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

async function graphGet(endpoint, token) {
  const url = endpoint.startsWith('http') ? endpoint : `${GRAPH}${endpoint}`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`HTTP ${res.status}: ${body.slice(0, 200)}`);
  }
  return res.json();
}

async function graphGetHtml(url, token) {
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) return `[Error: HTTP ${res.status}]`;
  return res.text();
}

async function fetchAllPages(endpoint, token) {
  let allPages = [];
  let url = endpoint;
  while (url) {
    const data = await graphGet(url, token);
    if (data.value) allPages = allPages.concat(data.value);
    url = data['@odata.nextLink'] || null;
  }
  return allPages;
}

async function processSection(section, token) {
  const sectionData = {
    id: section.id,
    name: section.displayName,
    createdDateTime: section.createdDateTime,
    lastModifiedDateTime: section.lastModifiedDateTime,
    pages: []
  };

  try {
    const pages = await fetchAllPages(`/me/onenote/sections/${section.id}/pages?$top=100`, token);
    console.log(`      ${pages.length} page(s)`);

    for (const page of pages) {
      const pageData = {
        id: page.id,
        title: page.title,
        createdDateTime: page.createdDateTime,
        lastModifiedDateTime: page.lastModifiedDateTime,
        contentText: ''
      };

      try {
        const html = await graphGetHtml(page.contentUrl, token);
        pageData.contentText = extractReadableText(html);
      } catch (err) {
        pageData.contentText = `[Error: ${err.message}]`;
      }

      sectionData.pages.push(pageData);
      process.stdout.write('.');
    }
    if (pages.length > 0) console.log('');
  } catch (err) {
    console.log(`      Error fetching pages: ${err.message}`);
  }

  return sectionData;
}

async function main() {
  const token = getAccessToken();
  if (!token) {
    console.error('No access token found. Run: node authenticate-v2.js');
    process.exit(1);
  }

  const dump = { exportDate: new Date().toISOString(), notebooks: [] };

  console.log('Fetching notebooks...');
  const notebooksRes = await graphGet('/me/onenote/notebooks', token);
  const notebooks = notebooksRes.value || [];
  console.log(`Found ${notebooks.length} notebook(s)\n`);

  for (const nb of notebooks) {
    console.log(`\nNotebook: "${nb.displayName}"`);
    const notebookData = {
      id: nb.id,
      name: nb.displayName,
      createdDateTime: nb.createdDateTime,
      lastModifiedDateTime: nb.lastModifiedDateTime,
      sectionGroups: [],
      sections: []
    };

    // Section groups
    try {
      const sgRes = await graphGet(`/me/onenote/notebooks/${nb.id}/sectionGroups`, token);
      for (const sg of (sgRes.value || [])) {
        console.log(`  Section Group: "${sg.displayName}"`);
        const sgData = { id: sg.id, name: sg.displayName, sections: [] };

        const sgSections = await graphGet(`/me/onenote/sectionGroups/${sg.id}/sections`, token);
        for (const section of (sgSections.value || [])) {
          console.log(`    Section: "${section.displayName}"`);
          sgData.sections.push(await processSection(section, token));
        }
        notebookData.sectionGroups.push(sgData);
      }
    } catch (err) {
      console.log(`  (No section groups or error: ${err.message})`);
    }

    // Top-level sections
    try {
      const sectionsRes = await graphGet(`/me/onenote/notebooks/${nb.id}/sections`, token);
      for (const section of (sectionsRes.value || [])) {
        console.log(`  Section: "${section.displayName}"`);
        notebookData.sections.push(await processSection(section, token));
      }
    } catch (err) {
      console.log(`  (No sections or error: ${err.message})`);
    }

    dump.notebooks.push(notebookData);
  }

  fs.writeFileSync(outputPath, JSON.stringify(dump, null, 2));
  console.log(`\n\nDump complete! Saved to: ${outputPath}`);

  const totalSections = dump.notebooks.reduce((sum, nb) =>
    sum + nb.sections.length + nb.sectionGroups.reduce((s, sg) => s + sg.sections.length, 0), 0);
  const totalPages = dump.notebooks.reduce((sum, nb) => {
    const fromSections = nb.sections.reduce((s, sec) => s + sec.pages.length, 0);
    const fromSG = nb.sectionGroups.reduce((s, sg) =>
      s + sg.sections.reduce((s2, sec) => s2 + sec.pages.length, 0), 0);
    return sum + fromSections + fromSG;
  }, 0);
  console.log(`Total notebooks: ${dump.notebooks.length}`);
  console.log(`Total sections: ${totalSections}`);
  console.log(`Total pages: ${totalPages}`);
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
