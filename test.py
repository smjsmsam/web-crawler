import sys
import re
import requests
from lxml import html, etree
from urllib.parse import urlparse


url = "https://stat.uci.edu/"

DOMAINS = ["ics.uci.edu",
           "cs.uci.edu",
           "informatics.uci.edu",
           "stat.uci.edu"]
 

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    
    try:
        parsed = urlparse(url)
        # print(parsed.hostname)
        if parsed.scheme not in set(["http", "https"]) or parsed.hostname not in DOMAINS:
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


if __name__ == "__main__":
    resp = requests.get(url)
    if(resp.status_code != 200):
        print(resp.status_code)
        sys.exit(1)
    print(resp.status_code)

    # print(resp.content)
    
    tree = html.fromstring(resp.content)
    etree.strip_elements(tree, 'script', 'style', 'template', 'meta', 'svg', 'embed', 'object', 'iframe', 'canvas', 'img')
    links = tree.xpath('//a/@href')
    text_content = tree.text_content()
    words = text_content.split()
    print(words)
    # print(links)
    # for link in links:
    #     if is_valid(link):
            # print(link)
