// Platform-specific imports
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let FormData: any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let fs: any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let path: any;

// Type guard for browser environment
declare const window: (Window & typeof globalThis) | undefined;

// Node.js environment
if (typeof window === 'undefined') {
  try {
    FormData = require('form-data');
    fs = require('fs');
    path = require('path');
  } catch {
    // form-data might not be available, will handle in code
  }
}

// Browser environment - use native FormData
if (typeof window !== 'undefined' && typeof FormData === 'undefined') {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  FormData = (window as any).FormData;
}

export interface StemSplitterOptions {
  /** API base URL (default: 'https://stem-splitter-api-production.up.railway.app') */
  baseUrl?: string;
  /** Request timeout in milliseconds (default: 300000 = 5 minutes) */
  timeout?: number;
}

export interface SeparationOptions {
  /** Number of stems: 2, 4, or 5 (default: 2) */
  stems?: 2 | 4 | 5;
}

export interface SeparationResult {
  /** Buffer containing the ZIP file with separated stems */
  data: Buffer;
  /** Filename of the downloaded file */
  filename: string;
  /** Request ID for tracking */
  requestId?: string;
}

export interface HealthStatus {
  /** Service status: "healthy", "degraded", or "unhealthy" */
  status: string;
  /** Service name */
  service: string;
  /** API version */
  version: string;
  /** Maximum file size in MB */
  max_file_size_mb: number;
  /** Allowed file extensions */
  allowed_extensions: string[];
  /** Directory accessibility status */
  directories?: {
    upload_accessible: boolean;
    output_accessible: boolean;
  };
  /** Available disk space in GB (if available) */
  disk_space_gb?: number;
  /** Whether disk space is sufficient (if available) */
  disk_ok?: boolean;
  /** Error message (if unhealthy) */
  error?: string;
}

export interface ApiInfo {
  /** API status message */
  message: string;
  /** API version */
  version: string;
  /** Documentation URL path */
  docs: string;
  /** Main endpoint path */
  endpoint: string;
  /** API description */
  description: string;
}

export class StemSplitterClient {
  private baseUrl: string;
  private timeout: number;

  constructor(options: StemSplitterOptions = {}) {
    this.baseUrl = options.baseUrl || 'https://stem-splitter-api-production.up.railway.app';
    this.timeout = options.timeout || 300000; // 5 minutes default
  }

  /**
   * Separate an audio file into stems (Node.js only)
   *
   * @param filePath - Path to the audio file
   * @param options - Separation options
   * @returns Promise resolving to the separation result
   *
   * @example
   * ```typescript
   * const client = new StemSplitterClient({ baseUrl: 'https://stem-splitter-api-production.up.railway.app' });
   * const result = await client.separate('./audio.mp3', { stems: 2 });
   * fs.writeFileSync('output.zip', result.data);
   * ```
   */
  async separate(filePath: string, options: SeparationOptions = {}): Promise<SeparationResult> {
    // Edge case: Check if running in Node.js
    if (typeof window !== 'undefined' && typeof window === 'object') {
      throw new Error(
        'separate() method is only available in Node.js. ' +
          'Use separateFromBuffer() in browser environments.'
      );
    }

    if (!fs || !path || !FormData) {
      throw new Error(
        'Node.js dependencies not available. ' +
          'Make sure form-data is installed: npm install form-data'
      );
    }

    const stems = options.stems || 2;

    // Edge case: Validate stems
    if (![2, 4, 5].includes(stems)) {
      throw new Error('Stems must be 2, 4, or 5');
    }

    // Edge case: Validate file path
    if (!filePath || typeof filePath !== 'string') {
      throw new Error('File path must be a non-empty string');
    }

    // Edge case: Validate file exists
    if (!fs.existsSync(filePath)) {
      throw new Error(`File not found: ${filePath}`);
    }

    // Edge case: Check if it's a file (not directory)
    try {
      const stats = fs.statSync(filePath);
      if (!stats.isFile()) {
        throw new Error(`Path is not a file: ${filePath}`);
      }
    } catch (e) {
      if (e instanceof Error && e.message.includes('not a file')) {
        throw e;
      }
      throw new Error(`Cannot access file: ${filePath}`);
    }

    // Create form data
    const formData = new FormData();
    formData.append('file', fs.createReadStream(filePath), {
      filename: path.basename(filePath),
    });
    formData.append('stems', stems.toString());

    // Make request
    const url = `${this.baseUrl}/separate`;

    try {
      const response = await this.fetchWithTimeout(url, {
        method: 'POST',
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        body: formData as any,
        headers: formData.getHeaders(),
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `API request failed with status ${response.status}`;

        try {
          const errorJson = JSON.parse(errorText);
          errorMessage = errorJson.detail || errorMessage;
        } catch {
          errorMessage = errorText || errorMessage;
        }

        throw new Error(errorMessage);
      }

      const buffer = Buffer.from(await response.arrayBuffer());
      const contentDisposition = response.headers.get('content-disposition');
      const requestId = response.headers.get('x-request-id') || undefined;

      // Edge case: Handle missing filename
      let filename = 'separated.zip';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1];
        }
      }

      // Edge case: Validate buffer
      if (!buffer || buffer.length === 0) {
        throw new Error('Received empty response from server');
      }

