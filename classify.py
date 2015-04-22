import datetime
import json
import requests
import threading

from firebase import firebase
from flask import Flask, render_template, request
from flask.ext.moment import Moment
from flask_bootstrap import Bootstrap
from hackernews import HackerNews
from pymongo import MongoClient
from time import sleep
from utils import get_link_content, CATEGORIES


PORT = 6000
DEBUG = True
LIMIT = 30
MAX_RETRIES = 5
COLORS = ['#D93B3B', '#7cb5ec', '#90ed7d', '#f7a35c', '#8085e9']

app = Flask(__name__)
Bootstrap(app)
moment = Moment(app)

hn = HackerNews()

mongo = MongoClient()
db = mongo.hn_demo
posts = db.posts

firebase = firebase.FirebaseApplication(
    'https://hacker-news.firebaseio.com',
    authentication=None
)


def classify(posts):
    if not posts:
        return []

    response = requests.post(
        "https://api.monkeylearn.com/v2/classifiers/cl_GLSChuJQ/classify/",
        data=json.dumps({
            'text_list': posts
        }),
        headers={
            'Authorization': 'Token e13b268ec3c09712b7869c21103923dfd7a31309',
            'Content-Type': 'application/json'
        })

    try:
        return json.loads(response.text)['result']
    except:
        print("Unexpected result:", json.loads(response.text))
        raise


def get_hn_post(postId):
    result = None
    t = 1
    while(not result and t < MAX_RETRIES):
        try:
            result = hn.item(postId)
        except:
            ++t
            sleep(5)
            continue
    return result


def get_unclassified_posts(posts_chunk, unclassified_hn_posts):
    for postId in posts_chunk:
        # Check if post was already classified
        post = posts.find_one({'id': postId})
        if not post:
            post = get_hn_post(postId)
            if post and hasattr(post, 'url'):
                text = get_link_content(post.url)
                if text:
                    print(post.url)
                    post_data = {
                        'id': postId,
                        'url': post.url,
                        'title': post.title,
                        'text': text,
                        'time': post.time,
                        'score': post.score,
                        'username': post.by,
                    }
                    if hasattr(post, 'descendants'):
                        post_data['comments'] = post.descendants

                    unclassified_hn_posts.append(post_data)


def classify_hn_top_posts():
    response = firebase.get('/v0/topstories', None)
    unclassified_hn_posts = []

    # Split response in list of 50 elements
    chunks = [
        response[i:i+20]
        for i in xrange(0, len(response), 20)
    ]
    threads = []
    for chunk in chunks:
        t = threading.Thread(
            target=get_unclassified_posts,
            args=(chunk, unclassified_hn_posts,)
        )
        threads.append(t)
        t.start()

    # Wait until every chunk was processed
    for t in threads:
        t.join()

    # Classify posts
    result = classify([p['text'] for p in unclassified_hn_posts])

    # Match results with its post
    for i, post in enumerate(unclassified_hn_posts):
        if result[i][0]['probability'] > 0.6:
            post['result'] = result[i][0]
        else:
            post['result'] = {
                'label': 'other',
                'probability': '--'
            }

        # Check if post was already classified
        old_post = posts.find_one({'id': post['id']})
        if not old_post:
            # Save classified post
            posts.insert(post)

    # Classify new HN posts again in 5 minutes
    threading.Timer(300, classify_hn_top_posts).start()

# Start classifing HN post in 10 seconds
threading.Timer(10, classify_hn_top_posts).start()


def get_statistics():
    data = {}
    now = datetime.datetime.now()
    time_intervals = [(
        (now-datetime.timedelta(hours=i)).replace(
            minute=0,
            second=0,
            microsecond=0),
        (now-datetime.timedelta(hours=i-1)).replace(
            minute=0,
            second=0,
            microsecond=0))
        for i in reversed(range(5))]
    for start, end in time_intervals:
        for category in CATEGORIES + ['other']:
            if category not in data:
                data[category] = []
            data[category].append(posts.find({
                'time': {
                    '$gte': start,
                    '$lte': end
                },
                'result.label': category
            }).count())

    return {
        'data': data,
        'categories': time_intervals,
        'colors': COLORS
    }


@app.route('/', methods=['GET'])
@app.route('/news', methods=['GET'])
def index():
    page = request.args.get('p')
    category = request.args.get('c')

    selector = {}
    if category and category != 'all':
        selector['result.label'] = category
    else:
        category = 'all'

    if not page:
        page = 1
    else:
        page = int(page)

    return render_template(
        'index.html',
        posts=posts.find(selector).sort('time', -1)
                   .skip((page-1)*LIMIT).limit(LIMIT),
        statistics=get_statistics(),
        labels=CATEGORIES + ['other'],
        page=page,
        category=category
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
