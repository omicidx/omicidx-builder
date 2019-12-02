"""Various utility functions for cli"""
import datetime


def dateconverter(o):
    """Convert an object from datetime to string

    Use this in the context of json to do custom
    conversions."""

    if isinstance(o, (datetime.datetime)):
        return o.__str__()
