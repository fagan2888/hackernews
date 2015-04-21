import requests

from lxml import html

CATEGORIES = [
    'programming',
    'business',
    'design',
    'entertaiment',
    'science',
    'security'
]


def get_link_content(link):
    """
    Extract relevant content related to the post
    """
    try:
        # Get post's site root
        root = html.fromstring(requests.get(link).content)
        # Extract content from p elements
        content = " ".join(root.xpath("//p/text()"))
    except:
        content = None

    return content
