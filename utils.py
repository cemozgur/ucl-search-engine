# -*- coding: utf-8 -*-
"""
Created on Sun Feb 26 22:28:04 2017

@author: Zhengyi, Yuan
"""

import urlparse
import requests
import argparse
from urllib import urlencode

from bs4 import BeautifulSoup
from tabulate import tabulate


def get_google(query, max_rows=10, num=None):
    max_rows = max_rows * 2

    results = []
    num = min(max_rows, 100)

    url = "https://www.google.co.uk/search?" + urlencode({'q': query}) + \
          "+site:cs.ucl.ac.uk&start={start}&num=" + str(num)

    useragent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'

    i = 0

    while 1:
        r = requests.get(url.format(start=i),
                         headers={'User-agent': useragent})
        data = r.text
        soup = BeautifulSoup(data, "lxml")

        found = soup.select('.srg .g .r a')
        if not found:
            break

        for result in found:
            domain = result.attrs['href']
            results.append(domain)
            if len(results) >= max_rows:
                return results

        i += num

    return results


def get_ucl_cs(query, max_rows=10):

    results = []

    url = 'http://search2.ucl.ac.uk/s/search.html?' + \
        urlencode({'query': query}) + \
        '&Submit=&collection=ucl-public-meta&subsite=cs&start_rank={start}'

    i = 1
    while 1:
        r = requests.get(url.format(start=i))
        data = r.text
        soup = BeautifulSoup(data, "lxml")

        fb_results = soup.find('ol', {'id': 'fb-results'})

        found = fb_results.findAll('cite')
        if not found:
            break

        for result in found:
            domain = result.text
            results.append(domain)
            if len(results) >= max_rows:
                return results
        i += 10

    return results


def get_ucl(query, max_rows=10):
    results = []

    url = 'https://search2.ucl.ac.uk/s/search.html?' + urlencode({'query': query}) +  \
        '&collection=website-meta&profile=_website&tab=websites&submit=Go&start_rank={start}'

    i = 1
    while 1:
        r = requests.get(url.format(start=i))
        data = r.text
        soup = BeautifulSoup(data, "lxml")

        found = soup.findAll('a', {'class': 'result__link'})
        if not found:
            break

        for result in found:
            domain = result.text
            if urlparse.urlparse(domain).netloc.endswith('cs.ucl.ac.uk'):
                results.append(domain)
                if len(results) >= max_rows:
                    return results
        i += 10

    return results


def get_solr(query, max_rows=10):
    url = 'http://138.68.161.137:8983/solr/ucl/select?wt=json&rows=' + str(max_rows) +\
          '&fl=url&' + urlencode({'q': query})

    json_response = requests.get(url).json()

    response = [r['url'][0] for r in json_response['response']['docs']]

    return response


def url_normalize(url):
    parsed = urlparse.urlparse(url)
    scheme = "%s://" % parsed.scheme
    normalized = parsed.geturl().replace(scheme, '', 1)
    return normalized


if __name__ == '__main__':
    import os
    import json
    from collections import defaultdict

    parser = argparse.ArgumentParser()
    parser.add_argument('query', help='query')
    parser.add_argument('-r', nargs='?', dest='rows', type=int, default=10,
                        help='the number of results')
    parser.add_argument('-o', nargs='?', dest='output', default=None,
                        help='output path to save the results in json')
    parser.add_argument('-g', dest='google', action='store_true', help='query google')
    parser.add_argument('-u', dest='ucl', action='store_true', help='query ucl')
    args = parser.parse_args()

    query = args.query
    rows = args.rows
    output = args.output
    query_google = args.google
    query_ucl = args.ucl

    if os.path.isfile(query):
        with open(query) as f:
            queries = f.readlines()
        queries = filter(lambda q: q and not q.startswith(
            '#'), map(str.strip, queries))
        print len(queries), ' queries'
    else:
        queries = [query]

    result_dict = defaultdict(dict)

    for i, q in enumerate(queries):
        result_dict['solr'][q] = solr_result = get_solr(q, rows)
        if query_google:
            result_dict['google'][q] = google_result = get_google(q, rows)
        if query_ucl:
            result_dict['ucl'][q] = url_result = get_ucl_cs(q, rows)

        if query_google and query_ucl:
            result = zip(range(1, rows + 1), google_result,
                         url_result, solr_result)
            headers = ['', 'google', 'ucl', 'solr']
        elif query_google:
            result = zip(range(1, rows + 1), google_result, solr_result)
            headers = ['', 'google', 'solr']
        elif query_ucl:
            result = zip(range(1, rows + 1), url_result, solr_result)
            headers = ['', 'ucl', 'solr']
        else:
            result = zip(range(1, rows + 1), solr_result)
            headers = ['', 'solr']

        print 'search ', i, ': ', q
        print tabulate(result, headers=headers, tablefmt='simple')

    if output is not None:
        with open(output, 'w') as f:
            json.dump(result_dict['solr'], f, indent=2, sort_keys=True)
        if query_google:
            with open('google_%s' % output, 'w') as f:
                json.dump(result_dict['google'], f)
        if query_ucl:
            with open('ucl_%s' % output, 'w') as f:
                json.dump(result_dict['ucl'], f)



