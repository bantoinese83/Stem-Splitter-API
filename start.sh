#!/bin/bash

# Stem Splitter API Startup Script

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Stem Splitter API...${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -q -r requirements.txt

# Create necessary directories
mkdir -p temp/uploads temp/output logs

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file from defaults...${NC}"
    cat > .env << EOF
APP_TITLE=Stem Splitter API
UPLOAD_DIR=temp/uploads
OUTPUT_DIR=temp/output
MAX_FILE_SIZE_MB=100
RATE_LIMIT_PER_MINUTE=30
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
EOF
fi

# Start the server
echo -e "${GREEN}Starting server on http://localhost:8000${NC}"
echo -e "${GREEN}API Docs: http://localhost:8000/docs${NC}"
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

