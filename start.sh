app="docker.tactification"
docker build --build-arg SECRET_KEY=$1 -t ${app} .
docker run -d -p 80:80 -v insidecode:/var/www/app/docs ${app}
