# Databricks notebook source
# COMMAND ----------

# MAGIC %md
# MAGIC # Solver Worker
# MAGIC Claims PENDING tasks from the Lakebase queue, runs OR-Tools CP-SAT, writes results back.

# COMMAND ----------

import json
import logging
import os
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("solver_worker")

POLL_INTERVAL_SECONDS = 2
IDLE_BACKOFF_SECONDS = 5
MAX_IDLE_CYCLES = 60  # Exit after 5 minutes idle

# Set defaults for Lakebase connection (serverless has no spark_env_vars)
os.environ.setdefault("LAKEBASE_INSTANCE_NAME", "shift-scheduler-instance")
os.environ.setdefault("LAKEBASE_DATABASE_NAME", "shift_scheduler")

# COMMAND ----------

# Add app source to path
app_path = os.environ.get(
    "APP_SOURCE_PATH",
    "/Workspace/Users/marion.lamoureux@databricks.com/.bundle/shift-scheduler/dev/files/src/app",
)
if app_path not in sys.path:
    sys.path.insert(0, app_path)
    logger.info(f"Added to sys.path: {app_path}")

# COMMAND ----------

from db import init_database, session_scope
from models import EmployeeSchema, ShiftSchema, SolveTask
from queue_ops import claim_next_task, complete_task, fail_task
from solver import SolverInput, solve_schedule

# COMMAND ----------

def process_task(task) -> str:
    """Parse task input, run solver, return output JSON."""
    input_data = json.loads(task.input_json)

    employees = [EmployeeSchema(**e) for e in input_data["employees"]]
    shifts = [ShiftSchema(**s) for s in input_data["shifts"]]

    solver_input = SolverInput(
        employees=employees,
        shifts=shifts,
        max_time_seconds=input_data.get("max_time_seconds", 10),
        fairness_weight=input_data.get("fairness_weight", 10),
    )

    result = solve_schedule(solver_input)

    output = {
        "status": result.status,
        "assignments": result.assignments,
        "solver_time_seconds": result.solver_time_seconds,
        "objective_value": result.objective_value,
        "stats": result.stats,
        "run_name": input_data.get("run_name", ""),
        "week_start_date": input_data.get("week_start_date", ""),
    }
    return json.dumps(output)

# COMMAND ----------

logger.info("Solver worker starting")
init_database()
logger.info("Connected to Lakebase")

idle_cycles = 0

while True:
    try:
        with session_scope() as session:
            task = claim_next_task(session)
            if task is None:
                idle_cycles += 1
                if idle_cycles >= MAX_IDLE_CYCLES:
                    logger.info(f"No tasks for {MAX_IDLE_CYCLES * IDLE_BACKOFF_SECONDS}s, exiting")
                    break
                time.sleep(IDLE_BACKOFF_SECONDS)
                continue

            idle_cycles = 0
            task_id = task.id
            logger.info(f"Claimed task {task_id} (user={task.user_id})")

        # Solve outside the claim transaction to avoid long locks
        try:
            with session_scope() as session:
                task = session.query(SolveTask).filter(SolveTask.id == task_id).first()
                output_json = process_task(task)
                complete_task(session, task_id, output_json)
                logger.info(f"Completed task {task_id}")
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            with session_scope() as session:
                fail_task(session, task_id, str(e))

    except Exception as e:
        logger.error(f"Worker loop error: {e}")
        time.sleep(POLL_INTERVAL_SECONDS)

logger.info("Solver worker exiting")
