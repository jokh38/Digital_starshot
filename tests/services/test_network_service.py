"""
Tests for NetworkService.

This module provides testing for network connectivity operations used
by the Starshot analyzer application.
"""

import unittest
from unittest.mock import patch, MagicMock, call
import subprocess
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from services.network_service import NetworkService


class TestNetworkServicePing(unittest.TestCase):
    """Test ping functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = NetworkService()

    @patch('subprocess.run')
    def test_ping_returns_true_on_success(self, mock_run):
        """Should return True when ping succeeds."""
        mock_run.return_value = MagicMock(returncode=0)

        result = self.service.ping('192.168.1.1')

        self.assertTrue(result)

    @patch('subprocess.run')
    def test_ping_returns_false_on_failure(self, mock_run):
        """Should return False when ping fails."""
        mock_run.return_value = MagicMock(returncode=1)

        result = self.service.ping('192.168.1.1')

        self.assertFalse(result)

    @patch('subprocess.run')
    def test_ping_uses_windows_flag_on_windows(self, mock_run):
        """Should use -n flag on Windows."""
        mock_run.return_value = MagicMock(returncode=0)

        with patch('sys.platform', 'win32'):
            self.service.ping('192.168.1.1')

        # Check that the command uses -n for Windows
        call_args = mock_run.call_args
        cmd = call_args[0][0] if call_args[0] else call_args[1].get('args', [])
        self.assertIn('-n', cmd)

    @patch('subprocess.run')
    def test_ping_uses_linux_flag_on_linux(self, mock_run):
        """Should use -c flag on Linux."""
        mock_run.return_value = MagicMock(returncode=0)

        with patch('sys.platform', 'linux'):
            self.service.ping('192.168.1.1')

        # Check that the command uses -c for Linux
        call_args = mock_run.call_args
        cmd = call_args[0][0] if call_args[0] else call_args[1].get('args', [])
        self.assertIn('-c', cmd)

    @patch('subprocess.run')
    def test_ping_includes_ip_address(self, mock_run):
        """Should include IP address in ping command."""
        mock_run.return_value = MagicMock(returncode=0)

        self.service.ping('192.168.1.100')

        # Check that IP is in the command
        call_args = mock_run.call_args
        cmd = call_args[0][0] if call_args[0] else call_args[1].get('args', [])
        self.assertIn('192.168.1.100', cmd)

    @patch('subprocess.run')
    def test_ping_handles_exception(self, mock_run):
        """Should return False when exception occurs."""
        mock_run.side_effect = Exception("Network error")

        result = self.service.ping('192.168.1.1')

        self.assertFalse(result)

    @patch('subprocess.run')
    def test_ping_uses_count_of_one(self, mock_run):
        """Should send only one ping request."""
        mock_run.return_value = MagicMock(returncode=0)

        self.service.ping('192.168.1.1')

        # Check that count parameter is 1
        call_args = mock_run.call_args
        cmd = call_args[0][0] if call_args[0] else call_args[1].get('args', [])
        self.assertIn('1', cmd)


class TestNetworkServiceIsIpReachable(unittest.TestCase):
    """Test IP reachability checking."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = NetworkService()

    @patch('subprocess.run')
    def test_is_reachable_returns_true_on_success(self, mock_run):
        """Should return True when IP is reachable."""
        mock_run.return_value = MagicMock(returncode=0)

        result = self.service.is_ip_reachable('192.168.1.1')

        self.assertTrue(result)

    @patch('subprocess.run')
    def test_is_reachable_returns_false_on_failure(self, mock_run):
        """Should return False when IP is unreachable."""
        mock_run.return_value = MagicMock(returncode=1)

        result = self.service.is_ip_reachable('192.168.1.1')

        self.assertFalse(result)

    @patch('subprocess.run')
    def test_is_reachable_handles_timeout(self, mock_run):
        """Should handle timeout gracefully."""
        mock_run.side_effect = subprocess.TimeoutExpired('ping', 5)

        result = self.service.is_ip_reachable('192.168.1.1', timeout=1)

        self.assertFalse(result)


class TestNetworkServiceSocketConnection(unittest.TestCase):
    """Test socket-based connection testing."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = NetworkService()

    @patch('socket.socket')
    def test_check_connection_returns_true_on_success(self, mock_socket_class):
        """Should return True when connection succeeds."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        result = self.service.check_connection('192.168.1.1', 8000)

        self.assertTrue(result)
        mock_socket.connect.assert_called_once()
        mock_socket.close.assert_called_once()

    @patch('socket.socket')
    def test_check_connection_returns_false_on_failure(self, mock_socket_class):
        """Should return False when connection fails."""
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = Exception("Connection refused")
        mock_socket_class.return_value = mock_socket

        result = self.service.check_connection('192.168.1.1', 8000)

        self.assertFalse(result)

    @patch('socket.socket')
    def test_check_connection_closes_socket_on_success(self, mock_socket_class):
        """Should close socket after successful connection."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        self.service.check_connection('192.168.1.1', 8000)

        mock_socket.close.assert_called_once()

    @patch('socket.socket')
    def test_check_connection_closes_socket_on_failure(self, mock_socket_class):
        """Should close socket even if connection fails."""
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = Exception("Connection refused")
        mock_socket_class.return_value = mock_socket

        self.service.check_connection('192.168.1.1', 8000)

        mock_socket.close.assert_called_once()

    @patch('socket.socket')
    def test_check_connection_with_default_port(self, mock_socket_class):
        """Should use default port if not specified."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        self.service.check_connection('192.168.1.1')

        # Check that port 8000 is used by default
        call_args = mock_socket.connect.call_args
        if call_args:
            self.assertEqual(call_args[0][0][1], 8000)


if __name__ == '__main__':
    unittest.main()
