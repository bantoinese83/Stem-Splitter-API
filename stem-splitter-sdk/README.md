# Stem Splitter API - JavaScript/TypeScript SDK

Easy-to-use JavaScript/TypeScript SDK for the Stem Splitter API. Separate audio files into stems (vocals, drums, bass, etc.) with just a few lines of code.

## Installation

```bash
npm install stem-splitter-api
# or
yarn add stem-splitter-api
# or
pnpm add stem-splitter-api
```

## Quick Start

```typescript
import { StemSplitterClient } from 'stem-splitter-api';
import fs from 'fs';

// Create client
const client = new StemSplitterClient({
  baseUrl: 'https://your-api-url.com'
});

// Separate audio file
const result = await client.separate('./audio.mp3', { stems: 2 });

// Save result
fs.writeFileSync('output.zip', result.data);
console.log(`Saved: ${result.filename}`);
```

## API Reference

### `StemSplitterClient`

Main client class for interacting with the Stem Splitter API.

#### Constructor

```typescript
new StemSplitterClient(options?: StemSplitterOptions)
```

**Options:**
- `baseUrl` (string, optional): API base URL (default: `'http://localhost:8000'`)
- `timeout` (number, optional): Request timeout in milliseconds (default: `300000` = 5 minutes)

#### Methods

##### `separate(filePath, options?)`

Separate an audio file from the file system.

**Parameters:**
- `filePath` (string): Path to the audio file
- `options` (object, optional):
  - `stems` (2 | 4 | 5): Number of stems (default: 2)

**Returns:** `Promise<SeparationResult>`

**Example:**
```typescript
const result = await client.separate('./song.mp3', { stems: 4 });
```

##### `separateFromBuffer(buffer, filename, options?)`

Separate an audio file from a buffer.

**Parameters:**
- `buffer` (Buffer): Audio file buffer
- `filename` (string): Original filename
- `options` (object, optional):
  - `stems` (2 | 4 | 5): Number of stems (default: 2)

**Returns:** `Promise<SeparationResult>`

**Example:**
```typescript
const audioBuffer = fs.readFileSync('./song.mp3');
const result = await client.separateFromBuffer(audioBuffer, 'song.mp3', { stems: 2 });
```

##### `healthCheck()`

Check API health status.

**Returns:** `Promise<HealthStatus>`

**Example:**
```typescript
const health = await client.healthCheck();
console.log(health.status); // "healthy"
console.log(health.disk_space_gb); // Available disk space
console.log(health.allowed_extensions); // [".flac", ".m4a", ".mp3", ...]
```

##### `getInfo()`

Get API information from root endpoint.

**Returns:** `Promise<ApiInfo>`

**Example:**
```typescript
const info = await client.getInfo();
console.log(info.message); // "Stem Splitter API is running"
console.log(info.docs); // "/docs"
```

## Examples

### Node.js Example

```typescript
import { StemSplitterClient } from 'stem-splitter-api';
import fs from 'fs';
import path from 'path';

async function main() {
  const client = new StemSplitterClient({
    baseUrl: 'https://api.example.com',
    timeout: 600000, // 10 minutes
  });

  try {
    // Check health
    const health = await client.healthCheck();
    console.log('API Status:', health.status);
    console.log('Max file size:', health.max_file_size_mb, 'MB');

    // Separate audio
    console.log('Separating audio...');
    const result = await client.separate('./input.mp3', { stems: 2 });

    // Save output
    const outputPath = path.join(__dirname, 'output.zip');
    fs.writeFileSync(outputPath, result.data);
    console.log(`Saved to: ${outputPath}`);
    console.log(`Request ID: ${result.requestId}`);
  } catch (error) {
    console.error('Error:', error.message);
  }
}

main();
```

### Browser Example (with File Input)

```typescript
import { StemSplitterClient } from 'stem-splitter-api';

const client = new StemSplitterClient({
  baseUrl: 'https://api.example.com',
});

async function handleFileUpload(file: File) {
  try {
    // Convert File to Buffer (in browser)
    const arrayBuffer = await file.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    // Separate audio
    const result = await client.separateFromBuffer(buffer, file.name, { stems: 2 });

    // Download result
    const blob = new Blob([result.data], { type: 'application/zip' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = result.filename;
    a.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    console.error('Error:', error.message);
  }
}
```

### Error Handling

```typescript
try {
  const result = await client.separate('./audio.mp3', { stems: 2 });
  // Handle success
} catch (error) {
  if (error.message.includes('File too large')) {
    console.error('File exceeds maximum size limit');
  } else if (error.message.includes('Invalid file type')) {
    console.error('File type not supported');
  } else if (error.message.includes('timeout')) {
    console.error('Request timed out - file may be too large or processing too slow');
  } else {
    console.error('Unexpected error:', error.message);
  }
}
```

## Supported Formats

- MP3
- WAV
- OGG
- FLAC
- M4A

## Stems Options

- **2 stems**: Vocals, Accompaniment
- **4 stems**: Vocals, Drums, Bass, Other
- **5 stems**: Vocals, Drums, Bass, Piano, Other

## TypeScript Support

Full TypeScript definitions are included. The package exports all types:

```typescript
import {
  StemSplitterClient,
  StemSplitterOptions,
  SeparationOptions,
  SeparationResult,
  HealthStatus,
  ApiInfo,
} from 'stem-splitter-api';
```

## License

MIT

## Support

For API documentation and support, visit the API docs at `/docs` endpoint.

