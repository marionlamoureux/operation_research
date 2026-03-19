"""Solver worker loop: claims PENDING tasks from Lakebase, runs OR-Tools, writes results.

Designed to run as a Databricks Job (single long-running task).
Multiple workers can run concurrently — SELECT FOR UPDATE SKIP LOCKED prevents conflicts.
"""

import json
import logging
import os
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 2
IDLE_BACKOFF_SECONDS = 5
MAX_IDLE_CYCLES = 60  # Exit after 5 minutes idle (60 × 5s) — job restarts on next trigger


def _setup_path():
    """Add the app directory to sys.path so shared modules are importable."""
    # When running as a Databricks Job with source=WORKSPACE, files are at:
    #   /Workspace/Users/.../files/src/worker/solver_worker.py
    #   /Workspace/Users/.../files/src/app/models.py
    # Try multiple strategies to find the app dir.
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app"),
        os.path.join(os.getcwd(), "src", "app"),
    ]
    # Also check PYTHONPATH or env-provided path
    env_app_path = os.environ.get("APP_SOURCE_PATH")
    if env_app_path:
        candidates.insert(0, env_app_path)

    for candidate in candidates:
        candidate = os.path.normpath(candidate)
        if os.path.isdir(candidate):
            if candidate not in sys.path:
                sys.path.insert(0, candidate)
            logger.info(f"Added to sys.path: {candidate}")
            return
        else:
            logger.debug(f"Candidate path not found: {candidate}")

    # Fallback: add parent of worker dir (works if both app/ and worker/ are siblings)
    parent = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    app_dir = os.path.join(parent, "app")
    sys.path.insert(0, app_dir)
    logger.warning(f"No app dir verified, adding best guess: {app_dir}")


def process_task(task) -> str:
    """Parse task input, run solver, return output JSON."""
    from models import EmployeeSchema, ShiftSchema
    from solver import SolverInput, solve_schedule

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


def worker_loop():
    """Main worker loop: poll for tasks, solve, repeat."""
    _setup_path()

    from db import init_database, session_scope
    from models import SolveTask
    from queue_ops import claim_next_task, complete_task, fail_task

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


if __name__ == "__main__":
    worker_loop()
