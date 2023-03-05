""" 
blueprint creation file for auth
"""
from flask import Blueprint

auth = Blueprint("auth", __name__)  # pylint: disable=invalid-name

from . import views
