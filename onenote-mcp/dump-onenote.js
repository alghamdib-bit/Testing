#!/usr/bin/env node

import { Client } from '@microsoft/microsoft-graph-client';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { JSDOM } from 'jsdom';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const tokenFilePath = path.join(__dirname, '.access-token.txt');
const outputPath = path.join(__dirname, 'onenote-dump.json');

function getAccessToken() {
  const tokenData = fs.readFileSync(tokenFilePath, 'utf8');
  try {
    return JSON.parse(tokenData).token;
  } catch {
    return tokenData.trim();
  }
}

function extractReadableText(html) {
  try {
    const dom = new JSDOM(html);
    const doc = dom.window.document;
    doc.querySelectorAll('script, style').forEach(el => el.remove());

    let lines = [];

    // Walk through body children in order to preserve structure
    function walk(node) {
      if (node.nodeType === 3) { // text node
        const t = node.textContent.trim();
        if (t) lines.push(t);
        return;
      }
      if (node.nodeType !== 1) return;

      const tag = node.tagName.toLowerCase();

      if (/^h[1-6]$/.test(tag)) {
        lines.push(`\n## ${node.textContent.trim()}\n`);
        return;
      }
      if (tag === 'li') {
        lines.push(`  - ${node.textContent.trim()}`);
        return;
      }
      if (tag === 'tr') {
        const cells = Array.from(node.querySelectorAll('td, th'))
          .map(c => c.textContent.trim()).join(' | ');
        if (cells) lines.push(`| ${cells} |`);
        return;
      }
      if (tag === 'p' || tag === 'div') {
        const t = node.textContent.trim();
        if (t) lines.push(t + '\n');
        return;
      }

      // Recurse for other elements
      for (const child of node.childNodes) {
        walk(child);
      }
    }

    if (doc.body) {
      for (const child of doc.body.childNodes) {
        walk(child);
      }
    }

    return lines.join('\n').replace(/\n{3,}/g, '\n\n').trim();
  } catch (error) {
    return `[Error extracting text: ${error.message}]`;
  }
}

async function fetchAllPages(client, url, accessToken) {
  let allPages = [];
  let nextUrl = url;

  while (nextUrl) {
    const response = await client.api(nextUrl).get();
    if (response.value) {
      allPages = allPages.concat(response.value);
    }
    nextUrl = response['@odata.nextLink'] || null;
    // The nextLink is a full URL, extract the path part
    if (nextUrl) {
      try {
        const parsed = new URL(nextUrl);
        nextUrl = parsed.pathname.replace('/v1.0', '') + parsed.search;
      } catch {
        // Already a path
      }
    }
  }
  return allPages;
}

async function main() {
  const accessToken = getAccessToken();
  if (!accessToken) {
    console.error('No access token found. Run: node authenticate.js');
    process.exit(1);
  }

  const client = Client.init({
    authProvider: (done) => done(null, accessToken)
  });

  const dump = {
    exportDate: new Date().toISOString(),
    notebooks: []
  };

  // Step 1: Get all notebooks
  console.log('Fetching notebooks...');
  const notebooksRes = await client.api('/me/onenote/notebooks').get();
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

    // Step 2: Get section groups
    try {
      const sgRes = await client.api(`/me/onenote/notebooks/${nb.id}/sectionGroups`).get();
      for (const sg of (sgRes.value || [])) {
        console.log(`  Section Group: "${sg.displayName}"`);
        const sgData = {
          id: sg.id,
          name: sg.displayName,
          sections: []
        };

        // Get sections within the section group
        const sgSectionsRes = await client.api(`/me/onenote/sectionGroups/${sg.id}/sections`).get();
        for (const section of (sgSectionsRes.value || [])) {
          console.log(`    Section: "${section.displayName}"`);
          const sectionData = await processSection(client, section, accessToken);
          sgData.sections.push(sectionData);
        }

        notebookData.sectionGroups.push(sgData);
      }
    } catch (err) {
      console.log(`  (No section groups or error: ${err.message})`);
    }

    // Step 3: Get top-level sections
    try {
      const sectionsRes = await client.api(`/me/onenote/notebooks/${nb.id}/sections`).get();
      for (const section of (sectionsRes.value || [])) {
        console.log(`  Section: "${section.displayName}"`);
        const sectionData = await processSection(client, section, accessToken);
        notebookData.sections.push(sectionData);
      }
    } catch (err) {
      console.log(`  (No sections or error: ${err.message})`);
    }

    dump.notebooks.push(notebookData);
  }

  // Step 4: Save to file
  fs.writeFileSync(outputPath, JSON.stringify(dump, null, 2));
  console.log(`\n\nDump complete! Saved to: ${outputPath}`);
  console.log(`Total notebooks: ${dump.notebooks.length}`);
  const totalSections = dump.notebooks.reduce((sum, nb) =>
    sum + nb.sections.length + nb.sectionGroups.reduce((s, sg) => s + sg.sections.length, 0), 0);
  const totalPages = dump.notebooks.reduce((sum, nb) => {
    const fromSections = nb.sections.reduce((s, sec) => s + sec.pages.length, 0);
    const fromSG = nb.sectionGroups.reduce((s, sg) =>
      s + sg.sections.reduce((s2, sec) => s2 + sec.pages.length, 0), 0);
    return sum + fromSections + fromSG;
  }, 0);
  console.log(`Total sections: ${totalSections}`);
  console.log(`Total pages: ${totalPages}`);
}

async function processSection(client, section, accessToken) {
  const sectionData = {
    id: section.id,
    name: section.displayName,
    createdDateTime: section.createdDateTime,
    lastModifiedDateTime: section.lastModifiedDateTime,
    pages: []
  };

  try {
    const pages = await fetchAllPages(client, `/me/onenote/sections/${section.id}/pages`, accessToken);
    console.log(`      ${pages.length} page(s)`);

    for (const page of pages) {
      const pageData = {
        id: page.id,
        title: page.title,
        createdDateTime: page.createdDateTime,
        lastModifiedDateTime: page.lastModifiedDateTime,
        contentText: ''
      };

      // Fetch page content
      try {
        const response = await fetch(page.contentUrl, {
          headers: { 'Authorization': `Bearer ${accessToken}` }
        });
        if (response.ok) {
          const html = await response.text();
          pageData.contentText = extractReadableText(html);
        } else {
          pageData.contentText = `[Error: HTTP ${response.status}]`;
        }
      } catch (err) {
        pageData.contentText = `[Error fetching content: ${err.message}]`;
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

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
