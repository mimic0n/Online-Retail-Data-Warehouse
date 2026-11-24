import os
from pathlib import Path
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(path):
        return False
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/retail_dwh')
SOURCE_FILE = os.getenv('SOURCE_FILE', str(ROOT / 'data/raw/online-retail-ii.xlsx'))
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '50000'))
