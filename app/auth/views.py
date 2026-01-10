"""
All custom login and logout apis are defined here.
"""
import os
import sys
import traceback
import logging
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
from app.auth import auth
from app.models import User, Permission, Role, Post, PostType, Trivia
from werkzeug.utils import secure_filename
from app.auth.forms import LoginForm, PosterCreateForm, PosterEditForm, TriviaCreateForm, TriviaEditForm
from app.auth.decorators import permission_required
from app.auth.utils import allowed_file


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

    db.session.delete(trivia)
    db.session.commit()

    return redirect(request.args.get("next") or url_for("main.index"))
