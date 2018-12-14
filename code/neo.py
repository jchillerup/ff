import json

from py2neo import Graph, Relationship, NodeMatcher
from py2neo.ogm import GraphObject, Property, RelatedFrom, RelatedTo

from util import *
from secrets import secrets

graph = Graph(secrets["graphene_endpoint"], user=secrets["graphene_user"], password=secrets["graphene_pass"], bolt = False)

class Company(GraphObject):
    __primarykey__ = "key"

    scraped = Property()
    key = Property()
    name = Property()
    jurisdiction = Property()
    number = Property()
    external_reference = Property()
    raw_data = Property()

    directors = RelatedFrom("Person", "IN_DIRECTION")

    def from_oc(oc):
        c = Company()
        c.name = oc["name"]
        c.number = oc["company_number"]
        c.jurisdiction = oc["jurisdiction_code"] 
        c.key = "%s%s" % (c.jurisdiction, c.number)
        c.raw_data = json.dumps(oc)

        return c

        
class Person(GraphObject):
    __primarykey__ = "name"

    scraped = Property()
    name = Property()
    raw_data = Property()
    
    directing = RelatedTo("Company")

    def from_oc(oc):
        self.raw_data = json.dumps(oc)

    

class Nexus(GraphObject):
    type = Property()
    url = Property()


if __name__ == '__main__':
    list_nodes(graph)

    # debug_create_people(graph)
    
