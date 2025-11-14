# Security Policy

## What Should NOT Be Committed

### ❌ Never Commit These Files:
- `.env` (actual environment variables)
- `.env.local`, `.env.production`, etc.
- `.claude/` directory (personal Claude Code configuration)
- Any files containing:
  - API keys
  - Passwords
  - Access tokens
  - Private keys (*.pem, *.key)
  - Database credentials
  - OAuth secrets

### ✅ Safe to Commit:
- `.env.example` (with placeholder values only)
- Configuration templates
- Public documentation
- Source code

## Current Security Status

### Protected in .gitignore:
```
.env
.env.local
.claude/
secrets/
*.pem
*.key
*.db
```

### Repository Scan Results:
- ✅ No active API keys in current commit
- ✅ `.env.example` contains only placeholders
- ✅ `.claude/` removed from repository
- ✅ `.gitignore` properly configured

## If You Accidentally Committed Secrets

### Immediate Actions:

1. **Rotate All Exposed Credentials Immediately**
   - Anthropic API keys: https://console.anthropic.com/
   - LangSmith API keys: https://smith.langchain.com/
   - Any other exposed keys

2. **Remove from Git History**
   ```bash
   # Use BFG Repo Cleaner or git filter-branch
   # Example with BFG:
   brew install bfg
   bfg --delete-files .env
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive
   git push --force
   ```

3. **Force Push to Update Remote**
   ```bash
   git push --force origin main
   ```

4. **Verify Removal**
   ```bash
   git log --all --full-history -- .env
   ```

## Best Practices

### 1. Use Environment Variables
```bash
# Set in your shell
export ANTHROPIC_API_KEY="your-key-here"
export LANGSMITH_API_KEY="your-key-here"

# Or use .env file (never commit!)
cp .env.example .env
# Edit .env with actual values
```

### 2. Pre-commit Hook
We have pre-commit hooks configured. Install them:
```bash
make pre-commit
# or
uv run pre-commit install
```

### 3. GitHub Secret Scanning
GitHub will block pushes containing secrets. If blocked:
- Remove the secret from files
- Amend the commit: `git commit --amend`
- Force push: `git push --force`

### 4. Use Secret Management Tools
For production:
- AWS Secrets Manager
- GCP Secret Manager
- HashiCorp Vault
- Azure Key Vault

## Reporting Security Issues

If you find a security vulnerability:

1. **DO NOT** open a public issue
2. Email: [your-security-email@domain.com]
3. Or use GitHub's private security advisory feature
4. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Developer Checklist

Before committing:
- [ ] Check for API keys: `grep -r "sk-" .`
- [ ] Check for tokens: `grep -r "token" .`
- [ ] Verify .env not staged: `git status`
- [ ] Review diff: `git diff --cached`
- [ ] Ensure .claude/ not included

Before pushing:
- [ ] Run: `git log --patch`
- [ ] Verify no secrets in history
- [ ] Confirm .gitignore is working

## Security Updates

This project follows security best practices:
- Dependencies are regularly updated
- Security patches are applied promptly
- Code undergoes security review
- Secrets are managed properly

## Questions?

For security questions, see:
- [GitHub Secret Scanning Docs](https://docs.github.com/en/code-security/secret-scanning)
- [Git Security Best Practices](https://git-scm.com/book/en/v2/Git-Tools-Credential-Storage)

---

**Last Updated:** November 2025
**Status:** Active Monitoring
