"""Unit tests for deploy/secrets.py — local .env parsing + app env distribution."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from deploy.secrets import _parse_env


class TestParseEnv(unittest.TestCase):
    """_parse_env: .env text → dict."""

    def test_empty(self):
        self.assertEqual(_parse_env(""), {})

    def test_simple(self):
        env = _parse_env("a=1\nb=2")
        self.assertEqual(env, {"a": "1", "b": "2"})

    def test_quoted_values(self):
        env = _parse_env("a='val'\nb=\"val2\"")
        self.assertEqual(env, {"a": "val", "b": "val2"})

    def test_spaces(self):
        env = _parse_env("  a  =  'val'  ")
        self.assertEqual(env, {"a": "val"})

    def test_comment_lines_skipped(self):
        env = _parse_env("a=1\n# comment\nb=2")
        self.assertEqual(env, {"a": "1", "b": "2"})

    def test_whitespace_lines(self):
        env = _parse_env("a=1\n\nb=2\n   ")
        self.assertEqual(env, {"a": "1", "b": "2"})

    def test_standard_keys(self):
        env = _parse_env("RESTIC_PASSWORD='secret'\nS3_ACCESS_KEY='key'\n")
        self.assertEqual(env, {"RESTIC_PASSWORD": "secret", "S3_ACCESS_KEY": "key"})

    def test_bifrost_prefix(self):
        env = _parse_env("BIFROST_OPENAI_KEY='sk-xxx'\nBIFROST_ANTHROPIC_KEY='sk-yyy'\n")
        self.assertEqual(env, {
            "BIFROST_OPENAI_KEY": "sk-xxx",
            "BIFROST_ANTHROPIC_KEY": "sk-yyy",
        })


class TestTemplateStructure(unittest.TestCase):
    """Verify template has expected required keys."""

    def test_template_has_required_keys(self):
        from deploy.secrets import TEMPLATE
        self.assertIn("RESTIC_PASSWORD", TEMPLATE)
        self.assertIn("S3_ACCESS_KEY", TEMPLATE)
        self.assertIn("S3_SECRET_KEY", TEMPLATE)
        self.assertIn("S3_BUCKET", TEMPLATE)
        self.assertIn("S3_ENDPOINT", TEMPLATE)
        self.assertIn("YANDEX_DISK_TOKEN", TEMPLATE)
        self.assertIn("BIFROST_", TEMPLATE)

    def test_template_has_placeholder(self):
        from deploy.secrets import TEMPLATE
        self.assertIn("''", TEMPLATE)


if __name__ == "__main__":
    unittest.main()
