"""
all db classes and attributes are defined in this function
"""
import logging
import re
import secrets
from datetime import datetime
from random import sample
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, url_for, Markup
from flask_login import UserMixin, AnonymousUserMixin
from sqlalchemy import event
from app import db
from . import login_manager

_TAG_RE = re.compile(r"<[^>]+>")
_WORDS_PER_MINUTE = 200


def compute_word_stats(html_body):
    """
    Strips HTML tags from a body of content and returns (word_count, read_time)
    where read_time is in whole minutes, rounded up to a minimum of 1 for any
    non-empty body.
    """
    if not html_body:
        return 0, 0
    text = _TAG_RE.sub(" ", html_body)
    word_count = len(text.split())
    read_time = max(1, round(word_count / _WORDS_PER_MINUTE)) if word_count else 0
    return word_count, read_time

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


def format_year_month(year, month):
    """
    e.g. (2026, 9) -> "Sep 2026". Used for the /socialmedia snapshot label.
    """
    return "{:s} {:d}".format(_MONTHNAMES[month], year)


class PostType:
    BLOG = 0x1
    ZINES = 0x2
    POSTER = 0x4
    TRIVIA = 0x8


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
    visit_count = db.Column(db.Integer, server_default='0', nullable=False)
    word_count = db.Column(db.Integer, server_default='0', nullable=False)
    read_time = db.Column(db.Integer, server_default='0', nullable=False)

    def month_of_date(self, month):
        return _MONTHNAMES[month]

    def post_date_in_isoformat(self):
        date_str = self.timestamp
        month = self.month_of_date(date_str.month)

        #day with single date and two date causes alignment in display.
        #Hence adding a 0 for day's with single digit.
        day = str(date_str.day)
        if len(day) == 1:
            day = '0{:s}'.format(day)
        else:
            day = '{:s}'.format(day)

        return "{:s} {:s}, {:d}".format(day, month, date_str.year)

    def show(self):
        '''
        To display the contents of a post.
        '''
        post_info = 'Id: {id} header: {header} path: {path} url: {url}'
        logging.info(post_info.format(id=self.id, header=self.header, path=self.doc, url=self.url))
        return

class Trivia(db.Model):
    """
    All trivia data is stored here.
    """

    __tablename__ = "trivias"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, index=True)
    body = db.Column(db.Text)
    header = db.Column(db.String(32))
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    tags = db.Column(db.String(64))
    post_type = db.Column(db.Integer)
    url = db.Column(db.String(256))
    visit_count = db.Column(db.Integer, server_default='0', nullable=False)
    word_count = db.Column(db.Integer, server_default='0', nullable=False)
    read_time = db.Column(db.Integer, server_default='0', nullable=False)

    def month_of_date(self, month):
        return _MONTHNAMES[month]

    def trivia_date_in_isoformat(self):
        date_str = self.date
        month = self.month_of_date(date_str.month)

        # Day with single digit and two digits causes alignment in display.
        # Hence adding a 0 for days with single digit.
        day = str(date_str.day)
        if len(day) == 1:
            day = '0{:s}'.format(day)
        else:
            day = '{:s}'.format(day)

        return "{:s} {:s}, {:d}".format(day, month, date_str.year)

    def show(self):
        """
        To display the contents of a trivia.
        """
        trivia_info = 'Id: {id} header: {header}'
        logging.info(trivia_info.format(id=self.id, header=self.header))
        return

@event.listens_for(Post, "before_insert")
@event.listens_for(Post, "before_update")
@event.listens_for(Trivia, "before_insert")
@event.listens_for(Trivia, "before_update")
def _set_read_stats(mapper, connection, target):
    """
    Populates word_count/read_time from body whenever a Post or Trivia is
    inserted/updated, so the values are stored on write rather than derived
    at render time.
    """
    target.word_count, target.read_time = compute_word_stats(target.body)


@login_manager.user_loader
def load_user(user_id):
    """ """
    return User.query.get(int(user_id))


class PageVisit(db.Model):
    """
    Tracks visit counts for static pages (index, aboutme, videos, etc.).
    """

    __tablename__ = "page_visits"
    page = db.Column(db.String(64), primary_key=True)
    count = db.Column(db.Integer, server_default='0', nullable=False)


class League:
    """
    Leagues tracked on the /socialmedia page.
    """

    EPL = "epl"
    LALIGA = "laliga"
    SERIEA = "seriea"
    BUNDESLIGA = "bundesliga"
    LIGUE1 = "ligue1"

    LABELS = {
        EPL: "Premier League",
        LALIGA: "La Liga",
        SERIEA: "Serie A",
        BUNDESLIGA: "Bundesliga",
        LIGUE1: "Ligue 1",
    }

    ORDER = [EPL, LALIGA, SERIEA, BUNDESLIGA, LIGUE1]


class Club(db.Model):
    """
    A football club tracked for social media follower counts.
    """

    __tablename__ = "clubs"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    league = db.Column(db.String(16), nullable=False, index=True)
    # Handle used to resolve the channel via the YouTube API (e.g. "@Arsenal").
    youtube_handle = db.Column(db.String(64))
    # Cached once resolved, so later refreshes can query by id directly.
    youtube_channel_id = db.Column(db.String(64))

    stats = db.relationship("YoutubeFollowerStat", backref="club", lazy="dynamic")

    def league_label(self):
        return League.LABELS.get(self.league, self.league)

    def __repr__(self):
        return "<Club %r (%s)>" % (self.name, self.league)


class YoutubeFollowerStat(db.Model):
    """
    A monthly snapshot of a club's YouTube subscriber count.
    One row per (club, year, month) -- refreshing mid-month overwrites it
    rather than adding a duplicate snapshot for that month.
    """

    __tablename__ = "youtube_follower_stats"
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey("clubs.id"), nullable=False, index=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    subscriber_count = db.Column(db.Integer, nullable=False)
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("club_id", "year", "month", name="uq_club_year_month"),
    )

    def __repr__(self):
        return "<YoutubeFollowerStat club_id=%r %d-%02d: %d>" % (
            self.club_id, self.year, self.month, self.subscriber_count,
        )


class NewsletterSubscriber(db.Model):
    """
    An email signed up for the quarterly post digest.

    `token` doubles as the confirm and unsubscribe link secret, so it is
    rotated on every (re)subscribe to invalidate any older emailed link.
    """

    __tablename__ = "newsletter_subscribers"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    token = db.Column(db.String(64), unique=True, index=True, nullable=False)
    confirmed = db.Column(db.Boolean, default=False, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime)

    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)

    def __repr__(self):
        return "<NewsletterSubscriber %r confirmed=%r active=%r>" % (
            self.email, self.confirmed, self.active,
        )


class NewsletterDigest(db.Model):
    """
    A record of each quarterly digest send, used to find which posts are
    "new since the last digest" the next time one goes out.
    """

    __tablename__ = "newsletter_digests"
    id = db.Column(db.Integer, primary_key=True)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    post_count = db.Column(db.Integer, nullable=False)
    recipient_count = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return "<NewsletterDigest sent_at=%r posts=%d recipients=%d>" % (
            self.sent_at, self.post_count, self.recipient_count,
        )
