#!/bin/bash

# Script to help fix virtual environment issues

echo "🔍 Checking current Python environment..."
echo "Current python3: $(which python3)"
echo "Current pip3: $(which pip3)"

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment is active: $VIRTUAL_ENV"
else
    echo "❌ Virtual environment is NOT active"
    echo ""
    echo "To fix this, run:"
    echo "  source venv/bin/activate"
    echo ""
    echo "Then run this script again to verify."
    exit 1
fi

# Check if python3 is from venv
if [[ "$(which python3)" == *"venv/bin/python3"* ]]; then
    echo "✅ Using virtual environment Python"
else
    echo "❌ NOT using virtual environment Python"
    echo "Please ensure you've activated the venv properly"
    exit 1
fi

echo ""
echo "📦 Installing requirements..."
pip3 install -r requirements.txt

echo ""
echo "🧪 Testing the application..."
python3 main.py --help

echo ""
echo "✅ If you see the help menu above, everything is working!"
echo ""
echo "Next steps:"
echo "1. Always activate your venv with: source venv/bin/activate"
echo "2. Run the app with: python3 main.py --help"
echo "3. To deactivate the venv later: deactivate"