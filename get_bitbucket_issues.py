#!/usr/bin/env python
# encoding: utf-8

from __future__ import unicode_literals

import os
import sys
import json

from collections import namedtuple

import requests

from requests.auth import HTTPBasicAuth

_USERNAME = None
_PASSWORD = None

Issue = namedtuple('Issue', ['id', 'title', 'priority', 'url'])


class NotFoundError(Exception):
    pass


class Query(object):
    REPOSITORY = 0
    ISSUES = 1

URLS = {
    Query.REPOSITORY: 'https://bitbucket.org/api/1.0/user/repositories/',
    Query.ISSUES:     ('https://bitbucket.org/api/1.0/repositories/'
                       '{owner}/{slug}/issues/'),
}


def main():
    if not get_credentials():
        return 1

    sys.stdout.write('<html><ul>')
    for repo in run_query(Query.REPOSITORY):
        (owner, slug) = (repo['owner'], repo['slug'])
        sys.stderr.write('{}/{}\n'.format(owner, slug))
        for issue in get_issues_for_repo(owner, slug):
            write_issue_html(owner, slug, issue)
    sys.stdout.write('</ul></html>')
    return 0


def get_credentials():
    global _USERNAME
    global _PASSWORD
    try:
        _USERNAME = os.environ['BITBUCKET_USERNAME']
        _PASSWORD = os.environ['BITBUCKET_PASSWORD']
    except KeyError:
        sys.stderr.write("No BitBucket credentials in environment:\n")
        sys.stderr.write('$ export BITBUCKET_USERNAME="your username"\n')
        sys.stderr.write('$ export BITBUCKET_PASSWORD="your password"\n')
        return False
    else:
        return True


def run_query(query, **args):
    url = URLS[query]
    url = url.format(**args)
    response = requests.get(url, auth=HTTPBasicAuth(_USERNAME, _PASSWORD))
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        if response.status_code == 404:  # not found
            raise NotFoundError(url)
        raise
    return json.loads(response.content)


def write_issue_html(owner, slug, issue):
    sys.stdout.write('<li>{owner}/{slug} <a href="{url}">#{id} '
                     '"{title}"</a></li>\n'.format(
                     url=issue.url,
                     owner=owner,
                     slug=slug,
                     id=issue.id,
                     title=issue.title))


def get_issues_for_repo(owner, slug):
    try:
        result = run_query(Query.ISSUES, owner=owner, slug=slug)
    except NotFoundError as e:
        sys.stderr.write('{}\n'.format(repr(e)))
        return

    for issue in result['issues']:
        if issue['status'] == 'resolved':
            continue
        yield Issue(
            id=issue['local_id'],
            title=issue['title'],
            priority=issue['priority'],
            url=make_issue_url(owner, slug, issue['local_id']))


def make_issue_url(owner, slug, issue_id):
    """
    >>> make_issue_url('scraperwikids', 'my_repo', '11')
    u'https://bitbucket.org/scraperwikids/my_repo/issue/11'
    """
    return 'https://bitbucket.org/{}/{}/issue/{}'.format(
        owner, slug, issue_id)


if __name__ == '__main__':
    sys.exit(main())
