from flask import Blueprint

newsletter = Blueprint("newsletter", __name__)  # pylint: disable=invalid-name

from . import views
