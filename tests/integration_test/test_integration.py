
import pytest
import subprocess
import json
from pathlib import Path
import os

cwd = Path.cwd()
scrapy_project_dir = Path(__file__).parent  # Needs to be in same dir as scarpy.cfg

log_file = scrapy_project_dir / 'scrapy.log'
data_file = scrapy_project_dir / 'cleaned_data.json'

log_file.unlink(missing_ok=True) # Delete the file if it exists
data_file.unlink(missing_ok=True) # Delete the file if it exists

try:
    if cwd != scrapy_project_dir:
        os.chdir(scrapy_project_dir)
    
    subprocess.run(['scrapy', 'crawl', 'dirty', '-O', 'cleaned_data.json'])
    
    def test_log_file():
        assert log_file.exists()
        
        with log_file.open('r') as file:
            log = file.read()
        
        assert 'log_count/ERROR' not in log
    
    def test_data_file():
        assert data_file.exists()
        
        with data_file.open('r') as file:
            data = json.load(file)
        
        # Should scrape in order
        expected_data = [
            {"date": "2016-02-03 17:04:27"},
            {"date": "2019-12-23 02:04:18"},
            {"date": "1992-12-25 12:00:00"},
            {"number": "1000"},
            {"number": "100"},
            {"price": {"amount": "1500.50", "currency": "¥", "amount_text": "1,500.50"}},
            {"text": "This really is a messy string!!!"},
            {"json": "This is some foo content."},
            {"json": "John Doe"}
        ]
        
        assert data == expected_data
        
except:
    assert False
finally:
    os.chdir(cwd)
        

