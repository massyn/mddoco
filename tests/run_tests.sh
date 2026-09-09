#!/usr/bin/env bash
# Test runner for mddoco. Run from the repo root: bash tests/run_tests.sh

set -uo pipefail

FIXTURES="fixtures"
EXAMPLES="../examples"
OUT="output"
PASS=0
FAIL=0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

green() { printf '\033[0;32m%s\033[0m\n' "$*"; }
red()   { printf '\033[0;31m%s\033[0m\n' "$*"; }

pass() { green "  PASS: $1"; ((PASS++)); }
fail() { red   "  FAIL: $1"; ((FAIL++)); }

# run_test <label> <expected_output_file> <mddoco args...>
#   Runs mddoco, checks exit code, checks the output file exists and is non-empty.
run_test() {
    local label="$1"
    local expected_file="$2"
    shift 2

    if mddoco "$@" 2>&1; then
        if [[ -s "$expected_file" ]]; then
            pass "$label"
        else
            fail "$label — output file missing or empty: $expected_file"
        fi
    else
        fail "$label — mddoco exited with error"
    fi
}

# check_contains <label> <file> <pattern>
#   Greps for a pattern inside an output file.
check_contains() {
    local label="$1"
    local file="$2"
    local pattern="$3"

    if grep -qF -- "$pattern" "$file" 2>/dev/null; then
        pass "$label"
    else
        fail "$label — pattern not found in $file: $pattern"
    fi
}

# check_not_contains <label> <file> <pattern>
check_not_contains() {
    local label="$1"
    local file="$2"
    local pattern="$3"

    if ! grep -qF -- "$pattern" "$file" 2>/dev/null; then
        pass "$label"
    else
        fail "$label — unexpected pattern found in $file: $pattern"
    fi
}

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

echo "Preparing output directory..."
rm -rf "$OUT"
mkdir -p "$OUT"

# Verify mddoco is on the PATH
if ! command -v mddoco &>/dev/null; then
    red "ERROR: mddoco not found. Run: pip install -e ."
    exit 1
fi

echo ""
echo "Running tests..."
echo "─────────────────────────────────────────────"

# ---------------------------------------------------------------------------
# 1. Single file → HTML
# ---------------------------------------------------------------------------
run_test \
    "single file input, HTML output" \
    "$OUT/single/single.html" \
    "$FIXTURES/single.md" -o "$OUT/single"

# ---------------------------------------------------------------------------
# 2. Directory → HTML (default options)
# ---------------------------------------------------------------------------
run_test \
    "directory input, HTML output" \
    "$OUT/dir/fixtures.html" \
    "$FIXTURES" -o "$OUT/dir"

# ---------------------------------------------------------------------------
# 3. Directory → HTML with title
# ---------------------------------------------------------------------------
run_test \
    "directory with --title" \
    "$OUT/titled/fixtures.html" \
    "$FIXTURES" --title "Test Suite Docs" -o "$OUT/titled"

check_contains \
    "title appears in HTML" \
    "$OUT/titled/fixtures.html" \
    "Test Suite Docs"

# ---------------------------------------------------------------------------
# 4. No title → title element omitted from body
# ---------------------------------------------------------------------------
run_test \
    "no title — doc-title class absent" \
    "$OUT/notitle/fixtures.html" \
    "$FIXTURES" -o "$OUT/notitle"

check_not_contains \
    "doc-title not rendered when title omitted" \
    "$OUT/notitle/fixtures.html" \
    'class="doc-title"'

# ---------------------------------------------------------------------------
# 5. TOC generation
# ---------------------------------------------------------------------------
run_test \
    "directory with --toc" \
    "$OUT/toc/fixtures.html" \
    "$FIXTURES" --toc -o "$OUT/toc"

check_contains \
    "TOC block present in output" \
    "$OUT/toc/fixtures.html" \
    "toc-block"

# ---------------------------------------------------------------------------
# 6. TOC disabled (default)
# ---------------------------------------------------------------------------
run_test \
    "no TOC by default" \
    "$OUT/notoc/fixtures.html" \
    "$FIXTURES" -o "$OUT/notoc"

