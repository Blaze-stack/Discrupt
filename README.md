# Discrupt

Status: active rebuild.

Discrupt is being repositioned as a consent-first toolkit for turning community conversation exports into clean, reviewable datasets. The goal is to support AI experiments without normalizing secret scraping, non-consensual logging, or public dumping of private chat history.

## What It Does

- Import approved `.csv`, `.json`, or plain-text exports.
- Redact common personal data before output is created.
- Deduplicate messages and normalize timestamps.
- Produce transparent dataset manifests with source hashes.
- Export training-ready JSONL for local model experiments.

## Quick Start

```bash
python discrupt.py examples/messages.csv -o dataset.jsonl --manifest manifest.json
```

## Testing

```bash
python -m unittest discover -s tests
```

## Non-Goals

- No token collection.
- No selfbot behavior.
- No stealth logging.
- No publishing private messages without permission.

## Structure

```txt
discrupt.py
tests/
examples/
```

## Security And Privacy

Discrupt should default to local processing, explicit input files, and reviewable output. Sample data must be synthetic or clearly licensed for reuse.
