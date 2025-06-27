# Git Commands to Push Your Code

After creating your GitHub repository, run these commands:

## Option 1: If your repo is named "AI-agent-article"
```bash
git remote add origin https://github.com/fmckie/AI-agent-article.git
git branch -M main
git push -u origin main
```

## Option 2: If you used a different name
```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

## To verify your remote is set:
```bash
git remote -v
```

## Future commits:
```bash
# Make changes
git add .
git commit -m "Your commit message"
git push
```

## To pull changes:
```bash
git pull origin main
```

## Helpful Git Commands

### Check status
```bash
git status
```

### See commit history
```bash
git log --oneline
```

### Create a new branch
```bash
git checkout -b feature/new-feature
```

### Switch branches
```bash
git checkout main
```

### Merge a branch
```bash
git checkout main
git merge feature/new-feature
```

## Important Notes

1. Your `.env` file is NOT tracked (good for security!)
2. The `venv/` folder is NOT tracked (good practice!)
3. The `drafts/` folder is NOT tracked (generated content)

These are all properly configured in your `.gitignore` file.

## What You've Committed

✅ All Python source code
✅ Configuration examples (.env.example)
✅ Documentation and explanations
✅ Test files
✅ Requirements and setup files
❌ NOT: API keys, virtual environment, or generated content

This is exactly what should be in version control!