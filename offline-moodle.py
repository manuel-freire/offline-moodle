#!/usr/bin/python3

###
# Author: manuel.freire@fdi.ucm.es
# Several inspirations from https://github.com/asayler/moodle-ws-python/
#
# The latest version of this code can always be found at
#   https://github.com/manuel-freire/offline-moodle
###

import requests
from datetime import date, datetime
from timeit import default_timer as timer
import argparse
import os, re, json
from shutil import unpack_archive
from tempfile import mkstemp

class WSError(Exception):
    """Base class for WS Exceptions"""

    def __init__(self, *args, **kwargs):
        super(WSError, self).__init__(*args, **kwargs)

class MoodleAPI:
    """Talks to a moodle server"""

    def __init__(self, token: str, url: str):
        """ Constructor.
        
        token -- typically a 32-char hexadecimal digit. Find yours by navigating
            to your preferences / user account / security credentials
        url -- server url; for example, https://cvmdp.ucm.es/moodle/webservice/rest/server.php
        """

        self.token = token
        self.url = url
        self.session = requests.Session()
        # see parse_assignments_response, parse_submissions
        self.assignments = {}
        # see parse_enrolled_students
        self.users = {}
        self.groups = {}

    def make_request(self, function, params=None) -> str:
        """ Makes a post request expecting a JSON response from the API server.

            Used internally by all requests, except for those that request file contents.
            Read the web services API docs found wherever you found your token for details.
            function -- the name of the function endpoint to call
            params -- whatever parameters are expected for the corresponding API call
        """

        print(f"Requesting {function} with {params}...")
        url = f"{self.url}"
        args = {'moodlewsrestformat': 'json', 'wstoken': self.token, 'wsfunction': function}
        if params:
            args.update(params)
        try:
            start = timer()
            r = self.session.post(url, params=args)
            wait_ms = int((timer() - start) * 1000)
        except requests.exceptions.SSLError as e:
            msg = f"SSL verification for '{url}' with '{args}' failed: {e}"
            raise WSError(msg)
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            msg = f"Request to '{url} with '{args}' failed: {e}"
            raise WSError(msg)
        res = r.json()
        print(f"... result for {function} in {wait_ms} ms")
        if res:
            if 'exception' in res:
                msg = "{:s}: {:s}".format(res['errorcode'], res['message'])
                raise WSError(msg)
            else:
                return res
        else:
            return None

    def _build_array(self, key: str, vals: list) -> dict:
        """ Converts a python list into a moodle-ws "json array".

            given key=foo and vals=[bar,quix], output would be
            { 'foo[0]': bar,
              'foo[1]': quix }
        """
        array = {}
        index = 0
        for val in vals:
            array[f'{key}[{index}]'] = int(val)
            index += 1
        return array

    def block_recentlyaccesseditems_get_recent_items(self) -> str:
        """ Returns recently accessed items. Useful to test if the API connection works """

        return self.make_request("block_recentlyaccesseditems_get_recent_items")

    def core_course_get_contents(self, courseid: int) -> str:
        """ Returns contents of a course. """
        
        return self.make_request("core_course_get_contents", 
            params={'courseid': courseid})

    def core_enrol_get_enrolled_users(self, courseid: int) -> str:
        """ Returns all users and groups in a course. Includes all roles. """

        response = self.make_request("core_enrol_get_enrolled_users", 
            params={'courseid': courseid})
        self.parse_enrolled_response(response)
        return response

    def mod_assign_get_assignments(self, courseids: list[int]) -> str:
        """ Returns all assignments for specified courses. """

        params = {}
        params.update(self._build_array('courseids', courseids))
        response = self.make_request("mod_assign_get_assignments", params)
        self.parse_assignments_response(response)
        return response

    def mod_assign_get_submissions(self, assignmentids: list[int]) -> str:
        """ Returns all submissions in for specified assignmentids. """

        params = {}
        params.update(self._build_array('assignmentids', assignmentids))
        response = self.make_request("mod_assign_get_submissions", params)
        self.parse_submissions_response(response)
        return response

    def mod_assign_get_grades(self, assignmentids) -> str:
        """ Returns all grades for specified assignmentids. """

        params = {}
        params.update(self._build_array('assignmentids', assignmentids))
        return self.make_request("mod_assign_get_grades", params)


    def get_file(self, url, file_name) -> None:
        """ Retrieves a file from the given url and downloads it to file_name. """

        args = {'token': self.token}
        print(f'GET {url} -> {file_name}', end='')
        try:
            # see https://stackoverflow.com/a/16696317/15472
            with self.session.get(url, params=args, stream=True) as req:
                req.raw.decode_content = True # fix gzip encoding
                req.raise_for_status()
                with open(file_name, 'wb') as f:
                    for chunk in req.iter_content(chunk_size=8192): 
                        f.write(chunk)
        except Exception:
            print(f'Failed!')

    def parse_enrolled_response(self, 
                                response: str, 
                                rolename=None) -> tuple[dict[str, str], dict[str,str]]:
        """ Parses response from core_enrol_get_enrolled_users.

            Updates (and returns) self.users and self.groups, which map  
            from userid->username and from groupid->groupname respectively

            rolename -- if specified, SKIPS any users with a different rolename to this one
        """

        for u in response:
            r = ((u['roles'])[0])['shortname']
            if rolename != None and r != rolename:
                continue
            self.users[u['id']] = u['fullname'].title()
            for g in u['groups']:
                gid = g['id']
                if g['id'] not in self.groups:
                    self.groups[g['id']] = g['name']
        return self.users, self.groups

    def parse_submissions_response(self, response: str):
        """ Parses response from mod_assign_get_submissions

            Updates self.assignments[aid].submissions.
            Does not actually download submissions, merely notes who submitted, 
            when, the size, where to download it, uploaded filename, and filetype.
        """

        subs = []
        for a in response['assignments']:
            aid = a['assignmentid']
            for s in a['submissions']:
                uid = s['userid']
                gid = s['groupid']
                for p in s['plugins']:
                    if p['type'] == 'file':
                        for fa in p['fileareas']:
                            for f in fa['files']:
                                if aid not in self.assignments:
                                    self.assignments[aid] = {}
                                assignment = self.assignments[aid]
                                if 'submissions' not in assignment:
                                    assignment['submissions'] = []
                                subs = assignment['submissions']

                                dt = datetime.fromtimestamp(s['timemodified'])
                                subs.append({
                                    'gid': gid,
                                    'uid': uid,
                                    'file_name': f['filename'],
                                    'file_url': f['fileurl'],
                                    'file_size': f['filesize'],
                                    'file_type': f['mimetype'],
                                    'file_time': str(dt)
                                })
        return self.assignments

    def parse_assignments_response(self, response: str):
        """ Parses response from mod_assign_get_assignments """

        for c in response['courses']:
            cid = c['id']
            for a in c['assignments']:
                aid = a['id']
                name = a['name']
                dt = datetime.fromtimestamp(a['duedate'])
                if aid not in self.assignments:
                    self.assignments[aid] = {}
                assignment = self.assignments[aid]
                assignment['name'] = name
                assignment['date'] = str(dt)
        return self.assignments

