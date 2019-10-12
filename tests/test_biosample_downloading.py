import pytest
import os
from omicidx_builder import cli

@pytest.mark.skipif(not os.getenv('LONG_TESTS', False),
                    reason = 'longrunning test')
def test_biosample_download():
    cli.download_biosample()
    assert os.path.exists('biosample_set.xml.gz')
    os.unlink('biosample_set.xml.gz')
