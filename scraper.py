import atexit
from itertools import groupby
import re
from urllib.parse import urljoin, urlparse, urldefrag
from lxml import html, etree
import time
from simhash import Simhash, SimhashIndex
import json
from utils import get_logger
import numpy as np


LOGGER = get_logger("SCRAPER")
VISITED = set()
HASH_DICT = {}
HASH_INDEX = SimhashIndex({}, k=3)
SUBDOMAINS = dict()
WORD_FREQ = dict()
LONGEST_PAGE = ["", 0]
LINKS_PARSED = 0
LOADED_DATA = False

BLACKLIST = set()
PATH_COUNT = dict()
MAX_PATH_SEGMENT_COUNT = 200
MAX_PATH_COUNT = 150

DOMAINS = ["ics.uci.edu",
           "cs.uci.edu",
           "informatics.uci.edu",
           "stat.uci.edu"]

STOP_WORDS = ["a", "about", "above", "after", "again", "against", "all",
            "am", "an", "and", "any", "are", "aren", "t", "as", "at",
            "be", "because", "been", "before", "being", "below", "between",
            "both", "but", "by", "can", "not", "cannot", "could",
            "couldn", "did", "didn", "do", "does", "doesn", "doing",
            "don", "down", "during", "each", "few", "for", "from",
            "further", "had", "hadn", "has", "hasn", "have", "haven",
            "having", "he", "d", "ll", "s", "her", "here", "hers",
            "herself", "him", "himself", "his", "how", "i", "if", "in",
            "into", "is", "isn", "it", "its", "itself", "let", "me",
            "more", "most", "mustn", "my", "myself", "no", "nor", "of",
            "off", "on", "once", "only", "or", "other", "ought",
            "our", "ours", "ourselves", "out", "over", "own", "same",
            "shan", "she", "should", "shouldn", "so", "some", "such",
            "than", "that", "the", "their", "theirs", "them", "themselves",
            "then", "there", "these", "they", "this", "those",
            "through", "to", "too", "under", "until", "up", "very",
            "was", "wasn", "we", "what", "when", "where", "which",
            "while", "who", "whom", "why", "with", "won", "would",
            "wouldn", "you", "your", "yours", "yourself", "yourselves"]

BLACKLIST_PATH = ["doku.php", "eppstein/pix"]

def scraper(url, resp):
    global LOGGER
    defragged = urldefrag(url)[0]
    links = extract_next_links(defragged, resp)
    LOGGER.info(f"URL produced {len(links)} links")

    time.sleep(0.5)
    valid_links = []
    for link in links:
        defrag = urldefrag(link)[0]
        if is_valid(defrag) and defrag != url:
            valid_links.append(defrag)
    return valid_links


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
    global VISITED, LONGEST_PAGE, STOP_WORDS, WORD_FREQ, \
        LINKS_PARSED, SUBDOMAINS, HASH_DICT, HASH_INDEX, LOGGER \
    
    if LOADED_DATA == False and len(VISITED) == 0:
        load_data()

    LOGGER.info("Extracting : " + url)

    dequery = urlparse(url.split("?")[0])  # url is already defragged
    parsed = urlparse(url)
    if(url in VISITED):
        LOGGER.info("URL has been visited, skipping")
        return list()

    VISITED.add(url)
    for path in BLACKLIST_PATH:
        if path in parsed.path:
            LOGGER.info("URL in blacklist, skipping")
            return list()
    if check_blacklist(dequery):
        LOGGER.info("URL in blacklist or just added to the blacklist, skipping")
        return list()
    
    if(resp.status != 200):
        LOGGER.info(f"{resp.status} status at {resp.url} : {resp.error}")
        return list()
    
    # VISITED.add(url)

    # avoid crawling large files
    try:
        content = resp.raw_response.content
    except Exception as e:
        LOGGER.info(f"No content: {e}")
        return list()
    byte_count = len(content)
    if byte_count > 10000000:
        # discord says 10MB is a lot
        LOGGER.info(f"File size too large : " + str(byte_count))
        return list()
    if byte_count < 1000:
        # either empty or uselessly small amount of content
        LOGGER.info(f"File size too small : " + str(byte_count))
        return list()
    LOGGER.info("URL has " + str(byte_count) + " bytes")

    # parse with lxml
    text_content = []
    try:
        content = content.strip()
        tree = html.fromstring(content)
        etree.strip_elements(tree, 'script', 'style', 'template', 'meta', 'svg', 'embed', 'object', 'iframe', 'canvas', 'img')
        text_content = tree.text_content()
    except Exception as e:
        # lxml.etree.ParserError: Document is empty usually
        LOGGER.info(f"LXML error: {e}")
        return list()

    # get hash
    current_hash = Simhash(text_content)
    similar_hash = HASH_INDEX.get_near_dups(current_hash)
    if similar_hash:
        HASH_INDEX.add(url, current_hash)
        HASH_DICT[url] = current_hash.value
        LOGGER.info("URL is similar to another")
        return list()
    HASH_INDEX.add(url, current_hash)
    HASH_DICT[url] = current_hash.value
    
    # track longest page based on number of words
    words = text_content.split()
    word_count = len(words)
    if word_count <= 100:
        # probably insignificant data
        return list()
    if word_count > LONGEST_PAGE[1]:
        LONGEST_PAGE = [url, word_count]
    LOGGER.info("URL has " + str(word_count) + " words")
    
    # generate total (across domains) list of common words ordered by frequency
    for word in words:
        word = word.lower()
        if word not in STOP_WORDS and word.isalnum():
            val = WORD_FREQ.get(word)
            if val == None:
                WORD_FREQ[word] = 1
            else:
                WORD_FREQ[word] += 1
    
    # write report every n links parsed
    if LINKS_PARSED % 100 == 0:
        write_report()
    LINKS_PARSED += 1

    # get links
    links = set()
    # links = set([urljoin(url, link) for link in tree.xpath('//a/@href')])

    for link in tree.xpath('//a/@href'):
        try:
            links.add(urljoin(url, link))
        except Exception as e:
            LOGGER.debug(f"Some invalid link {link} with error: {e}.")

    return list(links)


