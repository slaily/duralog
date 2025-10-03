# DuraLog

[![PyPI version](https://badge.fury.io/py/duralog.svg)](https://badge.fury.io/py/duralog)
[![Python Versions](https://img.shields.io/pypi/pyversions/duralog.svg)](https://pypi.org/project/duralog)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`duralog` is a high-performance Write-Ahead Log (WAL) for Python applications. It guarantees data durability without sacrificing speed.

`duralog` in three points:

*   **Guarantees data durability:** It ensures every write is safely stored on disk before your application proceeds, so you can reliably recover your state after a crash.
*   **Keeps your application fast:** Your application writes to an in-memory queue in microseconds and moves on. The slow work of disk I/O happens in the background, so your application remains highly responsive.
*   **Maximizes write throughput:** Allows your application to ingest over **141,000 events per second** under heavy, concurrent load.

### Table of Contents

-   [Installation](#installation)
-   [Quickstart](#quickstart)
-   [API Reference](#api-reference)
-   [Performance](#performance)
-   [License](#license)

### Installation

```bash
pip install duralog
```

### Quickstart

### API Reference

The public API of `duralog` is intentionally minimal, focusing on three core methods.

---

**`duralog.append(data: dict | str)`**

Asynchronously adds a record to a high-speed in-memory queue for later persistence.

```python
log.append({"event": "user_login", "user_id": 123, "status": "success"})
```

---

**`duralog.replay() -> Generator[dict | str, None, None]`**

Returns a memory-efficient generator that yields every valid record from the log file.

```python
# Replay the log to rebuild the application's state on startup
user_events = [record for record in log.replay() if record.get("event")]
```

---

**`duralog.close()`**

Durably writes all pending records to disk and gracefully closes the log file.

```python
# Call this on application shutdown to ensure no data is lost
log.close()
```

### Performance

All benchmarks were run on a modern Linux system with a consumer-grade NVMe SSD.

**Write performance**

The benchmark measures end-to-end throughput by having 8 concurrent threads write a total of 10 million records.

-   **Result:** Over **141,000 writes/second**.
-   **What this means for you:** You can confidently log every API request, database query, and user interaction in a high-traffic system without a sweat. Your application will never be blocked waiting for the log.

**Read (replay) performance**

The benchmark measures the aggregate throughput when 4 concurrent processes read the same log file. In total, 5 million records were processed.

-   **Result:** Over **1,298,000 reads/second**.
-   **What this means for you:** Minimizing downtime is critical. This speed means your application can restart, read a massive log file with millions of entries, and recover its state in a matter of seconds.

### License

duralog is available under the MIT License.
