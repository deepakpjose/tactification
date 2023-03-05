from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired
from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    SubmitField,
    FileField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo
from wtforms import ValidationError, validators


class PosterCreateForm(FlaskForm):
    header = StringField("Header", [validators.Length(min=1, max=255)])
    desc = TextAreaField("Description", [validators.Length(min=1, max=500)])
    body = TextAreaField(
        "Body", [validators.Length(min=1)], render_kw={"rows": 10, "cols": 81}
    )
    tags = StringField("Tags", [validators.Length(min=1, max=255)])
    poster = FileField("Image File", validators=[FileRequired()])
    submit = SubmitField("Submit")


class LoginForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[DataRequired(), Length(1, 64), Email()],
        render_kw={"class": "form-control", "placeholder": "abc@example.com"},
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired()],
        render_kw={"class": "form-control", "placeholder": "Password"},
    )
    remember_me = BooleanField("Keep me logged in")
    submit = SubmitField(
        "Sign In",
        render_kw={"style": "background-color:#007bff", "class": "form-control"},
    )
