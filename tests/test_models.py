from datetime import datetime
from itsdangerous.exc import BadSignature
from app import db
from app.models import (
    AnonymousUser,
    Permission,
    Role,
    User,
    Post,
    PostType,
    Trivia,
    load_user,
)


def create_user(email, role_name, password="secret"):
    role = Role.query.filter_by(name=role_name).first()
    user = User(email=email, username=email.split("@")[0], role=role)
    user.password = password
    db.session.add(user)
    db.session.commit()
    return user


def test_role_inserted(app_instance):
    with app_instance.app_context():
        roles = Role.query.order_by(Role.name).all()
        names = [role.name for role in roles]
        assert {"Administrator", "Moderator", "User"} == set(names)


def test_user_password_and_permissions(app_instance):
    with app_instance.app_context():
        user = create_user("user@example.com", "User")

        assert user.verify_password("secret")
        assert not user.verify_password("wrong")
        assert user.can(Permission.COMMENT)
        assert not user.can(Permission.WRITE_ARTICLES)
        assert not user.is_administrator()


def test_admin_permissions_and_auth_token(app_instance):
    with app_instance.app_context():
        admin = create_user("admin@example.com", "Administrator")

        assert admin.is_administrator()

        token = admin.generate_auth_token(expiration=60)
        decoded = User.verify_auth_token(token)
        assert decoded == admin.email


def test_confirmation_token_flow(app_instance):
    with app_instance.app_context():
        user = create_user("confirm@example.com", "User")

        token = user.generate_confirmation_token()
        print(
            {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "role_id": user.role_id,
                "is_active": user.is_active,
                "confirmed": user.confirmed,
                "password_hash": user.password_hash,
                "token": token,
            }
        )
        assert user.confirmed is False
        assert user.confirm(token) is True
        assert user.confirmed is True

        bad_token = token + b"corrupted"
        assert user.confirm(bad_token) is False


def test_anonymous_user_permissions():
    anon = AnonymousUser()
    assert anon.can(Permission.COMMENT)
    assert not anon.can(Permission.WRITE_ARTICLES)
    assert anon.is_administrator() is False


def test_post_date_helpers(app_instance):
    with app_instance.app_context():
        post = Post(
            body="body",
            header="Header",
            description="desc",
            post_type=PostType.POSTER,
            timestamp=datetime(2023, 1, 9, 12, 0, 0),
        )
        db.session.add(post)
        db.session.commit()

        assert post.month_of_date(1) == "Jan"
        assert post.post_date_in_isoformat() == "09 Jan, 2023"
        assert post.show() is None


def test_trivia_date_helpers(app_instance):
    with app_instance.app_context():
        trivia = Trivia(
            body="body",
            header="Header",
            tags="tags",
            post_type=PostType.TRIVIA,
            date=datetime(2023, 12, 3, 12, 0, 0),
        )
        db.session.add(trivia)
        db.session.commit()

        assert trivia.month_of_date(12) == "Dec"
        assert trivia.trivia_date_in_isoformat() == "03 Dec, 2023"
        assert trivia.show() is None


def test_load_user_returns_user(app_instance):
    with app_instance.app_context():
        user = create_user("load@example.com", "User")
        loaded = load_user(user.id)
        assert loaded.email == "load@example.com"
