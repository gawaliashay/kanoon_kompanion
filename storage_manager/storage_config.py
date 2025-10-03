# storage_manager\storage_config.py

import os
from storage_manager.storage_backend import LocalStorage, S3Storage, CompositeStorage

def get_storage():
    mode = os.getenv("STORAGE_MODE", "local")
    local = LocalStorage()

    if mode == "s3":
        bucket = os.getenv("S3_BUCKET")
        s3 = S3Storage(bucket_name=bucket)
        return CompositeStorage(s3, local)

    return local


# Global storage object
storage = get_storage()
