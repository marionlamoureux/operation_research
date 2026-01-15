# Quick Start - Sustainability Demo

## 1. Setup Bronze Data (5 minutes)

Copy the SQL from `sql_setup/01_create_bronze_tables.sql` and run in Databricks:

```bash
# Open Databricks SQL Editor or a notebook, paste the SQL, and run
```

This creates ~1000 rows across 3 bronze tables simulating Fivetran data.

## 2. Deploy dbt Bundle (2 minutes)

```bash
databricks bundle deploy -t dev
```

This deploys:
- dbt job configuration
- Notebook to run dbt
- All dbt models

## 3. Run dbt (3 minutes)

```bash
databricks bundle run dbt_daily_run -t dev
```

Or navigate to Databricks Workflows → Jobs → dbt_daily_run_dev → Run Now

This will:
1. Install dbt-databricks
2. Run `dbt deps` (install dependencies)
3. Run `dbt run` (create silver & gold tables)
4. Run `dbt test` (validate data quality)

## 4. View Results

```sql
-- See the final sustainability narrative
SELECT * FROM marion_test.dbt_analytics_gold.sustainability_narrative
ORDER BY year DESC;

-- See the underlying metric
SELECT * FROM marion_test.dbt_analytics_gold.claim_leather_audited_ratio
ORDER BY year DESC;

-- See the fact table
SELECT * FROM marion_test.dbt_analytics_silver.fact_material_sourcing
WHERE material_type = 'LEATHER'
LIMIT 100;
```

## 5. Show Lineage

1. Open Databricks Unity Catalog
2. Navigate to: `main` → `gold` → `sustainability_narrative`
3. Click the **Lineage** tab
4. Show how it traces back to bronze tables

## Demo Talking Points

✅ **Every claim is backed by tested SQL**
- Show `dbt test` results
- Show schema.yml with tests

✅ **Full data lineage from source to claim**
- Click through catalog lineage
- Show dbt DAG (in dbt docs if generated)

✅ **Automated updates**
- Change a value in bronze
- Re-run dbt
- Show narrative updates automatically

✅ **Multiple consumers**
- Same data powers website, LLM, partners
- Single source of truth

## File Structure

```
├── sql_setup/
│   └── 01_create_bronze_tables.sql    # Create bronze data
├── dbt_project/
│   ├── models/
│   │   ├── sources.yml                 # Bronze table definitions
│   │   ├── staging/                    # Silver staging views
│   │   │   ├── stg_procurement_orders.sql
│   │   │   ├── stg_supplier_audits.sql
│   │   │   └── stg_emissions.sql
│   │   ├── silver/                     # Silver fact tables
│   │   │   ├── fact_material_sourcing.sql
│   │   │   └── schema.yml              # Tests & docs
│   │   └── gold/                       # Gold narrative tables
│   │       ├── claim_leather_audited_ratio.sql
│   │       ├── sustainability_narrative.sql
│   │       └── schema.yml              # Tests & docs
│   ├── dbt_project.yml                 # dbt configuration
│   └── profiles.yml                    # Databricks connection
├── notebooks/
│   └── dbt_run.py                      # Notebook to execute dbt
├── resources/
│   └── dbt_job.yml                     # Job definition
└── databricks.yml                      # Bundle configuration
```

## Troubleshooting

**Job fails to find dbt project**
- Check that dbt_project folder is deployed
- Verify `databricks.yml` includes dbt_project in artifacts

**Tests fail**
- Check bronze data was created successfully
- Verify catalog/schema names match (marion_test.bronze, marion_test.silver, marion_test.gold)

**Notebook can't connect to Databricks**
- Ensure SQL Warehouse is running
- Check DATABRICKS_HTTP_PATH is set (or use cluster)

**Want to use a cluster instead of SQL Warehouse**
- Update `dbt_project/profiles.yml` to use cluster connection
- Remove `http_path` and add cluster-specific settings