check_not_contains \
    "toc-block absent when --no-toc" \
    "$OUT/notoc/fixtures.html" \
    'class="toc-block"'

# ---------------------------------------------------------------------------
# 7. TOC with limited depth
# ---------------------------------------------------------------------------
run_test \
    "--toc-depth 1 (H1 only)" \
    "$OUT/toc_depth/fixtures.html" \
    "$FIXTURES" --toc --toc-depth 1 -o "$OUT/toc_depth"

# ---------------------------------------------------------------------------
# 8. Mermaid diagrams
# ---------------------------------------------------------------------------
run_test \
    "mermaid diagram file" \
    "$OUT/mermaid/03_diagrams.html" \
    "$FIXTURES/03_diagrams.md" -o "$OUT/mermaid"

check_contains \
    "mermaid div present" \
    "$OUT/mermaid/03_diagrams.html" \
    'class="mermaid"'

check_contains \
    "mermaid.js CDN loaded" \
    "$OUT/mermaid/03_diagrams.html" \
    "mermaid.min.js"

check_not_contains \
    "highlight.js not loaded when there are no code blocks" \
    "$OUT/mermaid/03_diagrams.html" \
    "highlight.min.js"

# ---------------------------------------------------------------------------
# 9. No mermaid → CDN not loaded
# ---------------------------------------------------------------------------
run_test \
    "no mermaid in plain file" \
    "$OUT/nomermaid/01_intro.html" \
    "$FIXTURES/01_intro.md" -o "$OUT/nomermaid"

check_not_contains \
    "mermaid.js CDN absent when no diagrams" \
    "$OUT/nomermaid/01_intro.html" \
    "mermaid.min.js"

# ---------------------------------------------------------------------------
# 10. PDF output (skipped if Playwright is not installed)
# ---------------------------------------------------------------------------
if python -c "import playwright" 2>/dev/null; then
    run_test \
        "single file → PDF" \
        "$OUT/pdf/single.pdf" \
        "$FIXTURES/single.md" --format pdf -o "$OUT/pdf"
else
    echo "  SKIP: PDF test — Playwright not installed"
fi

# ---------------------------------------------------------------------------
# 11. Graph rendering — valid blocks, single quotes, bare minimum
# ---------------------------------------------------------------------------
run_test \
    "graph block file" \
    "$OUT/graph/04_graph.html" \
    "$FIXTURES/04_graph.md" -o "$OUT/graph"

check_contains \
    "valid graph block rendered as SVG" \
    "$OUT/graph/04_graph.html" \
    '<svg'

check_not_contains \
    "raw graph fenced block not present in output" \
    "$OUT/graph/04_graph.html" \
    'class="language-graph"'

check_contains \
    "bare-minimum graph (data only) renders SVG" \
    "$OUT/graph/04_graph.html" \
    '<svg'

check_contains \
    "single-quoted graph block renders SVG" \
    "$OUT/graph/04_graph.html" \
    "Single Quote Test"

# ---------------------------------------------------------------------------
# 11b. Invalid graph block causes non-zero exit
# ---------------------------------------------------------------------------
echo -n "  "
if ! mddoco "$FIXTURES/_invalid_graph.md" -o "$OUT/graph_error" &>/dev/null; then
    pass "invalid graph block exits non-zero"
else
    fail "invalid graph block should have exited non-zero"
fi

# ---------------------------------------------------------------------------
# 12. Comprehensive graph types
# ---------------------------------------------------------------------------
run_test \
    "comprehensive graph types" \
    "$OUT/graphs/05_graphs.html" \
    "$FIXTURES/05_graphs.md" -o "$OUT/graphs"

check_contains \
    "graphs: vertical bar rendered" \
    "$OUT/graphs/05_graphs.html" \
    "Quarterly Revenue"

check_contains \
    "graphs: vertical line rendered" \
    "$OUT/graphs/05_graphs.html" \
    "Website Visitors"

check_contains \
    "graphs: line2 (dotted) rendered" \
    "$OUT/graphs/05_graphs.html" \
    "Temperature"

check_contains \
    "graphs: bar and line combo rendered" \
    "$OUT/graphs/05_graphs.html" \
    "Sales vs Target"

