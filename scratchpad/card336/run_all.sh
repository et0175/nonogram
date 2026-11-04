#!/bin/zsh
# CARD-336: everything that needs pytest, in one lock window.
set -u
cd /Users/omelnikova/PycharmProjects/PythonProject4-card-336
PY=/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python
sweep() { find . -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null; }

echo "######## 1. the two Touches modules UNDER THE FIVE-KIND PROBE"
sweep
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="scratchpad/card338:scratchpad/card329" \
  $PY -m pytest -o addopts= -q -rEfs --tb=line -p probe_five_kinds \
  tests/test_book_puzzle_frame.py tests/property/test_book_pdf_geometry.py 2>&1 \
  | grep -E "^(FAILED|ERROR )|[0-9]+ (passed|failed|error|skipped)|Refusing"
sweep

echo
echo "######## 2. AC-2 and the pin, on the tree as committed"
sweep
PYTHONDONTWRITEBYTECODE=1 $PY -m pytest -o addopts= -q -rEfs --tb=line \
  "tests/test_book_pdf.py::TestEdgeOffset_ThePixelOraclesStillReadPixels" \
  "tests/test_book_pdf.py::TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium" \
  "tests/test_book_pdf.py::TestEdgeOffset_ATolerenceChangeCarriesItsExemption" 2>&1 \
  | grep -E "^(FAILED|ERROR )|[0-9]+ (passed|failed|error|skipped)|Refusing"
sweep

echo
echo "######## 3. the plants"
PYTHONDONTWRITEBYTECODE=1 $PY scratchpad/card336/plants.py 2>&1
echo "######## done"
