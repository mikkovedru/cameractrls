import unittest
from unittest.mock import patch

import cameractrls as c


class MxBrioShowModeTest(unittest.TestCase):
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



if __name__ == '__main__':
    unittest.main()