def dump_response(result, output_file):
    """ Dumps a JSON response into a file, pretty-printed. """

    with open(output_file, 'w', encoding="utf-8") as output_f:
        json.dump(result, output_f, ensure_ascii=False, sort_keys=False, indent=2)

def load_response(input_file):
    """ Loads a JSON response from a file, so that it can be parsed, for example. """

    with open(input_file, 'r', encoding="utf-8") as input_f:
        return json.load(input_f)

def download_submissions(submission_info, api):
    for aid, a_subs in submission_info.items():
        for sub in a_subs:
            submitter = max(sub['gid'], sub['uid'])
            api.get_file(sub['file_url'], submitter)

def main(config_file, output_file):  

    with open(config_file, 'r') as config_f:
        config = json.load(config_f)

    cid = 51447

    api = MoodleAPI(config["wstoken"], config["url"])
    api.core_enrol_get_enrolled_users(cid)
    api.mod_assign_get_assignments([cid])
    api.mod_assign_get_submissions(api.assignments.keys())

    aids: list[int] = []
    for aid, a in api.assignments.items():
        if 'submissions' in a:
            aids.append(aid)
            print(f"{len(aids)}\t -- {a['name']} (due {a['date']}, {len(a['submissions'])} submissions)")
    try:
        choice: int = int(input("Index of assignment to download? (0 to cancel): "))
    except:
        return None
    if choice <= 0 or choice > len(aids): return None
    assignment = api.assignments[aids[choice]]
    print(f"Ah, {assignment['name']} {aids[choice]} excellent choice!")

    for submission in assignment['submissions']:
        if submission['gid'] != '0':
            name = api.groups[submission['gid']]
        else:
            name = api.users[submission['uid']]
        if submission['file_type'] == 'application/zip':
            temp = mkstemp()
            try:
                api.get_file(submission['file_url'], temp)
                unpack_archive(temp, name)
            finally:
                os.remove(temp)
        else:
            api.get_file(submission['file_url'], name)

    ## TODO: 
    #   - add initial file with template for results
    #   - add upload-scores-from-template capability; testing this may
    #     be tricky.

if __name__ == '__main__':	
    parser = argparse.ArgumentParser(description=\
        "Download Moodle assignment for offline correction; and upload feedback to Moodle.")
    parser.add_argument("--config_file", 
            help="Configuration file to use, with credentials. Default is 'config.json'")        
    parser.add_argument("--output_file", 
            help="Where to write the output")             
    args = parser.parse_args()
    
    main(
        args.config_file, 
        args.output_file)
    