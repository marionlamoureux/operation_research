# Project Summary: Maison Étoile Sustainability Demo

## 🎯 Demo Objective

**"This sustainability page is not written by marketing — it is generated from governed data."**

Show how luxury brand sustainability claims are:
- ✅ Generated from real operational data
- ✅ Fully traceable with lineage
- ✅ Tested and validated
- ✅ Automatically updated

## 📊 Data Architecture

```
┌─────────────────────────────────────────────────────┐
│              SOURCE SYSTEMS                          │
│  SAP (ERP) | Dynamics 365 (ESG) | SharePoint (Excel)│
└────────────────────┬────────────────────────────────┘
                     │ Fivetran
                     ↓
┌─────────────────────────────────────────────────────┐
│              BRONZE LAYER (Raw)                      │
│  • sap_procurement_orders (~1000 rows)              │
│  • esg_supplier_audits (~50 rows)                   │
│  • esg_emissions (15 rows)                          │
└────────────────────┬────────────────────────────────┘
                     │ dbt Core
                     ↓
┌─────────────────────────────────────────────────────┐
│         SILVER LAYER (Normalized)                    │
│  Views:                                              │
│  • stg_procurement_orders                           │
│  • stg_supplier_audits                              │
│  • stg_emissions                                     │
│                                                       │
│  Tables:                                             │
│  • fact_material_sourcing                           │
└────────────────────┬────────────────────────────────┘
                     │ dbt Core
                     ↓
┌─────────────────────────────────────────────────────┐
│          GOLD LAYER (Metrics)                        │
│  • claim_leather_audited_ratio                      │
│  • sustainability_narrative                         │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│         CONSUMPTION LAYER                            │
│  Website | LLM/RAG | GenAI | Partner APIs           │
└─────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
dbtfivetrandatabricks/
├── databricks.yml                      # Bundle configuration
├── README.md                           # Full documentation
├── DEMO_GUIDE.md                       # Detailed demo script
├── QUICK_START.md                      # 5-minute quick start
├── PROJECT_SUMMARY.md                  # This file
│
├── sql_setup/
│   └── 01_create_bronze_tables.sql     # Creates ~1000 rows of demo data
│
├── dbt_project/                        # dbt Core project
│   ├── dbt_project.yml                 # Project config
│   ├── profiles.yml                    # Databricks connection
│   └── models/
│       ├── sources.yml                 # Bronze source definitions
│       │
│       ├── staging/                    # Silver - Normalized views
│       │   ├── stg_procurement_orders.sql
│       │   ├── stg_supplier_audits.sql
│       │   └── stg_emissions.sql
│       │
│       ├── silver/                     # Silver - Fact tables
│       │   ├── fact_material_sourcing.sql
│       │   └── schema.yml              # Tests & documentation
│       │
│       └── gold/                       # Gold - Metrics & narratives
│           ├── claim_leather_audited_ratio.sql
│           ├── sustainability_narrative.sql
│           └── schema.yml              # Tests & documentation
│
├── notebooks/
│   └── dbt_run.py                      # Databricks notebook to run dbt
│
└── resources/
    └── dbt_job.yml                     # Job definition (deps → run → test)
```

## 🎬 Demo Flow (10 minutes)

### 1. Setup (One-time, 2 min)
```bash
# Create bronze tables with sample data
# Run sql_setup/01_create_bronze_tables.sql in Databricks
```

### 2. Deploy Bundle (2 min)
```bash
databricks bundle deploy -t dev
```

### 3. Run dbt Pipeline (3 min)
```bash
databricks bundle run dbt_daily_run -t dev
```
Or: Databricks UI → Workflows → Jobs → Run Now

### 4. Show Results (3 min)

**A. The Generated Claim:**
```sql
SELECT * FROM marion_test.dbt_analytics_gold.sustainability_narrative
ORDER BY year DESC;
```

**Output:**
| brand | year | leather_claim |
|-------|------|---------------|
| Maison Étoile | 2024 | In 2024, 60.0% of our leather sourcing volume came from audited suppliers. |

**B. Show Full Lineage:**
- Catalog Explorer → gold.sustainability_narrative
- Click "Lineage" tab
- Trace back through silver → staging → bronze

**C. Show Data Quality Tests:**
```bash
# Tests run automatically, but can show:
dbt test
```

## 🔑 Key Demo Messages

### 1. **Governed Data, Not Marketing**
Every sentence can be traced back to source systems:
- SAP procurement orders
- Dynamics 365 supplier audits
- SharePoint emissions data

