#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import time
from datetime import datetime, timedelta
from os import path

import requests


def list_job_names(jenkins_url, jenkins_user, jenkins_token):
    resp = requests.get(f'{jenkins_url}/api/json', params={'tree': 'jobs[name]'},
                        auth=(jenkins_user, jenkins_token)).json()
    return [job['name'] for job in resp['jobs']]


def list_job_builds(jenkins_url, jenkins_user, jenkins_token, job_name, timestamp):
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


def main():
    parser = argparse.ArgumentParser(description='Generate Weekly Report of Jenkins Builds')
    parser.add_argument('--url', dest='url', type=str, help='jenkins url')
    parser.add_argument('--user', dest='user', type=str, help='jenkins user')
    parser.add_argument('--token', dest='token', type=str, help='jenkins user token')
    parser.add_argument('--dir', dest='dir', type=str, default='.', help='dir of report')
    args = parser.parse_args()

    beginning_of_week = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    beginning_of_week -= timedelta(days=beginning_of_week.weekday())

    f = open(path.join(args.dir, f'REPORT-{time.strftime("%Y-%m-%d", time.localtime())}.csv'), 'w')

    f.write('JOB_NAME, SUCCESS, NOT_SUCCESS, TOTAL\n')

    job_names = list_job_names(args.url, args.user, args.token)
    for job_name in job_names:
        success, not_success = list_job_builds(args.url, args.user, args.token, job_name,
                                               int(beginning_of_week.timestamp() * 1000))
        if success > 0 or not_success > 0:
            f.write(f'{job_name}, {success}, {not_success}, {success + not_success}\n')

    f.close()


if __name__ == '__main__':
    main()
