from py2neo import Graph, Relationship, NodeMatcher
from py2neo.ogm import GraphObject, Property, RelatedFrom, RelatedTo

def debug_create_people(graph):
    people = []
    relations = []
    
    for x in range(10):
        p = Person()
        p.name = "Alice %d" % x
        people.append(p)

        if len(people) > 0:
            r = Relationship(Graph.cast(p), "KNOWS", Graph.cast(people[-1]))
            relations.append(r)
    
    print(graph.create(people))
    print(graph.create(relations))

def list_nodes(graph):
    print("NODES: ")
    matcher = NodeMatcher(graph)

    for node in matcher.match():
        print("  ", node)


def get_person(graph, name):
    matcher = NodeMatcher(graph)
    match = matcher.match("Person", name=name)
    
    if len(match) > 0:
        return match.first()
    else:
        return None
    
