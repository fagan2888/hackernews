import csv
import praw

from utils import get_link_content, CATEGORIES

OUTPUTF = 'samples.csv'
LIMIT = 300


reddit = praw.Reddit(user_agent='my_cool_application')


def get_subreddit_tops(category):
    """
    Fectch subreddit top posts from Reddit's API
    """
    return reddit.get_subreddit(category).get_hot(limit=LIMIT)


def save_samples(samples):
    with open(OUTPUTF, 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        for s in samples:
            writer.writerow([
                s['text'].encode('ascii', 'ignore'),
                s['label'].encode('ascii', 'ignore')
            ])


def main():
    samples = []
    for category in CATEGORIES:
        # Get subreddit top posts
        subbreddit_top_posts = get_subreddit_tops(category)
        # Get sample from each post's url
        for post in subbreddit_top_posts:
            print(post.url)
            # If it's a self related post then take selftext as content
            if post.is_self:
                content = post.selftext
            else:
                content = get_link_content(post.url)
            if content:
                samples.append({
                    'text': content,
                    'label': category
                })
    # Generate .csv file
    save_samples(samples)


if __name__ == '__main__':
    main()
