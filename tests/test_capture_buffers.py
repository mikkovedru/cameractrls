import unittest
from unittest.mock import patch

import cameraview as view


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



if __name__ == '__main__':
    unittest.main()