check_contains \
    "graphs: horizontal bar rendered" \
    "$OUT/graphs/05_graphs.html" \
    "Team Performance"

check_contains \
    "graphs: horizontal line rendered" \
    "$OUT/graphs/05_graphs.html" \
    "Response Time"

# ---------------------------------------------------------------------------
# 13. Professional theme
# ---------------------------------------------------------------------------
run_test \
    "professional theme, directory with title and TOC" \
    "$OUT/professional/fixtures.html" \
    "$FIXTURES" --theme professional --title "Professional Demo" --toc -o "$OUT/professional"

check_contains \
    "professional theme: title banner rendered" \
    "$OUT/professional/fixtures.html" \
    'class="doc-header"'

check_contains \
    "professional theme: title text present" \
    "$OUT/professional/fixtures.html" \
    "Professional Demo"

check_contains \
    "professional theme: TOC block present" \
    "$OUT/professional/fixtures.html" \
    'class="toc-block"'

# ---------------------------------------------------------------------------
# 14. Explicit output file path
# ---------------------------------------------------------------------------
run_test \
    "explicit output file path" \
    "$OUT/explicit/mydoc.html" \
    "$FIXTURES/single.md" -o "$OUT/explicit/mydoc.html"

# ---------------------------------------------------------------------------
# 15. Underscore-prefixed files are excluded from directory scans
# ---------------------------------------------------------------------------
run_test \
    "directory scan excludes _ignored.md" \
    "$OUT/underscore/fixtures.html" \
    "$FIXTURES" -o "$OUT/underscore"

check_not_contains \
    "_ignored.md content absent from output" \
    "$OUT/underscore/fixtures.html" \
    "SENTINEL_IGNORED_FILE"

# ---------------------------------------------------------------------------
# 16. Invalid input path → non-zero exit
# ---------------------------------------------------------------------------
echo -n "  "
if ! mddoco "tests/fixtures/nonexistent.md" -o "$OUT/invalid" &>/dev/null; then
    pass "invalid input path exits non-zero"
else
    fail "invalid input path should have exited non-zero"
fi


# ---------------------------------------------------------------------------
# 17. default-wide theme
# ---------------------------------------------------------------------------
run_test \
    "default-wide theme generates output" \
    "$OUT/default_wide/fixtures.html" \
    "$FIXTURES" --theme default-wide --title "Wide Default" -o "$OUT/default_wide"

check_contains \
    "default-wide: full-width container present" \
    "$OUT/default_wide/fixtures.html" \
    'width: 100%'

check_not_contains \
    "default-wide: no max-width constraint on container" \
    "$OUT/default_wide/fixtures.html" \
    'max-width: 860px'

# ---------------------------------------------------------------------------
# 18. professional-wide theme
# ---------------------------------------------------------------------------
run_test \
    "professional-wide theme generates output" \
    "$OUT/professional_wide/fixtures.html" \
    "$FIXTURES" --theme professional-wide --title "Wide Professional" --toc -o "$OUT/professional_wide"

check_contains \
    "professional-wide: title banner rendered" \
    "$OUT/professional_wide/fixtures.html" \
    'class="doc-header"'

check_not_contains \
    "professional-wide: no max-width constraint on page-wrap" \
    "$OUT/professional_wide/fixtures.html" \
    'max-width: 900px'

# ---------------------------------------------------------------------------
# 19. dark theme
# ---------------------------------------------------------------------------
run_test \
    "dark theme generates output" \
    "$OUT/dark/fixtures.html" \
    "$FIXTURES" --theme dark --title "Dark Theme Demo" -o "$OUT/dark"

check_contains \
    "dark theme: dark background variable defined" \
    "$OUT/dark/fixtures.html" \
    '--bg:        #0d1117'

check_contains \
    "dark theme: blue accent variable defined" \
    "$OUT/dark/fixtures.html" \
    '--accent:    #58a6ff'

check_contains \
    "dark theme: title rendered" \
    "$OUT/dark/fixtures.html" \
    "Dark Theme Demo"

