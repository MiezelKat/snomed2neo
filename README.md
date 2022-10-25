# snomed2neo
A small dockerized program to write the SNOMED CT and ICD-9 vocabularies to a neo4j database.

## What you'll need

1. The code in this repository
3. Docker installed and running on your computer
2. The SNOMED CT and ICD-9 CM vocabularies from [Athena](https://athena.ohdsi.org/)

## Downloading the Athnea Vocabularies

Steps:
1. Visit [Athena](https://athena.ohdsi.org/vocabulary/list)
2. Login or create an account
3. Download both the 'SNOMED' and 'ICD9CM' vocabularies from Athena.
4. Place the following files in the 'vocabularies' folder: 
    * CONCEPT.csv
    * CONCEPT_CLASS.csv
    * CONCEPT_RELATIONSHIP.csv
    * RELATIONSHIP.csv

## Running the tool 

In the command line, navigate to the main folder and run

`sh start_docker_experiment.sh`

The script will do the following:
1. Build the docker containers `snomed2neo_neo` (The neo4j database host) and `snomed2neo_py` (a host to run python scripts to process the SNOMED data and write it to Neo4J)
2. Start up both containers.
3. Run the `code/write_snomed_icd9.py` script from the `snomed2neo_py` container. This scripts prompts you to make the following decisions:
    a. If additionally to the SNOMED vocabulary, you want to write ICD-9 CM
    b. If you want to include association relationships of the SNOMED hierarchy.
Running the whole script can take up to 5 minutes.

After the script is done, navigate to `http://localhost:7474` to start the Neo4j browser. Have fun exploring SNOMED and ICD9.

## Cleaning up

After you are done with exploring SNOMED in Neo4J, you can clean up the docker containers. You can use the `clean_docker.sh` script by running:

`sh clean_docker.sh`

It will:
* Stop the two docker containers for neo4j and the python script to load the data. 
* Remove the stopped containers.
* Remove the `.neo4j` folder that stores the database data.