"""AWS Lambda Handler Entrypoint.

Forwards execution to lambda_transform.transform.lambda_handler.
"""

from lambda_transform.transform import lambda_handler

__all__ = ["lambda_handler"]
