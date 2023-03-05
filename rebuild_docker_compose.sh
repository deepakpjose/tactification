docker ps | grep techtok_insidecode | awk '{ print $1;}' | xargs docker kill
docker images | grep none | awk '{ print $3; }' | xargs docker rmi -f
docker ps | grep techtok_tactification | awk '{ print $1;}' | xargs docker kill
docker images | grep none | awk '{ print $3; }' | xargs docker rmi -f
docker-compose build
docker-compose -f docker-compose.yml up -d
docker_id=`docker ps | grep techtok_backend | awk '{ print $1; }'`
docker exec -it $docker_id bash 
