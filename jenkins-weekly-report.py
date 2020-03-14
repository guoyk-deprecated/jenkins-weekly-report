#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import time
from datetime import datetime, timedelta
from os import path
from typing import List, Dict

import requests
from jinja2 import Template


def list_job_names(jenkins_url, jenkins_user, jenkins_token) -> List[str]:
    resp = requests.get(f'{jenkins_url}/api/json', params={'tree': 'jobs[name]'},
                        auth=(jenkins_user, jenkins_token)).json()
    return [job['name'] for job in resp['jobs']]


def count_job_builds(jenkins_url, jenkins_user, jenkins_token, job_name, timestamp) -> (int, int, List[Dict]):
    offset, limit, success, not_success, builds = 0, 5, 0, 0, []
    while True:
        resp = requests.get(f'{jenkins_url}/job/{job_name}/api/json',
                            params={'tree': 'builds[number,timestamp,result]{' + str(offset) + ',' + str(
                                offset + limit) + '}'},
                            auth=(jenkins_user, jenkins_token)).json()
        # break if no builds fetched
        if len(resp['builds']) == 0:
            break
        # find builds with timestamp greater than given timestamp
        end = False
        for build in resp['builds']:
            # mark search end if found timestamp less than given timestamp
            if build['timestamp'] < timestamp:
                end = True
                break
            # increase ether success or not_success
            if build['result'] == 'SUCCESS':
                success = success + 1
            else:
                not_success = not_success + 1
            # append builds
            builds.append({
                'number': build['number'],
                'success': build['result'] == 'SUCCESS',
                'timestamp': datetime.fromtimestamp(build['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S'),
            })
        # if end marked break loop
        if end:
            break
        # next page
        offset += limit
    return success, not_success, builds


TMPL = """
<!DOCTYPE html>
<html>

<head>
    <title>{{report_name}} {{report_date}}</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="stylesheet" href="//cdn.jsdelivr.net/npm/neoflat@4.4.1/dist/neoflat/bootstrap.min.css" />
    <link rel="stylesheet" href="//cdn.jsdelivr.net/npm/font-awesome@4.7.0/css/font-awesome.min.css" />
</head>

<body>
    <div class="container">
        <div class="row mt-3 mb-3">
            <div class="col-md-12">
                <h5><a href="../"><i class="fa fa-arrow-circle-o-up"></i>&nbsp;<i class="fa fa-folder-open"></i>&nbsp;<b>../</b></a></h5>
            </div>
 
            <div class="col-md-12">
                <h5>Jenkins Weekly Report</h5>
            </div>
            <div class="col-md-6">
                <h4><b>{{report_name}} {{report_date}}</b></h4>
            </div>
            <div class="col-md-6 text-right">
                <h5>
                    <span><i class="fa fa-cogs"></i>&nbsp;&nbsp;<b>{{total_total}}</b></span>&nbsp;&nbsp;
                    <span class="text-success"><i
                            class="fa fa-check-circle"></i>&nbsp;&nbsp;<b>{{total_success}}</b></span>&nbsp;&nbsp;
                    <span class="text-danger"><i
                            class="fa fa-exclamation-triangle"></i>&nbsp;&nbsp;<b>{{total_not_success}}</b></span>
                </h5>
            </div>
        </div>
        <div class="row">
            <div class="col-md-12">
                <table class="table table-sm table-hover">
                    <tbody>
                        {% for item in data %}
                        <tr class="table-light">
                            <td>
                                <a class="text-primary" href="{{public_url}}/job/{{item.job_name}}" target="_blank">
                                    <b><i class="fa fa-cube"></i>&nbsp;&nbsp;{{ item.job_name }}</b>
                                </a>
                            </td>
                            <td>
                                <span><i class="fa fa-cogs"></i>&nbsp;&nbsp;<b>{{ item.total }}</b>&nbsp;&nbsp;</span>
                                <span class="text-success"><i
                                        class="fa fa-check-circle"></i>&nbsp;&nbsp;<b>{{ item.success }}</b>&nbsp;&nbsp;</span>
                                <span class="text-danger"><i
                                        class="fa fa-exclamation-triangle"></i>&nbsp;&nbsp;<b>{{ item.not_success }}</b>&nbsp;&nbsp;</span>
                            </td>
                        </tr>
                        {% for build in item.builds %}
                        <tr>
                            <td class="pl-5" colspan="2">
                                <a class="text-primary" href="{{public_url}}/job/{{item.job_name}}/{{build.number}}"
                                    target="_blank">
                                    {% if build.success %}
                                    <span class="text-success"><i class="fa fa-check-circle"></i></span>
                                    {% else %}
                                    <span class="text-danger"><i class="fa fa-exclamation-triangle"></i></span>
                                    {% endif %}
                                    <span>&nbsp;&nbsp;{{build.timestamp}}&nbsp;<b>(#{{ build.number }})</b></span>
                                </a>
                            </td>
                        </tr>
                        {% endfor %}
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>

</html>
"""


def main():
    parser = argparse.ArgumentParser(description='Generate Weekly Report of Jenkins Builds')
    parser.add_argument('--url', dest='url', type=str, help='jenkins url')
    parser.add_argument('--public-url', dest='public_url', type=str, help='jenkins public url')
    parser.add_argument('--user', dest='user', type=str, help='jenkins user')
    parser.add_argument('--token', dest='token', type=str, help='jenkins user token')
    parser.add_argument('--dir', dest='dir', type=str, default='.', help='dir of report')
    parser.add_argument('--report-name', dest='report_name', type=str, default='', help='name of report')
    args = parser.parse_args()

    beginning_of_week = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    beginning_of_week -= timedelta(days=beginning_of_week.weekday())

    report_date = time.strftime("%Y-%m-%d", time.localtime())

    data = []

    total_success, total_not_success = 0, 0
    job_names = list_job_names(args.url, args.user, args.token)
    for i, job_name in enumerate(job_names):
        success, not_success, builds = count_job_builds(args.url, args.user, args.token, job_name,
                                                        int(beginning_of_week.timestamp() * 1000))
        print(f'{i + 1}/{len(job_names)}: {job_name}')
        if success > 0 or not_success > 0:
            total_success += success
            total_not_success += not_success
            data.append({
                'job_name': job_name,
                'success': success,
                'not_success': not_success,
                'total': success + not_success,
                'builds': builds,
            })
            break

    Template(TMPL).stream(
        data=data,
        public_url=args.public_url,
        report_name=args.report_name,
        report_date=report_date,
        total_success=total_success,
        total_not_success=total_not_success,
        total_total=total_success + total_not_success,
    ).dump(
        path.join(args.dir, f'REPORT-{report_date}.html')
    )


if __name__ == '__main__':
    main()
