import unittest
from unittest.mock import patch

import cameractrls as c


class FacecamHdrTest(unittest.TestCase):
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



if __name__ == '__main__':
    unittest.main()
