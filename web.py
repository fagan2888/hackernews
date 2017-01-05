import os
import datetime

from flask import Flask, render_template, request
from flask.ext.moment import Moment
from flask.ext.pymongo import PyMongo

from utils import CATEGORIES


COLORS = [
    '#D93B3B', '#7cb5ec', '#90ed7d', '#f7a35c',
    '#8085e9', '#c015e9', '#2B9658', '#b2b2b2'
]
LIMIT = 30


app = Flask(__name__)
moment = Moment(app)
# Mongo setup
# mongodb://mongo:27017/hn_demo
app.config['MONGO_URI'] = os.environ['MONGO_URI']
mongo = PyMongo(app)


def get_statistics(posts):
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


def search_posts(posts, category, page):
    selector = {'ranking': {'$ne': None}}

    if category and category != 'all':
        selector['result.label'] = category

    return posts.find(selector).sort('ranking', 1).skip((page-1)*LIMIT).limit(LIMIT)


@app.route('/', methods=['GET'])
@app.route('/news', methods=['GET'])
def index():
    page = request.args.get('p')
    category = request.args.get('c') or 'all'

    if not page:
        page = 1
    else:
        page = int(page)

    return render_template(
        'index.html',
        posts=search_posts(mongo.db.posts, category, page),
        statistics=get_statistics(mongo.db.posts),
        categories=CATEGORIES + ['random'],
        page=page,
        category=category
    )


@app.route('/feed.xml', methods=['GET'])
def category_rss():
    category = request.args.get('c') or 'all'
    page = 1

    return render_template(
        'category_rss.xml',
        posts=search_posts(mongo.db.posts, category, page),
        category=category
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000, debug=True)
