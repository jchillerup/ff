import requests, json
import requests_cache
from datetime import timedelta
from neo import Company, Person, Nexus, graph
from py2neo import Relationship, NodeMatcher
import urllib
from termcolor import colored
import pickle

requests_cache.install_cache(expire_after=timedelta(days=90))
name_cache = dict()
company_cache = dict()

try:
    fp = open('p_or_c.pickle', 'rb')
    p_or_c_cache = pickle.load(fp)
    fp.close()
except:
    p_or_c_cache = dict()


def fill_caches_from_graphene():
    for node in  Person.match(graph):
        name_cache[node.name] = node

    for node in Company.match(graph):
        code = str(node.jurisdiction) + str(node.number)
        company_cache[code] = node


# TODO: return kun hvis der faktisk er edges på noden. Det kan være at det er en leaf node og vi stadig har noget "dybde" tilbage ved anden kørsel
# alternativt kunne man vedligeholde en kø og ikke sætte et firma/person of interest i køen, men måske opdatere depth hvis vi når til det samme firma men har mere depth tilbage

def analyze_person(name, depth, require_strict_name_match=True):
    # Vi slutter søgningen hvis vi allerede har undersøgt personen, eller hvis vi er kommet for dybt
    if depth < 0:
        return;
    
    if name in name_cache and name_cache[name].scraped == True:
        print("%s in cache [%d]" % (name, depth))
        return name_cache.get(name)
    
    sanitized_name = name.replace(" ", "+").lower()

    cur_page = 1
    number_of_pages = 9999

    person_neo = Person()
    person_neo.name = name
    name_cache[name] = person_neo
    graph.create(person_neo)
    
    
    while cur_page < number_of_pages:
        r = requests.get("https://api.opencorporates.com/officers/search?q=%s&page=%d" % (sanitized_name, cur_page))
        # print(r.json())
        number_of_pages = int(r.json()["results"]["total_pages"])

        for officer in r.json()["results"]["officers"]:
            officer = officer["officer"]
            
            if require_strict_name_match and officer["name"] != name:
                continue

            assert officer["name"] == name

            print("  %s --[%s]--> %s" % (officer["name"], officer["position"], officer["company"]["name"]))

            # TODO: Check if the company has already been analyzed
            related_company = analyze_company(officer["company"]["jurisdiction_code"], officer["company"]["company_number"], depth - 1)

            if related_company is not None:
                relation_label = officer["position"]
                relation = Relationship(person_neo.__node__, officer["position"].upper(), related_company.__node__)
                graph.create(relation)
            
        cur_page += 1

    person_neo.scraped = True
    graph.push(person_neo)
    return person_neo


def resolve_company(name):
    page_no = 1
    num_pages = 1
    
    while page_no <= num_pages:
        qs = urllib.parse.urlencode({"q": name, "page": page_no})
        # print("https://api.opencorporates.com/companies/search?%s" % qs)
        r = requests.get("https://api.opencorporates.com/companies/search?%s" % qs).json()

        num_pages = int(r["results"]["total_pages"])

        for company in [x["company"] for x in r["results"]["companies"]]:
            # print(company["name"], name)
            if company["name"].lower() == name.lower():
                return company["jurisdiction_code"], company["company_number"]
        
        page_no += 1

    return None, None

def update_pickle_cache():
    fp = open('p_or_c.pickle', 'wb')
    pickle.dump(p_or_c_cache, fp)
    fp.close()
        
        
def analyze_company(jurisdiction, cvr, depth):
    cvr_shorthand = "%s%s"%(jurisdiction,cvr)
    
    if depth < 0:
        return

    if cvr_shorthand in company_cache and company_cache[cvr_shorthand].scraped == True:
        print("Returning already-scraped company")
        return company_cache.get(cvr_shorthand)

    # get the company
    r = requests.get("https://api.opencorporates.com/companies/%s/%s" % (jurisdiction, cvr))

    company_json_obj = r.json()["results"]["company"]
    company_neo = Company.from_oc(company_json_obj)
    company_cache["%s%s" %(jurisdiction,cvr)] = company_neo
    graph.create(company_neo)

    # API BUG: Nogle gange kan virksomheder optræde som officers, og man kan ikke se om det er
    # et firma eller en person i OCs API.
    for officer in company_json_obj["officers"]:
        officer = officer["officer"]
        print("%s <--[%s]-- %s" % (company_json_obj["name"], officer["position"], officer["name"]))

        person_or_company = p_or_c_cache.get(officer["name"], None)
        while person_or_company != 'p' \
              and person_or_company != 'c' \
                  and person_or_company != 'i':
            person_or_company = input(colored("-> Is %s a person or a company, or should the relation be ignored? p/c/i  " % officer["name"], 'red')).strip()

        # save it in the cache
        p_or_c_cache[officer["name"]] = person_or_company
        update_pickle_cache()
        
        if person_or_company == 'p':
            person = analyze_person(officer["name"], depth - 1)

            if person is not None:
                # Create a relation
                relation_label = officer["position"]
                relation = Relationship(person.__node__, relation_label.upper(), company_neo.__node__)
                graph.create(relation)
                
        elif person_or_company == 'c':
            print("Trying to find company %s" % officer["name"])
            r_jurisdiction, r_cvr = resolve_company(officer["name"])

            if r_cvr is not None:
                print("Found it... analyzing")
                related_company = analyze_company(r_jurisdiction, r_cvr, depth-1)

                if related_company is not None:
                    relation_label = officer["position"]
                    relation = Relationship(related_company.__node__, relation_label.upper(), company_neo.__node__)
                    graph.create(relation)
            else:
                print("Could not find company %s" % officer["name"])

    company_neo.scraped = True
    graph.push(company_neo)
    return company_neo
