# Contributing to APVA

Thank you for your interest in contributing to the **AI Productivity & Value Architecture (APVA)**!

APVA is the enterprise standard for measuring the time-denominated ROI of Generative AI systems. We welcome contributions ranging from scoring algorithms and SDK wrappers to backend optimisations and documentation.

---

## 1. Development Setup

### Prerequisites

- **Python 3.10+** (Python 3.12 recommended)
- **uv** (recommended) or pip
- **just** task runner (optional but recommended)
- **Docker & Docker Compose** (for multi-service backend testing)

### Bootstrap

```bash
git clone https://github.com/Hardonian/apva-framework.git
cd apva-framework

# Install dependencies in virtual environment
uv sync --all-extras

# Copy environment variables
cp .env.example .env
```

---

## 2. Common Development Workflows

We use `just` recipes to standardize development commands:

```bash
just test              # Run the complete pytest test suite
just lint              # Run ruff linter
just format            # Auto-format Python code with ruff
just type-check        # Run mypy static type analysis
just demo              # Run representative TVY simulation in table format
just audit             # Run executive audit against the golden dataset
just eval-gate         # Test the CI/CD pull request gate threshold
```

---

## 3. Architecture & Coding Conventions

- **Pure Mathematical Core**: All ROI, TVY, sensitivity, and Monte Carlo logic resides in `apva/` and must remain pure-functional and stateless without network dependencies.
- **Canonical Scoring**: Do not write ad-hoc string comparisons. Always use the canonical scorers in `apva.scoring` (`exact_span_recall`, `token_precision`, `f1_score`, `rouge_l_score`, `bleu_score`).
- **Typing & Annotations**: All new functions and methods must have complete type annotations and pass `mypy --strict`.
- **Formatting**: Strictly adhere to Black-compatible formatting enforced by Ruff (100 character line length limit).

---

## 4. Pull Request Requirements

Before opening a Pull Request:

1. **Verify All Tests Pass**:

   ```bash
   uv run pytest tests/ -v
   ```

2. **Verify CI Quality Gate**:

   ```bash
   uv run apva run-eval --golden-set data/golden_dataset.json --threshold 0.85
   ```

3. **Add Tests**: All bug fixes and new features must be accompanied by comprehensive tests in `tests/`.

---

## 5. Licensing

By contributing to APVA, you agree that your contributions will be licensed under its **Apache 2.0 License**.
