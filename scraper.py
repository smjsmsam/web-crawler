import re
from utils import get_logger
from urllib.parse import urlparse, urldefrag
from lxml import html

LOGGER = get_logger("SCRAPER")
VISITED = set()
SIMHASHES = list()
SUBDOMAINS = dict()
WORD_FREQ = dict()
LONGEST_PAGE = ["", 0]
BLACKLIST = set()
CURRENT_LINKS = dict()

REPORT_FILENAME = "report.txt"
LINKS_PARSED = 0

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


def scraper(url, resp):
    get_logger("").error("HELLO????")
    global LOGGER
    LOGGER.error("HELLO????")
    print("hello???")
    links = extract_next_links(url, resp)
    return [urldefrag(link)[0] for link in links if is_valid(link)]


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
    global VISITED, BLACKLIST, LONGEST_PAGE, STOP_WORDS, WORD_FREQ,  \
        REPORT_FILENAME, LINKS_PARSED, SUBDOMAINS, CURRENT_LINKS, LOGGER
    
    #TODO: politeness
    if(urldefrag(url)[0] in VISITED or url in BLACKLIST or resp.status != 200):
        LOGGER.info(resp.status + " status at " + resp.url + " : " + resp.error)
        print(resp.status + " status at " + resp.url + " : " + resp.error)
        return list()
    VISITED.append(urldefrag(url)[0])
    LOGGER.info(url)
    print(url)
    #TODO: avoid crawling large files
    # parse with lxml
    content = resp.raw_response.content
    byte_count = len(content)
    
    tree = html.fromstring(content)

    #TODO: simhash
    # track longest page based on number of words
    text_content = tree.text_content()
    words = text_content.split()
    word_count = len(words)
    if word_count == 0:
        return list()
    if word_count > LONGEST_PAGE[1]:
        LONGEST_PAGE = [url, word_count]
    LOGGER.info(word_count)
    print(word_count)
    # generate total (across domains) list of common words ordered by frequency
    for word in words:
        if word not in STOP_WORDS:
            val = WORD_FREQ.get(word)
            if val == None:
                WORD_FREQ[word] = 1
            else:
                WORD_FREQ[word] += 1    
    
    # write report every 10 links parsed
    if LINKS_PARSED % 10 == 0:
        with open(REPORT_FILENAME, 'w') as f:
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
            for key in WORD_FREQ.keys():
                f.write(f"{key}\n")

    # get links
    links = tree.xpath('//a/@href')
    LOGGER.info(links)
    print(links)
    # count link frequency
    CURRENT_LINKS.clear()
    for link in links:
        val = CURRENT_LINKS.get(link)
        if val == None:
            CURRENT_LINKS[link] = 1
        else:
            CURRENT_LINKS[link] += 1

    return links


def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    global DOMAINS, SUBDOMAINS
    
    try:
        parsed = urlparse(url, allow_fragments=False)
        if parsed.scheme not in set(["http", "https"]) or \
            re.match(
                r".*\.(css|js|bmp|gif|jpe?g|ico"
                + r"|png|tiff?|mid|mp2|mp3|mp4"
                + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
                + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
                + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
                + r"|epub|dll|cnf|tgz|sha1"
                + r"|thmx|mso|arff|rtf|jar|csv"
                + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower()) \
            or not any(parsed.hostname in domain for domain in DOMAINS):
            return False
        
        # track subdomains of uci.edu and number of unique pages in each
        if parsed.hostname not in DOMAINS:
            if not SUBDOMAINS[parsed.hostname]:
                SUBDOMAINS[parsed.hostname] = set()
            SUBDOMAINS[parsed.hostname].add(urldefrag(url)[0])
        return True

    except TypeError:
        print ("TypeError for ", parsed)
        raise


def sorted_frequency(dictionary):
    return sorted(dictionary.items(), key=lambda item: item[1], reverse=True)


def sorted_alphabetical(dictionary):
    return {key: len(dictionary[key]) for key in sorted(dictionary)}
    
