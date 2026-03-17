import pytest
import logging
import os
import shutil
from datetime import datetime

# --- TEST LOG CONFIGURATION ---
TEST_LOG_DIR = "logs"
TEST_ACTIVE_LOG = os.path.join(TEST_LOG_DIR, "test_RateEye.log")

# Global list to store results for the final summary
session_results = []

if not os.path.exists(TEST_LOG_DIR):
    os.makedirs(TEST_LOG_DIR)


def rotate_test_logs():
    today_str = datetime.now().strftime("%Y%m%d")
    archive_name = os.path.join(TEST_LOG_DIR, f"{today_str}_test_RateEye.log")
    if os.path.exists(TEST_ACTIVE_LOG):
        if not os.path.exists(archive_name):
            shutil.copy(TEST_ACTIVE_LOG, archive_name)
            with open(TEST_ACTIVE_LOG, "w") as f:
                f.write(f"--- Test Log Rotated/Started at {datetime.now()} ---\n")


@pytest.fixture(scope="session", autouse=True)
def setup_test_logging():
    rotate_test_logs()

    # Configure root logger for the test session
    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    file_handler = logging.FileHandler(TEST_ACTIVE_LOG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)

    logging.info("=" * 30 + " START TEST SESSION " + "=" * 30)
    yield
    logging.info("=" * 30 + " END TEST SESSION " + "=" * 30)


def pytest_runtest_logreport(report):
    """Hooks into pytest to log PASSED/FAILED for each test stage."""
    if report.when == "call":
        status = report.outcome.upper()
        test_name = report.nodeid
        # Log the result immediately to the file
        logging.info(f"TEST RESULT: {test_name} -> {status}")
        # Save for the final summary
        session_results.append((test_name, status))


def pytest_sessionfinish(session, exitstatus):
    """Writes the final summary table to the log file at the end."""
    with open(TEST_ACTIVE_LOG, "a") as f:
        f.write("\n" + "=" * 32 + " Test Results " + "=" * 32 + "\n")
        f.write(f"{'Test Name':<60} | {'Status':<10}\n")
        f.write("-" * 78 + "\n")
        for name, status in session_results:
            f.write(f"{name:<60} | {status:<10}\n")
        f.write("=" * 78 + "\n\n")
