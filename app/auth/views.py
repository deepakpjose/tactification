"""
All custom login and logout apis are defined here.
"""
import os
import sys
import traceback
import logging
from datetime import datetime
from flask import (
    redirect,
    url_for,
    request,
    session,
    render_template,
    flash,
    jsonify,
    abort,
)
from flask_login import current_user, login_required, login_user, logout_user
from app import db, app
from app import tags as tag_cache
from app import social
from app.auth import auth
from app.models import (
    User, Permission, Role, Post, PostType, Trivia, PageVisit,
    Club, YoutubeFollowerStat, League, format_year_month,
    NewsletterSubscriber, NewsletterDigest,
)
from werkzeug.utils import secure_filename
from app.auth.forms import LoginForm, PosterCreateForm, PosterEditForm, TriviaCreateForm, TriviaEditForm
from app.auth.decorators import permission_required, admin_required
from app.auth.utils import allowed_file
from app.brevo import send_email


def _pending_digest_items():
    """
    Posts and trivia published since the last digest send (or ever, if none
    sent), normalized to a common shape so the dashboard preview and the
    digest email can render both content types the same way.
    """
    last_digest = NewsletterDigest.query.order_by(NewsletterDigest.sent_at.desc()).first()
    since = last_digest.sent_at if last_digest else datetime.min

    posts = Post.query.filter(Post.post_type == PostType.POSTER, Post.timestamp > since).all()
    trivias = Trivia.query.filter(Trivia.post_type == PostType.TRIVIA, Trivia.date > since).all()

    items = [
        {
            "header": p.header,
            "date": p.timestamp,
            "date_label": p.post_date_in_isoformat(),
            "read_time": p.read_time,
            "description": p.description,
            "endpoint": "main.post",
            "url_args": {"id": p.id, "header": p.header},
        }
        for p in posts
    ] + [
        {
            "header": t.header,
            "date": t.date,
            "date_label": t.trivia_date_in_isoformat(),
            "read_time": t.read_time,
            "description": None,
            "endpoint": "main.trivia",
            "url_args": {"id": t.id, "header": t.header},
        }
        for t in trivias
    ]
    items.sort(key=lambda item: item["date"])
    return items, last_digest


@auth.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    static_visits = PageVisit.query.order_by(PageVisit.count.desc()).all()
    posts = Post.query.filter_by(post_type=PostType.POSTER).order_by(Post.visit_count.desc()).all()
    trivias = Trivia.query.filter_by(post_type=PostType.TRIVIA).order_by(Trivia.visit_count.desc()).all()

    latest = (
        db.session.query(YoutubeFollowerStat.year, YoutubeFollowerStat.month)
        .order_by(YoutubeFollowerStat.year.desc(), YoutubeFollowerStat.month.desc())
        .first()
    )
    social_last_updated = format_year_month(latest[0], latest[1]) if latest else None
    social_club_count = Club.query.count()

    newsletter_pending_items, newsletter_last_digest = _pending_digest_items()
    newsletter_subscriber_count = NewsletterSubscriber.query.filter_by(
        confirmed=True, active=True
    ).count()

    return render_template(
        "dashboard.html",
        static_visits=static_visits,
        posts=posts,
        trivias=trivias,
        social_last_updated=social_last_updated,
        social_club_count=social_club_count,
        newsletter_pending_items=newsletter_pending_items,
        newsletter_last_digest=newsletter_last_digest,
        newsletter_subscriber_count=newsletter_subscriber_count,
    )


@auth.route("/newsletter/send", methods=["POST"])
@login_required
@admin_required
def send_newsletter_digest():
    pending_items, _ = _pending_digest_items()
    if not pending_items:
        flash("No new posts since the last digest -- nothing to send.")
        return redirect(url_for("auth.dashboard"))

    subscribers = NewsletterSubscriber.query.filter_by(confirmed=True, active=True).all()
    sent = 0
    for subscriber in subscribers:
        unsubscribe_url = url_for(
            "newsletter.unsubscribe", token=subscriber.token, _external=True
        )
        html = render_template(
            "newsletter/digest_email.html",
            items=pending_items,
            unsubscribe_url=unsubscribe_url,
        )
        try:
            send_email(
                to_email=subscriber.email,
                subject="What's new on Tactification",
                html_content=html,
            )
            sent += 1
        except Exception:
            app.logger.exception("Failed to send newsletter digest to %s", subscriber.email)

    db.session.add(
        NewsletterDigest(post_count=len(pending_items), recipient_count=sent)
    )
    db.session.commit()
    flash(
        "Digest ({:d} item{:s}) sent to {:d} of {:d} subscribers.".format(
            len(pending_items), "s" if len(pending_items) != 1 else "", sent, len(subscribers)
        )
    )
    return redirect(url_for("auth.dashboard"))


