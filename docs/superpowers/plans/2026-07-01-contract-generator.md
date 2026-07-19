# Contract Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python web workbench that generates filled Word contracts from manually added rows or uploaded Excel/CSV files.

**Architecture:** Keep document logic in `contract_generator.py` and web/UI logic in `app.py`, `templates/`, and `static/`. The generator edits the docx XML directly so existing underline styling stays intact.

**Tech Stack:** Python, Flask, openpyxl, pytest, vanilla HTML/CSS/JavaScript, Windows `start.bat`.

---

### Task 1: Core Parsing And Validation

**Files:**
- Create: `contract_generator.py`
- Create: `tests/test_contract_generator.py`
- Create: `requirements.txt`

- [ ] Write failing tests for date normalization and row validation.
- [ ] Run `python -m pytest tests/test_contract_generator.py -v` and confirm failures.
- [ ] Implement `format_chinese_date`, `normalize_row`, and `parse_csv_rows`.
- [ ] Run tests and confirm they pass.

### Task 2: Word Template Filling

**Files:**
- Modify: `contract_generator.py`
- Modify: `tests/test_contract_generator.py`

- [ ] Write failing tests that generate from `resource/奇点电商平台产品服务合同模板.docx`.
- [ ] Confirm the tests fail because generation is not implemented.
- [ ] Implement direct docx XML replacement while preserving run styles.
- [ ] Confirm generated documents contain expected filled text and keep signing date blanks when omitted.

### Task 3: Flask App And Frontend

**Files:**
- Create: `app.py`
- Create: `templates/index.html`
- Create: `static/styles.css`
- Create: `static/app.js`

- [ ] Write route tests for CSV import and generation validation.
- [ ] Implement Flask endpoints and the single-page workbench.
- [ ] Verify import and generation manually through the local server.

### Task 4: One-Click Startup

**Files:**
- Create: `start.bat`

- [ ] Add a Windows launcher that creates `.venv`, installs dependencies, and starts Flask.
- [ ] Verify syntax and startup command.

### Task 5: Final Verification

**Files:**
- All project files

- [ ] Run all tests with `python -m pytest -v`.
- [ ] Generate a sample contract with signing date present.
- [ ] Generate a sample contract with signing date blank.
- [ ] Confirm output files are created.
