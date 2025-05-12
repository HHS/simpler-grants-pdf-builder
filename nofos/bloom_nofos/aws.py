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


def generate_iam_auth_token(env):
    db_host = env.get_value("DB_HOST")
    db_user = env.get_value("DB_USER")
    db_port = int(env.get_value("DB_PORT", default=5432))
    aws_region = env.get_value("AWS_REGION")

    client = boto3.client("rds", region_name=aws_region)
    return client.generate_db_auth_token(
        DBHostname=db_host, Port=db_port, DBUsername=db_user, Region=aws_region
    )
