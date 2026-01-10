import io
import os
import pytest
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import Forbidden
from flask_login import login_user
from app import db
from app.auth.decorators import permission_required
from app.auth.utils import allowed_file
from app.auth.forms import PosterEditForm, TriviaEditForm
from app.auth.views import poster_create, poster_update, poster_delete
from app.models import Permission, Post, PostType, Role, User


def create_user(email, role_name, password="secret"):
    role = Role.query.filter_by(name=role_name).first()
    user = User(email=email, username=email.split("@")[0], role=role)
    user.password = password
    db.session.add(user)
    db.session.commit()
    return user


def test_allowed_file():
    assert allowed_file("poster.png")
    assert allowed_file("doc.PDF")
    assert not allowed_file("script.sh")
    assert not allowed_file("noextension")


def test_permission_required_allows_authorized(app_instance):
    with app_instance.app_context():
        admin = create_user("admin@example.com", "Administrator")

        @permission_required(Permission.WRITE_ARTICLES)
        def secured():
            return "ok"

        with app_instance.test_request_context("/"):
            login_user(admin)
            assert secured() == "ok"


def test_permission_required_blocks_unauthorized(app_instance):
    with app_instance.app_context():
        user = create_user("user@example.com", "User")

        @permission_required(Permission.WRITE_ARTICLES)
        def secured():
            return "ok"

        with app_instance.test_request_context("/"):
            login_user(user)
            with pytest.raises(Forbidden):
                secured()


def _build_file(name, content=b"file-bytes"):
    return FileStorage(stream=io.BytesIO(content), filename=name, content_type="image/png")


def test_poster_create_updates_post_fields(app_instance):
    with app_instance.app_context():
        post = Post(
            body="body",
            header="Header",
            description="desc",
            tags="tags",
            post_type=PostType.POSTER,
        )
        db.session.add(post)
        db.session.commit()

        path = app_instance.config["UPLOAD_FOLDER"]
        file_storage = _build_file("poster.png")

        with app_instance.test_request_context("/auth/writeposters"):
            assert poster_create(post, path, file_storage) is True
            assert os.path.exists(post.doc)
            assert "/download_file/" in post.url


def test_poster_update_replaces_existing_file(app_instance):
    with app_instance.app_context():
        post = Post(
            body="body",
            header="Header",
            description="desc",
            tags="tags",
            post_type=PostType.POSTER,
        )
        db.session.add(post)
        db.session.commit()

        path = app_instance.config["UPLOAD_FOLDER"]
        original = _build_file("original.png")
        with app_instance.test_request_context("/"):
            assert poster_create(post, path, original)

        # Replace with a new file.
        new_file = _build_file("updated.png", b"new-bytes")
        with app_instance.test_request_context("/"):
            assert poster_update(post, path, new_file) is True
            assert os.path.exists(post.doc)
            with open(post.doc, "rb") as saved:
                assert saved.read() == b"new-bytes"


def test_poster_delete_removes_file(app_instance):
    with app_instance.app_context():
        post = Post(
            body="body",
            header="Header",
            description="desc",
            tags="tags",
            post_type=PostType.POSTER,
        )
        db.session.add(post)
        db.session.commit()

        path = app_instance.config["UPLOAD_FOLDER"]
        file_storage = _build_file("to_delete.png")
        with app_instance.test_request_context("/"):
            assert poster_create(post, path, file_storage)
            assert os.path.exists(post.doc)

        poster_delete(post)
        assert not os.path.exists(post.doc)


