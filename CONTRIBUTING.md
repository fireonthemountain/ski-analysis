# Contributing to Ski Technique Analysis

Thank you for your interest in contributing to Ski Technique Analysis! This document provides guidelines and instructions for contributing to the project.

## 🎯 Ways to Contribute

- **Report bugs** - Submit detailed bug reports with reproduction steps
- **Suggest features** - Propose new features or enhancements
- **Improve documentation** - Help us improve our docs
- **Submit code** - Fix bugs or implement new features
- **Test and provide feedback** - Try the app and share your experience

## 🚀 Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/ski-analysis.git
cd ski-analysis

# Add upstream remote
git remote add upstream https://github.com/fireonthemountain/ski-analysis.git
```

### 2. Set Up Development Environment

```bash
# Install frontend dependencies
cd frontend
npm install

# Install backend dependencies
cd ../backend
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run with Docker Compose (recommended)
docker-compose up
```

### 3. Create a Branch

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

## 📝 Development Guidelines

### Code Style

**Python (Backend)**
- Follow PEP 8 style guide
- Use `black` for code formatting: `black .`
- Use `flake8` for linting: `flake8 .`
- Use type hints where appropriate
- Maximum line length: 100 characters

**TypeScript/React (Frontend)**
- Follow the existing code style
- Use ESLint: `npm run lint`
- Use functional components with hooks
- Prefer named exports over default exports
- Use TypeScript strict mode

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(analysis): add edge angle calculation for carving detection

fix(video): resolve upload timeout for large files

docs(readme): update installation instructions for Windows
```

### Testing

**Backend Tests**
```bash
cd backend
pytest
pytest --cov  # With coverage report
```

**Frontend Tests**
```bash
cd frontend
npm test
npm run test:coverage
```

**Before submitting a PR**:
- All tests must pass
- Add tests for new features
- Maintain or improve code coverage

### Documentation

- Update README.md if you change setup/installation
- Add docstrings to new functions and classes
- Update API documentation for endpoint changes
- Add comments for complex logic

## 🔄 Pull Request Process

### 1. Ensure Quality

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New code has tests
- [ ] Documentation is updated
- [ ] No console errors or warnings
- [ ] Commit messages follow convention

### 2. Submit PR

1. Push your branch to your fork
2. Go to the original repository on GitHub
3. Click "New Pull Request"
4. Select your branch
5. Fill out the PR template with:
   - Description of changes
   - Related issue numbers
   - Screenshots (if UI changes)
   - Testing steps

### 3. PR Template

```markdown
## Description
Brief description of what this PR does

## Related Issues
Fixes #123
Related to #456

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Manual testing completed
- [ ] Tested on multiple browsers (if frontend)

## Screenshots (if applicable)
[Add screenshots here]

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests pass locally
```

### 4. Code Review

- Be open to feedback and suggestions
- Respond to review comments promptly
- Make requested changes in new commits (don't force push)
- Once approved, we'll merge your PR

## 🐛 Reporting Bugs

### Before Submitting

1. Check existing issues to avoid duplicates
2. Try to reproduce on the latest version
3. Collect relevant information

### Bug Report Template

```markdown
**Describe the bug**
Clear description of what the bug is

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What you expected to happen

**Screenshots**
If applicable, add screenshots

**Environment:**
 - OS: [e.g. macOS 14.0]
 - Browser: [e.g. Chrome 120]
 - Version: [e.g. 0.1.0]

**Additional context**
Any other relevant information
```

## 💡 Feature Requests

### Feature Request Template

```markdown
**Problem Statement**
What problem does this feature solve?

**Proposed Solution**
How should this feature work?

**Alternatives Considered**
Other solutions you've thought about

**Additional Context**
Mockups, examples, or references
```

## 🎨 Design Contributions

- Follow existing UI/UX patterns
- Ensure accessibility (WCAG 2.1 AA)
- Test on multiple screen sizes
- Consider mobile experience
- Use existing design system components

## 📚 Documentation Contributions

- Use clear, concise language
- Include code examples where helpful
- Add diagrams for complex concepts
- Keep formatting consistent
- Check for spelling and grammar

## 🏗️ Project Structure

```
ski-analysis/
├── frontend/          # React application
├── backend/          # FastAPI application
├── docs/            # Documentation
├── tests/           # Integration tests
└── scripts/         # Utility scripts
```

## 🤝 Community Guidelines

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Follow our Code of Conduct

## ❓ Questions?

- Open a [Discussion](https://github.com/fireonthemountain/ski-analysis/discussions) for questions
- Join our community chat (if available)
- Check existing documentation first

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Ski Technique Analysis! 🎿
