import datetime
import json
import os
import requests
import threading

from firebase import firebase
from flask import Flask, render_template, request
from flask.ext.moment import Moment
from flask_bootstrap import Bootstrap
from pymongo import MongoClient
from time import sleep
from utils import get_link_content, CATEGORIES


PORT = 6000
DEBUG = True
LIMIT = 30
MAX_RETRIES = 5
COLORS = [
    '#D93B3B', '#7cb5ec', '#90ed7d', '#f7a35c',
    '#8085e9', '#c015e9', '#2B9658', '#b2b2b2'
]

app = Flask(__name__)
Bootstrap(app)
moment = Moment(app)

mongo = MongoClient(os.environ.get('MONGO_URL', None))
db = mongo[os.environ.get('MONGO_DB', 'hn_demo')]
posts = db.posts

firebase = firebase.FirebaseApplication(
    'https://hacker-news.firebaseio.com',
    authentication=None
)

if 'MONKEYLEARN_APIKEY' in os.environ:
    MONKEYLEARN_TOKEN = 'token %s' % os.environ.get('MONKEYLEARN_APIKEY')
else:
    raise Exception("Monkeylearn token is required")


def classify(posts):
    if not posts:
        return []

    response = requests.post(
        "https://api.monkeylearn.com/v2/classifiers/cl_GLSChuJQ/classify/",
        data=json.dumps({
            'text_list': posts
        }),
        headers={
            'Authorization': MONKEYLEARN_TOKEN,
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
            result = firebase.get('/v0/item/%s' % postId, None)
        except:
            ++t
            sleep(5)
            continue
    return result


def update_post(old_post, new_post, ranking):
    update = {'$set': {}}
    # Update ranking position
    if old_post['ranking'] != ranking:
        update['$set']['ranking'] = ranking
        # Update ranking of posts that had this position previously
        posts.update({'ranking': ranking}, {'$set': {'ranking': None}})

    # Update post comments count
    if 'descendants' in new_post\
       and old_post['ranking'] != new_post['descendants']:
        update['$set']['comments'] = new_post['descendants']

    # Update post score
    if old_post['score'] != new_post['score']:
        update['$set']['score'] = new_post['score']

    if update['$set']:
        print('Updated: ' + old_post['url'])
        posts.update({'id': old_post['id']}, update)


def get_unclassified_posts(posts_chunk, unclassified_hn_posts, chunk_number):
    for i, postId in enumerate(posts_chunk):
        ranking = chunk_number * 20 + (i + 1)
        # Check if post was already classified
        old_post = posts.find_one({'id': postId})
        new_post = get_hn_post(postId)
        if not old_post:
            if new_post and 'url' in new_post:
                text = get_link_content(new_post['url'])
                if text:
                    print(new_post['url'])
                    time = datetime.datetime\
                        .fromtimestamp(int(new_post['time']))
                    post_data = {
                        'id': postId,
                        'url': new_post['url'],
                        'title': new_post['title'],
                        'text': text,
                        'time': time,
                        'score': new_post['score'],
                        'username': new_post['by'],
                        'ranking': ranking
                    }
                    if 'descendants'in new_post:
                        post_data['comments'] = new_post['descendants']

                    unclassified_hn_posts.append(post_data)
        else:
            update_post(old_post, new_post, ranking)


def classify_hn_top_posts():
    response = firebase.get('/v0/topstories', None)
    unclassified_hn_posts = []

    # Split response in list of 50 elements
    chunks = [
        response[i:i+20]
        for i in xrange(0, len(response), 20)
    ]

    # Proccess each chunk in its own thread
    threads = []
    for i, chunk in enumerate(chunks):
        t = threading.Thread(
            target=get_unclassified_posts,
            args=(chunk, unclassified_hn_posts, i,)
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
        if result[i][0]['probability'] > 0.5:
            post['result'] = result[i][0]
        else:
            post['result'] = {
                'label': 'random',
                'probability': '--'
            }
            post['original_result'] = result[i][0]

        # Check if post was already classified
        old_post = posts.find_one({'id': post['id']})
        if not old_post:
            # Save classified post
            posts.insert(post)

    # Classify new HN posts again in 5 minutes
    threading.Timer(300, classify_hn_top_posts).start()

# Start classifing HN post
t = threading.Thread(target=classify_hn_top_posts,).start()


def get_statistics():
    data = {}

    # Generate time intervals used to filter posts
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
        for i in reversed(range(10))]

    # Get posts count for each category in the time intervals defined
    for start, end in time_intervals:
        for category in CATEGORIES + ['random']:
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
        'time_intervals': time_intervals,
        'colors': COLORS
    }


@app.route('/', methods=['GET'])
@app.route('/news', methods=['GET'])
def index():
    page = request.args.get('p')
    category = request.args.get('c')

    selector = {'ranking': {'$ne': None}}
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
        posts=posts.find(selector).sort('ranking', 1)
                   .skip((page-1)*LIMIT).limit(LIMIT),
        statistics=get_statistics(),
        categories=CATEGORIES + ['random'],
        page=page,
        category=category
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
