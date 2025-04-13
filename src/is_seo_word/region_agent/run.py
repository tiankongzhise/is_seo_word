from ..utils import update_rsp_fail_txt_to_score_with_reason,load_toml,get_abs_file_path
from .async_call import async_main

import asyncio


# --- Script Entry Point ---
def run(batch_size: int|None = None):
    # Run the main asynchronous function
    # For Python 3.7+
    #补录之前的错误 如果存在
    config = load_toml('config.toml')
    fail_file_path = get_abs_file_path(config['FAIL_RSP_FILE_PATH'])
    batch_size = batch_size or config['BATCH_SIZE']
    update_rsp_fail_txt_to_score_with_reason(fail_txt_path=fail_file_path,ai_model=config['AI_MODEL'])
    asyncio.run(async_main(batch_size=batch_size)) # Adjust batch_size if needed