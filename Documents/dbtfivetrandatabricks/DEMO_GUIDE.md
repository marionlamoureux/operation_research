# Sustainability Data Demo - Maison Étoile

## Demo Narrative

**"This sustainability page is not written by marketing — it is generated from governed data."**

## Architecture

```
Sources (ERP, ESG, CMS)
        ↓
     Fivetran
        ↓
 Databricks Bronze
        ↓
      dbt Core
        ↓
 Databricks Silver/Gold
        ↓
Sustainability Knowledge Layer
        ↓
Website | LLM | GenAI Assistant | Partners
```

## Demo Flow

### 1. Setup Bronze Layer (Simulate Fivetran Ingestion)

Run the setup script to create bronze tables with 1000+ rows:

```sql
-- In Databricks SQL or notebook
%sql
-- Execute the contents of sql_setup/01_create_bronze_tables.sql
```

This creates three bronze tables:
- `bronze.sap_procurement_orders` (~1000 rows) - ERP data
- `bronze.esg_supplier_audits` (~50 rows) - ESG audit data
- `bronze.esg_emissions` (15 rows) - Emissions tracking

### 2. Run dbt Transformation

Deploy and run the dbt job:

```bash
databricks bundle deploy -t dev
databricks bundle run dbt_daily_run -t dev
```

Or run locally:
```bash
cd dbt_project
dbt run
dbt test
```

### 3. Data Lineage

**Bronze → Silver → Gold**

```
bronze.sap_procurement_orders
bronze.esg_supplier_audits        → stg_* (views)
bronze.esg_emissions                     ↓
                                 fact_material_sourcing
                                          ↓
                              claim_leather_audited_ratio
                                          ↓
                              sustainability_narrative
```

### 4. Show the Generated Content

```sql
SELECT * FROM gold.sustainability_narrative
ORDER BY year DESC;
```

**Example Output:**
| brand | year | leather_claim |
|-------|------|---------------|
| Maison Étoile | 2024 | In 2024, 60.0% of our leather sourcing volume came from audited suppliers. |
| Maison Étoile | 2023 | In 2023, 55.2% of our leather sourcing volume came from audited suppliers. |

### 5. Show Data Lineage in Databricks

Navigate to:
- Catalog Explorer → gold schema → sustainability_narrative
- Click "Lineage" tab
- Show the full dependency graph back to bronze tables

### 6. Show dbt Tests

```bash
dbt test
```

Demonstrates:
- Data quality checks on all transformations
- Uniqueness constraints
- Not null validations
- Every claim is backed by tested SQL

## Key Demo Points

### 1. **Governed Data, Not Marketing Copy**
- Every sentence can be traced back to source data
- Changes to supplier audits automatically update the website
- No manual editing required

### 2. **Full Lineage**
- From SAP/Dynamics → Fivetran → Bronze → Silver → Gold
- Click through in Databricks Catalog Explorer
- Show impact analysis: what breaks if we change a source?

### 3. **Testable & Verifiable**
- dbt tests ensure data quality
- Schema documentation
- Column-level lineage

### 4. **Multiple Downstream Consumers**
- Website content generation
- LLM/RAG systems can query with confidence
- Partner portals
- API endpoints

### 5. **Real-Time Updates**
- When new supplier audit arrives via Fivetran
- dbt job runs (scheduled or triggered)
- Sustainability claims automatically update
- No marketing team intervention needed

## Sample Sustainability Page

```
═══════════════════════════════════════════════════
             MAISON ÉTOILE
        Craftsmanship meets Responsibility
═══════════════════════════════════════════════════

Our Commitment to Responsible Craftsmanship

At Maison Étoile, sustainability is an extension of
our craftsmanship.

Responsible sourcing
In 2024, 60.0% of our leather sourcing volume came
from audited suppliers, certified through
internationally recognized standards.

Climate responsibility
We continuously work to reduce our operational
footprint, with year-over-year reductions in our
Scope 1 and Scope 2 emissions.

These commitments are reviewed annually and grounded
in verifiable operational data.

[View Data Lineage] [Download Report]
═══════════════════════════════════════════════════
```

## Technical Details

### dbt Models

**Staging (Silver - Views)**
- `stg_procurement_orders` - Normalized procurement data
- `stg_supplier_audits` - Certified suppliers only
- `stg_emissions` - Emissions by scope

**Silver (Tables)**
- `fact_material_sourcing` - Core fact table with audit status

**Gold (Tables)**
- `claim_leather_audited_ratio` - Calculated metric
- `sustainability_narrative` - Human-readable claims

### Bronze Data Sources

1. **SAP Procurement** (ERP)
   - Materials: Leather, Cotton, Silk, Wool, etc.
   - 25 suppliers, multiple years
   - Random realistic volumes

2. **Dynamics 365 Audits** (ESG Platform)
   - Certifications: LWG Gold/Silver, GOTS, OEKO-TEX, FSC
   - Audit status: Passed/Failed/Not Audited
   - Coverage: 2023-2024

3. **SharePoint Excel** (Manual ESG Tracking)
   - Scope 1, 2, 3 emissions
   - Year-over-year trends
   - 2020-2024 data

## Questions to Address in Demo

**Q: How do you ensure data accuracy?**
A: Every transformation has dbt tests. We can show test results.

**Q: What if supplier audit data changes?**
A: The entire pipeline re-runs. Claims update automatically.

**Q: Can you prove this claim?**
A: Click through lineage from sustainability_narrative → bronze tables → source systems.

**Q: How do you handle multiple languages/formats?**
A: The gold layer is a clean data product. Any downstream system can consume it - LLMs, websites, APIs, etc.

**Q: What about regulatory reporting?**
A: Same data powers CSRD reporting, ESG disclosures, and marketing content. Single source of truth.

## Next Steps

- Add more claims (organic cotton, renewable energy, etc.)
- Integrate with LLM for dynamic content generation
- Add emissions claims from `stg_emissions`
- Create API layer for partner access
- Build Streamlit/Gradio app for interactive exploration
