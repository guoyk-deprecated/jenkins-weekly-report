#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import time
from datetime import datetime, timedelta
from os import path

import requests
from jinja2 import Template


def list_job_names(jenkins_url, jenkins_user, jenkins_token):
    resp = requests.get(f'{jenkins_url}/api/json', params={'tree': 'jobs[name]'},
                        auth=(jenkins_user, jenkins_token)).json()
    return [job['name'] for job in resp['jobs']]


def count_job_builds(jenkins_url, jenkins_user, jenkins_token, job_name, timestamp):
    offset, limit, success, not_success = 0, 5, 0, 0
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
        # if end marked break loop
        if end:
            break
        # next page
        offset += limit
    return success, not_success


TMPL = """
<!DOCTYPE html>
<html>
    <head>
        <title>{{report_name}} {{report_date}}</title>
        <meta charset="utf-8" />
        <link rel="stylesheet" href="//cdn.jsdelivr.net/npm/neoflat@4.4.1/dist/neoflat/bootstrap.min.css" integrity="sha256-GNVjGVdZcMXJDF/FzQvaoP9Zlt7UuNvym/1i60c4tf0=" crossorigin="anonymous">
        <link rel="stylesheet" href="//cdn.jsdelivr.net/npm/font-awesome@4.7.0/css/font-awesome.min.css" integrity="sha256-eZrrJcwDc/3uDhsdt61sL2oOBY362qM3lon1gyExkL0=" crossorigin="anonymous">
    </head>
    <body>
        <div class="container">
            <div class="row mt-3 mb-3">
                <div class="col-md-12">
                    <h4>Jenkins Weekly Report</h4>
                    <h3>
                        {{report_name}} {{report_date}}&nbsp;&nbsp;
                        <small>
                        <span><i class="fa fa-cogs"></i> {{total_total}}</span>&nbsp;&nbsp;
                        <span class="text-success"><i class="fa fa-check-circle"></i> {{total_success}}</span>&nbsp;&nbsp;
                        <span class="text-danger"><i class="fa fa-exclamation-triangle"></i> {{total_not_success}}</span>&nbsp;&nbsp;
                        </small>
                    </h3>
                </div>
            </div>
            <div class="row">
                <div class="col-md-12">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th><i class="fa fa-cube"></i> Job Name</th>
                                <th><i class="fa fa-cogs"></i></th>
                                <th class="text-success"><i class="fa fa-check-circle"></i></th>
                                <th class="text-danger"><i class="fa fa-exclamation-triangle"></i></th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for item in data %}
                            <tr>
                                <td><b>{{ item.job_name }}</b></td>
                                <td>{{ item.total }}</td>
                                <td class="text-success">{{ item.success }}</td>
                                <td class="text-danger">{{ item.not_success }}</td>
                            </tr>
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
    for job_name in job_names:
        success, not_success = count_job_builds(args.url, args.user, args.token, job_name,
                                                int(beginning_of_week.timestamp() * 1000))
        if success > 0 or not_success > 0:
            total_success += success
            total_not_success += not_success
            data.append(
                {'job_name': job_name, 'success': success, 'not_success': not_success, 'total': success + not_success})

    Template(TMPL).stream(
        data=data,
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
