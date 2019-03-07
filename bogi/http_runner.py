import requests
import difflib
from collections import namedtuple

from bogi.parser.tail_transformer import ContentLine, InputFileRef

TestFailure = namedtuple('TestFailure', ['request', 'error'])
CompareJob = namedtuple('CompareJob', ['req', 'resp', 'request_id'])


class HttpRunner:

    def __init__(self, requests, ignore_headers):
        self._requests = requests
        self._ignore_headers = ignore_headers

    def run(self):
        resp_by_id = {}
        compare_jobs = []
        failures = []

        for req in self._requests:
            resp = self._execute_request(req)
            if req.id:
                resp_by_id[req.id] = resp

            if req.tail.response_handler:
                # TODO
                pass

            if req.tail.response_ref:
                compare_jobs.append(CompareJob(req=req,
                                               resp=resp,
                                               request_id=req.tail.response_ref.path))

        for job in compare_jobs:
            cmp_resp = resp_by_id.get(job.request_id)
            if cmp_resp is None:
                req_ids = list(resp_by_id.keys())
                error = 'Request with id "{}" not found. Defined requests: {}'.format(job.request_id, req_ids)
                failures.append(TestFailure(request=job.req,
                                            error=error))
                continue

            diff = self._diff_responses(job.resp, cmp_resp)
            if diff:
                failures.append(TestFailure(request=job.req, error=diff))

        return failures

    def _execute_request(self, req):
        headers = {
            header.field: header.value
            for header in req.headers
        }
        data = self._request_payload(req)
        return requests.request(req.method, req.target, headers=headers, data=data)

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
        except:
            if resp1.text != resp2.text:
                return "Response body mismatch."

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
