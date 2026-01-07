import unittest
import datetime
import pytz
from sla_utils import calculate_sla_due_date, get_business_hours_settings, get_next_business_moment

# Mock get_system_settings to avoid database dependency
from unittest.mock import patch

def mock_get_system_settings_utc():
    return {
        'sla_calculation_mode': 'business_hours',
        'timezone': 'UTC',
        'working_hour_start': '09:00',
        'working_hour_end': '17:00',
        'working_days': 'Mon,Tue,Wed,Thu,Fri',
    }

class TestSlaUtils(unittest.TestCase):

    @patch('sla_utils.get_system_settings', new=mock_get_system_settings_utc)
    def test_friday_afternoon_ticket(self):
        """
        Test a ticket created on a Friday afternoon with an SLA that spans the weekend.
        """
        settings = get_business_hours_settings()
        
        # Friday @ 3:00 PM UTC
        start_dt = datetime.datetime(2024, 1, 5, 15, 0, 0, tzinfo=pytz.utc) 

        # --- Test case 1: 4-hour SLA ---
        # 2 hours on Friday (3pm-5pm) + 2 hours on Monday (9am-11am)
        sla_hours_1 = 4
        expected_due_date_1 = datetime.datetime(2024, 1, 8, 11, 0, 0, tzinfo=pytz.utc) # Next Monday
        due_date_1 = calculate_sla_due_date(start_dt, sla_hours_1, settings)
        self.assertEqual(due_date_1, expected_due_date_1)

        # --- Test case 2: 10-hour SLA ---
        # 2 hours on Friday (3pm-5pm) + 8 hours on Monday (9am-5pm)
        sla_hours_2 = 10
        expected_due_date_2 = datetime.datetime(2024, 1, 8, 17, 0, 0, tzinfo=pytz.utc)
        due_date_2 = calculate_sla_due_date(start_dt, sla_hours_2, settings)
        self.assertEqual(due_date_2, expected_due_date_2)
        
        # --- Test case 3: 12-hour SLA ---
        # 2 hours on Friday (3pm-5pm) + 8 hours on Monday (9am-5pm) + 2 hours on Tuesday (9am-11am)
        sla_hours_3 = 12
        expected_due_date_3 = datetime.datetime(2024, 1, 9, 11, 0, 0, tzinfo=pytz.utc)
        due_date_3 = calculate_sla_due_date(start_dt, sla_hours_3, settings)
        self.assertEqual(due_date_3, expected_due_date_3)

    @patch('sla_utils.get_system_settings', new=mock_get_system_settings_utc)
    def test_ticket_created_outside_business_hours(self):
        """ Test a ticket created on a weekend or before/after hours. """
        settings = get_business_hours_settings()

        # Saturday
        start_dt_saturday = datetime.datetime(2024, 1, 6, 12, 0, 0, tzinfo=pytz.utc)
        # With 1 hour SLA, should be due Monday at 10 AM
        expected_due_saturday = datetime.datetime(2024, 1, 8, 10, 0, 0, tzinfo=pytz.utc)
        due_date_saturday = calculate_sla_due_date(start_dt_saturday, 1, settings)
        self.assertEqual(due_date_saturday, expected_due_saturday)
        
        # Before hours on a weekday
        start_dt_before_hours = datetime.datetime(2024, 1, 8, 4, 0, 0, tzinfo=pytz.utc) # Monday 4 AM
        # With 2 hour SLA, should be due Monday at 11 AM
        expected_due_before = datetime.datetime(2024, 1, 8, 11, 0, 0, tzinfo=pytz.utc)
        due_date_before = calculate_sla_due_date(start_dt_before_hours, 2, settings)
        self.assertEqual(due_date_before, expected_due_before)

if __name__ == '__main__':
    unittest.main()
