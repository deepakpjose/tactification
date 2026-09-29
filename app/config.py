"""
Settings for the flask app is set here.
"""
import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """
    Base class for all the configs
    """

    SECRET_KEY = os.environ.get("SECRET_KEY")
    YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.getenv("APP_PATH") + "/docs"
    ALLOWED_EXTENSIONS = {
        "txt",
        "pdf",
        "png",
        "jpg",
        "jpeg",
        "gif",
        "webp",
        "docx",
        "doc",
    }

    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, 'docs', "tactification.data.sqlite")
    # sqlite3's default busy timeout is effectively 0 -- a second writer gets
    # "database is locked" immediately instead of waiting. 30s lets a writer
    # queue behind another brief write (e.g. a page-visit counter) instead
    # of erroring out the request.
    SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"timeout": 30}}