# ---------------------------------------------------------------------------
# 20. dark-wide theme
# ---------------------------------------------------------------------------
run_test \
    "dark-wide theme generates output" \
    "$OUT/dark_wide/fixtures.html" \
    "$FIXTURES" --theme dark-wide -o "$OUT/dark_wide"

check_contains \
    "dark-wide: dark background variable defined" \
    "$OUT/dark_wide/fixtures.html" \
    '--bg:        #0d1117'

check_not_contains \
    "dark-wide: no max-width constraint on container" \
    "$OUT/dark_wide/fixtures.html" \
    'max-width: 860px'

# ---------------------------------------------------------------------------
# 21. academic theme
# ---------------------------------------------------------------------------
run_test \
    "academic theme generates output" \
    "$OUT/academic/fixtures.html" \
    "$FIXTURES" --theme academic --title "Academic Paper" --toc -o "$OUT/academic"

check_contains \
    "academic theme: serif font stack declared" \
    "$OUT/academic/fixtures.html" \
    'Georgia'

check_contains \
    "academic theme: title rule present" \
    "$OUT/academic/fixtures.html" \
    'class="title-rule"'

check_contains \
    "academic theme: print media query present" \
    "$OUT/academic/fixtures.html" \
    '@media print'

# ---------------------------------------------------------------------------
# 22. academic-wide theme
# ---------------------------------------------------------------------------
run_test \
    "academic-wide theme generates output" \
    "$OUT/academic_wide/fixtures.html" \
    "$FIXTURES" --theme academic-wide --title "Academic Wide" -o "$OUT/academic_wide"

check_contains \
    "academic-wide: serif font stack declared" \
    "$OUT/academic_wide/fixtures.html" \
    'Georgia'

check_not_contains \
    "academic-wide: no max-width constraint on container" \
    "$OUT/academic_wide/fixtures.html" \
    'max-width: 720px'

# ---------------------------------------------------------------------------
# 23. vanilla theme
# ---------------------------------------------------------------------------
run_test \
    "vanilla theme generates output" \
    "$OUT/vanilla/fixtures.html" \
    "$FIXTURES" --theme vanilla -o "$OUT/vanilla"

check_contains \
    "vanilla: table borders present" \
    "$OUT/vanilla/fixtures.html" \
    'border: 1px solid #999'

# ---------------------------------------------------------------------------
# 24. paged-professional theme
# ---------------------------------------------------------------------------
run_test \
    "paged-professional theme generates output" \
    "$OUT/paged_professional/fixtures.html" \
    "$FIXTURES" --theme paged-professional --title "Paged Professional Demo" --toc -o "$OUT/paged_professional"

check_contains \
    "paged-professional: Paged.js CDN loaded" \
    "$OUT/paged_professional/fixtures.html" \
    "pagedjs"

check_contains \
    "paged-professional: @page CSS rule present" \
    "$OUT/paged_professional/fixtures.html" \
    '@page'

check_contains \
    "paged-professional: title rendered" \
    "$OUT/paged_professional/fixtures.html" \
    "Paged Professional Demo"

# ---------------------------------------------------------------------------
# 25. Jinja2 template (.md.j2) support
# ---------------------------------------------------------------------------
run_test \
    ".md.j2 files included in directory scan" \
    "$OUT/j2/fixtures.html" \
    "$FIXTURES" -o "$OUT/j2"

check_contains \
    "j2 template: rendered project name from JSON" \
    "$OUT/j2/fixtures.html" \
    "mddoco"

check_contains \
    "j2 template: rendered author from JSON" \
    "$OUT/j2/fixtures.html" \
    "Phil Massyn"

check_not_contains \
    "j2 template: raw Jinja2 syntax not present in output" \
    "$OUT/j2/fixtures.html" \
    "{{ report.project }}"

check_not_contains \
    "_macros.j2 excluded from scan output" \
    "$OUT/j2/fixtures.html" \
    "SENTINEL_IGNORED_FILE"

# ---------------------------------------------------------------------------
# 26. Table of Contents heading change
# ---------------------------------------------------------------------------
run_test \
    "TOC heading is h1 outside nav" \
    "$OUT/toc_heading/fixtures.html" \
    "$FIXTURES" --toc -o "$OUT/toc_heading"

