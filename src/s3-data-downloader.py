import boto3
import os

s3 = boto3.client('s3')
bucket_name = 'knowledge-graph-external-data'
local_folder = './downloaded-files'

# List and download all objects
paginator = s3.get_paginator('list_objects_v2')
for page in paginator.paginate(Bucket=bucket_name):
    if 'Contents' in page:
        for obj in page['Contents']:
            key = obj['Key']
            local_path = os.path.join(local_folder, key)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            s3.download_file(bucket_name, key, local_path)
            print(f"Downloaded: {key}")
