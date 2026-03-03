"""
In-memory tag cache for Post and Trivia content.

Structure
---------
_cache['post']   : dict  tag (str) -> list of post dicts
_cache['trivia'] : dict  tag (str) -> list of trivia dicts

Each post dict: {id, header, date, image_url}
Each trivia dict: {id, header, date}

Counts are derived as len(list), so no separate counter is needed.
A full rebuild only happens lazily on first access after a cold start.
Mutations (write / edit / delete) update only the affected tag lists.
"""
from collections import Counter


_cache = {
    'post': None,
    'trivia': None,
}


# ── Serialisers ───────────────────────────────────────────────────────────────

def _post_dict(post):
    return {
        'id': post.id,
        'header': post.header,
        'date': post.post_date_in_isoformat(),
        'post_url': post.url,
    }


def _trivia_dict(trivia):
    return {
        'id': trivia.id,
        'header': trivia.header,
        'date': trivia.trivia_date_in_isoformat(),
        'post_url': trivia.url,
    }


# ── Build ─────────────────────────────────────────────────────────────────────

def _build_map(items, to_dict_fn):
    tag_map = {}
    for item in items:
        if item.tags:
            for raw_tag in item.tags.split():
                tag = raw_tag.lower()
                tag_map.setdefault(tag, []).append(to_dict_fn(item))
    return tag_map


def rebuild():
    from app.models import Post, PostType, Trivia
    posts = Post.query.filter_by(post_type=PostType.POSTER).all()
    trivias = Trivia.query.filter_by(post_type=PostType.TRIVIA).all()
    _cache['post'] = _build_map(posts, _post_dict)
    _cache['trivia'] = _build_map(trivias, _trivia_dict)


def _ensure(kind):
    if _cache[kind] is None:
        rebuild()


# ── Read ──────────────────────────────────────────────────────────────────────

def get_all_tags():
    """Sorted list of (tag, count) across posts and trivias, by count desc."""
    _ensure('post')
    _ensure('trivia')
    combined = Counter()
    for tag, items in _cache['post'].items():
        combined[tag] += len(items)
    for tag, items in _cache['trivia'].items():
        combined[tag] += len(items)
    return sorted(combined.items(), key=lambda x: (-x[1], x[0]))


def get_posts_for_tag(tag):
    _ensure('post')
    return _cache['post'].get(tag.lower(), [])


def get_trivias_for_tag(tag):
    _ensure('trivia')
    return _cache['trivia'].get(tag.lower(), [])


# ── Incremental mutations ─────────────────────────────────────────────────────

def _tag_list(tags_str):
    return [t.lower() for t in tags_str.split()] if tags_str else []


def add_item(item, kind):
    """Call after a new post/trivia is committed to DB."""
    if _cache[kind] is None:
        return  # not yet built; rebuild on next read will include this item
    to_dict = _post_dict if kind == 'post' else _trivia_dict
    d = to_dict(item)
    for tag in _tag_list(item.tags):
        _cache[kind].setdefault(tag, []).append(d)


def remove_item(item, kind):
    """Call before/after a post/trivia is deleted from DB."""
    if _cache[kind] is None:
        return
    for tag in _tag_list(item.tags):
        lst = _cache[kind].get(tag)
        if lst is not None:
            _cache[kind][tag] = [d for d in lst if d['id'] != item.id]
            if not _cache[kind][tag]:
                del _cache[kind][tag]


def update_item(item, old_tags_str, kind):
    """Call after editing a post/trivia.

    item.tags already holds the NEW tag string.
    old_tags_str is the tag string captured before the edit.
    Only the diffed tags are touched.
    """
    if _cache[kind] is None:
        return

    old_tags = set(_tag_list(old_tags_str))
    new_tags = set(_tag_list(item.tags))
    to_dict = _post_dict if kind == 'post' else _trivia_dict

    # Remove item from tags that were dropped
    for tag in old_tags - new_tags:
        lst = _cache[kind].get(tag)
        if lst is not None:
            _cache[kind][tag] = [d for d in lst if d['id'] != item.id]
            if not _cache[kind][tag]:
                del _cache[kind][tag]

    # Add item to tags that are newly added
    d = to_dict(item)
    for tag in new_tags - old_tags:
        _cache[kind].setdefault(tag, []).append(d)

    # Update the dict for tags that stayed (header/image_url may have changed)
    for tag in old_tags & new_tags:
        lst = _cache[kind].get(tag, [])
        for i, entry in enumerate(lst):
            if entry['id'] == item.id:
                lst[i] = d
                break
