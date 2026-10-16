import importlib.machinery
import importlib.util
import os
from pathlib import Path
import pty
import select
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch


sys.dont_write_bytecode = True
HELPER = Path(__file__).resolve().parents[2] / "integration/helpers/nautilus-actions.py"
loader = importlib.machinery.SourceFileLoader("nautilus_actions", str(HELPER))
nautilus = importlib.util.module_from_spec(importlib.util.spec_from_loader("nautilus_actions", loader))
loader.exec_module(nautilus)


class NautilusActionsTest(unittest.TestCase):
    def test_nautilus_terminal_opens_console_tab_in_selected_directory(self):
        with tempfile.TemporaryDirectory(prefix="miubomz-console-") as directory:
            process = MagicMock()
            process.wait.return_value = 0
            with patch.object(nautilus.subprocess, "Popen", return_value=process) as launch:
                nautilus.perform("terminal", [Path(directory).as_uri()])
            self.assertEqual(launch.call_args.args[0],
                             ["/usr/bin/kgx", "--tab", "--working-directory=" + directory])
            self.assertEqual(launch.call_args.kwargs["cwd"], directory)

    def test_nautilus_command_runner_uses_blackbox_with_interactive_bash(self):
        with tempfile.TemporaryDirectory(prefix="miubomz-blackbox-") as directory:
            home = Path(directory)
            folder = home / "folder 'quotes' $(literal)"
            folder.mkdir()
            (home / ".bashrc").write_text(
                "HISTFILE=\"$HOME/.bash_history\"\n"
                "shopt -s histappend\n"
                "alias report=runner_probe\n"
                "runner_probe() { printf '%s\\n' \"$PWD\" \"$@\" > result; return 23; }\n"
            )
            command = "report 'spaces; $(literal)' \"double 'quotes'\" $'line\\nbreak'"
            process = MagicMock()
            process.wait.return_value = 0
            with patch.object(nautilus, "ask_command", return_value=command), \
                    patch.object(nautilus.subprocess, "Popen", return_value=process) as launch:
                nautilus.perform("execute", [folder.as_uri()])
            arguments = launch.call_args.args[0]
            self.assertEqual(arguments[0], "/usr/bin/blackbox-terminal")
            self.assertIn("--working-directory=" + str(folder), arguments)
            self.assertEqual(launch.call_args.kwargs["cwd"], str(folder))
            shell_command = next(value.removeprefix("--command=") for value in arguments
                                 if value.startswith("--command="))
            master, slave = pty.openpty()
            output = b""
            try:
                with subprocess.Popen(["/bin/bash", "-c", shell_command], cwd=folder,
                                      env={**os.environ, "HOME": str(home), "TERM": "xterm-256color"},
                                      stdin=slave, stdout=slave, stderr=slave) as runner:
                    try:
                        deadline = time.monotonic() + 10
                        while b"Press any key" not in output and time.monotonic() < deadline:
                            if select.select([master], [], [], 0.1)[0]:
                                output += os.read(master, 65536)
                        self.assertIn(b"Exit status: 23.", output)
                        self.assertIn(b"Press any key", output)
                        self.assertIsNone(runner.poll())
                        self.assertEqual((folder / "result").read_text(),
                                         str(folder) + "\nspaces; $(literal)\ndouble 'quotes'\nline\nbreak\n")
                        self.assertIn(command, (home / ".bash_history").read_text())
                        os.write(master, b"x")
                        self.assertEqual(runner.wait(timeout=5), 23)
                    finally:
                        if runner.poll() is None:
                            runner.kill()
                            runner.wait()
            finally:
                os.close(master)
                os.close(slave)

    def test_nautilus_cancelled_command_does_not_open_terminal(self):
        with tempfile.TemporaryDirectory(prefix="miubomz-blackbox-") as directory:
            with patch.object(nautilus, "ask_command", return_value=None), \
                    patch.object(nautilus.subprocess, "Popen") as launch:
                nautilus.perform("execute", [Path(directory).as_uri()])
            launch.assert_not_called()
