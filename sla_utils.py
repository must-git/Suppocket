"""
This module contains utility functions for Service Level Agreement (SLA) calculations,
including business hours logic.
"""
import datetime
import pytz

def get_business_hours_settings():
    """
    Retrieves business hours and other SLA settings from the database.
    Returns a dictionary with parsed settings.
    """
    from db.system_settings import get_system_settings
    system_settings = get_system_settings()

    # --- Parse SLA Calculation Mode ---
    sla_mode = system_settings.get('sla_calculation_mode', 'calendar_hours')

    # --- Parse Timezone ---
    try:
        tz_str = system_settings.get('timezone', 'UTC')
        sla_tz = pytz.timezone(tz_str)
    except pytz.UnknownTimeZoneError:
        sla_tz = pytz.timezone('UTC')

    # --- Parse Working Hours ---
    try:
        start_time_str = system_settings.get('working_hour_start', '09:00')
        working_hour_start = datetime.time.fromisoformat(start_time_str)
    except (ValueError, TypeError):
        working_hour_start = datetime.time(9, 0)

    try:
        end_time_str = system_settings.get('working_hour_end', '17:00')
        working_hour_end = datetime.time.fromisoformat(end_time_str)
    except (ValueError, TypeError):
        working_hour_end = datetime.time(17, 0)

    # --- Parse Working Days ---
    working_days_str = system_settings.get('working_days', 'Mon,Tue,Wed,Thu,Fri')
    day_mapping = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6}
    working_weekdays = [day_mapping[day] for day in working_days_str.split(',') if day in day_mapping]

    return {
        "mode": sla_mode,
        "timezone": sla_tz,
        "start_time": working_hour_start,
        "end_time": working_hour_end,
        "working_days": working_weekdays # List of integers 0-6
    }

def get_next_business_moment(dt_input, settings):
    """
    If the given datetime is outside of business hours, returns the start of the next business period.
    If it's already inside business hours, returns the original datetime.
    All datetimes are in UTC but calculations respect the configured timezone.
    """
    tz = settings['timezone']
    start_time = settings['start_time']
    end_time = settings['end_time']
    working_days = settings['working_days']

    # Convert the UTC input time to the business timezone
    dt_local = dt_input.astimezone(tz)

    # If we are on a non-working day, or after hours on a working day,
    # jump to the start of the next working day.
    is_non_working_day = dt_local.weekday() not in working_days
    is_after_hours = dt_local.time() >= end_time

    if is_non_working_day or is_after_hours:
        # Move to the beginning of the next day and find the next working day
        next_day = (dt_local + datetime.timedelta(days=1)).replace(hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0)
        while next_day.weekday() not in working_days:
            next_day += datetime.timedelta(days=1)
        dt_local = next_day

    # If we are before hours on a working day, jump to the start of business hours for that day
    is_before_hours = dt_local.time() < start_time
    if is_before_hours:
        dt_local = dt_local.replace(hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0)
    
    # Convert back to UTC before returning
    return dt_local.astimezone(pytz.utc)


def calculate_sla_due_date(start_dt_utc, sla_hours, settings):
    """
    Calculates the due date for an SLA, considering business hours if the mode is set.
    start_dt_utc: The starting datetime object (in UTC).
    sla_hours: The number of hours for the SLA.
    settings: The business hours settings dictionary.
    Returns a datetime object for the due date in UTC.
    """
    if not sla_hours:
        return None

    if settings['mode'] == 'calendar_hours':
        return start_dt_utc + datetime.timedelta(hours=sla_hours)

    # --- Business Hours Calculation ---
    tz = settings['timezone']
    start_time = settings['start_time']
    end_time = settings['end_time']
    working_days = settings['working_days']
    
    # Ensure the clock starts within business hours
    current_dt = get_next_business_moment(start_dt_utc, settings)
    
    remaining_sla = datetime.timedelta(hours=sla_hours)
    
    current_dt_local = current_dt.astimezone(tz)

    while remaining_sla.total_seconds() > 0:
        if current_dt_local.weekday() in working_days:
            business_day_end = current_dt_local.replace(hour=end_time.hour, minute=end_time.minute, second=0, microsecond=0)
            
            time_left_in_day = business_day_end - current_dt_local
            
            if remaining_sla <= time_left_in_day:
                current_dt_local += remaining_sla
                remaining_sla = datetime.timedelta(0)
            else:
                remaining_sla -= time_left_in_day
                
                current_dt_local = (current_dt_local + datetime.timedelta(days=1)).replace(hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0)
                
                while current_dt_local.weekday() not in working_days:
                    current_dt_local += datetime.timedelta(days=1)
        else:
            current_dt_local = (current_dt_local + datetime.timedelta(days=1)).replace(hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0)
            while current_dt_local.weekday() not in working_days:
                current_dt_local += datetime.timedelta(days=1)

    return current_dt_local.astimezone(pytz.utc)


def check_resolution_sla_status(ticket, sla_due_date):
    """
    Checks the resolution SLA status for a ticket against its due date.
    """
    if ticket['status'] in ['Resolved', 'Closed']:
        return 'N/A'
    
    if not sla_due_date:
        return 'N/A'

    now_utc = datetime.datetime.now(pytz.utc)
    
    if now_utc > sla_due_date:
        return 'Breached'
    else:
        return 'On Track'

def check_response_sla_status(ticket, response_due_date):
    """
    Checks the response SLA status for a ticket against its due date.
    """
    if not response_due_date:
        return "N/A"
        
    is_responded = ticket['agent_id'] is not None or ticket['status'] != 'Open'

    if is_responded:
        if not ticket['updated_at']:
             return 'Met'
        
        responded_at_utc = datetime.datetime.fromisoformat(ticket['updated_at']).replace(tzinfo=pytz.utc)

        if responded_at_utc > response_due_date:
            return 'Breached'
        else:
            return 'Met'
    else: 
        now_utc = datetime.datetime.now(pytz.utc)
        if now_utc > response_due_date:
            return 'Breached'
        else:
            return 'Pending'
