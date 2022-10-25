import pandas as pd
import numpy as np
from simple_term_menu import TerminalMenu

snomedlocation = "../vocabularies/"

from neo4j import GraphDatabase

# adjust the following in case of not running with the provided docker environment
neo_usr = "neo4j" 
neo_pwd = "passw0rd"
neo_host = "snomed2neo_neo" 
# neo_host = "localhost" # if not running with docker, but e.g., neo4j Desktop 
neo_db = "neo4j"
neo_bolt_port  = 7687

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

def preprocess_concept(concept_raw, concept_class_raw):
    # combine with human readable terms
    concept = concept_raw.merge(concept_class_raw[["concept_class_id", "concept_class_name"]], how = "left", on = "concept_class_id")
    # filter vocabs
    concept = concept[concept.vocabulary_id.isin(["SNOMED","ICD9CM"])]

    # filter concept domains
    concept = concept[concept.domain_id.isin(["Condition","Measurement", "Observation", "Procedure"])]

    return concept

def preprocess_kg_relationships(relationship_raw, concept_rel_raw, sm_concept_ids):
    # filter relationships that are relevant:
    relationship_sm = relationship_raw[(relationship_raw.relationship_id.isin(["Is a","Subsumes"])) | (relationship_raw.relationship_name.str.contains("\(SNOMED\)"))]

    # filter the concept-concept relationships for snomed graph
    concept_rel_sm = concept_rel_raw[concept_rel_raw.relationship_id.isin(relationship_sm.relationship_id)]

    concept_rel_sm[(concept_rel_sm.concept_id_1.isin(sm_concept_ids)) & (concept_rel_sm.concept_id_2.isin(sm_concept_ids))]

    # merge in names
    concept_rel_sm = concept_rel_sm.merge(relationship_sm[["relationship_id", "relationship_name"]], how = "left", on = "relationship_id")

    return concept_rel_sm
    

def preprocess_icd(concept_rel_raw, icd_concept_ids, sm_concept_ids):
    concept_rel_icd_sm = concept_rel_raw[
    (concept_rel_raw.concept_id_1.isin(icd_concept_ids)) &
    (concept_rel_raw.concept_id_2.isin(sm_concept_ids))]

    return concept_rel_icd_sm

def add_concepts(n4j, concepts, node_label, label_col):
    print("Add concepts for main label " + node_label)
    for label in concepts[label_col].unique():
        print("second label: " + label)
        query = f'''
            UNWIND $rows AS row
            MERGE (a:{node_label}:{label} {{
                                concept_id: row.concept_id,
                                concept_code: row.concept_code,
                                name: row.concept_name, 
                                class_id: row.concept_class_id,
                                class_name: row.concept_class_name}})
            RETURN count(*) as total
            '''
        n = n4j.query(query, parameters = {'rows': concepts[concepts[label_col] == label].to_dict("records")})
        print("wrote " + str(n) + " nodes of domain " + label)

def add_icd_to_snomed_concept_relationships(n4j, rels):

    pd.options.mode.chained_assignment = None  

    # is a:
    print("write ICD-SM relationships...")
    
    query_icd_sm = '''
            UNWIND $rows AS row
            MATCH (c1:ICD9_Concept {concept_id: row.concept_id_1})
            MATCH (c2:SNOMED_Concept {concept_id: row.concept_id_2})
            MERGE (c1)-[:ICD_TO_SNOMED]->(c2)
            RETURN count(*) as total
            '''
    n = n4j.query(query_icd_sm, parameters = {'rows': rels.to_dict("records")})
    print("     ... wrote " + str(n) + " is a rel.")


def add_snomed_concept_relationships(n4j, rels, add_association):

    # is a:
    print("write 'Is a' relationships...")
    
    query_isa = '''
            UNWIND $rows AS row
            MATCH (c1:SNOMED_Concept {concept_id: row.concept_id_1})
            MATCH (c2:SNOMED_Concept {concept_id: row.concept_id_2})
            MERGE (c1)-[:IS_A]->(c2)
            RETURN count(*) as total
            '''
    n = n4j.query(query_isa, parameters = {'rows': rels[rels.relationship_id == "Is a"].to_dict("records")})
    print("     ... wrote " + str(n) + " is a rel.")
    
    # subsumes:
    print("write 'Subsumes' relationships...")
    
    query_subsumes = '''
            UNWIND $rows AS row
            MATCH (c1:SNOMED_Concept {concept_id: row.concept_id_1})
            MATCH (c2:SNOMED_Concept {concept_id: row.concept_id_2})
            MERGE (c1)-[:SUBSUMES]->(c2)
            RETURN count(*) as total
            '''
    n = n4j.query(query_subsumes, parameters = {'rows': rels[rels.relationship_id == "Subsumes"].to_dict("records")})
    print("     ... wrote " + str(n) + " subsumes rel.")
    
    if add_association:
        # associations
        print("write other relationships...")
        rels_association = rels[~(rels.relationship_id.isin(["Subsumes", "Is a"]))]

        for rel_id in rels_association.relationship_id.unique():
            # rel_id_masked = rel_id.replace(" ", ".")
            print("write other " + rel_id)
        
            query_association = f'''
                    UNWIND $rows AS row
                    MATCH (c1:SNOMED_Concept {{concept_id: row.concept_id_1}})
                    MATCH (c2:SNOMED_Concept {{concept_id: row.concept_id_2}})
                    MERGE (c1)-[:ASSOCIATION{{type: '{rel_id}' }}]->(c2)
                    RETURN count(*) as total
                    '''
            n = n4j.query(query_association, parameters = {'rows': rels_association[rels_association.relationship_id == rel_id].to_dict("records")})
            print("     ... wrote " + str(n) + " other rel. of id " + rel_id)


