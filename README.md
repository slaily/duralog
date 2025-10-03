# DuraLog

[![PyPI version](https://badge.fury.io/py/duralog.svg)](https://badge.fury.io/py/duralog)
[![Python Versions](https://img.shields.io/pypi/pyversions/duralog.svg)](https://pypi.org/project/duralog)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`duralog` is a high-performance Write-Ahead Log (WAL) for Python applications. It guarantees data durability without sacrificing speed.

`duralog` in three points:

*   **Guarantees data durability:** It ensures every write is safely stored on disk *before* your application proceeds, so you can reliably recover your state after a crash.
*   **Keeps your application fast:** Your application writes to an in-memory queue in microseconds and moves on. The slow work of disk I/O happens in the background, so your application remains highly responsive.
*   **Maximizes write throughput:** Allows your application to ingest over **141,000 events per second** under heavy, concurrent load.

### See it in Action (Quickstart)

Let's simulate a crash. We'll write two critical user events, "close" the log, and then prove that the data is still there when we "restart" the application.

```python
import os
from duralog import DuraLog

log_file = "my_app.log"
if os.path.exists(log_file):
    os.remove(log_file)

# --- Your Application ---
print("Phase 1: Writing initial data...")
log = DuraLog(file_path=log_file)
log.append({"event": "user_signup", "user_id": "user-123"})
log.append({"event": "user_purchase", "user_id": "user-123", "item": "item-abc"})
log.close() # Graceful shutdown
print("Data written. Application has 'crashed'.")

# --- Application Restarts ---
print("\nPhase 2: Recovering data after restart...")
recovered_log = DuraLog(file_path=log_file)

# The replay() method reads all records from the log.
recovered_data = list(recovered_log.replay())

assert len(recovered_data) == 2
assert recovered_data[0]["event"] == "user_signup"
assert recovered_data[1]["item"] == "item-abc"

print(f"Successfully recovered {len(recovered_data)} records.")
for record in recovered_data:
    print(f"  - {record}")

recovered_log.close()
```