def test_login_logout_flow(client, app_instance):
    with app_instance.app_context():
        user = create_user("login@example.com", "Administrator")

    response = client.post(
        "/auth/login",
        data={"email": "login@example.com", "password": "secret", "remember_me": "y"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")

    # Logout should redirect back to home.
    response = client.get("/auth/logout")
    assert response.status_code == 302


def _login_as_admin(client, app_instance):
    with app_instance.app_context():
        create_user("admin@example.com", "Administrator")
    client.post(
        "/auth/login",
        data={"email": "admin@example.com", "password": "secret"},
        follow_redirects=False,
    )


def test_write_posters_flow(client, app_instance):
    _login_as_admin(client, app_instance)

    # GET should render form
    assert client.get("/auth/writeposters").status_code == 200

    data = {
        "header": "Poster",
        "desc": "Caption",
        "body": "Body",
        "tags": "tag1",
        "poster": (io.BytesIO(b"poster-bytes"), "poster.png"),
    }
    response = client.post(
        "/auth/writeposters",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app_instance.app_context():
        saved = Post.query.filter_by(header="Poster").first()
        assert saved is not None
        assert os.path.exists(saved.doc)


def test_edit_and_delete_posters(client, app_instance):
    _login_as_admin(client, app_instance)
    upload_dir = app_instance.config["UPLOAD_FOLDER"]

    with app_instance.app_context():
        post = Post(
            body="body",
            header="Header",
            description="desc",
            tags="tags",
            post_type=PostType.POSTER,
        )
        db.session.add(post)
        db.session.commit()
        # Seed an existing file to replace.
        file_path = os.path.join(upload_dir, "existing.png")
        with open(file_path, "wb") as handle:
            handle.write(b"old")
        post.doc = file_path
        post.url = "/existing"
        db.session.add(post)
        db.session.commit()
        post_id = post.id

    edit_data = {
        "header": "Updated",
        "description": "New caption",
        "body": "new body",
        "tags": "new",
        "poster": (io.BytesIO(b"new"), "new.png"),
    }
    resp = client.post(
        f"/auth/editposters/{post_id}",
        data=edit_data,
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert resp.status_code == 302

    with app_instance.app_context():
        post = Post.query.get(post_id)
        assert post.header == "Updated"
        assert os.path.exists(post.doc)
        updated_doc_path = post.doc

    delete_resp = client.get(f"/auth/deleteposters/{post_id}")
    assert delete_resp.status_code == 302
    with app_instance.app_context():
        assert Post.query.get(post_id) is None
    assert not os.path.exists(updated_doc_path)


def test_trivia_crud_flow(client, app_instance):
    _login_as_admin(client, app_instance)

    trivia_data = {
        "header": "Trivia",
        "body": "Facts",
        "tags": "tag",
        "date": "2024-01-01",
        "url": "https://example.com",
    }
    create_resp = client.post(
        "/auth/writetrivias",
        data=trivia_data,
        follow_redirects=False,
    )
    assert create_resp.status_code == 302

    with app_instance.app_context():
        from app.models import Trivia as TriviaModel

        trivia_item = TriviaModel.query.filter_by(header="Trivia").first()
        assert trivia_item is not None
        trivia_id = trivia_item.id

    edit_data = {
        "header": "Trivia Updated",
        "body": "New facts",
        "tags": "tag2",
        "date": "2024-01-02",
        "url": "https://example.com/repo",
    }
    edit_resp = client.post(
        f"/auth/edittrivias/{trivia_id}", data=edit_data, follow_redirects=False
    )
    assert edit_resp.status_code == 302

    with app_instance.app_context():
        from app.models import Trivia as TriviaModel

        trivia_item = TriviaModel.query.get(trivia_id)
        assert trivia_item.header == "Trivia Updated"

    delete_resp = client.get(f"/auth/deletetrivias/{trivia_id}")
    assert delete_resp.status_code == 302
    with app_instance.app_context():
        from app.models import Trivia as TriviaModel
        assert TriviaModel.query.get(trivia_id) is None


def test_form_show_helpers(app_instance):
    with app_instance.test_request_context("/"):
        poster_form = PosterEditForm(
            header="Header",
            description="Desc",
            body="Body",
            tags="tag",
            poster=_build_file("poster.png"),
        )
        assert poster_form.show() is None

        trivia_form = TriviaEditForm(
            header="Header",
            body="Body",
            tags="tag",
            date="2024-01-01",
            url="https://example.com",
        )
        assert trivia_form.show() is None
