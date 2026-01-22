#!/bin/bash
# Test script to verify implementation progress

set -e

echo "============================================================"
echo "🧪 Konko Agent - Progress Testing"
echo "============================================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo "📊 Current Branch:"
git branch --show-current

echo ""
echo "📝 Recent Commits:"
git log --oneline -5

echo ""
echo "🔍 Setup Verification:"
python scripts/verify_setup.py

echo ""
echo "🧪 Running Tests (if any exist):"
if [ -f "tests/test_config_schema.py" ]; then
    echo -e "${GREEN}Running tests...${NC}"
    pytest -v --tb=short || echo -e "${YELLOW}Some tests failed${NC}"
else
    echo -e "${YELLOW}No tests found yet${NC}"
fi

echo ""
echo "📦 Checking Package Imports:"
python -c "
try:
    from packages.agent_config import schemas
    print('✓ agent-config importable')
except ImportError:
    print('⚠ agent-config not ready yet')

try:
    from packages.agent_runtime import state
    print('✓ agent-runtime importable')
except ImportError:
    print('⚠ agent-runtime not ready yet')

try:
    from packages.agent_core import agent
    print('✓ agent-core importable')
except ImportError:
    print('⚠ agent-core not ready yet')
" || echo -e "${YELLOW}Packages not ready yet${NC}"

echo ""
echo "============================================================"
echo "✅ Progress check complete!"
echo "============================================================"
