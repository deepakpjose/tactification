import os
import pytest
from app import create_app, db
from app.models import Role

# Ensure a default path exists before the app module is imported anywhere else.
os.environ.setdefault("APP_PATH", "/var/www/app")


@pytest.fixture
def app_instance(monkeypatch):
    """
    Create a fresh Flask app and database for each test.
    """
    app_path = "/var/www/app"
    monkeypatch.setenv("APP_PATH", app_path)

    app = create_app()
    upload_dir = os.path.join(app_path, "docs")
    os.makedirs(upload_dir, exist_ok=True)

    app.config.update(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": "sqlite:////var/www/app/docs/tactification.data.sqlite",
            "SECRET_KEY": "test-secret",
            "SERVER_NAME": "localhost",
        }
    )

    with app.app_context():
        db.drop_all()
        db.create_all()
        Role.insert_roles()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app_instance):
    return app_instance.test_client()