### 2. **Automatic Updates**
When Fivetran ingests new data:
1. Bronze tables update
2. dbt job runs (scheduled)
3. Sustainability claims regenerate
4. Website updates automatically

No manual copywriting needed.

### 3. **Full Lineage**
Click through Unity Catalog to see:
- Which bronze tables feed each claim
- Impact analysis: what breaks if we change a source?
- Column-level lineage

### 4. **Tested & Validated**
Every transformation has dbt tests:
- Uniqueness constraints
- Not null checks
- Data type validations
- Custom business logic tests

### 5. **Multiple Consumers**
Same governed data powers:
- 🌐 Website content
- 🤖 LLM/RAG systems
- 🤝 Partner portals
- 📊 Regulatory reports
- 📱 Mobile apps

## 📈 Sample Output

### Gold Table: sustainability_narrative

| brand | year | leather_claim | audited_volume_kg | total_volume_kg |
|-------|------|---------------|-------------------|-----------------|
| Maison Étoile | 2024 | In 2024, 60.0% of our leather sourcing volume came from audited suppliers. | 12,450.50 | 20,751.23 |
| Maison Étoile | 2023 | In 2023, 55.2% of our leather sourcing volume came from audited suppliers. | 11,230.75 | 20,343.89 |

### Rendered Website

```
═══════════════════════════════════════════════════
             MAISON ÉTOILE
        Craftsmanship meets Responsibility
═══════════════════════════════════════════════════

Our Commitment to Responsible Craftsmanship

At Maison Étoile, sustainability is an extension of
our craftsmanship.

📍 Responsible sourcing
In 2024, 60.0% of our leather sourcing volume came
from audited suppliers, certified through
internationally recognized standards.

[View Data Lineage] [Download Verification Report]
═══════════════════════════════════════════════════
```

## 🧪 dbt Tests Included

**Silver Layer Tests:**
- ✅ Order IDs are unique
- ✅ No null values in key fields
- ✅ All suppliers have valid IDs

**Gold Layer Tests:**
- ✅ Years are unique
- ✅ Ratios are between 0 and 1
- ✅ No null values in claims

## 🚀 Next Steps / Extensions

1. **Add More Claims:**
   - Organic cotton percentage
   - Renewable energy usage
   - Water consumption reduction
   - Waste recycling rates

2. **LLM Integration:**
   - Query gold tables via RAG
   - Generate dynamic content based on year/material
   - Multi-language support

3. **API Layer:**
   - REST API for partner access
   - Real-time claim verification
   - Webhook notifications on updates

4. **Regulatory Reporting:**
   - CSRD compliance
   - ESG disclosure automation
   - Audit trail generation

5. **Data Quality Monitoring:**
   - dbt Cloud for CI/CD
   - Great Expectations for advanced tests
   - Monte Carlo for data observability

## 📞 Demo Questions & Answers

**Q: How do you ensure this is accurate?**
A: Every claim has dbt tests. We can show failed tests and how we fix them.

**Q: What happens when supplier data changes?**
A: The entire pipeline re-runs automatically. Claims update within minutes.

**Q: Can auditors verify these claims?**
A: Yes - full lineage from claim → SQL → bronze table → Fivetran → source system.

**Q: How do you handle multiple languages?**
A: The gold layer is structured data. Any consumer (website, LLM) can format it appropriately.

**Q: What about regulatory compliance?**
A: Same pipeline powers CSRD reports, ESG disclosures, and marketing. Single source of truth.

## 🎓 Technologies Used

- **Databricks**: Data lakehouse platform
- **Unity Catalog**: Data governance & lineage
- **dbt Core**: SQL transformations & testing
- **Databricks Asset Bundles**: CI/CD deployment
- **Fivetran**: (Simulated) Data ingestion
- **Delta Lake**: Bronze/Silver/Gold medallion architecture

## 📊 Data Volumes

- **Bronze**: ~1,065 rows across 3 tables
- **Silver**: ~1,000 fact rows + 3 staging views
- **Gold**: 2 metric tables (claim + narrative)
- **Processing Time**: <2 minutes end-to-end

## ✅ Ready to Deploy

```bash
# Validate
databricks bundle validate -t dev

# Deploy
databricks bundle deploy -t dev

# Run
databricks bundle run dbt_daily_run -t dev
```

---

**Built for demonstrating governed, traceable, automated sustainability reporting.**
