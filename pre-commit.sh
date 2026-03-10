#!/bin/bash
# Pre-commit check script for Cafe Order Processor
# Run this before committing to ensure code quality

set -e  # Exit on any error

echo "🔍 Running pre-commit checks for Cafe Order Processor..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print success
success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Function to print error
error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to print warning
warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Activate the local virtual environment if available
VENV_ACTIVATED=false
for VENV_DIR in ".venv" "venv" "env"; do
    if [ -d "${VENV_DIR}" ]; then
        if [ -f "${VENV_DIR}/bin/activate" ]; then
            # shellcheck source=/dev/null
            source "${VENV_DIR}/bin/activate"
            VENV_ACTIVATED=true
            break
        elif [ -f "${VENV_DIR}/Scripts/activate" ]; then
            # shellcheck source=/dev/null
            source "${VENV_DIR}/Scripts/activate"
            VENV_ACTIVATED=true
            break
        fi
    fi
done

if [ "${VENV_ACTIVATED}" = true ]; then
    success "Using Python virtual environment"
else
    warning "Proceeding without activating .venv (tools must already be on PATH)"
fi

# Determine which Python executable to use
PYTHON_CMD="python"
if ! command -v "${PYTHON_CMD}" > /dev/null 2>&1; then
    if command -v python3 > /dev/null 2>&1; then
        PYTHON_CMD="python3"
    else
        error "Python interpreter not found. Install Python or create a .venv environment."
        exit 1
    fi
fi

# 1. Formatting check
echo "1️⃣  Checking code formatting (Black)..."
if black --check . > /dev/null 2>&1; then
    success "Code formatting is correct"
else
    error "Code formatting failed. Run: black ."
    exit 1
fi

# 2. Import sorting check
echo ""
echo "2️⃣  Checking import sorting (isort)..."
if isort --check-only --profile=black --line-length=120 . > /dev/null 2>&1; then
    success "Imports are properly sorted"
else
    error "Import sorting failed. Run: isort ."
    exit 1
fi

# 3. Linting check
echo ""
echo "3️⃣  Running linting (flake8)..."
if flake8 . --max-line-length=120 --extend-ignore=E203,W503,E501 --exclude=.git,__pycache__,.venv,venv > /dev/null 2>&1; then
    success "Linting passed"
else
    error "Linting failed. Run: flake8 . --max-line-length=120 --extend-ignore=E203,W503,E501"
    exit 1
fi

# 4. Syntax validation (ast.parse to avoid writing .pyc)
echo ""
echo "4️⃣  Validating Python syntax..."
if "${PYTHON_CMD}" -c "
import ast
for f in ['cafe_order_processor.py']:
    ast.parse(open(f).read())
" 2>/dev/null; then
    success "Syntax validation passed"
else
    error "Syntax validation failed"
    exit 1
fi

# 5. .env.example check
echo ""
echo "5️⃣  Checking .env.example..."
if [ ! -f .env.example ]; then
    error ".env.example missing"
    exit 1
fi
if ! grep -q "OPENAI_API_KEY" .env.example; then
    error ".env.example must contain OPENAI_API_KEY"
    exit 1
fi
success ".env.example is valid"

# 6. Running tests
echo ""
echo "6️⃣  Running tests..."
if "${PYTHON_CMD}" -m pytest tests/ -v --tb=short > /dev/null 2>&1; then
    success "All tests passed"
else
    error "Tests failed. Run: pytest tests/ -v"
    exit 1
fi

# 7. Type checking (optional)
echo ""
echo "7️⃣  Running type checking (mypy)..."
if command -v mypy > /dev/null 2>&1; then
    if mypy cafe_order_processor.py --ignore-missing-imports --no-strict-optional 2>/dev/null; then
        success "Type checking passed"
    else
        warning "Type checking completed (warnings are acceptable)"
    fi
else
    warning "mypy not installed; skipping type check"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ All critical checks passed! Ready to commit.${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
