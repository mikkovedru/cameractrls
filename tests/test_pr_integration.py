"""Hardware-free regressions for the reviewed upstream integrations."""

import sys
import types
import unittest
from unittest.mock import Mock, patch

import cameractrls as c
import cameraview as view


class HelperProcessTest(unittest.TestCase):
    def test_real_child_is_stopped_after_timeout(self):
        with patch.object(c, 'ptz_helper_timeout', 0.1), self.assertLogs(level='WARNING'):
            self.assertEqual([], c.exec_and_get_lines(
                [sys.executable, '-c', 'import time; time.sleep(30)']))

    def test_real_successful_child_output_is_preserved(self):
        self.assertEqual([b'one', b'two'], c.exec_and_get_lines(
            [sys.executable, '-c', 'print("one"); print("two")']))


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


class CaptureBufferTest(unittest.TestCase):
    def allocate(self, granted):
        camera = object.__new__(view.V4L2Camera)
        camera.device, camera.fd = '/dev/test', -1
        camera.num_cap_bufs, camera.cap_bufs = 6, []
        queried = []

        def ioctl(fd, command, data):
            if command == view.VIDIOC_REQBUFS:
                data.count = granted
            elif command == view.VIDIOC_QUERYBUF:
                queried.append(data.index)
                data.length = 4096

        with patch.object(view, 'ioctl', side_effect=ioctl), patch.object(view.mmap, 'mmap'):
            camera.init_buffers()
        self.assertEqual(list(range(granted)), queried)
        self.assertEqual(granted, len(camera.cap_bufs))
        self.assertEqual(granted, camera.num_cap_bufs)

    def test_three_granted_buffers_are_usable(self):
        with self.assertLogs(level='WARNING'):
            self.allocate(3)

    def test_requested_count_is_usable(self):
        self.allocate(6)

    def test_more_than_requested_is_usable(self):
        with self.assertLogs(level='WARNING'):
            self.allocate(8)

    def test_zero_buffers_is_fatal(self):
        with self.assertLogs(level='ERROR'), self.assertRaises(SystemExit) as error:
            self.allocate(0)
        self.assertEqual(3, error.exception.code)


class VendorControlTest(unittest.TestCase):
    def facecam(self, usb_id='0fd9:0094', unit=9):
        with patch.object(c, 'find_unit_id_in_sysfs', return_value=unit), \
                patch.object(c, 'find_usb_ids_in_sysfs', return_value=usb_id):
            return c.FacecamCtrls('/dev/test', -1)

    def test_facecam_hdr_payloads_and_invalid_value(self):
        camera = self.facecam()
        for value, expected in [('high', b'\x01'), ('low', b'\x00')]:
            with patch.object(c, 'query_xu_control') as query:
                errors = []
                camera.setup_ctrls({'facecam_dynamic_range': value}, errors)
            self.assertEqual([], errors)
            args = query.call_args.args
            self.assertEqual((-1, 9, 0x15, c.UVC_SET_CUR), args[:4])
            self.assertEqual(expected, bytes(args[4])[:-1])
            self.assertEqual(value, camera.ctrls[0].value)
        with patch.object(c, 'query_xu_control') as query, self.assertLogs(level='WARNING'):
            errors = []
            camera.setup_ctrls({'facecam_dynamic_range': 'invalid'}, errors)
        self.assertTrue(errors)
        query.assert_not_called()

    def test_facecam_controls_are_gated_by_model_and_extension(self):
        for usb_id, unit in [('3564:fef8', 9), ('0fd9:0094', 0)]:
            camera = self.facecam(usb_id, unit)
            self.assertEqual([], camera.get_ctrls())
            with patch.object(c, 'query_xu_control') as query:
                camera.setup_ctrls({'facecam_dynamic_range': 'high'}, [])
            query.assert_not_called()

    def logitech(self, usb_id):
        def unit(device, guid):
            return 9 if guid == c.LOGITECH_BRIO_GUID else 0
        with patch.object(c, 'find_unit_id_in_sysfs', side_effect=unit), \
                patch.object(c, 'find_usb_ids_in_sysfs', return_value=usb_id), \
                patch.object(c, 'query_xu_control'):
            return c.LogitechCtrls('/dev/test', -1)

    def test_show_mode_only_exposed_on_mx_brio(self):
        self.assertIsNotNone(c.find_by_text_id(
            self.logitech('046d:0944').get_ctrls(), 'logitech_brio_show_mode'))
        for usb_id in ('046d:085e', '3564:fef8'):
            self.assertIsNone(c.find_by_text_id(
                self.logitech(usb_id).get_ctrls(), 'logitech_brio_show_mode'))

    def test_show_mode_off_precedes_fov_write(self):
        camera = self.logitech('046d:0944')
        writes = []
        def query(fd, unit, selector, command, data):
            if command == c.UVC_SET_CUR:
                writes.append((selector, bytes(data)[:-1]))
        errors = []
        with patch.object(c, 'query_xu_control', side_effect=query):
            camera.setup_ctrls({'logitech_brio_show_mode': 'off', 'logitech_brio_fov': '90'}, errors)
        self.assertEqual([], errors)
        self.assertEqual([(0x0d, b'\x00'), (c.LOGITECH_BRIO_FOV_SEL, b'\x00')], writes)


class ResolutionRefreshTest(unittest.TestCase):
    def camera(self):
        camera = object.__new__(c.V4L2FmtCtrls)
        camera.res_ctrl = c.BaseCtrl('resolution', 'Resolution', 'menu', menu=[
            c.BaseCtrlMenu('640x480', '640x480', None)])
        camera.ctrls = [camera.res_ctrl]
        fmt = c.v4l2_format()
        fmt.fmt.pix.pixelformat = c.V4L2_PIX_FMT_MJPEG
        camera.get_fmt = Mock(return_value=fmt)
        camera.get_resolutions = Mock(return_value=['3840x2160', '640x480'])
        camera.set_resolution = Mock()
        return camera

    def test_resolution_newly_available_in_current_format_is_set(self):
        camera = self.camera()
        errors = []
        camera.setup_ctrls({'resolution': '3840x2160'}, errors)
        self.assertEqual([], errors)
        camera.get_resolutions.assert_called_once_with(c.V4L2_PIX_FMT_MJPEG)
        camera.set_resolution.assert_called_once_with(camera.res_ctrl, '3840x2160', errors)

    def test_unavailable_resolution_is_rejected(self):
        camera = self.camera()
        errors = []
        with self.assertLogs(level='WARNING'):
            camera.setup_ctrls({'resolution': '9999x9999'}, errors)
        self.assertTrue(errors)
        camera.set_resolution.assert_not_called()

    def test_failed_format_read_does_not_apply_resolution(self):
        camera = self.camera()
        camera.get_fmt.return_value = None
        errors = []
        with self.assertLogs(level='WARNING'):
            camera.setup_ctrls({'resolution': '3840x2160'}, errors)
        self.assertTrue(errors)
        camera.set_resolution.assert_not_called()


if __name__ == '__main__':
    unittest.main()
