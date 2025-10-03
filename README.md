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
-   [Performance](#performance)
-   [License](#license)

### Installation

```bash
pip install duralog
```

### Quickstart


### Performance

`duralog` is built for speed. All benchmarks were run on a modern Linux system with a consumer-grade NVMe SSD.

**Write performance**

The benchmark measures end-to-end throughput by having 8 concurrent threads write a total of 10 million records.

-   **Result:** Over **141,000 writes/second**.
-   **What this means for you:** You can confidently log every API request, database query, and user interaction in a high-traffic system without a sweat. Your application will never be blocked waiting for the log.

**Read (replay) performance**

The benchmark measures the aggregate throughput of 4 separate processes all reading a 2-million-record log file at the same time.

-   **Result:** Over **1,300,000 reads/second**.
-   **What this means for you:** Minimizing downtime is critical. This speed means your application can restart, read a massive log file with millions of entries, and recover its state in a matter of seconds.
