app="docker.tactification"
docker build -t ${app} .
docker run -d -p 80:80 -v /etc/nginx/conf.d/nginx.conf:/home/ubuntu/tactification/nginx.conf ${app}
