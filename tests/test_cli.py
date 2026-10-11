"""Unit tests for the spatch CLI."""

import unittest
import tempfile
from pathlib import Path
from semantic_patch.cli import main

FILE_A = '''def greet():
    return "hi"
'''

FILE_B = '''def greet():
    return "hello world"
'''


class TestCLI(unittest.TestCase):
    def test_cli_diff_and_apply_flow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            orig_p = Path(tmpdir) / "orig.py"
            mod_p = Path(tmpdir) / "mod.py"
            patch_p = Path(tmpdir) / "change.spatch"
            target_p = Path(tmpdir) / "target.py"

            orig_p.write_text(FILE_A, encoding="utf-8")
            mod_p.write_text(FILE_B, encoding="utf-8")
            target_p.write_text(FILE_A, encoding="utf-8")

            # 1. Diff
            ret = main(["diff", str(orig_p), str(mod_p), "-o", str(patch_p)])
            self.assertEqual(ret, 0)
            self.assertTrue(patch_p.exists())

            # 2. Inspect
            ret = main(["inspect", str(patch_p)])
            self.assertEqual(ret, 0)

            # 3. Verify
            ret = main(["verify", str(target_p), str(patch_p)])
            self.assertEqual(ret, 0)

            # 4. Apply
            ret = main(["apply", str(target_p), str(patch_p), "-i"])
            self.assertEqual(ret, 0)

            updated = target_p.read_text(encoding="utf-8")
            self.assertIn("hello world", updated)

            # 5. Symbols
            ret = main(["symbols", str(target_p)])
            self.assertEqual(ret, 0)


if __name__ == "__main__":
    unittest.main()
