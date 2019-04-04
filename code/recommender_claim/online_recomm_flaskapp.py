""" Recommend from saved model in online setting
"""

import json
import os
import time
import zlib
from flask import Flask, render_template, request, redirect

app = Flask(__name__)

# IPC
pipe_query_fn = 'arXivCS_query_fifo'
pipe_recomm_fn = 'arXivCS_recomm_fifo'

pipe_out = os.open(pipe_query_fn, os.O_WRONLY)
pipe_in = open(pipe_recomm_fn, 'r')

def log_eval(uid, eval_json):
    timestamp = str(int(time.time()))
    with open('freetext_eval_log', 'a') as f:
        line = '{}\n'.format('\u241f'.join([timestamp, uid, eval_json]))
        f.write(line)

def get_uid(request):
    ip = request.remote_addr
    user_agent = request.headers.get('User-Agent')
    lang = request.headers.get('Accept-Language')
    uid = '{:x}'.format(
        zlib.adler32(str.encode('{}{}{}'.format(ip, user_agent, lang)))
        )
    return uid

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', context='', recs_bow=[], recs_pp=[], recs_np=[])

@app.route('/', methods=['POST'])
def recomm():
    input_text = request.form['input_text']
    msg = '{}\n'.format(input_text)
    os.write(pipe_out, msg.encode())
    recomm_json = pipe_in.readline()
    recomm = json.loads(recomm_json)
    recs_bow = recomm[0]
    recs_pp = recomm[1]
    recs_np = recomm[2]
    context = input_text
    return render_template('index.html', context=context, recs_bow=recs_bow, recs_pp=recs_pp, recs_np=recs_np)

@app.route('/rate', methods=['POST'])
def rate():
    uid = get_uid(request)
    log_eval(uid, json.dumps(request.form))
    return redirect('/')
