import json
import tempfile
import unittest
from pathlib import Path

from discrupt import load_messages, redact_text, sanitize_file, sanitize_messages


class DiscruptTests(unittest.TestCase):
    def test_redact_text(self):
        redacted = redact_text("email me at test@example.com and call 555-123-4567")
        self.assertNotIn("test@example.com", redacted)
        self.assertNotIn("555-123-4567", redacted)

    def test_sanitize_messages_deduplicates(self):
        messages = load_messages(Path("examples/messages.csv"))
        sanitized = sanitize_messages(messages + messages)
        self.assertEqual(len(sanitized), 3)
        self.assertIn("[redacted-email]", json.dumps(sanitized))

    def test_sanitize_file_writes_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "out.jsonl"
            manifest = Path(directory) / "manifest.json"
            result = sanitize_file(Path("examples/messages.csv"), output, manifest)
            self.assertEqual(result.message_count, 3)
            self.assertTrue(output.exists())
            self.assertTrue(manifest.exists())


if __name__ == "__main__":
    unittest.main()
