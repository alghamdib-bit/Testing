#!/usr/bin/env node

// Zero-dependency authentication using native fetch (works on Node.js v18+)
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const tokenFilePath = path.join(__dirname, '.access-token.txt');

const clientId = '14d82eec-204b-4c2f-b7e8-296a70dab67e';
const scopes = 'Notes.Read.All Notes.ReadWrite.All User.Read offline_access';
const tenant = 'common';

async function authenticate() {
  console.log('Starting authentication...');
  console.log('You will see a URL and code to enter shortly...\n');

  // Step 1: Request device code
  const deviceCodeRes = await fetch(
    `https://login.microsoftonline.com/${tenant}/oauth2/v2.0/devicecode`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `client_id=${clientId}&scope=${encodeURIComponent(scopes)}`
    }
  );

  const deviceCode = await deviceCodeRes.json();

  if (deviceCode.error) {
    console.error('Error getting device code:', deviceCode.error_description);
    process.exit(1);
  }

  console.log(deviceCode.message);

  // Step 2: Poll for token
  const interval = (deviceCode.interval || 5) * 1000;
  const expiresAt = Date.now() + deviceCode.expires_in * 1000;

  while (Date.now() < expiresAt) {
    await new Promise(r => setTimeout(r, interval));

    const tokenRes = await fetch(
      `https://login.microsoftonline.com/${tenant}/oauth2/v2.0/token`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `grant_type=urn:ietf:params:oauth:grant-type:device_code&client_id=${clientId}&device_code=${deviceCode.device_code}`
      }
    );

    const tokenData = await tokenRes.json();

    if (tokenData.access_token) {
      fs.writeFileSync(tokenFilePath, JSON.stringify({ token: tokenData.access_token }));
      console.log('\nAuthentication successful!');
      console.log('Access token saved to:', tokenFilePath);
      return;
    }

    if (tokenData.error === 'authorization_pending') {
      process.stdout.write('.');
      continue;
    }

    if (tokenData.error === 'slow_down') {
      await new Promise(r => setTimeout(r, 5000));
      continue;
    }

    console.error('\nAuth error:', tokenData.error_description || tokenData.error);
    process.exit(1);
  }

  console.error('\nDevice code expired. Please try again.');
  process.exit(1);
}

authenticate();
