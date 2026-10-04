"""
Public newsletter routes: subscribe, confirm (double opt-in), unsubscribe.
"""
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request
from app import app, db
from app.models import NewsletterSubscriber
from app.brevo import send_email
from . import newsletter
from .forms import SubscribeForm


@newsletter.route("/subscribe", methods=["POST"])
def subscribe():
    form = SubscribeForm()
    if not form.validate_on_submit():
        flash("Please enter a valid email address.", "danger")
        return redirect(request.referrer or url_for("main.index"))

    email = form.email.data.strip().lower()
    subscriber = NewsletterSubscriber.query.filter_by(email=email).first()

    if subscriber and subscriber.confirmed and subscriber.active:
        flash("You're already subscribed.", "info")
        return redirect(request.referrer or url_for("main.index"))

    if subscriber is None:
        subscriber = NewsletterSubscriber(
            email=email, token=NewsletterSubscriber.generate_token()
        )
        db.session.add(subscriber)
    else:
        # Re-subscribing (or a prior confirm email never arrived) -- rotate
        # the token so any old emailed link stops working.
        subscriber.token = NewsletterSubscriber.generate_token()
        subscriber.active = True
    db.session.commit()

    confirm_url = url_for("newsletter.confirm", token=subscriber.token, _external=True)
    try:
        send_email(
            to_email=subscriber.email,
            subject="Confirm your subscription to Tactification",
            html_content=render_template("newsletter/confirm_email.html", confirm_url=confirm_url),
        )
    except Exception:
        app.logger.exception("Failed to send newsletter confirmation to %s", subscriber.email)
        flash("Something went wrong sending the confirmation email. Please try again later.", "danger")
        return redirect(request.referrer or url_for("main.index"))

    flash("Check your inbox to confirm your subscription.", "success")
    return redirect(request.referrer or url_for("main.index"))


@newsletter.route("/confirm/<token>")
def confirm(token):
    subscriber = NewsletterSubscriber.query.filter_by(token=token).first_or_404()
    subscriber.confirmed = True
    subscriber.active = True
    subscriber.confirmed_at = datetime.utcnow()
    db.session.commit()
    flash("Subscription confirmed. Thanks for joining!", "success")
    return redirect(url_for("main.index"))


@newsletter.route("/unsubscribe/<token>")
def unsubscribe(token):
    subscriber = NewsletterSubscriber.query.filter_by(token=token).first_or_404()
    subscriber.active = False
    db.session.commit()
    flash("You've been unsubscribed.", "info")
    return redirect(url_for("main.index"))
