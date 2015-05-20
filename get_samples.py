import csv
import praw
import threading

from utils import get_link_content

OUTPUT_FILE = 'samples.csv'

REDDIT_CATEGORIES = [
    ('programming', 'machinelearning', 150),
    ('programming', 'computerscience', 250),
    ('programming', 'programming', 150),
    ('programming', 'learnprogramming', 150),

    ('business', 'Entrepreneur', 200),
    ('business', 'startups', 200),
    ('business', 'business', 200),

    ('design', 'web_design', 300),
    ('design', 'graphic_design', 300),

    ('entertaiment', 'Music', 150),
    ('entertaiment', 'movies', 150),
    ('entertaiment', 'books', 150),
    ('entertaiment', 'television', 150),

    ('science', 'science', 100),
    ('science', 'Physics', 100),
    ('science', 'chemistry', 100),
    ('science', 'biology', 100),
    ('science', 'math', 100),

    ('security', 'networking', 200),
    ('security', 'hacking', 200),
    ('security', 'ComputerSecurity', 200),

    ('worldnews', 'worldnews', 200),
    ('worldnews', 'news', 200),
    ('worldnews', 'TrueNews', 200),
]


reddit = praw.Reddit(user_agent='my_cool_application')


def get_subreddit_tops(category, limit=100):
    """
    Fectch subreddit top posts from Reddit's API
    """
    return reddit.get_subreddit(category).get_hot(limit=limit)


def save_samples(samples):
    with open(OUTPUT_FILE, 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        for s in samples:
            writer.writerow([
                s['text'].encode('ascii', 'ignore'),
                s['label'].encode('ascii', 'ignore')
            ])


def get_subreddit_samples(category, subreddit, posts_chunk, samples):
    # Get sample from each post's url
    for post in posts_chunk:
        print(subreddit + ': ' + post.url)
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


def get_reddit_samples():
    samples = []
    threads = []
    for category, subreddit, limit in REDDIT_CATEGORIES:
        # Get subreddit top posts
        subbreddit_top_posts = list(get_subreddit_tops(subreddit, limit))
        chunks = [
            subbreddit_top_posts[i:i+50]
            for i in xrange(0, len(subbreddit_top_posts), 50)
        ]
        for chunk in chunks:
            t = threading.Thread(
                target=get_subreddit_samples,
                args=(category, subreddit, chunk, samples,)
            )
            threads.append(t)
            t.start()

    for t in threads:
        t.join()

    return samples


def main():
    reddit_samples = get_reddit_samples()

    # Generate .csv file
    save_samples(reddit_samples)


if __name__ == '__main__':
    main()
