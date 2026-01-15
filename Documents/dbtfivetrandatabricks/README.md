# dbt Fivetran Databricks - Asset Bundle

This repository contains a Databricks Asset Bundle for deploying dbt Core models as Databricks jobs.

## Project Structure

```
.
├── databricks.yml                 # Main bundle configuration
├── resources/
│   └── dbt_job.yml               # Job definitions
├── notebooks/
│   └── dbt_run.py                # Notebook to execute dbt commands
├── dbt_project/
│   ├── dbt_project.yml           # dbt project configuration
│   ├── profiles.yml              # dbt profiles
│   └── models/
│       ├── staging/              # Staging models
│       └── marts/                # Mart models
└── README.md
```

## Prerequisites

1. Databricks CLI installed (v0.230.0 or higher)
2. Databricks workspace access
3. Unity Catalog enabled (recommended)

## Setup

### 1. Configure Databricks Authentication

Set up authentication using one of these methods:

**Option A: Using .databrickscfg**
```bash
databricks configure --host <your-workspace-url>
```

**Option B: Using environment variables**
```bash
export DATABRICKS_HOST=<your-workspace-url>
export DATABRICKS_TOKEN=<your-token>
```

### 2. Configure dbt Project

Update the following files in `dbt_project/`:
- Add your dbt models in `models/staging/` and `models/marts/`
- Update `dbt_project.yml` with your project settings
- Configure `profiles.yml` if needed (defaults use environment variables)

### 3. Update Job Configuration

Edit `resources/dbt_job.yml` to customize:
- Schedule (default: 2 AM UTC daily, paused)
- Cluster configuration
- Email notifications
- dbt commands to run

## Deployment

### Deploy to Development

```bash
databricks bundle deploy -t dev
```

### Deploy to Production

```bash
databricks bundle deploy -t prod
```

## Running the Job

### Trigger the job manually

```bash
databricks bundle run dbt_daily_run -t dev
```

### View job status

```bash
databricks jobs list
```

## Environment Variables

The bundle uses these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABRICKS_HOST` | Databricks workspace URL | Required |
| `DATABRICKS_TOKEN` | Authentication token | Required |
| `DBT_CATALOG` | Unity Catalog name | `main` |
| `DBT_SCHEMA` | Schema for dbt models | `dbt_analytics` |
| `DATABRICKS_HTTP_PATH` | SQL Warehouse HTTP path | Required for dbt |

## Configuration Variables

Bundle variables can be set in `databricks.yml` or via CLI:

```bash
databricks bundle deploy -t prod --var="catalog=production" --var="schema=analytics"
```

## dbt Commands

The job runs three tasks in sequence:
1. `dbt deps` - Install dependencies
2. `dbt run` - Run models
3. `dbt test` - Run tests

To customize commands, edit the `base_parameters` in `resources/dbt_job.yml`.

## Troubleshooting

### Check bundle validation

```bash
databricks bundle validate -t dev
```

### View deployed resources

```bash
databricks bundle summary -t dev
```

### Check job logs

Navigate to your Databricks workspace → Workflows → Jobs → dbt_daily_run_dev

## Next Steps

1. Add your dbt models to `dbt_project/models/`
2. Configure Fivetran sources in your dbt project
3. Test locally: `cd dbt_project && dbt run`
4. Deploy to development: `databricks bundle deploy -t dev`
5. Test the job: `databricks bundle run dbt_daily_run -t dev`
6. Enable the schedule in production once tested

## Resources

- [Databricks Asset Bundles Documentation](https://docs.databricks.com/dev-tools/bundles/index.html)
- [dbt-databricks Documentation](https://docs.getdbt.com/reference/warehouse-setups/databricks-setup)
- [Databricks CLI Reference](https://docs.databricks.com/dev-tools/cli/index.html)
