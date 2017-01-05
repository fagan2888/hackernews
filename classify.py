import os
import datetime
import json
import threading
from time import sleep

from firebase import firebase
from monkeylearn import MonkeyLearn

from pymongo import MongoClient

from utils import get_link_content


if 'MONKEYLEARN_APIKEY' not in os.environ:
    raise Exception("Monkeylearn token is required")

MAX_RETRIES = 5

MONGO_URI, MONGO_DB = os.environ['MONGO_URI'].rsplit('/', 1)

MONKEYLEARN_TOKEN = os.environ['MONKEYLEARN_APIKEY']
MONKEYLEARN_MODULE_ID = 'cl_GLSChuJQ'

firebase = firebase.FirebaseApplication(
    'https://hacker-news.firebaseio.com',
    authentication=None
)

db = MongoClient(MONGO_URI)[MONGO_DB]


def update_post(post, cached_post, ranking):
    update = {'$set': {}}
    # Update ranking position
    if cached_post['ranking'] != ranking:
        update['$set']['ranking'] = ranking
        # Update ranking of posts that had this position previously
        db.posts.update({'ranking': ranking}, {'$set': {'ranking': None}})

    # Update post comments count
    if 'descendants' in post\
       and cached_post['ranking'] != post['descendants']:
        update['$set']['comments'] = post['descendants']

    # Update post score
    if cached_post['score'] != post['score']:
        update['$set']['score'] = post['score']

    if update['$set']:
        db.posts.update({'id': cached_post['id']}, update)


def get_hn_post(post_id):
    result = None
    fail_count = 0
    while (not result and fail_count <= MAX_RETRIES):
        try:
            result = firebase.get('/v0/item/%s' % post_id, None)
        except:
            fail_count += 1
            sleep(2)
            continue
    return result


def classify_top_posts(max_posts=None):
    top_posts_ids = firebase.get('/v0/topstories', None)

    new_posts = []
    unclassified_rankings = {}

    for i, post_id in enumerate(top_posts_ids):
        ranking = i + 1
        post = get_hn_post(post_id)
        cached_post = db.posts.find_one({'id': post_id})

        if cached_post:
            print 'Updating post {}'.format(post_id)
            update_post(post, cached_post, ranking)
        else:
            print 'Adding unclassified post {}'.format(post_id)
            if post and 'url' in post:
                text = get_link_content(post['url'])
                if text:
                    post_data = {
                        'id': post_id,
                        'url': post['url'],
                        'title': post['title'],
                        'text': text,
                        'time': datetime.datetime .fromtimestamp(int(post['time'])),
                        'score': post['score'],
                        'username': post['by'],
                        'ranking': ranking
                    }
                    if 'descendants'in post:
                        post_data['comments'] = post['descendants']

                    new_posts.append(post_data)
                    unclassified_rankings[post_id] = ranking
        if max_posts and ranking >= max_posts:
            break

    # Classify posts
    if new_posts:
        print "Classifying {} post with MonkeyLearn".format(len(new_posts))
        ml = MonkeyLearn(MONKEYLEARN_TOKEN)
        result = ml.classifiers.classify(
            MONKEYLEARN_MODULE_ID,
            (p['text'] for p in new_posts)
        ).result

        # Add classification data to new posts and save to db
        for i, post in enumerate(new_posts):
            if result[i][0]['probability'] > 0.5:
                post['result'] = result[i][0]
            else:
                post['result'] = {
                    'label': 'random',
                    'probability': '--'
                }
            post['original_result'] = result[i][0]

            db.posts.insert(post)


if __name__ == '__main__':
    classify_top_posts()
