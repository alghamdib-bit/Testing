#!/usr/bin/env node

import { PublicClientApplication } from '@azure/msal-node';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const tokenFilePath = path.join(__dirname, '.access-token.txt');

const msalConfig = {
  auth: {
    clientId: '14d82eec-204b-4c2f-b7e8-296a70dab67e',
    authority: 'https://login.microsoftonline.com/common'
  }
};

const scopes = ['Notes.Read.All', 'Notes.ReadWrite.All', 'User.Read'];

async function authenticate() {
  const pca = new PublicClientApplication(msalConfig);

  console.log('Starting authentication...');
  console.log('You will see a URL and code to enter shortly...\n');

  const deviceCodeRequest = {
    scopes,
    deviceCodeCallback: (response) => {
      console.log(response.message);
    }
  };

  try {
    const result = await pca.acquireTokenByDeviceCode(deviceCodeRequest);
    fs.writeFileSync(tokenFilePath, JSON.stringify({ token: result.accessToken }));
    console.log('\nAuthentication successful!');
    console.log('Access token saved to:', tokenFilePath);
  } catch (error) {
    console.error('Authentication error:', error.message);
  }
}

authenticate();