def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    global DOMAINS, SUBDOMAINS
    
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]) or \
            re.match(
                r".*\.(css|js|bmp|gif|img|jpe?g|ico"
                + r"|png|tiff?|mid|mp2|mp3|mp4"
                + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
                + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
                + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
                + r"|epub|dll|cnf|tgz|sha1|docs|docx"
                + r"|thmx|mso|arff|rtf|jar|csv"
                + r"|rm|smil|wmv|swf|wma|zip|rar|gz|htm|css|js"
                + r"|calendar|events|event|date|blog|page|archive"
                + ")$", parsed.path.lower()) \
            or not any(parsed.hostname and parsed.hostname.endswith(domain) for domain in DOMAINS):
            return False
        
        # track subdomains of uci.edu and number of unique pages in each
        if parsed.hostname not in DOMAINS:
            if parsed.hostname not in SUBDOMAINS:
                SUBDOMAINS[parsed.hostname] = set()
            SUBDOMAINS[parsed.hostname].add(url)
        dequery = urlparse(url.split("?")[0])  # url is already defragged
        if is_blacklisted(dequery):
            return False
        return True

    except TypeError:
        print ("TypeError for ", parsed)
        raise


def sorted_frequency(dictionary):
    return dict(sorted(dictionary.items(), key=lambda item: item[1], reverse=True))


def sorted_alphabetical(dictionary):
    return {key: len(dictionary[key]) for key in sorted(dictionary)}

def generate_simhash(url, words):
    global HASH_DICT, HASH_INDEX
    hash = {k:sum(1 for _ in g) for k, g in groupby(sorted(words))}
    
    HASH_INDEX.add(hash)
    HASH_DICT[url] = hash

def check_blacklist(dequery):
    global BLACKLIST, MAX_PATH_COUNT, MAX_PATH_SEGMENT_COUNT, PATH_COUNT
    domain = dequery.netloc
    path = dequery.path.strip("/")
    path_segments = path.split("/") if path else []
    blacklisted = False

    if path_segments and "." in path_segments[-1]:
      path_segments = path_segments[:-1]

    modified_path = domain
    for p in path_segments:
        PATH_COUNT[p] = PATH_COUNT.get(p, 0) + 1
        if PATH_COUNT.get(p, 0) > MAX_PATH_SEGMENT_COUNT:
            BLACKLIST.add(p)
            blacklisted = True
        modified_path += "/" + p
        PATH_COUNT[modified_path] = PATH_COUNT.get(modified_path, 0) + 1
        if PATH_COUNT.get(modified_path, 0) > MAX_PATH_COUNT:
            BLACKLIST.add(modified_path)
            blacklisted = True
    return blacklisted


