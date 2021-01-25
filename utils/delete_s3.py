import boto3


if __name__ == "__main__":
    s3 = boto3.resource('s3')

    print("Buckets :")
    for bucket in s3.buckets.all():
        if bucket.name.lower() == "firehose-log-storage":
            print(f"\t{bucket.name}\t{bucket.creation_date}")
            bucket.objects.all().delete()
            bucket.delete()
