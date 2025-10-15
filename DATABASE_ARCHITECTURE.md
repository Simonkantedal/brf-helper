# BRF Helper - Database Architecture

## Overview

BRF Helper now uses a SQLite database to store BRF metadata and analysis results. This eliminates the need to re-run expensive LLM queries every time you want to view analysis results.

## Why Database Storage?

**Problem:** Running analysis on-demand required 11 LLM queries per BRF, taking 1-2 minutes each time.

**Solution:** Run analysis once during ingestion, store results in SQLite database, read instantly on-demand.

### Benefits:
- ✅ **Instant results** - No waiting for LLM queries
- ✅ **Batch processing** - Analyze multiple BRFs during ingestion
- ✅ **Persistent storage** - Results survive restarts
- ✅ **Easy migration** - SQLite → Postgres when ready for production
- ✅ **Cost effective** - Run analysis once, query many times

## Database Schema

### Core Tables

#### `brfs` - Main BRF metadata
```sql
- id (PRIMARY KEY)
- brf_name (UNIQUE, indexed)
- display_name
- organization_number
- pdf_path, num_pages, num_chunks
- building_year, num_apartments, total_area, address
- ingested_at, analyzed_at, updated_at
- is_analyzed (BOOLEAN, indexed)
- analysis_version
```

#### `brf_metrics` - Financial metrics
```sql
- id (PRIMARY KEY)
- brf_id (FOREIGN KEY → brfs.id)
- annual_result, operating_result, interest_costs
- cash_flow, liquid_assets, total_debt, equity
- solvency_ratio, monthly_fee_per_sqm
- maintenance_reserves
- extracted_at
```

#### `brf_health_scores` - Health scores (0-100)
```sql
- id (PRIMARY KEY)
- brf_id (FOREIGN KEY → brfs.id)
- overall_score
- financial_stability_score
- cost_efficiency_score
- liquidity_score
- debt_management_score
- maintenance_readiness_score
- overall_explanation
- calculated_at
```

#### `brf_red_flags` - Detected red flags
```sql
- id (PRIMARY KEY)
- brf_id (FOREIGN KEY → brfs.id)
- title, category, severity
- description, impact, recommendation
- evidence, metric_value
- detected_at
```

#### `brf_analysis_summary` - Quick lookup stats
```sql
- id (PRIMARY KEY)
- brf_id (UNIQUE FOREIGN KEY → brfs.id)
- overall_risk_level (MINIMAL, LÅG, MÅTTLIG, HÖG, KRITISK)
- total_red_flags, critical_red_flags, high_red_flags, etc.
- summary
- created_at, updated_at
```

### Supporting Tables

- `brf_strengths` - Identified strengths
- `brf_concerns` - Identified concerns  
- `brf_recommendations` - Recommendations

## Workflow

### 1. Ingestion with Analysis (Recommended)

```bash
# Ingest PDF and run analysis in one step
brf ingest data/report.pdf

# Ingest directory of PDFs and analyze all
brf ingest data/ --reset

# Skip analysis during ingestion (faster)
brf ingest data/ --no-analyze
```

**What happens:**
1. PDF is processed and added to ChromaDB vector store
2. BRF metadata saved to SQLite database
3. Financial analysis runs (11 LLM queries, ~1-2 min)
4. All results saved to database
5. BRF marked as `is_analyzed = TRUE`

### 2. Viewing Analysis (Instant)

```bash
# View analysis (reads from database, instant)
brf analyze brf_fribergsgatan_8_2024

# View with full details
brf analyze brf_fribergsgatan_8_2024 --full

# Force re-analysis (slow, 1-2 min)
brf analyze brf_fribergsgatan_8_2024 --reanalyze
```

**What happens:**
1. Check if BRF exists in database
2. Check if BRF has been analyzed
3. Read pre-computed results from database
4. Display instantly (no LLM queries)

### 3. Re-analysis

```bash
# Force fresh analysis
brf analyze brf_fribergsgatan_8_2024 --reanalyze
```

Use when:
- You've updated the analysis logic
- You want to refresh old results
- The first analysis failed

## Database Location

**Default:** `./data/brf_analysis.db`

**Custom location:**
```bash
brf ingest data/ --db /path/to/custom.db
brf analyze brf_name --db /path/to/custom.db
```

## Migration Path to Postgres

The architecture is designed for easy migration:

1. **Current (Development):** SQLite for simplicity
2. **Future (Production):** Postgres for scalability

### Migration steps:
1. Export schema from `brf_helper/database/schema.sql`
2. Convert SQLite-specific syntax to Postgres
3. Update `BRFDatabase` class to use Postgres connection
4. Use connection pooling for concurrent access
5. Add proper indexing for production queries

### Code changes needed:
- Replace `sqlite3` with `psycopg2` or `asyncpg`
- Update connection string management
- Handle transaction isolation properly
- Add connection pooling

## API Integration

The database layer is separate from the CLI, making it easy to add a REST API:

```python
from brf_helper.database.db import BRFDatabase

db = BRFDatabase()

# Get BRF with all analysis
analysis = db.get_full_analysis("brf_fribergsgatan_8_2024")

# Get just metrics
metrics = db.get_metrics(brf_id=1)

# Get just red flags
red_flags = db.get_red_flags(brf_id=1)
```

## Performance Considerations

### Indexes
- `brf_name` - For quick BRF lookup
- `is_analyzed` - For filtering analyzed BRFs
- `severity` on red_flags - For filtering by severity
- Foreign keys - For join performance

### Query Optimization
- Use `get_full_analysis()` for complete data (one query with joins)
- Use specific getters for partial data
- Batch operations during ingestion

### Scalability
- SQLite: Good for < 10,000 BRFs
- Postgres: Required for > 10,000 BRFs or concurrent writes
- Consider caching layer for frequently accessed BRFs

## Backup & Recovery

### Backup
```bash
# Simple file copy for SQLite
cp ./data/brf_analysis.db ./backups/brf_analysis_$(date +%Y%m%d).db
```

### Recovery
```bash
# Restore from backup
cp ./backups/brf_analysis_20241215.db ./data/brf_analysis.db
```

### Re-building from scratch
```bash
# Delete database
rm ./data/brf_analysis.db

# Re-ingest and analyze all PDFs
brf ingest data/ --reset --analyze
```

## Monitoring

### Check database status
```bash
# Count analyzed BRFs
sqlite3 ./data/brf_analysis.db "SELECT COUNT(*) FROM brfs WHERE is_analyzed = 1"

# Show all BRFs
sqlite3 ./data/brf_analysis.db "SELECT brf_name, is_analyzed FROM brfs"

# Count red flags by severity
sqlite3 ./data/brf_analysis.db "SELECT severity, COUNT(*) FROM brf_red_flags GROUP BY severity"
```

## Future Enhancements

1. **Caching layer** - Redis for frequently accessed data
2. **Analytics** - Aggregate statistics across all BRFs
3. **Comparison queries** - Find BRFs with similar characteristics
4. **Time series** - Track changes in BRF health over time
5. **Export** - Generate PDF reports from database
6. **API** - REST endpoints for web/mobile apps
