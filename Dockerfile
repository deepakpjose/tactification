FROM tiangolo/uwsgi-nginx-flask:python3.8

ARG SECRET_KEY="hello world"
ENV CSRF_KEY=${SECRET_KEY}

ENV STATIC_URL /static
ENV STATIC_PATH /var/www/app/static
ENV UWSGI_INI  /var/www/app.ini
ENV PYTHONPATH=/var/www
ENV SECRET_KEY=$CSRF_KEY
ENV APP_PATH=/var/www/app

COPY ./requirements.txt /var/www/requirements.txt
RUN echo "csrf key is $CSRF_KEY"

RUN pip install -r /var/www/requirements.txt

COPY ./nginx.conf /etc/nginx/nginx.conf
COPY ./app /var/www/app
COPY ./app.ini /var/www/app.ini
COPY ./manage.py /var/www/manage.py
COPY ./wsgi.py /var/www/wsgi.py
COPY ./conf.d.nginx.conf /etc/nginx/conf.d/nginx.conf
COPY ./upload.conf /etc/nginx/conf.d/upload.conf
COPY ./nginx.conf /app/nginx.conf
