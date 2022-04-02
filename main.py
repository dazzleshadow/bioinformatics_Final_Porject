import json
import re
import os
from flask import Flask, request, escape, render_template, render_template_string, redirect, url_for
from werkzeug import secure_filename
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'data/abstracts/'

def get_short_id(id):
    return id.split('/')[-1]

def enum_synonym_pred(pred):
    if pred == 'hasRelatedSynonym':
        return 'RELATED'
    elif pred == 'hasExactSynonym':
        return 'EXACT'
    elif pred == 'hasNarrowSynonym':
        return 'NARROW'
    elif pred == 'hasBroadSynonym':
        return 'BROAD'
    else:
        return pred

with open("data/dataset/goslim_pir.json") as f:
    graph = json.load(f)["graphs"][0]
    nodes = graph["nodes"]
    
    for node in nodes:
        node['short_id'] = get_short_id(node['id'])

        if 'meta' in node and 'synonyms' in node['meta']:
            for synonym in node['meta']['synonyms']:
                if 'pred' in synonym:
                    synonym['pred'] = enum_synonym_pred(synonym['pred'])

    edges = graph["edges"]


def find_term_by_short_id(term_id):
    try:
        return next(x for x in nodes if x['short_id'] == term_id)
    except StopIteration:
        return None

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/term/<term_id>')
def term(term_id):
    '''Route for showing specific term'''

    # Finds term with correct id
    term = find_term_by_short_id(term_id)

    if term is None:
        return render_template('term.html', term=None)

    # Find all 'is_a' neighbours of the term
    term['is_a_edges'] = []
    is_a_neighbour_ids = [edge["obj"] for edge in edges if edge["sub"] == term['id'] and edge["pred"] == "is_a"]
    for neighbour_id in is_a_neighbour_ids:
        neighbour_short_id = get_short_id(neighbour_id)
        neighbor = find_term_by_short_id(neighbour_short_id)

        if neighbor is not None:
            term['is_a_edges'].append({
                'id': neighbour_id,
                'short_id': neighbour_short_id,
                'lbl': neighbor['lbl'],
                })
    
    return render_template('term.html', term=term)


@app.route('/query')
def query():
    '''Route for showing all GO terms (possibly matching query)'''
    query=request.args.get('q')
    if (query):
        try:
            results = [x for x in nodes if query in x['lbl'] or query in x['short_id']]
            
        except StopIteration:
            results = None

        return render_template('query.html', query=query, results=results)
    else:
        return render_template('query.html', query='no query, showing all', results=nodes)

@app.route('/mappings/<filename>')
def mappings(filename):
    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename),encoding="utf-8") as f:
        abstract = f.read()
        for node in nodes:
            pattern = node["lbl"]
            repl = render_template_string("<a href={{ url_for('term', term_id=node['short_id']) }}>{{ node['lbl'] }}</a>", node=node)
            abstract = re.sub(pattern=pattern, repl=repl, string=abstract)
        return render_template("mappings.html", abstract=abstract)

    return 'Abstract not found'

@app.route('/upload', methods=['POST'])
def upload():
    # check if the post request has the file part
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return redirect(url_for('mappings', filename=filename))

if __name__ == "__main__":
    app.run(debug=True)
