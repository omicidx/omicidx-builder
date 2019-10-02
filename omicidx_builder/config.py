import toml
import os

def get_configfile_location():
    """Get toml config file location

    Assumes that an environment variable, "OMICIDX_CONFIGURATION_FILE" 
    contains the path to a configuration file in toml format

    Returns:
    str
    """
    return os.environ.get('OMICIDX_CONFIGURATION_FILE', 'config.toml')

class Config(dict):
    def __init__(self, configfile: str = None):
        
        configfile_location = configfile
        if(configfile is None):
            configfile_location = get_configfile_location()

        self.update(toml.load(configfile_location))

    
