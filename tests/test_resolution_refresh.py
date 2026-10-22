import unittest
from unittest.mock import Mock

import cameractrls as c


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
