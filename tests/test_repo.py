from __future__ import unicode_literals
from unittest import TestCase
try:
    from unittest import mock
except ImportError:
    import mock

import os
import yaml
import requests
import pyhelm.repo as repo
from botocore.exceptions import ClientError

class TestRepo(TestCase):
    _http404 = requests.Response()
    _http404.status_code = 404

    _index = u'''
apiVersion: v1
entries:
  foo:
  - name: foo
    urls:
    - foo-0.1.0.tgz
    version: 0.1.2
  - name: foo
    urls:
    - foo-0.1.12.tgz
    version: 0.1.12
  bar:
  - name: bar
    urls:
    - http://test/bar-0.1.0.tgz
    version: 0.1.0
'''

    def test_wrong_scheme(self):
        with self.assertRaises(repo.SchemeError):
            repo.repo_index('ssh://test')

    @mock.patch('pyhelm.repo.requests.get', return_value=_http404)
    @mock.patch('pyhelm.repo.tempfile.mkdtemp', return_value='')
    def test_not_found(self, _0, _1):
        with self.assertRaises(repo.HTTPGetError):
            repo.from_repo('http://test', '')
        repo.requests.get.assert_called_once_with(
            os.path.join('http://test', 'index.yaml'), headers=None)

    @mock.patch('pyhelm.repo._get_from_http', return_value=_index)
    @mock.patch('pyhelm.repo.tempfile.mkdtemp', return_value='')
    def test_chart_not_found(self, _0, _1):
        with self.assertRaises(repo.ChartError):
            repo.from_repo('http://test', 'baz')

    @mock.patch('pyhelm.repo._get_from_http', return_value=_index)
    @mock.patch('pyhelm.repo.tempfile.mkdtemp', return_value='')
    def test_version_not_found(self, _0, _1):
        with self.assertRaises(repo.VersionError):
            repo.from_repo('http://test', 'bar', version='1.0.0')

    @mock.patch('pyhelm.repo.tarfile.open', return_value=mock.Mock())
    @mock.patch('pyhelm.repo._get_from_repo', return_value='data')
    @mock.patch('pyhelm.repo.repo_index', return_value=yaml.safe_load(_index))
    @mock.patch('pyhelm.repo.tempfile.mkdtemp', return_value='/tmp/dir')
    def test_latest_version(self, _0, _1, _2, _3):
        r = repo.from_repo('http://test', 'foo')
        self.assertEqual(r, '/tmp/dir/foo')

    @mock.patch('pyhelm.repo.tarfile.open', return_value=mock.Mock())
    @mock.patch('pyhelm.repo._get_from_repo', return_value='data')
    @mock.patch('pyhelm.repo.repo_index', return_value=yaml.safe_load(_index))
    @mock.patch('pyhelm.repo.tempfile.mkdtemp', return_value='/tmp/dir')
    def test_specific_version(self, _0, _1, _2, _3):
        r = repo.from_repo('http://test', 'foo', version='0.1.2')
        self.assertEqual(r, '/tmp/dir/foo')

    @mock.patch('pyhelm.repo.tempfile.mkdtemp', return_value='/tmp/dir')
    @mock.patch('pyhelm.repo.Repo.clone_from', return_value='')
    def test_git_clone(self, _0, mocked_git):
        r = repo.git_clone('git://test', path='foo')
        self.assertEqual(r, '/tmp/dir/foo')

    @mock.patch('pyhelm.repo.shutil')
    def test_source_cleanup(self, mock_shutil):
        repo.source_cleanup('foo')
        mock_shutil.rmtree.assert_called_once_with('foo')

    @mock.patch('boto3.client')
    def test_get_from_s3_ok(self, mocked_s3client):
        repo._get_from_repo('s3', 'test', 'bar')
        mocked_s3client.return_value.get_object.assert_called()

    @mock.patch('boto3.client')
    def test_get_from_s3_repo_error(self, mocked_s3client):
        mocked_s3client.return_value.get_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchBucket'}}, '')
        with self.assertRaises(repo.RepositoryError):
            repo._get_from_repo('s3', 'test', 'foo')

    @mock.patch('boto3.client')
    def test_get_from_s3_chart_error(self, mocked_s3client):
        mocked_s3client.return_value.get_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey'}}, '')
        with self.assertRaises(repo.ChartError):
            repo._get_from_repo('s3', 'test', 'foo')

    @mock.patch('boto3.client')
    def test_get_from_s3_client_error(self, mocked_s3client):
        mocked_s3client.return_value.get_object.side_effect = ClientError(
            {'Error': {'Code': ''}}, '')
        with self.assertRaises(ClientError):
            repo._get_from_repo('s3', 'test', 'foo')
