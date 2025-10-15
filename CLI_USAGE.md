# BRF CLI - Red Flag Detection Usage Guide

## Quick Start

### 1. List Available BRFs
```bash
brf list
```
Shows all BRFs in the database with their names.

**Important:** You must use the exact BRF name from this list when running `brf analyze`.

### 2. Analyze a BRF (Quick Mode - Recommended)
```bash
brf analyze <brf_name> --quick
```
**Fast** red flag detection based on document queries (5-10 seconds).
- Checks for governance issues, legal problems, auditor remarks
- No health score computation
- Best for initial screening

### 3. Full Analysis (Slow)
```bash
brf analyze <brf_name>
```
**Comprehensive** analysis with financial metrics (1-2 minutes).
- Extracts 11 financial metrics via LLM queries
- Computes health scores (0-100) across 6 categories
- Detects metric-based red flags (debt, liquidity, maintenance, etc.)
- Shows star ratings and detailed scores

### 4. Red Flags Only
```bash
brf analyze <brf_name> --red-flags-only
```
Same as quick mode but hides health score table.

### 5. Full Details
```bash
brf analyze <brf_name> --full
```
Shows everything:
- Health scores
- All financial metrics in a table
- Strengths and concerns
- Recommendations
- Red flags with evidence

## Example Workflow

```bash
# 1. See what's available
brf list

# 2. Quick check for red flags (fast)
brf analyze brf_fribergsgatan_8_2024 --quick

# 3. If needed, get full financial analysis (slow but detailed)
brf analyze brf_fribergsgatan_8_2024 --full

# 4. Ask specific questions
brf query "Vad är soliditeten?" --brf brf_fribergsgatan_8_2024
```

## Red Flag Categories

The system detects 7 types of red flags:

1. **Financial Stability** - Negative results, low solvency
2. **Debt Risk** - High interest costs, excessive debt-to-equity
3. **Liquidity** - Negative cash flow, low liquid assets
4. **Maintenance** - Old buildings with insufficient reserves
5. **Governance** - Auditor remarks, board issues
6. **Legal** - Ongoing disputes, past special assessments
7. **Operational** - High monthly fees

## Severity Levels

- 🔴 **Critical** - Dealbreaker, avoid purchase
- 🟠 **High** - Serious concern requiring investigation
- 🟡 **Medium** - Area needing attention
- 🟢 **Low** - Minor concern

## Performance Notes

**Quick Mode (`--quick`):**
- ~5-10 seconds
- Only checks governance/legal issues via queries
- No metric extraction
- Good for initial screening

**Full Mode (default):**
- ~1-2 minutes
- Extracts 11 metrics with separate LLM queries
- Comprehensive financial analysis
- Use when seriously considering a property

## Tips

1. **Start with quick mode** for initial screening
2. **Use full mode** only for BRFs you're seriously interested in
3. **Compare multiple BRFs** using quick mode first
4. **Ask follow-up questions** with `brf query` for specific concerns
5. **Use `--full`** when preparing for viewing/offer

## Other Commands

```bash
brf info                              # Database statistics
brf query "question" --brf <name>     # Ask specific questions
brf chat --brf <name>                 # Interactive chat
brf ingest data/report.pdf            # Add new BRF reports
```