def is_blacklisted(dequery):
    global BLACKLIST
    domain = dequery.netloc
    path = dequery.path.strip("/")
    path_segments = path.split("/") if path else []
    if path_segments and "." in path_segments[-1]:
      path_segments = path_segments[:-1]
    modified_path = domain
    for p in path_segments:
        if p in BLACKLIST:
            return True
        modified_path += "/" + p
        if modified_path in BLACKLIST:
            return True
    return False


def write_report():
    global VISITED, LONGEST_PAGE, WORD_FREQ,  \
        LINKS_PARSED, SUBDOMAINS, BLACKLIST
    with open("report.txt", 'w') as f:
        f.write(f"Unique Pages: {len(VISITED)}\n")
        f.write("-----------\n")
        f.write(f"Longest Page: {LONGEST_PAGE[0]} with {LONGEST_PAGE[1]} words\n")
        f.write("-----------\n")
        f.write(f"Subdomains: {len(SUBDOMAINS)}\n")
        f.write("-----------\n")
        f.write("List of Subdomains:\n\n")
        subdomain_freq = sorted_alphabetical(SUBDOMAINS)
        for key in subdomain_freq.keys():
            f.write(f"{key}, {subdomain_freq.get(key)}\n")
        f.write("-----------\n")
        f.write(f"50 Most Common Words:\n\n")
        WORD_FREQ = sorted_frequency(WORD_FREQ)
        for key in list(WORD_FREQ.keys())[:50]:
            f.write(f"{key}\n")
    
    with open("longest-page.json", 'w') as f1, \
        open("word-frequencies.json", 'w') as f2, \
        open("subdomains.json", 'w') as f3, \
        open("visited.txt", 'w') as f4, \
        open("simhashes.json", "w") as f5, \
        open("blacklist.txt", "w") as f6:

        if (LONGEST_PAGE[1] != 0):
            json.dump(LONGEST_PAGE, f1)
        json.dump(WORD_FREQ, f2)
        json.dump({k: list(v) for k, v in SUBDOMAINS.items()}, f3)
        for link in VISITED:
            f4.write(link + "\n")
        json.dump(HASH_DICT, f5)
        for link in BLACKLIST:
            f6.write(link + "\n")


def load_data():
    global LONGEST_PAGE, WORD_FREQ, SUBDOMAINS, HASH_DICT, \
      HASH_INDEX, LOADED_DATA, VISITED
    
    LOADED_DATA = True
    print("Loading backup data")

    try:
        with open("visited.txt", "r") as f:
            # load visited from backup file
            for line in f:
                VISITED.add(line.rstrip())
    except FileNotFoundError:
        pass
    
    try:
        # load longest page from backup file
        with open("longest-page.json", "r") as f1:
            LONGEST_PAGE = json.load(f1)
    except FileNotFoundError:
        pass
    except json.JSONDecodeError:
        pass
    
    try:
        # load word frequencies
        with open("word-frequencies.json", "r") as f2:
            WORD_FREQ = json.load(f2)
    except FileNotFoundError:
        pass
    
    try:
        # load subdomains
        with open("subdomains.json", 'r') as f3:
            raw_dict = json.load(f3)
            for subdomain, unique_pages in raw_dict.items():
                SUBDOMAINS[subdomain] = set(unique_pages)
    except FileNotFoundError:
        pass
    
    try:
        # load blacklist
        with open("blacklist.txt", 'r') as f4:
            for link in f4:
                BLACKLIST.add(link.rstrip())
    except FileNotFoundError:
        pass

    try:
        # load simhashes
        with open("simhashes.json", "r") as f5:
            HASH_DICT = dict(json.load(f5))
            HASH_INDEX = SimhashIndex([(url, Simhash(text_content)) for url, text_content in HASH_DICT.items()])
    except FileNotFoundError:
        pass

@atexit.register
def last_report():
    print("Writing the last report\n\n\n")
    write_report()