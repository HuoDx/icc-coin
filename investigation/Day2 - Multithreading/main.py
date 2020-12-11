from flask import Flask, request, jsonify, send_file
import requests


from data import peers, local_ip, messages, message_hash_list

import socket
hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)

print('Local IP: %s'%local_ip)

server = Flask(__name__)
PORT = 10001
def contruct_url(peer, route):
    global PORT
    return 'http://%s:%s%s'%(peer, PORT, route)

def update_peers(new_peer):
    return requests.get(contruct_url(new_peer, '/network-discovery'), json={
                'peers': peers
            })
    
@server.route('/network-discovery', methods = ['GET'])
def network_peers():
    visitor_ip = request.remote_addr
    if request.json is None:
        return '???', 401
    discovery_queue = [p for p in request.json.get('peers', [visitor_ip])]
    if visitor_ip not in discovery_queue:
        discovery_queue.append(visitor_ip)
    print(visitor_ip)
    while len(discovery_queue) > 0:
        new_peer = discovery_queue.pop()
        if new_peer not in peers and new_peer != local_ip:
            try:
                r = update_peers(new_peer)
                if r.status_code == 200: # HTTP OK
                    peers.append(new_peer)
                    # update peers
                    for discovered_peer in r.json().get('peers',[]):
                        if discovered_peer not in discovery_queue and discovered_peer not in peers:
                            discovery_queue.append(new_peer)
            except Exception:
                print('Peer "%s" unreachable; ignored.'%new_peer)
    return jsonify({
        'peers': peers
    })

def broadcast_message(message, uid):
    succeed = 0
    for p in peers:
        r = request.post(contruct_url(p, '/message'), json={'message': message, 'uid': uid})
        if r.status_code == 200:
            succeed += 1
    return 0 if len(peers) == 0 else succeed * 1.0 / len(peers)

import time
from hashlib import sha256
from uuid import uuid1


signal = False


@server.route('/message', methods=['POST'])
def on_message():
    global signal
    peer_ip = request.remote_addr
    msg = request.json.get('message', '')
    msg_uid = request.json.get('uuid', str(uuid1()))
    if msg_uid not in message_hash_list:
        message_hash_list.append(msg_uid)
        success_rate = broadcast_message(msg, msg_uid)
        messages.append('<broadcasted to %d peers, success rate = %.2f >'%(len(peers), success_rate))
        messages.append('[%s] %s'%(peer_ip, msg))
        signal = True
    return 'ok.', 200


TIMEOUT = 5

@server.route('/api/poll', methods=['GET'])
def poll():

    start_timestamp = time.time()
    global signal
    while not signal and (time.time() - start_timestamp) < TIMEOUT:
        time.sleep(1.0/24)
    if signal:
        signal = False
        return jsonify({
            'status': 0,
            'result': messages
        })
    return jsonify({
        'status': 1
    })
    
@server.route('/', methods=['GET'])
def index():
    return send_file('index.html')

from requests.exceptions import ConnectionError
if __name__ == '__main__':
    try:
        r = requests.get('http://%s:%s/network-discovery/'%(input('Network Discovery Server IP: '), input('Network Discovery Server Port: ')), json={
            
        })
        print('Request done (%d)'%r.status_code) 
        if r.status_code == 200:
            print('Finished update.')
            result = r.json()
            p = result.get('peers',[])
            if len(p) > 0:
                print('Peers found:')
                for peer in p:
                    if peer not in peers and peer != local_ip:
                        peers.append(peer)
                        print('  · %s'%peer)
    except ConnectionError:
        print('Cannot reach any peers...')
        print('Nevermind!')
    
    PORT = input('Server Port:')
    import webbrowser
    webbrowser.open('http://%s:%s/'%(local_ip, PORT), new=2)
    import waitress
    waitress.serve(server, port = PORT)



    