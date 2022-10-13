#!/bin/bash

# start docker compose
docker-compose up -d

# wait for neo4j to be up

neo4j_host_name="localhost"
echo "neo4j host: $neo4j_host_name"

status_code=$(curl --write-out %{http_code} --silent --output /dev/null $neo4j_host_name:7474)
echo "Site status changed to $status_code"

while (( $status_code < 200 )) || (( $status_code >= 300 )) ;
do
    sleep 3
    status_code=$(curl --write-out %{http_code} --silent --output /dev/null $neo4j_host_name:7474)
    echo "Site status changed to $status_code"
done

docker exec -it snomed2neo_py jupyter lab --port 8888 --ip 0.0.0.0 --allow-root

# echo "starting py script"
# docker exec -it py_experiment python main.py 