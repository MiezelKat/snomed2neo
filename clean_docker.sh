echo "stop containers"
docker stop snomed2neo_py
docker stop snomed2neo_neo

echo "remove containers"
docker rm snomed2neo_py
docker rm snomed2neo_neo

echo "remove neo4j database filess"
rm -rf .neo4j