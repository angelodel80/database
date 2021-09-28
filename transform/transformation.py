import codecs 
import networkx as nx 
import sys 
import re 
from lxml import etree as et 


# Transforms files DOT and metadata to TEI and Graphml
# The file changed is in the variable: changed_file. The script checks if the file changed is DOT or txt and transforms both
# It is applied automaticly with each push for the files changed
# To perform for all files in bash: 
# for changed_file in ./* ; do python ./transform/transformation.py $changed_file ; done
# 
# Local:
# for changed_file in $( find ~/Dokumente/OpenStemmata/database/data -name '*.*' ) ; do ~/Dokumente/OpenStemmata/venv/bin/python3 ~/Dokumente/OpenStemmata/database/transform/transformation.py $changed_file ; done

attributes_regex = '(\w+)="([^"]*)",?\s*'

if len(sys.argv) > 1:
    changed_file = str(sys.argv[1])
    
    dotFile = ''
    txtFile = ''
    path = changed_file.split('/')[0:-1]
    new_file_name = path[-1]
    

    if changed_file[-3:] == '.gv':
        dotFile = changed_file
        txtFile = '/'.join(path) + '/metadata.txt'
    elif changed_file[-12:] == 'metadata.txt':
        txtFile = changed_file
        dotFile = '/'.join(path) + '/stemma.gv'
    else:
        # sys.exit('Changed file is not .txt nor .gv')
        sys.exit()

    
    print("Processing: ", changed_file)
    

    with codecs.open(dotFile, 'r', 'utf-8') as dot:
        lines = dot.readlines()
        nodes = {}
        edges = []
        for line in lines:
            noAttrib = re.sub('\'.+?\'', '', line) 
            noAttrib = re.sub('".+?"', '', line)
            if "->" in noAttrib or "--" in noAttrib:
                origin = re.split('->', noAttrib)[0].strip()
                dest = re.split('->', noAttrib)[1].strip()
                if '[' in dest:
                    dest = re.split('\[', dest)[0].strip()
                if ';' in dest:
                    dest = re.split(';', dest)[0].strip()
                if origin not in nodes:
                    nodes[origin] = {}
                if dest not in nodes:
                    nodes[dest] = {}
                edge_attr = {'type': 'filiation', 'cert': 'unknown'}
                if '[' in noAttrib:
                    attributes = re.findall(attributes_regex, line)    
                    for attr in attributes:
                        if attr[0] == 'style':
                            if attr[1] == 'dashed':
                                edge_attr['type'] = 'contamination'
                        elif attr[0] == 'color':
                            if attr[1] == 'red':
                                edge_attr['cert'] = 'low'

                edges.append((origin,dest, edge_attr))
                
            elif '[' in noAttrib:
                node = re.split('\[', noAttrib)[0].strip()
                nodes[node] = {}
                attributes = re.findall(attributes_regex, line)    
                for attr in attributes:
                    nodes[node][attr[0]] = attr[1]

    nodes = [ (x,nodes[x]) for x in nodes ]

    G = nx.DiGraph()
    # print(edges)
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)

    nx.write_graphml(G, '/'.join(path) + '/' + 'stemma.graphml', encoding="utf-8")


    tree = et.parse('./transform/template.tei.xml')
    root = tree.getroot()

    ns = {'tei': 'http://www.tei-c.org/ns/1.0', 'od': 'http://openstemmata.github.io/odd.html' }
    et.register_namespace('tei', 'http://www.tei-c.org/ns/1.0')
    et.register_namespace('od', 'http://openstemmata.github.io/odd.html')

    # TEIHEADER
    with codecs.open(txtFile, 'r', 'utf-8') as metadatafile:
        metadata = metadatafile.readlines()
        titleStmt = root.find('.//tei:teiHeader/tei:fileDesc/tei:titleStmt', ns)
        bibl = root.find('.//tei:bibl', ns)
        creation = root.find('./tei:teiHeader/tei:profileDesc/tei:creation', ns)
        keywords = root.find('./tei:teiHeader/tei:profileDesc/tei:textClass/tei:keywords', ns)
        listWit = root.find('./tei:teiHeader/tei:fileDesc/tei:sourceDesc/tei:listWit', ns)
        # date = root.find('./tei:teiHeader/tei:fileDesc/tei:publicationStmt/tei:data', ns)
        graph = root.find('.//tei:graph', ns)

        #This is useful for the url of the graphic element
        facsimileLink = "https://github.com/OpenStemmata/database/blob/main/data/"



        for line in metadata:
            if re.match('^[\s]*publicationType', line):
                cont = re.findall('"([^"]*)"', line)
                if len(cont) > 0:
                    cont = cont[0]
                    bibl.attrib['type'] = cont
            elif re.match('^[\s]*publicationTitle', line):
                cont = re.findall('"([^"]*)"', line)
                if len(cont) > 0:
                    cont = cont[0]
                    el = bibl.find('./tei:title', ns)
                    el.text = cont
            elif re.match('^[\s]*publicationDate', line):
                cont = re.findall('"([^"]*)"', line)
                if len(cont) > 0:
                    cont = cont[0]
                    el = bibl.find('./tei:date', ns)
                    el.text = cont
            elif re.match('^[\s]*publicationPlace', line):
                cont = re.findall('"([^"]*)"', line)
                if len(cont) > 0:
                    cont = cont[0]
                    el = bibl.find('./tei:pubPlace', ns)
                    el.text = cont
            elif re.match('^[\s]*publicationSeries', line):
                cont = re.findall('"([^"]*)"', line)
                if len(cont) > 0:
                    cont = cont[0]
                    el = bibl.find('./tei:series', ns)
                    el.text = cont
            elif re.match('^[\s]*publicationNum', line):
                cont = re.findall('"([^"]*)"', line)[0]
                el = bibl.find('./tei:biblScope[@unit="volume"]', ns)
                el.attrib['n'] = cont
            elif re.match('^[\s]*publicationStemmaNum', line):
                cont = re.findall('"([^"]*)"', line)[0]
                graphLabel = et.SubElement(graph, 'label')
                graphLabel.text = cont
            elif re.match('^[\s]*publicationAuthors', line):
                cont = re.findall('"([^"]*)"', line)[0]
                el = et.SubElement(bibl, 'author')
                el.text = cont
                el2 = et.SubElement(titleStmt, 'author')
                el2.text = cont
            elif re.match('^[\s]*publicationPage', line):
                cont = re.findall('"([^"]*)"', line)[0]
                el = bibl.find('./tei:biblScope[@unit="page"]', ns)
                el.attrib['n'] = cont
            elif re.match('^[\s]*publicationLink', line):
                cont = re.findall('"([^"]*)"', line)[0]
                el = bibl.find('./tei:ptr[@type="digitised"]', ns)
                el.attrib['target'] = cont
            elif re.match('^[\s]*workTitle', line):
                cont = re.findall('"([^"]*)"', line)[0]
                el = creation.find('./tei:title', ns)
                el.text = cont
                el2 = titleStmt.find('./tei:title[@type="variable"]', ns)
                el2.text = cont
            elif re.match('^[\s]*workViaf', line):
                cont = re.findall('"([^"]*)"', line)[0]
                el = creation.find('./tei:title', ns)
                el.attrib['ref'] = 'http://viaf.org/' + cont
            elif re.match('^[\s]*workOrigDate', line):
                cont = re.findall('"([^"]*)"', line)[0]
                el = creation.find('./tei:origDate', ns)
                el.text = cont
            elif re.match('^[\s]*workOrigPlace', line):
                cont = re.findall('"([^"]*)"', line)[0]
                el = creation.find('./tei:origPlace', ns)
                el.text = cont
            elif re.match('^[\s]*workAuthor[^V]', line):
                cont = re.findall('"([^"]*)"', line)[0]
                el = creation.find('./tei:persName[@role="author"]', ns)
                el.text = cont
            elif re.match('^[\s]*workAuthorViaf', line):
                cont = re.findall('"([^"]*)"', line)[0]
                el = creation.find('./tei:persName[@role="author"]', ns)
                el.attrib['ref'] = 'http://viaf.org/' + cont
            elif re.match('^[\s]*workGenre', line):
                cont = re.findall('"([^"]*)"', line)[0]
                el = keywords.find('./tei:term[@type="workGenre"]', ns)
                el.text = cont
            elif re.match('^[\s]*workLangCode', line):
                cont = re.findall('"([^"]*)"', line)[0]
                el = root.find('./tei:teiHeader/tei:profileDesc/tei:langUsage/tei:language', ns)
                el.attrib['ident'] = cont
                facsimileLink += cont + "/"
            elif re.match('^[\s]*stemmaType', line):
                cont = re.findall('"([^"]*)"', line)[0]
                el = keywords.find('./tei:term[@type="stemmaType"]', ns)
                el.text = cont
            elif re.match('^[\s]*contam', line):
                cont = re.findall('"([^"]*)"', line)[0]
                el = keywords.find('./tei:term[@type="contam"]', ns)
                el.text = cont
            elif re.match('^[\s]*extraStemmContam', line):
                cont = re.findall('"([^"]*)"', line)[0]
                el = keywords.find('./tei:term[@type="extraStemmContam"]', ns)
                el.text = cont
            elif re.match('^[\s]*rootType', line):
                cont = re.findall('"([^"]*)"', line)[0]
                el = keywords.find('./tei:term[@type="rootType"]', ns)
                el.text = cont
            elif re.match('^[\s]*contributor[^O]', line):
                cont = re.findall('"([^"]*)"', line)[0]
                respStmt = et.SubElement(titleStmt, 'respStmt')
                resp = et.SubElement(respStmt, 'resp')
                resp.text = "contributed to OpenStemmata by"
                el = et.SubElement(respStmt, 'persName')
                el.text = cont
            elif re.match('^[\s]*contributorORCID', line):
                cont = re.findall('"([^"]*)"', line)[0]
                if len(cont) > 5:
                    el.attrib['ref'] = cont
            elif re.match('^[\s]*note', line):
                cont = re.findall('"([^"]*)"', line)[0]
                el = root.find('./tei:teiHeader/tei:fileDesc/tei:notesStmt/tei:note', ns)
                el.text = cont
            elif re.match('^[\s]+- witSigla', line):
                cont = re.findall('"([^"]*)"', line)[0]
                if cont != '':
                    wit = et.SubElement(listWit, 'witness', attrib= {'{http://www.w3.org/XML/1998/namespace}id': cont})
                    el = et.SubElement(wit, 'label', attrib= {'type': 'siglum'})
                    el.text = cont 
            elif re.match('^[\s]+witSignature', line):
                cont = re.findall('"([^"]*)"', line)[0]
                if cont != '':
                    split_cont = cont.split(',')
                    if len(split_cont) != 3:
                        el = et.SubElement(wit, 'idno')
                        el.text = cont
                    else:
                        settlement = et.SubElement(wit, 'settlement')
                        settlement.text = split_cont[0]
                        repository = et.SubElement(wit, 'repository')
                        repository.text = split_cont[1]
                        idno = et.SubElement(wit, 'idno')
                        idno.text = split_cont[2]
            elif re.match('^[\s]+witOrigDate', line):
                cont = re.findall('"([^"]*)"', line)[0]
                if cont != '':
                    el = et.SubElement(wit, 'origDate')
                    el.text = cont
            elif re.match('^[\s]+witOrigPlace', line):
                cont = re.findall('"([^"]*)"', line)[0]
                if cont != '':
                    el = et.SubElement(wit, 'origPlace')
                    el.text = cont
            elif re.match('^[\s]+witNotes', line):
                cont = re.findall('"([^"]*)"', line)[0]
                if cont != '':
                    el = et.SubElement(wit, 'note')
                    el.text = cont
            elif re.match('^[\s]+witMsDesc', line):
                cont = re.findall('"([^"]*)"', line)[0]
                if cont != '':
                    et.SubElement(wit, 'ptr', attrib={'type': 'description', 'target': cont})
            elif re.match('^[\s]+witDigit', line):
                cont = re.findall('"([^"]*)"', line)[0]
                if cont != '':
                    et.SubElement(wit, 'ptr', attrib={'type': 'digitised', 'target': cont})
        
        graphic = root.find('./tei:facsimile/tei:graphic', ns)
        graphic.attrib['url'] = facsimileLink + new_file_name + '/stemma.png?raw=true'

    if len(list(listWit)) == 0:
        # print("Zero")
        listWit.getparent().remove(listWit)


    # GRAPH
    
    graph.attrib['type'] = 'directed'
    graph.attrib['order'] = str(len(G.nodes))
    graph.attrib['size'] = str(len(G.edges))

    for node in G.nodes(data=True):
        nodeEl = et.SubElement(graph, 'node', attrib={'{http://www.w3.org/XML/1998/namespace}id': "n_" + node[0]})
        labelEl = et.SubElement(nodeEl, 'label')
        if 'label' in node[1]:
            label = node[1]['label']
            if not re.match(r'^\s*$', label):   
                labelEl.text = label   
            else:
                labelEl.text = ''  
        else:
            labelEl.text = node[0]  
        if 'color' in node[1]:
            color = node[1]['color']
            if color == 'grey':
                nodeEl.attrib['type'] = 'hypothetical'
            else:
                nodeEl.attrib['type'] = 'witness'
        else:
            nodeEl.attrib['type'] = 'witness'
        in_degree = G.in_degree(node[0])
        out_degree = G.out_degree(node[0])
        nodeEl.attrib['inDegree'] = str(in_degree)
        nodeEl.attrib['outDegree'] = str(out_degree)
        

                
    for edge in G.edges(data=True):
        edgeEl = et.SubElement(graph, 'arc', attrib= {'from': "#n_" + edge[0], 
            'to': "#n_" + edge[1],})
        
        if 'type' in edge[2]:
            edgeEl.attrib["{http://openstemmata.github.io/odd.html}type"] = edge[2]['type']
        else:
            edgeEl.attrib['{http://openstemmata.github.io/odd.html}type'] = 'filiation' 
        if 'cert' in edge[2]:
            edgeEl.attrib["cert"] = edge[2]['cert']
        




    tree.write( '/'.join(path) + '/' + new_file_name + '.tei.xml', pretty_print=True, encoding="UTF-8", xml_declaration=True)


        