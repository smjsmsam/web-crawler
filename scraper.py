import re
from urllib.parse import urlparse
import lxml

VISITED = set()
SIMHASHES = list()
SUBDOMAINS = dict()
WORD_FREQ = dict()
LONGEST_PAGE = ["", 0]
BLACKLIST = set()

DOMAINS = [".ics.uci.edu/",
           ".cs.uci.edu/",
           ".informatics.uci.edu/",
           ".stat.uci.edu/"]

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    global VISITED, BLACKLIST
    # TODO:
        # track longest page based on number of words
        # generate total (across domains) list of common words ordered by frequency
    if(url in VISITED or url in BLACKLIST or resp.status != 200):
        print(resp.status + " status at " + resp.url + " : " + resp.error)
        return list()
    
    content = resp.raw_response.content
    tree = lxml.html.fromstring(content)
    links = tree.xpath('//a/@href')

    # TODO:
        # discard fragment part of url
        # track subdomains of uci.edu and number of unique pages in each
            # listed alphabetically
            # format: subdomain, number
    result = list()
    for link in links:
        print(link)
        if is_valid(link):
            result.append(link)
    
    return result

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    global DOMAINS
    
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"] or parsed.hostname not in DOMAINS):
            return False
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise
