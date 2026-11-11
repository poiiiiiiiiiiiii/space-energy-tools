# TandEx browser runtime

This directory contains a pinned subset of [Pyodide 0.27.7](https://github.com/pyodide/pyodide/releases/tag/0.27.7). The worker loads the runtime and the NumPy, SciPy, and pandas dependency trees from the same origin. The original upstream lock is retained and the package bytes match its SHA-256 entries. Optional Python plots are not used by the browser interface; the J–V charts use the separate local Plotly bundle.

The Pyodide license and bundled third-party notices are in [LICENSE](LICENSE). Python distributions retain their upstream metadata and license files in the wheel archives. The separate TandEx model license is [here](../LICENSE).
