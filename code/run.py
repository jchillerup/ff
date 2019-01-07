from oc import analyze_company, fill_caches_from_graphene


if __name__ == '__main__':
    print("Loading cache")
    fill_caches_from_graphene()

    print("Analyzing company")
    analyze_company("pl", "0000363634", 3)
