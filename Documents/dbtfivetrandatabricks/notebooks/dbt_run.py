# Databricks notebook source
# MAGIC %md
# MAGIC # dbt Runner Notebook
# MAGIC This notebook executes dbt commands in a Databricks environment

# COMMAND ----------

import subprocess
import sys
import os

# COMMAND ----------

# Get parameters
dbutils.widgets.text("dbt_command", "run", "dbt Command")
dbutils.widgets.text("warehouse_id", "", "SQL Warehouse ID")
dbt_command = dbutils.widgets.get("dbt_command")
warehouse_id = dbutils.widgets.get("warehouse_id")

# Set environment variables for dbt
os.environ["DBT_CATALOG"] = "marion_test"
os.environ["DBT_SCHEMA"] = "dbt_analytics"
os.environ["DATABRICKS_HOST"] = spark.conf.get("spark.databricks.workspaceUrl")
# Construct SQL Warehouse http_path from warehouse_id
if warehouse_id:
    os.environ["DATABRICKS_HTTP_PATH"] = f"/sql/1.0/warehouses/{warehouse_id}"
else:
    os.environ["DATABRICKS_HTTP_PATH"] = ""
os.environ["DATABRICKS_TOKEN"] = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install dbt-databricks

# COMMAND ----------

# MAGIC %pip install dbt-databricks

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Execute dbt Command

# COMMAND ----------

# Import after restart
import subprocess
import os

# Re-get parameters after Python restart
dbt_command = dbutils.widgets.get("dbt_command")
warehouse_id = dbutils.widgets.get("warehouse_id")

# Re-set environment variables after restart
os.environ["DBT_CATALOG"] = "marion_test"
os.environ["DBT_SCHEMA"] = "dbt_analytics"
os.environ["DATABRICKS_HOST"] = spark.conf.get("spark.databricks.workspaceUrl")
# Construct SQL Warehouse http_path from warehouse_id
if warehouse_id:
    os.environ["DATABRICKS_HTTP_PATH"] = f"/sql/1.0/warehouses/{warehouse_id}"
else:
    os.environ["DATABRICKS_HTTP_PATH"] = ""
os.environ["DATABRICKS_TOKEN"] = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()

# Get the dbt project directory from the bundle deployment
# The bundle syncs files to the workspace
bundle_root = "/Workspace" + dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get().rsplit('/', 1)[0]
dbt_project_dir = f"{bundle_root}/../dbt_project"

print(f"dbt project directory: {dbt_project_dir}")
print(f"Executing: dbt {dbt_command}")

# Execute dbt command
result = subprocess.run(
    f"cd {dbt_project_dir} && dbt {dbt_command} --profiles-dir .",
    shell=True,
    capture_output=True,
    text=True
)

print(result.stdout)
if result.returncode != 0:
    print(result.stderr)
    raise Exception(f"dbt {dbt_command} failed with return code {result.returncode}")

# COMMAND ----------

print(f"dbt {dbt_command} completed successfully!")
