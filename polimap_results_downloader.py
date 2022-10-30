import clarify
import csv
import os
from pathlib import Path
import requests
from zipfile import ZipFile


class ResultsDownloader:
    def __init__(self, election_owner, election_id, contest_name,
                 contest_shortname, formatted_candidate_names, downloaded):
        self.base_url = 'https://results.enr.clarityelections.com/%s/%s' % (
            election_owner, election_id)
        self.election_id = election_id
        self.contest_name = contest_name
        self.contest_shortname = contest_shortname
        self.formatted_candidate_names = formatted_candidate_names
        self.downloaded = downloaded
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36",
          

        Path("downloads").mkdir(exist_ok=True)
        Path("output").mkdir(exist_ok=True)

    def fetch_and_parse_results(self):
        results_filename = 'downloads/detailxml-%s' % self.election_id

        if not self.downloaded:
            current_ver_response = requests.get(
                self.base_url + '/current_ver.txt')
            current_ver_response.raise_for_status()

            results_response = requests.get(
                self.base_url +
                '/' +
                current_ver_response.text +
                '/reports/detailxml.zip',
                headers={
                    'Accept-Encoding': 'gzip'},
                stream=True)
            results_response.raise_for_status()

            with open('%s.zip' % results_filename, 'wb') as file:
                for chunk in results_response.iter_content(chunk_size=128):
                    file.write(chunk)

            with ZipFile('%s.zip' % results_filename, 'r') as zip:
                path = os.path.splitext(results_filename)[0]
                zip.extractall(path=path)

        clarity_parser = clarify.Parser()
        clarity_parser.parse('%s/detail.xml' % results_filename)

        self.contest_results = [
            r for r in clarity_parser.results if r.choice
            and r.jurisdiction
            and r.contest.text == self.contest_name]

    def process_precincts(self):
        filename = "output/results-precinct-%s-%s.csv" % (
            self.election_id, self.contest_shortname)

        with open(filename, "wt") as csvfile:
            w = csv.writer(csvfile)
            w.writerow(['jurisdiction', 'party',
                       'candidate', 'vote_type', 'votes'])

            for result in self.contest_results:
                name = result.choice.text
                if name in self.formatted_candidate_names:
                    name = self.formatted_candidate_names[name]

                w.writerow([
                    result.jurisdiction.name,
                    result.choice.party,
                    name,
                    result.vote_type,
                    result.votes
                ])

    def run(self):
        self.fetch_and_parse_results()
        self.process_precincts()