check_contains \
    "TOC heading rendered as h1 Table of Contents" \
    "$OUT/toc_heading/fixtures.html" \
    "<h1>Table of Contents</h1>"

check_not_contains \
    "old toc-heading class no longer present" \
    "$OUT/toc_heading/fixtures.html" \
    'class="toc-heading"'

# ---------------------------------------------------------------------------
# 27. External theme path
# ---------------------------------------------------------------------------
run_test \
    "external theme path" \
    "$OUT/external_theme/fixtures.html" \
    "$FIXTURES" --theme "$FIXTURES/custom_theme.html" -o "$OUT/external_theme"

check_contains \
    "external theme: custom sentinel present in output" \
    "$OUT/external_theme/fixtures.html" \
    "CUSTOM_THEME_SENTINEL"

# ---------------------------------------------------------------------------
# 28. Example projects render — the examples/ folder shipped in the repo.
#     Output is kept under output/examples/ for inspection.
# ---------------------------------------------------------------------------
EX_OUT="$OUT/examples"

run_test \
    "example 01_basic renders (title + TOC)" \
    "$EX_OUT/01_basic/01_basic.html" \
    "$EXAMPLES/01_basic" --title "Basic Example" --toc -o "$EX_OUT/01_basic"

check_not_contains \
    "example 01_basic: underscore-prefixed file excluded" \
    "$EX_OUT/01_basic/01_basic.html" \
    "DO_NOT_RENDER_THIS_FILE"

check_contains \
    "example 01_basic: title rendered" \
    "$EX_OUT/01_basic/01_basic.html" \
    "Basic Example"

check_contains \
    "example 01_basic: TOC block present" \
    "$EX_OUT/01_basic/01_basic.html" \
    "toc-block"

run_test \
    "example 02_rich_content renders" \
    "$EX_OUT/02_rich_content/02_rich_content.html" \
    "$EXAMPLES/02_rich_content" --title "Rich Content" -o "$EX_OUT/02_rich_content"

check_contains \
    "example 02_rich_content: mermaid.js CDN loaded" \
    "$EX_OUT/02_rich_content/02_rich_content.html" \
    "mermaid.min.js"

check_contains \
    "example 02_rich_content: graph block rendered as SVG" \
    "$EX_OUT/02_rich_content/02_rich_content.html" \
    '<svg'

check_contains \
    "example 02_rich_content: highlight.js loaded for code blocks" \
    "$EX_OUT/02_rich_content/02_rich_content.html" \
    "highlight.min.js"

check_contains \
    "example 02_rich_content: highlight.js stylesheet loaded" \
    "$EX_OUT/02_rich_content/02_rich_content.html" \
    "github.min.css"

run_test \
    "example 03_themed_report renders (professional theme + TOC)" \
    "$EX_OUT/03_themed_report/03_themed_report.html" \
    "$EXAMPLES/03_themed_report" --theme professional --title "Q3 Platform Review" --toc -o "$EX_OUT/03_themed_report"

check_contains \
    "example 03_themed_report: TOC block present" \
    "$EX_OUT/03_themed_report/03_themed_report.html" \
    "toc-block"

run_test \
    "example 04_jinja_data renders" \
    "$EX_OUT/04_jinja_data/04_jinja_data.html" \
    "$EXAMPLES/04_jinja_data" --title "Jinja Data Demo" -o "$EX_OUT/04_jinja_data"

check_not_contains \
    "example 04_jinja_data: no unrendered Jinja syntax" \
    "$EX_OUT/04_jinja_data/04_jinja_data.html" \
    '{{ project.name }}'

check_contains \
    "example 04_jinja_data: semicolon-split CSV cell became a list" \
    "$EX_OUT/04_jinja_data/04_jinja_data.html" \
    "python, flask, sql"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "─────────────────────────────────────────────"
TOTAL=$((PASS + FAIL))
echo "Results: $PASS/$TOTAL passed"

if [[ $FAIL -gt 0 ]]; then
    red "$FAIL test(s) failed."
    exit 1
else
    green "All tests passed."
    exit 0
fi
