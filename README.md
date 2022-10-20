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
3. Download both the 'SNOMED' and 'ICD9CM' Vocabularies
4. Place the following files in the 'snomed+icd_vocab' folder: 
    * CONCEPT.csv
    * CONCEPT_CLASS.csv
    * CONCEPT_RELATIONSHIP.csv
    * RELATIONSHIP.csv

## Running the tool 

In the command line, navigate to the main folder and run

`sh start_docker_experiment.sh`

After the script is done, navigate to `localhost:7474` to start the Neo4j browser. Have fun exploring SNOMED.
