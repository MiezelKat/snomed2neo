#!/bin/bash

docker-compose build

# start docker compose
docker-compose up -d

# wait for neo4j to be up

neo4j_host_name="localhost"
echo "neo4j host: $neo4j_host_name"

status_code=$(curl --write-out %{http_code} --silent --output /dev/null $neo4j_host_name:7474)
echo "Waiting for Neo4J to start (status $status_code)"

while (( $status_code < 200 )) || (( $status_code >= 300 )) ;
do
    sleep 5
    status_code=$(curl --write-out %{http_code} --silent --output /dev/null $neo4j_host_name:7474)
    echo "Still waiting for Neo4J to start (status $status_code)"
done
echo "Neo4j started up. Writing data now..."

# start the script
docker exec -it snomed2neo_py python /app/write_snomed_icd9.py