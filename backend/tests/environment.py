import os


def setup_test_environment():
    """
    Setup environment variables for testing.
    This should be called before importing app/config if we want to override defaults
    that rely on os.environ, OR we can rely on pydantic settings validation.

    For now, we just ensure critical vars are set.
    """
    # Force testing mode if applicable
    os.environ["TESTING"] = "True"

    # Ensure we use a test-safe secret key if not provided (though .env usually handles this)
    if not os.environ.get("SECRET_KEY"):
        os.environ["SECRET_KEY"] = "super-secret-test-key-12345"

    # We can add other overrides here
