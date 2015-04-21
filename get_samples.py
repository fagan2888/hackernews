import csv
import praw
import threading

from utils import get_link_content

OUTPUTF = 'samples.csv'

REDDIT_CATEGORIES = [
    ('programming', 'machinelearning', 100),
    ('programming', 'computerscience', 100),
    ('programming', 'programming', 100),
    ('programming', 'learnprogramming', 100),

    ('business', 'Entrepreneur', 150),
    ('business', 'startups', 150),
    ('business', 'business', 150),

    ('design', 'web_design', 200),
    ('design', 'graphic_design', 200),

    ('entertaiment', 'Music', 100),
    ('entertaiment', 'movies', 100),
    ('entertaiment', 'books', 100),
    ('entertaiment', 'television', 100),

    ('science', 'science', 100),
    ('science', 'Physics', 100),
    ('science', 'chemistry', 100),
    ('science', 'biology', 100),
    ('science', 'math', 100),

    ('security', 'networking', 150),
    ('security', 'hacking', 150),
    ('security', 'ComputerSecurity', 150),
]


reddit = praw.Reddit(user_agent='my_cool_application')


def get_subreddit_tops(category, limit=100):
    """
    Fectch subreddit top posts from Reddit's API
    """
    return reddit.get_subreddit(category).get_hot(limit=limit)


def save_samples(samples):
    with open(OUTPUTF, 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        for s in samples:
            writer.writerow([
                s['text'].encode('ascii', 'ignore'),
                s['label'].encode('ascii', 'ignore')
            ])


def get_subreddit_samples(category, subreddit, limit, samples):
    # Get subreddit top posts
    subbreddit_top_posts = get_subreddit_tops(subreddit, limit)
    # Get sample from each post's url
    for post in subbreddit_top_posts:
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
        t = threading.Thread(
            target=get_subreddit_samples,
            args=(category, subreddit, limit, samples,)
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
