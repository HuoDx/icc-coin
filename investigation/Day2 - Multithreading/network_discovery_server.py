from flask import Flask, request, jsonify
import requests

server = Flask(__name__)

peers = []
PORT = 5000
CLIENT_PORT = 10001

def contruct_url(peer, route):
    global CLIENT_PORT
    return '%s:%s%s'%(peer, CLIENT_PORT, route)

def update_peers(new_peer):
    global peers
    return requests.get(contruct_url(new_peer, '/network-discovery'), json={
                'known_peers': peers
            })

import socket

local_ip = socket.gethostbyname(socket.gethostname())


@server.route('/network-discovery', methods = ['GET'])
def network_peers():
    visitor_ip = request.remote_addr
    if request.json is None:
        return '???', 401
    discovery_queue = [p for p in request.json.get('peers', [visitor_ip])]
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
@server.route('/peers')
def see_peers():
    global peers
    content = ''
    for p in peers:
        content += '\n<li> %s </li>'%p
    return '<ul style="margin: 36px">%s</ul>'%content

if __name__ == '__main__':
    # import waitress
    # waitress.serve(server, port = PORT)
    server.run(debug=True)