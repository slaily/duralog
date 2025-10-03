# DuraLog

[![PyPI version](https://badge.fury.io/py/duralog.svg)](https://badge.fury.io/py/duralog)
[![Python Versions](https://img.shields.io/pypi/pyversions/duralog.svg)](https://pypi.org/project/duralog)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Never lose data again. `duralog` is a high-performance Python library that makes your application's data durable without slowing it down.**

Imagine your application processes critical events—orders, transactions, user actions. If your server crashes or loses power, how do you ensure none of that data is lost? Writing directly to a database on every event can be slow and quickly become a bottleneck.