      return {
        data: buffer,
        filename,
        requestId,
      };
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error(`Failed to separate audio: ${String(error)}`);
    }
  }

  /**
   * Separate an audio file from a buffer (works in both Node.js and browser)
   *
   * @param buffer - Audio file buffer (Buffer in Node.js, ArrayBuffer/Blob in browser)
   * @param filename - Original filename
   * @param options - Separation options
   * @returns Promise resolving to the separation result
   */
  async separateFromBuffer(
    buffer: Buffer | ArrayBuffer | Blob,
    filename: string,
    options: SeparationOptions = {}
  ): Promise<SeparationResult> {
    const stems = options.stems || 2;

    // Edge case: Validate stems
    if (![2, 4, 5].includes(stems)) {
      throw new Error('Stems must be 2, 4, or 5');
    }

    // Edge case: Validate buffer
    if (!buffer) {
      throw new Error('Buffer is required');
    }

    // Edge case: Validate filename
    if (!filename || typeof filename !== 'string' || filename.trim().length === 0) {
      throw new Error('Filename must be a non-empty string');
    }

    // Edge case: Convert Blob/ArrayBuffer to Buffer if needed
    let bufferToUse: Buffer;
    if (buffer instanceof Blob) {
      const arrayBuffer = await buffer.arrayBuffer();
      bufferToUse = Buffer.from(arrayBuffer);
    } else if (buffer instanceof ArrayBuffer) {
      bufferToUse = Buffer.from(buffer);
    } else if (Buffer.isBuffer(buffer)) {
      bufferToUse = buffer;
    } else {
      throw new Error('Invalid buffer type. Expected Buffer, ArrayBuffer, or Blob');
    }

    // Edge case: Check buffer size
    if (bufferToUse.length === 0) {
      throw new Error('Buffer is empty');
    }

    // Create form data (platform-specific)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let formData: any;
    let headers: Record<string, string> = {};

    if (typeof window !== 'undefined' && typeof window === 'object') {
      // Browser environment - use native FormData
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const BrowserFormData = (window as any).FormData;
      formData = new BrowserFormData();
      // Convert Buffer to Uint8Array for browser compatibility
      const uint8Array = new Uint8Array(bufferToUse);
      const blob = new Blob([uint8Array]);
      formData.append('file', blob, filename);
      formData.append('stems', stems.toString());
      // Browser will set Content-Type automatically with boundary
    } else {
      // Node.js environment
      if (!FormData) {
        throw new Error('FormData not available. Install form-data: npm install form-data');
      }
      formData = new FormData();
      formData.append('file', bufferToUse, {
        filename,
      });
      formData.append('stems', stems.toString());
      headers = formData.getHeaders();
    }

    // Make request
    const url = `${this.baseUrl}/separate`;

    try {
      const response = await this.fetchWithTimeout(url, {
        method: 'POST',
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        body: formData as any,
        headers,
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `API request failed with status ${response.status}`;

        try {
          const errorJson = JSON.parse(errorText);
          errorMessage = errorJson.detail || errorMessage;
        } catch {
          errorMessage = errorText || errorMessage;
        }

        throw new Error(errorMessage);
      }

      const arrayBuffer = await response.arrayBuffer();
      const resultBuffer = Buffer.from(arrayBuffer);
      const contentDisposition = response.headers.get('content-disposition');
      const requestId = response.headers.get('x-request-id') || undefined;

      // Edge case: Handle missing filename
      let resultFilename = 'separated.zip';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch && filenameMatch[1]) {
          resultFilename = filenameMatch[1];
        }
      }

      // Edge case: Validate result buffer
      if (!resultBuffer || resultBuffer.length === 0) {
        throw new Error('Received empty response from server');
      }

      return {
        data: resultBuffer,
        filename: resultFilename,
        requestId,
      };
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error(`Failed to separate audio: ${String(error)}`);
    }
  }

  /**
   * Check API health status
   *
   * @returns Promise resolving to health status
   */
  async healthCheck(): Promise<HealthStatus> {
    try {
      const response = await fetch(`${this.baseUrl}/health`);
      if (!response.ok) {
        throw new Error(`Health check failed: ${response.status}`);
      }
      const data = (await response.json()) as HealthStatus;
      return data;
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error(`Health check failed: ${String(error)}`);
    }
  }

  /**
   * Get API information from root endpoint
   *
   * @returns Promise resolving to API information
   */
  async getInfo(): Promise<ApiInfo> {
    try {
      const response = await fetch(`${this.baseUrl}/`);
      if (!response.ok) {
        throw new Error(`API info request failed: ${response.status}`);
      }
      const data = (await response.json()) as ApiInfo;
      return data;
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error(`Failed to get API info: ${String(error)}`);
    }
  }

  /**
   * Fetch with timeout support and error handling
   */
  private async fetchWithTimeout(
    url: string,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    options: RequestInit & { body?: any }
  ): Promise<Response> {
    // Edge case: Validate URL
    if (!url || typeof url !== 'string') {
      throw new Error('Invalid URL provided');
    }

    try {
      new URL(url); // Validate URL format
    } catch {
      throw new Error(`Invalid URL format: ${url}`);
    }

    // Edge case: Check if fetch is available
    if (typeof fetch === 'undefined') {
      // Node.js < 18 - need to use node-fetch or similar
      throw new Error(
        'fetch is not available. ' +
          'For Node.js < 18, install node-fetch: npm install node-fetch@2'
      );
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new Error(`Request timeout after ${this.timeout}ms`);
        }
        // Edge case: Network errors
        if (error.message.includes('fetch')) {
          throw new Error(`Network error: ${error.message}`);
        }
      }
      throw error;
    }
  }
}

// Export default instance creator
export function createClient(options?: StemSplitterOptions): StemSplitterClient {
  return new StemSplitterClient(options);
}

// Default export - using separate export to avoid duplicate export warning
const StemSplitterClientDefault = StemSplitterClient;
export default StemSplitterClientDefault;
