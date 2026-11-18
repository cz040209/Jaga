"""Data access layer: plain reads and writes, one module per table.

Rules for everything in this package:
- No business rules (no password checks, no "is this allowed?"). Those live in services/.
- Never commit. The service decides where a transaction starts and ends, so
  several crud calls can succeed or fail together.
- flush() only when the caller needs a generated value such as an id.
"""
