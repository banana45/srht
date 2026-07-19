# Contract Generator Design

## Goal

Build a Python web project that reads the Word contract template in `resource/`, lets the user add contract rows through a visual interface or import Excel/CSV data, fills the underlined blanks for party name and dates, and exports generated `.docx` files.

## User Workflow

The app opens as a single-page workbench. The user can add rows manually. Each row has fields for:

- Party A name
- Contract start date
- Contract end date
- Signing date

The signing date field is optional. Date inputs show a format hint and accept common date strings such as `2026-7-1`, `2026/7/1`, and `2026年7月1日`. Output dates are normalized to `xxxx年x月x日`.

The user can also upload `.xlsx` or `.csv` files with equivalent columns. Uploaded rows are added to the editable table. The interface does not need a separate preview step; validation appears inline beside rows and fields.

When the user clicks generate, the app creates one contract per valid row. Multiple generated contracts are returned as a `.zip`; a single generated contract may be returned directly as `.docx`.

## Template Filling

The source template is `resource/奇点电商平台产品服务合同模板.docx`.

The app fills:

- Header party name: `甲方：_________________________`
- Contract term: `合同履行期限自 ____ 至 ____`
- Signature party names: main signature section and attachment signature section
- Signing date blanks when the row includes signing date

If signing date is blank, the original signing date underline text remains unchanged.

The Word generation layer edits docx XML while preserving paragraph, run, font, and underline styling. Replacement text is placed into existing underlined or blank runs where possible instead of rebuilding paragraphs.

## Interface

The UI is a restrained single-page operations surface:

- Left/top controls: import Excel/CSV, add row, clear rows
- Main grid: editable row fields and row status
- Action area: generate contracts and show generation errors/download link

No landing page or marketing content is needed.

## Project Structure

- `app.py`: Flask routes, file upload handling, generation endpoint
- `contract_generator.py`: parsing dates, parsing row payloads, filling docx template, zip export helpers
- `templates/index.html`: workbench page
- `static/styles.css`: visual styling
- `static/app.js`: row editing, import request, generation request
- `tests/`: automated tests for date parsing, row validation, and docx generation behavior
- `requirements.txt`: runtime and test dependencies
- `start.bat`: Windows one-click launcher that creates a virtual environment, installs dependencies, and starts the web server
- `output/`: generated contracts, ignored by the app if absent

## Validation

Required fields are Party A name, start date, and end date. Signing date is optional.

Invalid rows are not generated. The UI reports field-level errors. The server also validates all submitted rows so bad client-side state cannot generate malformed contracts.

## Testing

Automated tests cover:

- Date normalization to `xxxx年x月x日`
- Empty signing date remains empty at the data layer
- Manual row validation
- CSV/XLSX import parsing
- Generated docx contains Party A and contract start/end dates
- Generated docx does not fill signing date when the input signing date is blank
