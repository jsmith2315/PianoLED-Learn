import unittest
import subprocess
import sys
from pathlib import Path

from piano_led.main import main


class EntrypointTest(unittest.TestCase):
    def test_main_starts_cleanly(self) -> None:
        self.assertEqual(main(), 0)

    def test_module_entrypoint_forwards_subcommands(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "-m", "piano_led", "midi-list-ports"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertNotIn("Piano LED runtime ready", result.stdout)
        self.assertIn("MIDI inputs:", result.stdout)
