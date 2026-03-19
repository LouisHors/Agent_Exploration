"""Slack notification helper for OA alerts."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


class SlackNotifier:
    """Send notifications to Slack via OpenClaw CLI."""

    def __init__(self):
        self.openclaw_bin = self._find_openclaw()

    def _find_openclaw(self) -> str | None:
        """Find OpenClaw binary."""
        # Try common locations
        paths = [
            'openclaw',
            '/usr/local/bin/openclaw',
            os.path.expanduser('~/.nvm/versions/node/*/bin/openclaw'),
        ]

        for path in paths:
            if '*' in path:
                import glob
                matches = glob.glob(path)
                if matches:
                    return matches[0]
            elif subprocess.run(['which', path], capture_output=True).returncode == 0:
                return path

        return None

    def send(self, target: str, message: str) -> bool:
        """Send message to Slack target.

        Args:
            target: Slack target like 'user:U4143EF46' or 'channel:C123456'
            message: Message text (can include newlines)
        """
        if not self.openclaw_bin:
            print("Warning: OpenClaw not found, skipping Slack notification")
            return False

        try:
            # Use openclaw message command
            cmd = [
                self.openclaw_bin,
                'message',
                'send',
                '--channel', 'slack',
                '--target', target,
                '--message', message,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                print(f"Slack notification failed: {result.stderr}")
                return False

            return True

        except Exception as e:
            print(f"Failed to send Slack notification: {e}")
            return False


class ConsoleNotifier:
    """Fallback notifier that prints to console."""

    def send(self, target: str, message: str) -> bool:
        """Print alert to console."""
        print("=" * 60)
        print("OA ALERT")
        print("=" * 60)
        print(message)
        print("=" * 60)
        return True
