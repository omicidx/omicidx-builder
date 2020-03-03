"""Config comes from environment variables"""
import os


class Config(object):
    def __init__(self):
        
        self.ES_HOST=os.getenv('ES_HOST')
        self.GCS_STAGING_URL=os.getenv('GCS_STAGING_URL')
        self.GCS_EXPORT_URL =os.getenv('GCS_EXPORT_URL')

config = Config()
