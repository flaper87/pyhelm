import cStringIO
import itertools
import os
from git import Repo
import requests
import shutil
import tarfile
import tempfile
import yaml


def repo_index(repo_url, headers=None):
    """Downloads the Chart's repo index"""
    index_url = os.path.join(repo_url, 'index.yaml')
    index = requests.get(index_url, headers=headers)
    return yaml.load(index.content)


def from_repo(repo_url, chart, version=None, headers=None):
    """Downloads the chart from a repo."""
    _tmp_dir = tempfile.mkdtemp(prefix='pyhelm-')
    index = repo_index(repo_url, headers)

    if chart not in index['entries']:
        raise RuntimeError('Chart not found in repo')

    versions = index['entries'][chart]

    if version is not None:
        versions = itertools.ifilter(lambda k: k['version'] == version,
                                     versions)

    try:
        metadata = sorted(versions, key=lambda x: x['version'])[0]
        for url in metadata['urls']:
            fname = url.split('/')[-1]
            try:
                req = requests.get(url, stream=True, headers=headers)
                fobj = cStringIO.StringIO(req.content)
                tar = tarfile.open(mode="r:*", fileobj=fobj)
                tar.extractall(_tmp_dir)
                return os.path.join(_tmp_dir, chart)
            except:
                # NOTE(flaper87): Catch requests errors
                # and untar errors
                pass
    except IndexError:
        raise RuntimeError('Chart version %s not found' % version)


def git_clone(repo_url, branch='master', path=''):
    """clones repo to a /tmp/ dir"""

    _tmp_dir = tempfile.mkdtemp(prefix='pyhelm-', dir='/tmp')
    repo = Repo.clone_from(repo_url, _tmp_dir, branch=branch)

    return os.path.join(_tmp_dir, path)


def source_cleanup(target_dir):
    """Clean up source."""
    shutil.rmtree(target_dir)
