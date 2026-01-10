import os
from datetime import datetime
from app import db
from app.models import Post, PostType, Trivia


def seed_content():
    post = Post(
        body="Post body",
        header="Header",
        description="Desc",
        tags="tag",
        post_type=PostType.POSTER,
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
    )
    trivia = Trivia(
        body="Trivia body",
        header="Trivia",
        tags="tag",
        post_type=PostType.TRIVIA,
        date=datetime(2024, 1, 2, 12, 0, 0),
    )
    db.session.add_all([post, trivia])
    db.session.commit()
    return post, trivia


def test_index_shows_posts(client, app_instance):
    with app_instance.app_context():
        seed_content()

    response = client.get("/")
    assert response.status_code == 200
    assert b"Header" in response.data


def test_archives_and_videos(client, app_instance):
    with app_instance.app_context():
        seed_content()

    assert client.get("/postindex").status_code == 200
    assert client.get("/triviasindex").status_code == 200
    assert client.get("/videos").status_code == 200
    assert client.get("/aboutme").status_code == 200


def test_post_and_trivia_pages(client, app_instance):
    with app_instance.app_context():
        post, trivia = seed_content()
        post_id, post_header = post.id, post.header
        trivia_id, trivia_header = trivia.id, trivia.header

    assert client.get(f"/post/{post_id}/{post_header}").status_code == 200
    assert client.get(f"/trivia/{trivia_id}/{trivia_header}").status_code == 200
    # Invalid ids return the error template instead of 404.
    assert client.get("/post/-1/bad").status_code == 404
    assert client.get("/trivia/-1/bad").status_code == 404 


def test_download_file_serves_uploaded_file(client, app_instance, tmp_path):
    upload_dir = app_instance.config["UPLOAD_FOLDER"]
    filename = "sample.txt"
    file_path = os.path.join(upload_dir, filename)
    with open(file_path, "w", encoding="utf-8") as handle:
        handle.write("content")

    response = client.get(f"/download_file/1/{filename}")
    assert response.status_code == 200
    assert response.data == b"content"


def test_sitemap_includes_posts(client, app_instance):
    with app_instance.app_context():
        post, _ = seed_content()
        post_id = post.id

    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert b"<loc>" in response.data
    assert bytes(str(post_id), "utf-8") in response.data


def test_robots_txt_served(client):
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert b"User-agent" in response.data