def main():
    print("Start script to write SNOMED and ICD-9 to Neo4j...")
    n4j = create_neo4j_connection(neo_usr = neo_usr, neo_pwd = neo_pwd, 
        neo_host = neo_host, 
        neo_db = neo_db, 
        neo_bolt  = neo_bolt_port)

    print("Do you want to write just SNOMED data or also ICD-9 Data?")
    options = ["just SNOMED", "SNOMED and ICD-9"]

    terminal_menu = TerminalMenu(options, accept_keys=("enter", "alt-d", "ctrl-i"))
    menu_entry_index = terminal_menu.show()

    print("You selected: " + options[menu_entry_index])
    add_icd = menu_entry_index == 1
        

    print("In the SNOMED CT, do you want to include association relationships?")
    options = ["just 'Is a' and 'Subsumes' relationships", "all SNOMED relationships"]

    terminal_menu = TerminalMenu(options, accept_keys=("enter", "alt-d", "ctrl-i"))
    menu_entry_index = terminal_menu.show()

    print("You selected: " + options[menu_entry_index])
    add_association = menu_entry_index == 1

    # load data
    print("load vocabulary data ...")
    concept_raw = pd.read_csv(snomedlocation + "CONCEPT.csv", sep="\t", low_memory=False)
    concept_rel_raw = pd.read_csv(snomedlocation + "CONCEPT_RELATIONSHIP.csv", sep="\t", low_memory=False)
    relationship_raw = pd.read_csv(snomedlocation + "RELATIONSHIP.csv", sep="\t", low_memory=False) # mapping to human readable naming and reverse relationship
    concept_class_raw = pd.read_csv(snomedlocation + "CONCEPT_CLASS.csv", sep="\t", low_memory=False)

    concept = preprocess_concept(concept_raw=concept_raw, concept_class_raw=concept_class_raw)

    print("filter relevant concepts and relationships ...")
    concept_sm = concept[concept.vocabulary_id.isin(["SNOMED"])]
    concept_icd = concept[concept.vocabulary_id.isin(["ICD9CM"])]
    concept_icd.concept_code = concept_icd.apply(lambda r: r.concept_code.replace(".", ""), axis = 1)

    concept_rel_sm = preprocess_kg_relationships(relationship_raw=relationship_raw, concept_rel_raw=concept_rel_raw, sm_concept_ids = concept_sm.concept_id)
    concept_rel_icd_sm = preprocess_icd(concept_rel_raw=concept_rel_raw, icd_concept_ids=concept_icd.concept_id, sm_concept_ids=concept_sm.concept_id)

    print("neo4j constraints ...")
    n4j.query('CREATE CONSTRAINT snomed_concept_id IF NOT EXISTS ON (c:SNOMED_Concept) ASSERT c.concept_id IS UNIQUE')
    n4j.query('CREATE CONSTRAINT snomed_concept_code IF NOT EXISTS ON (c:SNOMED_Concept) ASSERT c.concept_code IS UNIQUE')
    if add_icd == 1:
        n4j.query('CREATE CONSTRAINT icd_concept_id IF NOT EXISTS ON (c:ICD9_Concept) ASSERT c.concept_id IS UNIQUE')
        n4j.query('CREATE CONSTRAINT icd_concept_code IF NOT EXISTS ON (c:ICD9_Concept) ASSERT c.concept_code IS UNIQUE')

    print("add SNOMED concepts ...")
    add_concepts(n4j, concepts = concept_sm, node_label = "SNOMED_Concept", label_col = "domain_id")

    if add_icd == 1:
        print("add ICD-9 concepts ...")
        add_concepts(n4j, concepts = concept_icd, node_label = "ICD9_Concept", label_col = "domain_id")
        add_icd_to_snomed_concept_relationships(n4j, concept_rel_icd_sm)

    print("add SNOMED relationships ...")
    add_snomed_concept_relationships(n4j, concept_rel_sm, add_association)

    print("Done loading SNOMED to Neo4J. Navigate to http://localhost:7474 to browse.")


if __name__ == "__main__":
    main()