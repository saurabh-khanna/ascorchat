# Contributing to surveychat

Thank you for your interest in contributing to surveychat! This document provides guidelines for contributions.

## Reporting Issues

If you find a bug or have a feature request, please [open an issue](../../issues) on GitHub. When reporting a bug, include:

- A clear description of the problem
- Steps to reproduce the issue
- Your Python version and operating system
- The full error message or traceback, if applicable

## Submitting Changes

1. Fork the repository and create a new branch from `main`.
2. Make your changes in the new branch.
3. Test your changes locally by running `streamlit run app.py`.
4. Submit a pull request with a clear description of what you changed and why.

## Development Setup

```bash
git clone https://github.com/YOUR_USERNAME/surveychat.git
cd surveychat
pip install -r requirements.txt
cp .env.example .env
# Add your OPENAI_API_KEY to .env
streamlit run app.py
```

## Code Style

- Keep `app.py` self-contained; avoid splitting into multiple modules unless strictly necessary.
- Use clear, descriptive variable names and add comments where the logic isn't self-evident.
- Follow existing formatting conventions in the codebase.

## Code of Conduct

Please be respectful and constructive in all interactions. We are committed to providing a welcoming and inclusive experience for everyone.
