import pandas as pd

from pathlib import Path

def get_keyword(file_path:Path):
    if file_path.is_file():
        df = pd.read_csv(file_path,sep='\t',header=None)
        return df[0].tolist()
    else:
        return []