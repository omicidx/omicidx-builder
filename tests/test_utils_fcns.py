from omicidx_builder import utils
import datetime

def test_dateconverter():
    """Datetime to string date is working"""
    dt = datetime.datetime(year=2019, month=12, day=2)
    assert(utils.dateconverter(dt)=="2019-12-02 00:00:00")
    dt = datetime.datetime(year=2019, month=12, day=2, hour=13, minute=34, second=22)
    assert(utils.dateconverter(dt)=="2019-12-02 13:34:22")
