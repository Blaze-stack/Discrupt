"""Consent-first message export sanitizer."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b")
PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")
TOKEN_RE = re.compile(r"(mfa\.[A-Za-z0-9_-]{20,}|[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{20,})")
INVITE_RE = re.compile(r"(?:https?://)?discord(?:\.gg|\.com/invite)/[A-Za-z0-9-]+", re.IGNORECASE)


@dataclass(frozen=True)
class Message:
    author: str
    content: str
    timestamp: str | None = None


@dataclass(frozen=True)
class Manifest:
    created_at: str
    input_file: str
    output_file: str
    input_sha256: str
    message_count: int
    redaction_rules: list[str]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def redact_text(text: str) -> str:
    text = EMAIL_RE.sub("[redacted-email]", text)
    text = PHONE_RE.sub("[redacted-phone]", text)
    text = TOKEN_RE.sub("[redacted-token]", text)
    text = INVITE_RE.sub("[redacted-invite]", text)
    return " ".join(text.split())


def load_messages(path: Path) -> list[Message]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("messages", [])
        return [
            Message(
                author=str(item.get("author", "unknown")),
                content=str(item.get("content", "")),
                timestamp=item.get("timestamp"),
            )
            for item in data
            if isinstance(item, dict)
        ]

    if suffix == ".csv":
        with path.open(newline="", encoding="utf-8") as handle:
            rows = csv.DictReader(handle)
            return [
                Message(
                    author=row.get("author") or row.get("username") or "unknown",
                    content=row.get("content") or row.get("message") or "",
                    timestamp=row.get("timestamp") or row.get("created_at"),
                )
                for row in rows
            ]

    messages = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            messages.append(Message(author="unknown", content=line))
    return messages


def sanitize_messages(messages: list[Message]) -> list[dict]:
    sanitized = []
    seen = set()
    for message in messages:
        content = redact_text(message.content)
        if not content:
            continue
        key = (message.author, content, message.timestamp)
        if key in seen:
            continue
        seen.add(key)
        sanitized.append(
            {
                "author": redact_text(message.author) or "unknown",
                "content": content,
                "timestamp": message.timestamp,
            }
        )
    return sanitized


def write_jsonl(messages: list[dict], path: Path) -> None:
    path.write_text(
        "".join(json.dumps(message, sort_keys=True) + "\n" for message in messages),
        encoding="utf-8",
    )


def sanitize_file(input_file: Path, output_file: Path, manifest_file: Path) -> Manifest:
    messages = sanitize_messages(load_messages(input_file))
    write_jsonl(messages, output_file)
    manifest = Manifest(
        created_at=datetime.now(timezone.utc).isoformat(),
        input_file=str(input_file),
        output_file=str(output_file),
        input_sha256=sha256_file(input_file),
        message_count=len(messages),
        redaction_rules=["email", "phone", "discord-like-token", "discord-invite"],
    )
    manifest_file.write_text(json.dumps(asdict(manifest), indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sanitize approved chat exports into JSONL datasets.")
    parser.add_argument("input_file", type=Path)
    parser.add_argument("-o", "--output", type=Path, default=Path("dataset.jsonl"))
    parser.add_argument("--manifest", type=Path, default=Path("manifest.json"))
    args = parser.parse_args(argv)

    manifest = sanitize_file(args.input_file, args.output, args.manifest)
    print(f"Wrote {manifest.message_count} sanitized messages to {args.output}")
    print(f"Manifest: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
