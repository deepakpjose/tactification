import logging
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

#Ensure the fields name are same as in the fields in the Models for Post.
class PosterCreateForm(FlaskForm):
    header = StringField("Header", [validators.Length(min=1, max=255)])
    desc = TextAreaField("Image Caption", [validators.Length(min=1, max=500)])
    body = TextAreaField(
        "Body", [validators.Length(min=1)], render_kw={"rows": 10, "cols": 81}
    )
    tags = StringField("Tags", [validators.Length(min=1, max=255)])
    poster = FileField("Image File", validators=[FileRequired()])
    submit = SubmitField("Submit")

class PosterEditForm(FlaskForm):
    header = StringField("Header", [validators.Length(min=1, max=255)])
    description = TextAreaField("Image Caption", [validators.Length(min=1, max=500)])
    body = TextAreaField(
        "Body", [validators.Length(min=1)], render_kw={"rows": 10, "cols": 81}
    )
    tags = StringField("Tags", [validators.Length(min=1, max=255)])
    poster = FileField("Image File")
    submit = SubmitField("Submit")

    def show(self):
        header_data = 'header: {data}'
        logging.info(header_data.format(data=self.header.data)) 
        description_data = 'caption: {data}'
        logging.info(description_data.format(data=self.description.data))
        tags_data = 'tags: {data}'
        logging.info(tags_data.format(data=self.tags.data))
        if bool(self.poster.data):
            poster_fields = 'poster: {filename}'
            logging.info(poster_fields.format(filename=self.poster.data.filename))
        return

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
