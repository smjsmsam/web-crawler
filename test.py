import sys
import requests
import lxml


url = "https://www.ics.uci.edu"

if __name__ == "__main__":
    resp = requests.get(url)
    if(resp.status != 200):
        print(resp.status_code)
        sys.exit(1)
    print(resp.status_code)

    tree = lxml.html.fromstring(resp.content)
    links = tree.xpath('//a/@href')
    print(links)
