import json
import time

import requests
import difflib
from collections import namedtuple

import js2py
from requests import RequestException

from bogi.callbacks import CallbackBase
from bogi.response_handler import HttpClient, HttpResponse

from bogi.parser.tail_transformer import ContentLine, InputFileRef

TestFailure = namedtuple('TestFailure', ['request', 'error', 'response_time'])
TestSuccess = namedtuple('TestSuccess', ['request', 'latency', 'response_time'])
CompareJob = namedtuple('CompareJob', ['req', 'resp', 'request_id'])


class HttpRunner:
    response_handler_scripts = dict()

    def __init__(self, _requests, ignore_headers, base_dir=None, callback=None):
        if callback is None:
            callback = CallbackBase()
        self._requests = _requests
        self._ignore_headers = ignore_headers
        self.callback = callback
        self.base_dir = base_dir
        self.session = requests.Session()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.session.close()

    def run(self):
        resp_by_id = {}
        compare_jobs = []

        for req in self._requests:
            response_time = -1  # time between sending the request and finishing parsing the entire response
            latency = -1    # time between sending the request and finishing parsing the response headers
            try:
                resp, response_time = self._execute_request(req)
                latency = resp.elapsed.total_seconds() * 100
            except RequestException as e:
                self.callback.failure(TestFailure(request=req,
                                                  response_time=-1,
                                                  error=f'Error issuing the request, root cause: {str(e)}'))
                continue

            if req.id:
                resp_by_id[req.id] = resp

            if req.tail.response_handler:
                h = req.tail.response_handler
                if h.expected_status_code and resp.status_code != h.expected_status_code:
                    self.callback.failure(TestFailure(request=req,
                                                      response_time=response_time,
                                                      error=f'Expected status code {h.expected_status_code},'
                                                            f' but got {resp.status_code}'))
                    break

                # Supporting loading scripts from paths, e.g. `> scripts/my-my-script.js`
                response_handler_script = None
                if h.path:
                    if h.path not in self.response_handler_scripts:
                        with open(self.base_dir + '/' + h.path, 'r', encoding='utf-8') as file:
                            self.response_handler_scripts[h.path] = file.read()
                    response_handler_script = self.response_handler_scripts[h.path]
                elif h.script:
                    response_handler_script = h.script

                if response_handler_script:
                    # Response handler script should be written in JavaScript ECMAScript 5.1 specification.
                    # See examples in
                    # https://www.jetbrains.com/help/webstorm/http-response-handling-examples.html#script-var-example
                    # TODO support a python variant
                    context = js2py.EvalJs(
                        {
                            'client': HttpClient(),
                            'response': HttpResponse(resp),
                        }
                    )

                    try:
                        context.execute(response_handler_script)
                    except js2py.internals.simplex.JsException as e:
                        self.callback.failure(TestFailure(request=req,
                                                          response_time=response_time,
                                                          error=str(e).replace('Error: your Python function failed!  ', '')))

            if req.tail.response_ref:
                compare_jobs.append(CompareJob(req=req,
                                               resp=resp,
                                               request_id=req.tail.response_ref.path))

            self.callback.success(TestSuccess(request=req, latency=latency, response_time=response_time))

        for job in compare_jobs:
            cmp_resp = resp_by_id.get(job.request_id)
            if cmp_resp is None:
                req_ids = list(resp_by_id.keys())
                error = 'Request with id "{}" not found. Defined requests: {}'.format(job.request_id, req_ids)
                self.callback.failure(TestFailure(request=job.req,
                                                  response_time=job.resp.elapsed.total_seconds() * 100,
                                                  error=error))
                continue

            diff = self._diff_responses(job.resp, cmp_resp)
            if diff:
                self.callback.failure(TestFailure(request=job.req, response_time=job.resp.elapsed.total_seconds() * 100,
                                                  error=diff))

        return self.callback

    def _execute_request(self, req):
        headers = {
            header.field: header.value
            for header in req.headers
        }
        data = self._request_payload(req)

        allow_redirects = True
        if '@no-redirect' in req.options:
            allow_redirects = False

        no_cookie_jar = False
        if '@no-cookie-jar' in req.options:
            no_cookie_jar = True

        if no_cookie_jar:
            start = time.time()
            resp = requests.request(req.method, req.target, headers=headers, data=data,
                                    allow_redirects=allow_redirects)
        else:
            start = time.time()
            resp = self.session.request(req.method, req.target, headers=headers, data=data,
                                        allow_redirects=allow_redirects)
        return resp, (time.time() - start) * 100

    def _diff_responses(self, resp1, resp2):
        if resp1.status_code != resp2.status_code:
            return "Status code mismatch. {} != {}".format(resp1.status_code, resp2.status_code)

        if not self._ignore_headers and resp1.headers != resp2.headers:
            headers1 = self._headers_to_list(resp1.headers)
            headers2 = self._headers_to_list(resp2.headers)
            diff = ''.join(difflib.ndiff(headers1, headers2))
            return "Response headers mismatch.\n{}".format(diff)

        try:
            json1, json2 = resp1.json(), resp2.json()
            if json1 != json2:
                return "Response body mismatch."
        except (json.decoder.JSONDecodeError, UnicodeDecodeError, TypeError) as e:
            if resp1.text != resp2.text:
                return "Response body mismatch. Encountered error while comparing: %s" % e

        return None

    def _request_payload(self, req):
        if req.tail.message_body is None:
            return None

        encoding = req.charset or 'utf-8'
        res = []

        for part in req.tail.message_body.messages:
            if type(part) is ContentLine:
                res.append(part.content)
            elif type(part) is InputFileRef:
                with open(part.path, 'r', encoding=encoding) as f:
                    res.append(f.read())
        return ''.join(res)

    def _headers_to_list(self, headers):
        return [key + ': ' + val + '\n' for key, val in headers.items()]

