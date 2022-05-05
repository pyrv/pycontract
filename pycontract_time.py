
import re
from datetime import datetime, timedelta


class Time:
    '''
    Class for features related to time. The class is static and is not meant to
    be instantiated.
    '''

    # The year occurring in time stamps. Is assumed to be the same for all EHAs.
    YEAR = None

    # Once the year is known, this denotes the first day of the year.
    START_OF_YEAR = None

    # Regular expression for extracting values from time stamp ending with milliseconds.
    # Such occur in logs.
    # Example: 2021-349T00:07:26.986
    RE_TIME_MS = re.compile(r'(\d\d\d\d)-(\d\d\d)T(\d\d):(\d\d):(\d\d).(\d\d\d)')

    # Regular expression for extracting values from time stamp ending with seconds.
    # Such are provided as options to the script (start and end time).
    # Example: 2021-349T00:07:26
    RE_TIME_SEC = re.compile(r'(\d\d\d\d)-(\d\d\d)T(\d\d):(\d\d):(\d\d)$')

    @classmethod
    def stamp_to_datetime(cls, timestamp: str) -> "DateTime":
        '''
        Turns a time stamp with milliseconds into a datetime.
        :param timestamp: the timestamp to be converted.
        :return: the resulting datetime.
        '''
        time_match = Time.RE_TIME_MS.match(timestamp)
        year = int(time_match[1])
        if Time.YEAR is None:
            Time.YEAR = year
            Time.START_OF_YEAR = datetime(Time.YEAR, 1, 1)
        else:
            assert year == Time.YEAR
        days = int(time_match[2])
        hours = int(time_match[3])
        minutes = int(time_match[4])
        seconds = int(time_match[5])
        milliseconds = int(time_match[6])
        date_time = Time.START_OF_YEAR + timedelta(
            days=days - 1,
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            microseconds=milliseconds * 1000)
        return date_time

    @classmethod
    def diff_seconds(cls, time_stamp1: str, time_stamp2: str) -> int:
        """
        returns the difference between two timestamps in seconds.
        :param time_stamp1: the earliest timestamp.
        :param time_stamp2: the latest timestamp.
        :return: the difference in seconds.
        """
        date_time1 = Time.stamp_to_datetime(time_stamp1)
        date_time2 = Time.stamp_to_datetime(time_stamp2)
        diff = date_time2 - date_time1
        return diff.total_seconds()


