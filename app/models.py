"""
all db classes and attributes are defined in this function
"""
from datetime import datetime
from random import sample
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, url_for, Markup
from flask_login import UserMixin, AnonymousUserMixin
from app import db
from . import login_manager

_MONTHNAMES = [
    None,
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


class PostType:
    BLOG = 0x1
    ZINES = 0x2
    POSTER = 0x4


# pg112
class Permission:
    """
    user permissions are defined here
    """

    COMMENT = 0x1
    WRITE_ARTICLES = 0x02
    MODERATE_COMMENTS = 0x4
    ADMINISTER = 0x8


# pg 54: Model definition. Tables are represented as models thru class.
class Role(db.Model):
    """
    roles of users are defined in this class
    """

    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    # pg 112
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)

    # pg 56. backref will create an attribute named 'role' to User.
    # it can be used to access 'Role' from 'User' instead of 'role_id' in user.
    users = db.relationship("User", backref="role", lazy="dynamic")

    def __repr__(self):
        return "<Role %r>" % self.name

    @staticmethod
    def insert_roles():
        """
        inserting roles
        """
        roles = {
            "User": (Permission.COMMENT, True),
            "Moderator": (
                Permission.COMMENT
                | Permission.WRITE_ARTICLES
                | Permission.MODERATE_COMMENTS,
                False,
            ),
            "Administrator": (
                Permission.COMMENT
                | Permission.WRITE_ARTICLES
                | Permission.MODERATE_COMMENTS
                | Permission.ADMINISTER,
                False,
            ),
        }
        for r in roles:
            role = Role(name=r)

            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)

        db.session.commit()


class User(db.Model, UserMixin):
    """
    all user related information is stored here.
    """

    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    # pg 95
    # pg 66. When add new fields, upgrade the db.
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(32))
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"))
    is_active = db.Column(db.Boolean)
    confirmed = db.Column(db.Boolean, default=False)
    # pg 91
    password_hash = db.Column(db.String(128))
    posts = db.relationship("Post", backref="author", lazy="dynamic")

    @property
    def password(self):
        raise AttributeError("password is not a readable attribute")

    @password.setter
    def password(self, password):
        """
        password setter
        """
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        """
        verifying password
        """
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        """
        username
        """
        return "<User %r>" % self.username

    @property
    def is_active(self):
        return True

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)

    def can(self, permissions):
        """
        have sufficient permissions
        """
        print(
            "Permissions: {:d} passed permissions: {:d}".format(
                self.role.permissions, permissions
            )
        )
        return self is not None and (
            self.role.permissions and self.role.permissions & permissions
        )

    def is_administrator(self):
        """
        is adminstrator
        """
        return self.can(Permission.ADMINISTER)

    def generate_confirmation_token(self, expiration=3600):
        """
        generate the token for user.
        """
        s = Serializer(current_app.config["SECRET_KEY"], expiration)
        return s.dumps({"confirm": self.id})

    def confirm(self, token):
        """
        to set confirm. right now, its used anywhere
        """
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get("confirm") != self.id:
            return False

        self.confirmed = True
        db.session.add(self)
        return True

    def generate_auth_token(self, expiration):
        """
        To generate authentication via rest
        """
        s = Serializer(current_app.config["SECRET_KEY"], expires_in=expiration)
        return s.dumps({"id": self.email})

    @staticmethod
    def verify_auth_token(token):
        """
        for verification of authentication via rest
        """
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token)
        except:
            return None

        return data["id"]


class AnonymousUser(AnonymousUserMixin):
    """
    class for anonymous users
    """

    def can(self, permissions):
        """
        can user comment or not?
        """
        if permissions == Permission.COMMENT:
            return True
        return False

    def is_administrator(self):
        """
        return false always under anonymousUser
        """
        return False


login_manager.anonymous_user = AnonymousUser


class Post(db.Model):
    """
    All post data is stored here.
    """

    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    body = db.Column(db.Text)
    header = db.Column(db.String(32))
    description = db.Column(db.Text)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    tags = db.Column(db.String(64))

    # using flask-uploads
    # This is used for main page
    doc = db.Column(db.String(64))
    url = db.Column(db.String(64))

    post_type = db.Column(db.Integer)

    def month_of_date(self, month):
        return _MONTHNAMES[month]

    def post_date_in_isoformat(self):
        date_str = self.timestamp
        month = self.month_of_date(date_str.month)

        return "{:d} {:s}, {:d}".format(date_str.day, month, date_str.year)


@login_manager.user_loader
def load_user(user_id):
    """ """
    return User.query.get(int(user_id))
