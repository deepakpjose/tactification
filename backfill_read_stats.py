import sys
from app import create_app, db
from app.models import Post, Trivia, compute_word_stats

"""
One-off backfill for the word_count/read_time columns on Post and Trivia.
Run once after applying the migration that adds those columns, so existing
rows get real values instead of the server_default of 0.
"""

app = create_app()


def backfill(model):
    updated = 0
    for row in model.query.all():
        row.word_count, row.read_time = compute_word_stats(row.body)
        updated += 1
    db.session.commit()
    return updated


def main():
    with app.app_context():
        posts = backfill(Post)
        trivias = backfill(Trivia)
        print("Updated {:d} posts and {:d} trivias.".format(posts, trivias))


if __name__ == "__main__":
    sys.exit(main())
