#!/usr/bin/env python3

import subprocess
import sys
import unittest
from unittest.mock import patch

import cameractrls


class ExecAndGetLinesTest(unittest.TestCase):
    @patch('cameractrls.subprocess.run')
    def test_returns_output_lines_with_a_bounded_probe(self, run):
        run.return_value.stdout = b'first\nsecond\n'

        self.assertEqual(
            [b'first', b'second'],
            cameractrls.exec_and_get_lines(['/helper', '-l']),
        )
        run.assert_called_once_with(
            ['/helper', '-l'],
            capture_output=True,
            timeout=cameractrls.ptz_helper_timeout,
        )

    @patch('cameractrls.subprocess.run')
    def test_skips_a_probe_that_times_out(self, run):
        run.side_effect = subprocess.TimeoutExpired(['/helper', '-l'], 5)

        with self.assertLogs(level='WARNING') as logs:
            self.assertEqual([], cameractrls.exec_and_get_lines(['/helper', '-l']))

        self.assertIn('/helper timed out, skipping', logs.output[0])


class HelperProcessTest(unittest.TestCase):
    def test_real_child_is_stopped_after_timeout(self):
        with patch.object(cameractrls, 'ptz_helper_timeout', 0.1), self.assertLogs(level='WARNING'):
            self.assertEqual([], cameractrls.exec_and_get_lines(
                [sys.executable, '-c', 'import time; time.sleep(30)']))

    def test_real_successful_child_output_is_preserved(self):
        self.assertEqual([b'one', b'two'], cameractrls.exec_and_get_lines(
            [sys.executable, '-c', 'print("one"); print("two")']))



if __name__ == '__main__':
    unittest.main()
