# -*- coding: utf-8 -*-
import calendar
from datetime import timedelta, datetime, date
from dateutil.relativedelta import *

# Constant value
SHORT_DATETIME_FORMAT = "%b %d"
APPEAR_DATE_FORMAT = "%m/%d/%Y"
BY_DAY = "day"
BY_WEEK = "week"
BY_MONTH = "month"
BY_QUARTER = "quarter"
BY_YEAR = "year"
BY_YTD = "ytd"
BY_MTD = 'mtd'
BY_FISCAL_YEAR = "fiscal_year"


def get_start_end_date_value(self, date_value, period_type):
    """ Function get the start date_value and end date_value from datetime
    value follow with period_type and return couple of value
    start_date_value and end_date_value type DateTime of date_value follow
    by period_type
    :param self:
    :param date_value:
    :param period_type:
    :return:
    """
    start_date_value = None
    end_date_value = None
    if date_value and period_type:
        if period_type == BY_DAY:
            start_date_value = date_value
            end_date_value = date_value
        elif period_type == BY_WEEK:
            # get Monday of (week, year)
            date_delta = date_value.isoweekday()
            start_date_value = date_value - timedelta(days=(date_delta - 1))
            end_date_value = date_value + timedelta(days=(7 - date_delta))
        elif period_type == BY_MONTH:
            start_date_value = datetime(date_value.year, date_value.month, 1)
            end_date_value = datetime(date_value.year, date_value.month,
                                      calendar.monthrange(date_value.year, date_value.month)[1])
        elif period_type == BY_QUARTER:
            month = int((date_value.month - 1) / 3) * 3 + 1
            start_date_value = datetime(date_value.year, month, 1)

            end_date_value = datetime(date_value.year, month + 2, calendar.monthrange(date_value.year, month + 2)[1])
        elif period_type == BY_YEAR:
            start_date_value = datetime(date_value.year, 1, 1)
            end_date_value = datetime(date_value.year, 12, 31)
        elif period_type == BY_YTD:
            current_date = datetime.now()
            company_fiscalyear_dates = self.env.user.company_id.compute_fiscalyear_dates(date_value)
            start_date_value = datetime.combine(company_fiscalyear_dates['date_from'], datetime.min.time())
            raw_end_date_value = company_fiscalyear_dates['date_to']
            end_date_value = datetime(raw_end_date_value.year, current_date.month, current_date.day)
        elif period_type == BY_FISCAL_YEAR:
            company_fiscalyear_dates = self.env.user.company_id.compute_fiscalyear_dates(date_value)
            start_date_value = datetime.combine(company_fiscalyear_dates['date_from'], datetime.min.time())
            end_date_value = datetime.combine(company_fiscalyear_dates['date_to'], datetime.min.time())
        elif period_type == BY_MTD:
            end_date_value = date_value
            start_date_value = end_date_value - relativedelta(days=(end_date_value.day - 1))

    return start_date_value, end_date_value


def get_start_end_date_value_with_delta(self, date_value, period_type, time_delta):
    start, end = get_start_end_date_value(self, date_value, period_type)
    times = abs(time_delta)
    while times > 0:
        times -= 1
        start, end = get_start_end_date_value(self, start + timedelta(days=1 if time_delta > 0 else -1), period_type)
    return start, end

def get_same_date_delta_period(date_value, month=0, day=0):
    same_date_result = date_value
    if not 1 <= month <= 12:
        month = date_value.month
    if day >= 1:
        fail_convert = True
        while fail_convert:
            try:
                same_date_result = date_value.replace(day=day, month=month)
                fail_convert = False
            except:
                day -= 1
    return same_date_result

def get_list_period_by_type(self, date_from, date_to, period_type=BY_MONTH):
    """ Function return list of periods base on start, end time and
    type of period to generate periods have sorted and lie between
    start and end date

    :param date_from: datetime
    :param date_to: datetime
    :param period_type:
    :return: list of tuples date value: start date and end date.
            both of them is date type
    """
    next = timedelta(days=1)
    start = date_from
    end = date_from
    list_periods = []
    while end <= date_to:
        start, end = get_start_end_date_value(self, start, period_type)
        if start < date_from:
            start = date_from
        if end > date_to:
            end = date_to
        list_periods.append((start.date(), end.date()))
        start = end + next
        end = start

    return list_periods
