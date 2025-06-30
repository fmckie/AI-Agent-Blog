# Virtual Environment Troubleshooting Guide

## The Problem
Your terminal shows `(venv)` but you're actually using system Python, not the virtual environment Python. This causes import errors because packages are installed in the wrong location.

## Quick Fix

Run these commands in order:

```bash
# 1. Deactivate any partial activation
deactivate

# 2. Properly activate the virtual environment
source venv/bin/activate

# 3. Verify you're using the right Python
which python3
# Should show: /Users/willmckie/AI_agent_article/venv/bin/python3

# 4. Install all requirements
pip3 install -r requirements.txt

# 5. Test the application
python3 main.py --help
```

## Understanding Virtual Environments

### What is a Virtual Environment?
A virtual environment is an isolated Python installation that:
- Has its own packages separate from system Python
- Prevents version conflicts between projects
- Keeps your system Python clean

### How Activation Works
When you activate a virtual environment:
1. It modifies your PATH to prioritize venv binaries
2. Sets VIRTUAL_ENV environment variable
3. Changes your prompt to show `(venv)`

### Common Issues

1. **Partial Activation**
   - Symptom: `(venv)` in prompt but wrong Python
   - Cause: Shell configuration issues
   - Fix: Deactivate and reactivate

2. **Wrong Python Path**
   - Symptom: `which python3` shows `/usr/local/bin/python3`
   - Cause: PATH not updated properly
   - Fix: Source the activation script again

3. **Missing Packages**
   - Symptom: ModuleNotFoundError
   - Cause: Packages installed to wrong Python
   - Fix: Activate venv, then reinstall

## Verification Steps

After activation, all these should be true:
```bash
# Check Python location
which python3
# ✅ Should contain: venv/bin/python3

# Check pip location  
which pip3
# ✅ Should contain: venv/bin/pip3

# Check environment variable
echo $VIRTUAL_ENV
# ✅ Should show: /Users/willmckie/AI_agent_article/venv

# Check installed packages
pip3 list | grep backoff
# ✅ Should show: backoff 2.2.1 (or higher)
```

## Best Practices

1. **Always activate venv first**
   ```bash
   cd /Users/willmckie/AI_agent_article
   source venv/bin/activate
   ```

2. **Use the helper script**
   ```bash
   ./fix_venv.sh
   ```

3. **Add to your shell profile** (optional)
   Add this to ~/.bashrc or ~/.zshrc:
   ```bash
   alias ai-venv='cd /Users/willmckie/AI_agent_article && source venv/bin/activate'
   ```

4. **Check before running**
   Always verify with `which python3` before running commands

## Troubleshooting Commands

```bash
# See all installed packages
pip3 list

# See where a package is installed
pip3 show backoff

# Reinstall all requirements
pip3 install --force-reinstall -r requirements.txt

# Create a fresh venv if needed
python3 -m venv venv --clear
```

## Why This Matters

Using the wrong Python can cause:
- Import errors (like we saw)
- Version conflicts
- Accidentally installing packages globally
- Inconsistent behavior between developers

Always ensure you're in the right environment before working on a project!