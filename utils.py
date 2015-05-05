import requests

from lxml import html

CATEGORIES = [
    'programming',
    'business',
    'design',
    'entertainment',
    'science',
    'security',
    'worldnews'
]


def get_link_content(link):
    """
    Extract relevant content related to the post
    """
    try:
        request = requests.get(link)
        if request.status_code == 403 or\
           request.status_code == 404:
            return None
        # Get post's site root
        root = html.fromstring(request.content)
        # Extract text from p, div and span elements
        texts = root.xpath("//p/text()")\
            + root.xpath("//div/text()")\
            + root.xpath("//span/text()")\
            + root.xpath("//pre/text()")
        content = " ".join([text.strip() for text in texts])
    except:
        content = None

    return content
