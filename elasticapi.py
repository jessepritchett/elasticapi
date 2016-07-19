import sys, getopt, json, flask, elasticsearch
from urllib.parse import urlparse
from auth import requires_auth

# define Flask WSGI app
app = flask.Flask(__name__)

# define options and usage
try:
    opts, rest = getopt.getopt(sys.argv[1:], 'l:t:n', ['local=', 'target='])
except getopt.GetoptError:
    print('usage: [-l <local url>] [-t <target url>] [-n]')
    sys.exit(1)

# default to non-SSL Elasticsearch server on localhost
local_url = 'http://localhost:5001'
target_url = 'http://localhost:9200'
cert = True

# parse options
for opt, val in opts:
    if opt in ('-l', '--local'):
        # assign local URL
        local_url = val
    elif opt in ('-t', '--target'):
        # assign target URL
        target_url = val
    elif opt in ('-n', '--no-cert'):
        # allow for SSL, but no cert (will generate warning)
        cert = False

# one Elasticsearch connection?
es = elasticsearch.Elasticsearch(
    [target_url],
    connection_class=elasticsearch.RequestsHttpConnection,
    verify_certs=cert
)


def pretty(data):
    """ pretty print json """
    return json.dumps(data, sort_keys=True, indent=4)


def error(err):
    """ very basic error handling """
    if err.status_code != 'N/A':
        flask.abort(err.status_code, str(err))
    else:
        flask.abort(500, str(err))


# Flask paths #

@app.route('/')
def root():
    """
    Index
    """
    return "Hello from Jesse P."


@app.route('/cluster', defaults={'indices': '', 'level': ''}, methods=['GET'])
@app.route('/cluster/<indices>', defaults={'level': 'indices'}, methods=['GET', 'POST', 'DELETE'])
@app.route('/cluster/<indices>/shards', defaults={'level': 'shards'}, methods=['GET'])
@requires_auth(methods=['POST', 'DELETE'])
def cluster(indices, level):
    """
    Cluster health
    see: https://www.elastic.co/guide/en/elasticsearch/reference/current/cluster-health.html

    Reduced to three GET use-cases:
        GET /cluster gives cluster-level health
        GET /cluster/{index1,index2,...} gives filtered indices-level health
        GET /cluster/{index1,index2,...}/shards gives filtered shard-level health

    Wait mechanics, and local flag are not exposed.

    Index management
    see: https://www.elastic.co/guide/en/elasticsearch/reference/current/indices-create-index.html,
         https://www.elastic.co/guide/en/elasticsearch/reference/current/indices-delete-index.html

    Added ability to create/delete multiple indices at once
        POST /cluster/{index1,index2,...} creates one or more indices
        DELETE /cluster/{index1,index2,...} deletes one or more indices
    """

    res = {}

    try:
        # define GET
        if flask.request.method == 'GET':
            missing = []

            # check if indices exist, instead of timing out
            for index in indices.split(','):
                if index != '' and not es.indices.exists(index=index):
                    missing.append(index)

            if len(missing) > 0:
                flask.abort(404, 'Elasticsearch indices not found: '+','.join(missing))

            # could do something fancy here, like process the response
            # for now, simply dump the json (destroys the order originally provided by Elasticsearch)
            res = es.cluster.health(index=indices, level=level)

        # define POST
        elif flask.request.method == 'POST':
            # fortunately, we only arrive here for /cluster/<indices>
            for index in indices.split(','):
                if index != '':
                    # FIXME account for mixed ack/nacks
                    res = es.indices.create(index)

        # define DELETE
        elif flask.request.method == 'DELETE':
            # fortunately, we only arrive here for /cluster/<indices>
            for index in indices.split(','):
                if index != '':
                    # FIXME account for mixed ack/nacks
                    res = es.indices.delete(index)

    except elasticsearch.exceptions.TransportError as err:
        error(err)

    return pretty(res)


@app.route('/nodes')
@requires_auth
def nodes():
    """
    Node info
    see: https://www.elastic.co/guide/en/elasticsearch/reference/current/cluster-nodes-info.html

    Reduced to one use-case:
        GET /nodes gives full info for all nodes
    """
    return pretty(es.nodes.info())


@app.route('/allocate/<index>/<shard>/<node>', methods=['POST'])
@requires_auth(methods=['POST'])
def allocate(index, shard, node):
    """
    Cluster reroute: allocate
    see: https://www.elastic.co/guide/en/elasticsearch/reference/current/cluster-reroute.html

    Reduced to one use-case:
        POST /allocate/{index}/{shard}/{node} allocates the given unassigned shard to the given node
    """
    cmd = {
        'commands': [{
            'allocate': {
                'index': index,
                'shard': shard,
                'node': node
            }
        }]
    }
    res = es.cluster.reroute(body=cmd)
    return pretty(res)


@app.route('/move/<index>/<shard>/<from_node>/<to_node>', methods=['POST'])
@requires_auth(methods=['POST'])
def move(index, shard, from_node, to_node):
    """
    Cluster reroute: move
    see: https://www.elastic.co/guide/en/elasticsearch/reference/current/cluster-reroute.html

    Reduced to one use-case:
        POST /allocate/{index}/{shard}/{from_node}/{to_node} moves the given shard from one node to another
    """
    cmd = {
        'commands': [{
            'move': {
                'index': index,
                'shard': shard,
                'from_node': from_node,
                'to_node': to_node
            }
        }]
    }
    res = es.cluster.reroute(body=cmd)
    return pretty(res)


if __name__ == '__main__':
    # not production ready, but fine for running as a demo/test
    url = urlparse(local_url)
    app.run(host=url.hostname, port=int(url.port))
