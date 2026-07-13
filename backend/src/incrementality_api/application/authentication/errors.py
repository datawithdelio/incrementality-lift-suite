class AuthenticationApplicationError(Exception):
    """Base exception for authentication use cases."""


class InvalidCredentialsError(AuthenticationApplicationError):
    """
    Raised when login credentials cannot be authenticated.

    The message must not reveal whether the email or password was wrong.
    """
