FROM tiangolo/uwsgi-nginx-flask:python3.8

# Secrets (SECRET_KEY, YOUTUBE_API_KEY, BREVO_*) are intentionally NOT set
# here as ARG/ENV: that bakes them into the image layers, readable by
# anyone who can pull the image or run `docker history`. They're injected
# at container runtime instead, via docker-compose's `env_file: .env`.

ENV STATIC_URL /static
ENV STATIC_PATH /var/www/app/static
ENV UWSGI_INI  /var/www/app.ini
ENV PYTHONPATH=/var/www
ENV APP_PATH=/var/www/app

COPY ./requirements.txt /var/www/requirements.txt

RUN pip install -r /var/www/requirements.txt

COPY ./nginx.conf /etc/nginx/nginx.conf
COPY ./app /var/www/app
COPY ./app.ini /var/www/app.ini
COPY ./manage.py /var/www/manage.py
COPY ./wsgi.py /var/www/wsgi.py
COPY ./conf.d.nginx.conf /etc/nginx/conf.d/nginx.conf
COPY ./upload.conf /etc/nginx/conf.d/upload.conf
COPY ./nginx.conf /app/nginx.conf
COPY ./db_migrate.py /var/www/db_migrate.py
COPY ./docker_migrate.sh /var/www/docker_migrate.sh
COPY ./seed_social_clubs.py /var/www/seed_social_clubs.py
COPY ./data /var/www/data
