"""Tests for matuwrap.commands.sunshine module."""

import subprocess
import unittest
from unittest import mock

from matuwrap.commands import sunshine

SERVICE = "app-dev.lizardbyte.app.Sunshine"


def _completed(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


class TestServiceName(unittest.TestCase):
    """Sunshine ships as a user unit without a `sunshine.service` alias unless enabled."""

    def test_service_name_is_packaged_unit(self):
        """SERVICE_NAME should be the unit name shipped by the Sunshine package."""
        self.assertEqual(sunshine.SERVICE_NAME, SERVICE)


@mock.patch("matuwrap.commands.sunshine.notify")
@mock.patch("matuwrap.core.systemd.subprocess.run")
class TestServiceCommands(unittest.TestCase):
    """Service actions should target the packaged unit via systemctl --user."""

    def _assert_called_with(self, run: mock.Mock, action: str) -> None:
        run.assert_any_call(
            ["systemctl", "--user", action, SERVICE],
            capture_output=True,
            text=True,
        )

    def test_start_uses_service_name(self, run, _notify):
        """start should check status and start the packaged unit."""
        run.return_value = _completed("inactive")
        self.assertEqual(sunshine.start(), 0)
        self._assert_called_with(run, "is-active")
        self._assert_called_with(run, "start")

    def test_stop_uses_service_name(self, run, _notify):
        """stop should stop the packaged unit when it is active."""
        run.return_value = _completed("active")
        self.assertEqual(sunshine.stop(), 0)
        self._assert_called_with(run, "stop")

    def test_restart_uses_service_name(self, run, _notify):
        """restart should restart the packaged unit."""
        run.return_value = _completed()
        self.assertEqual(sunshine.restart(), 0)
        self._assert_called_with(run, "restart")

    def test_status_reports_active_unit(self, run, _notify):
        """status should query the packaged unit."""
        run.return_value = _completed("active")
        with mock.patch("matuwrap.commands.sunshine.console"), \
                mock.patch("matuwrap.commands.sunshine.print_header"), \
                mock.patch("matuwrap.commands.sunshine.print_kv"):
            self.assertEqual(sunshine.status(), 0)
        self._assert_called_with(run, "is-active")
        self._assert_called_with(run, "is-enabled")


if __name__ == "__main__":
    unittest.main()