@auth.route("/socialmedia/refresh", methods=["POST"])
@login_required
@admin_required
def refresh_social_media():
    try:
        results = social.refresh_all_clubs()
    except RuntimeError as exc:
        flash(str(exc))
        return redirect(url_for("auth.dashboard"))

    flash("Updated {:d} clubs' YouTube stats.".format(results["updated"]))
    if results["failed"]:
        failed_names = ", ".join(name for name, _ in results["failed"][:10])
        flash("Failed for: {:s}".format(failed_names))
    return redirect(url_for("auth.dashboard"))


@auth.route("/login", methods=["POST", "GET"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        users = User.query.all()

        if user is not None and user.verify_password(form.password.data):
            if login_user(user, remember=form.remember_me.data) is False:
                return abort(403)
            flash("Successfully logged in.")
            return redirect(request.args.get("next") or url_for("main.index"))
        flash("Invalid username or password.")

    return render_template("signin.html", loginform=form)


@auth.route("/logout", methods=["GET"])
def logout():
    """
    login uses flask-oauthlib api's. But logout is defined here
    for both fb and twitter.
    """
    logout_user()
    return redirect(url_for("main.index"))

def poster_delete(post):
    if post.doc == None:
        logging.info('file path for id {:d} is None'.format(post.id))
        return

    logging.info('file path is {:s}'.format(post.doc))

    try:
        os.remove(post.doc)
    except:
        return AttributeError

    logging.info('file deletion {:s} is success'.format(post.doc))
    return

def poster_create(post, path, f):
    filename = 'tactification_' + str(post.id) + f.filename
    absolute_path = os.path.join(path, filename)
    logging.info('poster_create path: {:s} filename: {:s}'.format(path, absolute_path))

    f.save(absolute_path)
    uploaded_file_url = url_for("main.download_file", id=post.id, filename=filename)
    post.doc = absolute_path 
    post.url = uploaded_file_url
    post.show()
    return True

def poster_update(post, path, f):
    filename = 'tactification_' + str(post.id) + f.filename

    try:
        # Check if file already exists.
        if (os.path.exists(post.doc) and os.path.isfile(post.doc) is False):
            raise NameError
        #remove the current file
        os.remove(post.doc)
        #add new file.
        absolute_path = os.path.join(path, filename)
        logging.info('poster_update path: {:s} filename: {:s}'.format(path, absolute_path))
        f.save(absolute_path)
    except:
        return False

    uploaded_file_url = url_for("main.download_file", id=post.id, filename=filename)
    post.doc = absolute_path 
    post.url = uploaded_file_url
    post.show()
    return True

@auth.route("/writeposters", methods=["GET", "POST"])
@login_required
@permission_required(Permission.WRITE_ARTICLES)
def writeposters():
    posterform = PosterCreateForm()

    if posterform.validate_on_submit():
        header = posterform.header.data
        body = posterform.body.data
        description = posterform.desc.data
        tags = posterform.tags.data
        f = posterform.poster.data
        filename = secure_filename(f.filename)

        if filename and allowed_file(filename):
            try:
                #Create the object post of class Post.
                post = Post(body=body, header=header, description=description,
                            tags=tags, post_type=PostType.POSTER)
            except:
                return render_template("error.html", msg="Poster creation failed")

            db.session.add(post)
            db.session.commit()

            path = "{:s}".format(app.config["UPLOAD_FOLDER"])
            print("directory:{:s} id={:s}", path, post.id)
            if poster_create(post, path, f) is False:
                flash("Failed creating file in upload folder")
                return redirect(url_for("auth.writeposters"))

            db.session.add(post)
            db.session.commit()
            tag_cache.add_item(post, 'post')

            flash("Created post")
            return redirect(request.args.get("next") or url_for("main.index"))

        flash("Unacceptable file type")
        return redirect(url_for("auth.writeposters"))

    return render_template("writeposter.html", posterform=posterform)


@auth.route("/editposters/<int:id>", methods=["GET", "POST"])
@login_required
@permission_required(Permission.WRITE_ARTICLES)
def editposters(id):
    #Find the post and get the post form. Return for any errors.
    try:
        post = Post.query.get_or_404(id)
        posterform = PosterEditForm(obj=post)
        posterform.show()
    except:
        print(traceback.format_exc())
        post_err_string = 'ID: {id} not found to edit'
        logging.info(post_err_string.format(id=id))
        return redirect(url_for("auth.writeposters"))

    #Do all the needful while submitting.
    if posterform.validate_on_submit():
        header = posterform.header.data
        body = posterform.body.data
        description = posterform.description.data
        tags = posterform.tags.data
        #Do the needful if form has poster file passed.
        if bool(posterform.poster.data):
            try: 
                f = posterform.poster.data
                filename = secure_filename(f.filename)
                if allowed_file(filename) == False:
                    raise NotImplemented
            except:
                posterform.show()
                post_err_string = 'filename: {filename} has issues'
                logging.info(post_err_string.format(filename=filename))
                return redirect(url_for("auth.writeposters"))

        #Update the post field in the db.
        old_tags = post.tags
        try:
            post.body = body
            post.header = header
            post.description = description
            post.tags = tags
            post.post_type = PostType.POSTER
            if bool(posterform.poster.data):
                path = "{:s}".format(app.config["UPLOAD_FOLDER"])
                poster_update(post, path, f)
        except:
            msg = "Poster editing failed: {:s}".format(sys.exc_info()[0])
            return render_template("error.html", msg=msg)

        db.session.add(post)
        db.session.commit()
        tag_cache.update_item(post, old_tags, 'post')
        flash("Edited post")
        return redirect(
            request.args.get("next")
            or url_for("main.post", id=post.id, header=post.header)
        )

    #Populate the form with the object's data.
    posterform.populate_obj(post)
    return render_template("editposter.html", posterform=posterform)

@auth.route("/deleteposters/<int:id>", methods=["GET", "POST"])
@login_required
@permission_required(Permission.WRITE_ARTICLES)
def deleteposters(id):
    logging.info('Deleting post: {:d}'.format(id))
    try:
        post = Post.query.get_or_404(id)
    except:
        msg = "Poster deletion failed"
        return render_template("error.html", msg=msg)

    tag_cache.remove_item(post, 'post')
    poster_delete(post)
    db.session.delete(post)
    db.session.commit()

    logging.info('file deletion {:s} from db is success'.format(post.doc))
    return redirect(request.args.get("next") or url_for("main.index"))

@auth.route("/writetrivias", methods=["GET", "POST"])
@login_required
@permission_required(Permission.WRITE_ARTICLES)
def writetrivias():
    triviaform = TriviaCreateForm()

    if triviaform.validate_on_submit():
        header = triviaform.header.data
        body = triviaform.body.data
        tags = triviaform.tags.data
        date = triviaform.date.data
        url = triviaform.url.data

        try:
            # Create the object trivia of class Post with PostType.TRIVIA.
            trivia = Trivia(body=body, header=header,
                            tags=tags, date=date, #url=url,
                            post_type=PostType.TRIVIA)
        except Exception as e:
            logging.error(f"Error occurred while creating trivia: {e}")
            traceback.print_exc()
            return render_template("error.html", msg="Trivia creation failed")

        db.session.add(trivia)
        db.session.commit()
        tag_cache.add_item(trivia, 'trivia')

        flash("Created trivia")
        return redirect(request.args.get("next") or url_for("main.index"))

    return render_template("writetrivia.html", triviaform=triviaform)

@auth.route("/edittrivias/<int:id>", methods=["GET", "POST"])
@login_required
@permission_required(Permission.WRITE_ARTICLES)
def edittrivias(id):
    try:
        trivia = Trivia.query.get_or_404(id)
        triviaform = TriviaEditForm(obj=trivia)
    except:
        print(traceback.format_exc())
        trivia_err_string = 'ID: {id} not found to edit'
        logging.info(trivia_err_string.format(id=id))
        return redirect(url_for("auth.writetrivias"))

    if triviaform.validate_on_submit():
        header = triviaform.header.data
        body = triviaform.body.data
        tags = triviaform.tags.data
        date = triviaform.date.data
        url = triviaform.url.data

        old_tags = trivia.tags
        try:
            trivia.body = body
            trivia.header = header
            trivia.tags = tags
            trivia.date = date
            #trivia.url = url
        except:
            msg = "Trivia editing failed: {:s}".format(sys.exc_info()[0])
            return render_template("error.html", msg=msg)
        
        db.session.add(trivia)
        db.session.commit()
        tag_cache.update_item(trivia, old_tags, 'trivia')
        flash(f"Edited trivia with ID: {trivia.id}")
        return redirect(
            request.args.get("next")
            or url_for("main.trivia", id=trivia.id, header=trivia.header)
        )
    
    triviaform.populate_obj(trivia)
    return render_template("edittrivia.html", triviaform=triviaform)

@auth.route("/deletetrivias/<int:id>", methods=["GET", "POST"])
@login_required
@permission_required(Permission.WRITE_ARTICLES)
def deletetrivias(id):
    logging.info('Deleting trivia: {:d}'.format(id))
    try:
        trivia = Trivia.query.get_or_404(id)
    except:
        msg = "Trivia deletion failed"
        return render_template("error.html", msg=msg)

    tag_cache.remove_item(trivia, 'trivia')
    db.session.delete(trivia)
    db.session.commit()

    return redirect(request.args.get("next") or url_for("main.index"))
