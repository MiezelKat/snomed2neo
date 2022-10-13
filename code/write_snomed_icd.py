import pandas as pd
import numpy as np

mimic = "/mimic-preprocessed/"
snomedlocation = "/snomed+icd_vocab/"

from neo4j import GraphDatabase


class __Neo4jConnection:
    
    def __init__(self, uri, user, pwd, db):
        self.__uri = uri
        self.__user = user
        self.__pwd = pwd
        self.__driver = None
        self.db = db
        try:
            self.__driver = GraphDatabase.driver(self.__uri, auth=(self.__user, self.__pwd))
        except Exception as e:
            print("Failed to create the driver:", e)
        
    def close(self):
        if self.__driver is not None:
            self.__driver.close()
        
    def query(self, query, parameters=None, return_response = True):
        assert self.__driver is not None, "Driver not initialized!"
        session = None
        response = None
        try: 
            session = self.__driver.session(database=self.db) if self.db is not None else self.__driver.session() 
            response = list(session.run(query, parameters))
        except Exception as e:
            print("Query failed:", e)
        finally: 
            if session is not None:
                session.close()
        if return_response:
            return response

def create_neo4j_connection(neo_usr, neo_pwd, neo_host, neo_bolt, neo_db ):

    n4j_bolt_url = f"bolt://{neo_host}:{neo_bolt}"

    n4j_conn = __Neo4jConnection(uri=n4j_bolt_url, 
                            user=neo_usr,              
                            pwd=neo_pwd, 
                            db = neo_db)

    return n4j_conn

def add_concepts(n4j, concepts, label_col):
    for label in concepts[label_col].unique():
        print("write concepts of domain " + label + "...")
        query = f'''
            UNWIND $rows AS row
            MERGE (a:Concept:{label} {{
                                concept_id: row.concept_id, 
                                name: row.concept_name, 
                                vocabulary: row.vocabulary_id, 
                                code: row.concept_code,
                                class: row.concept_class_id}})
            RETURN count(*) as total
            '''
        n = n4j.query(query, parameters = {'rows': concepts[concepts[label_col] == label].to_dict("records")})
        print("     ... wrote " + str(n) + " nodes of domain " + label)

def add_concept_relationships(n4j, rels):

    # is a:
    # print("write 'Is a' relationships...")
    
    # query_isa = '''
    #         UNWIND $rows AS row
    #         MATCH (c1:Concept {concept_id: row.concept_id_1})
    #         MATCH (c2:Concept {concept_id: row.concept_id_2})
    #         MERGE (c1)-[:IS_A]->(c2)
    #         RETURN count(*) as total
    #         '''
    # n = n4j.query(query_isa, parameters = {'rows': rels[rels.relationship_id == "Is a"].to_dict("records")})
    # print("     ... wrote " + str(n) + " is a rel.")
    
    # subsumes:
    print("write 'Subsumes' relationships...")
    
    query_subsumes = '''
            UNWIND $rows AS row
            MATCH (c1:Concept {concept_id: row.concept_id_1})
            MATCH (c2:Concept {concept_id: row.concept_id_2})
            MERGE (c1)-[:SUBSUMES]->(c2)
            RETURN count(*) as total
            '''
    n = n4j.query(query_subsumes, parameters = {'rows': rels[rels.relationship_id == "Subsumes"].to_dict("records")})
    print("     ... wrote " + str(n) + " subsumes rel.")
    
    # associations
    print("write other relationships...")
    rels_association = rels[~(rels.relationship_id.isin(["Subsumes", "Is a"]))]

    for rel_id in rels_association.relationship_id.unique():
        # rel_id_masked = rel_id.replace(" ", ".")
        print("write other " + rel_id)
    
        query_association = f'''
                UNWIND $rows AS row
                MATCH (c1:Concept {{concept_id: row.concept_id_1}})
                MATCH (c2:Concept {{concept_id: row.concept_id_2}})
                MERGE (c1)-[:ASSOCIATION{{type: '{rel_id}' }}]->(c2)
                RETURN count(*) as total
                '''
        n = n4j.query(query_association, parameters = {'rows': rels_association[rels_association.relationship_id == rel_id].to_dict("records")})
        print("     ... wrote " + str(n) + " other rel. of id " + rel_id)

def main():
    print("Start script to write SNOMED and ICD-9 to Neo4j...")
    n4j = create_neo4j_connection(neo_usr = "neo4j", neo_pwd = "passw0rd", 
        neo_host = "snomed2neo_neo", 
        neo_db = "neo4j", 
        neo_bolt  = 7687)

    # load data
    print("load data ...")
    concept = pd.read_csv(snomedlocation + "CONCEPT.csv", sep="\t", low_memory=False)
    concept_rel = pd.read_csv(snomedlocation + "CONCEPT_RELATIONSHIP.csv", sep="\t", low_memory=False)

    print("filter relevant concepts and relationships ...")
    #filter jusr snomed and icd9 concepts
    concept_filt = concept[concept.vocabulary_id.isin(["SNOMED","ICD9CM","ICD9Proc"])]
    # there is one entry with a NA name: replace it
    concept_filt = concept_filt.fillna("")
    # filter relationships
    concept_rel_filt = concept_rel[(concept_rel.concept_id_1.isin(concept_filt.concept_id)) & (concept_rel.concept_id_2.isin(concept_filt.concept_id))]

    # remove '.' from icd codes:
    print("remove '.' from icd-9 codes (for compatability with MIMIC)")
    concept_filt.concept_code = concept_filt.apply(lambda r: r.concept_code.replace(".", "") if r.vocabulary_id != "SNOMED" else r.concept_code, axis = 1)

    print("Make domain ids suitable labels for neo4j (remove space)")
    concept_filt.domain_id = concept_filt.domain_id.apply(lambda l: l.replace(" ","_"))

    print("neo4j constraints ...")
    n4j.query('CREATE CONSTRAINT concept IF NOT EXISTS ON (c:Concept) ASSERT c.concept_id IS UNIQUE')

    # add_concepts(n4j, concept_filt, label_col = "domain_id")

    add_concept_relationships(n4j, concept_rel_filt)


if __name__ == "__main__":
    main()