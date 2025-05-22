from django.db.backends.postgresql.base import DatabaseWrapper as BaseDatabaseWrapper


class DatabaseWrapper(BaseDatabaseWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        options = self.settings_dict.get("OPTIONS", {})
        self.generate_iam_auth_token = options.pop("generate_iam_auth_token", None)

    def get_connection_params(self):
        params = super().get_connection_params()

        if self.generate_iam_auth_token:
            params["password"] = self.generate_iam_auth_token()

        return params
