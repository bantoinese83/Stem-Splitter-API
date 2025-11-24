/**
 * Node.js Example - Stem Splitter API
 * 
 * This example demonstrates how to use the Stem Splitter API
 * from Node.js using the SDK or raw fetch.
 */

// Option 1: Using the SDK (recommended)
const { StemSplitterClient } = require('stem-splitter-api');
const fs = require('fs');
const path = require('path');

async function exampleWithSDK() {
  console.log('=== Using SDK ===');
  
  const client = new StemSplitterClient({
    baseUrl: 'http://localhost:8000', // Change to your API URL
    timeout: 600000, // 10 minutes
  });

  try {
    // Check API health
    console.log('Checking API health...');
    const health = await client.healthCheck();
    console.log('API Status:', health.status);
    console.log('Max file size:', health.max_file_size_mb, 'MB');
    console.log('Allowed formats:', health.allowed_extensions.join(', '));

    // Separate audio file
    const inputFile = './data/audio_example.mp3'; // Change to your audio file
    if (!fs.existsSync(inputFile)) {
      console.error(`File not found: ${inputFile}`);
      return;
    }

    console.log(`\nSeparating audio: ${inputFile}`);
    console.log('This may take a few minutes...');
    
    const result = await client.separate(inputFile, { stems: 2 });

    // Save output
    const outputPath = path.join(__dirname, 'output.zip');
    fs.writeFileSync(outputPath, result.data);
    
    console.log(`\n✅ Success!`);
    console.log(`Saved to: ${outputPath}`);
    console.log(`Filename: ${result.filename}`);
    console.log(`Request ID: ${result.requestId}`);
  } catch (error) {
    console.error('\n❌ Error:', error.message);
    if (error.message.includes('File too large')) {
      console.error('   → File exceeds maximum size limit');
    } else if (error.message.includes('Invalid file type')) {
      console.error('   → File type not supported');
    } else if (error.message.includes('timeout')) {
      console.error('   → Request timed out');
    }
  }
}

// Option 2: Using raw fetch (without SDK)
async function exampleWithFetch() {
  console.log('\n=== Using Raw Fetch ===');
  
  const FormData = require('form-data');
  const fs = require('fs');
  const fetch = require('node-fetch');

  try {
    const formData = new FormData();
    formData.append('file', fs.createReadStream('./data/audio_example.mp3'));
    formData.append('stems', '2');

    const response = await fetch('http://localhost:8000/separate', {
      method: 'POST',
      body: formData,
      headers: formData.getHeaders(),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    const buffer = await response.buffer();
    fs.writeFileSync('./output-fetch.zip', buffer);
    
    console.log('✅ Success! Saved to output-fetch.zip');
    console.log('Request ID:', response.headers.get('x-request-id'));
  } catch (error) {
    console.error('❌ Error:', error.message);
  }
}

// Run examples
(async () => {
  await exampleWithSDK();
  // Uncomment to try raw fetch example:
  // await exampleWithFetch();
})();

