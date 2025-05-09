import boto3


# Check if we're using AWS RDS with IAM authentication
def is_aws_db(env):
    return all(
        [
            env.get_value("DB_HOST", default=None),
            env.get_value("DB_NAME", default=None),
            env.get_value("DB_USER", default=None),
            env.get_value("AWS_REGION", default=None),
        ]
    )


def generate_iam_auth_token(aws_region, host, port, user):
    client = boto3.client("rds", region_name=aws_region)
    token = client.generate_db_auth_token(
        DBHostname=host, Port=port, DBUsername=user, Region=aws_region
    )
    return token
