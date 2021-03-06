__author__ = 'faye'
from scrapi_tools import lint
from scrapi_tools.document import RawDocument, NormalizedDocument
import requests
import xmltodict
import json
import time
from datetime import date, timedelta
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import settings

TODAY = str(date.today()) + "T00:00:00Z"
YESTERDAY = str(date.today() - timedelta(4)) + "T00:00:00Z"
MAX_ROWS_PER_REQUEST = 999

NAME = 'PLoS'


def consume():
    payload = {"api_key": settings.API_KEY, "rows": "0"}
    base_url = 'http://api.plos.org/search?q=publication_date:[{}%20TO%20{}]'.format(YESTERDAY, TODAY)
    plos_request = requests.get(base_url, params=payload)
    response = xmltodict.parse(plos_request.text)
    num_articles = int(response["response"]["result"]["@numFound"])

    start = 0
    rows = MAX_ROWS_PER_REQUEST
    doc_list = []

    while rows < num_articles + MAX_ROWS_PER_REQUEST:
        payload = {"api_key": settings.API_KEY, "rows": rows, "start": start}
        results = requests.get(base_url, params=payload)
        tick = time.time()

        doc = xmltodict.parse(results.text)

        full_response = doc["response"]["result"]["doc"]

        # TODO Incooporate "Correction" article type
        try:
            for result in full_response:
                try:
                    if result["arr"][1]["@name"] == "abstract" and result["str"][3]["#text"] == "Research Article":
                        doc_list.append(RawDocument({
                            'doc': json.dumps(result, indent=4, sort_keys=True),
                            'source': NAME,
                            'doc_id': result["str"][0]["#text"],
                            'filetype': 'json',
                        }))
                except KeyError:
                    pass

            start += MAX_ROWS_PER_REQUEST
            rows += MAX_ROWS_PER_REQUEST

            if time.time() - tick < 5:
                time.sleep(5 - (time.time() - tick))
        except KeyError:
            print "No new files/updates!"
            break

    return doc_list


def normalize(raw_doc, timestamp):
    raw_doc = raw_doc.get('doc')
    record = json.loads(raw_doc)

    return NormalizedDocument({
        'title': record["str"][4]["#text"],
        'contributors': [{
            'email': '',
            'full_name': name,
        } for name in record["arr"][0]["str"]],
        'properties': {
            'description': record["arr"][1]["str"],
        },
        'meta': {},
        'id': record["str"][0]["#text"],
        'source': NAME,
        'timestamp': timestamp
    })

if __name__ == '__main__':
    print(lint(consume, normalize))
