import sys
import types
import unittest
from unittest.mock import Mock, patch

import cameractrls as c


class PortalTokenTest(unittest.TestCase):
    def test_autostart_request_uses_valid_object_path_element(self):
        proxy = Mock()
        gio = types.SimpleNamespace(
            DBusProxy=types.SimpleNamespace(new_for_bus_sync=Mock(return_value=proxy)),
            BusType=types.SimpleNamespace(SESSION=0),
            DBusProxyFlags=types.SimpleNamespace(NONE=0))
        repository = types.ModuleType('gi.repository')
        repository.Gio = gio
        repository.GLib = types.SimpleNamespace(Variant=lambda signature, value: value)
        portal = object.__new__(c.DesktopPortal)
        errors = []
        with patch.dict(sys.modules, {'gi.repository': repository}):
            portal.request_autostart(True, errors)
        self.assertEqual([], errors)
        options = proxy.RequestBackground.call_args.args[2]
        self.assertRegex(options['handle_token'], r'^[A-Za-z0-9_]+$')
        self.assertTrue(options['autostart'])
        self.assertEqual(['cameractrlsd.py'], options['commandline'])



if __name__ == '__main__':
    unittest.main()
