from __future__ import unicode_literals
from unittest import TestCase
try:
    from unittest import mock
except ImportError:
    import mock

import io
from hapi.chart.template_pb2 import Template
from hapi.chart.metadata_pb2 import Metadata
from hapi.chart.config_pb2 import Config
from google.protobuf.any_pb2 import Any
from pyhelm.chartbuilder import ChartBuilder

class TestChartBuilder(TestCase):

    _chart = io.StringIO('''
apiVersion: v1
description: testing
name: foobar
version: 1.2.3
appVersion: 3.2.1
''')

    _values = io.StringIO('''
---
foo:
  bar: baz
''')

    _file = io.StringIO('')

    _files_walk = (x for x in [
        ('charts', '', []),
        ('templates', '', []),
        ('files', '', ['.helmignore', 'Chart.yaml', 'data']),
    ])

    _template = io.StringIO('''
---
apiVersion: v1
kind: Deployment
metadata:
  name: {{ include "foo.fullname" . }}
  namespace: "{{ .Values.namespace }}"
''')

    _templates_walk = (x for x in [
        ('t', '', ['deployment.yaml'])
    ])

    _mock_source_clone = 'pyhelm.chartbuilder.ChartBuilder.source_clone'

    def setUp(self):
        ChartBuilder._logger = mock.Mock()

    def test_no_type(self):
        cb = ChartBuilder({'name': '', 'source': {}})
        self.assertIsNone(cb.source_directory)
        cb._logger.exception.assert_called()

    def test_unknown_type_with_parent(self):
        cb = ChartBuilder({'name': 'bar',
                           'parent': 'foo',
                           'source': {'location': 'test', 'type': 'none'}})
        self.assertIsNone(cb.source_directory)
        cb._logger.info.assert_called()
        cb._logger.exception.assert_called()

    @mock.patch('pyhelm.chartbuilder.repo.git_clone', return_value='/test')
    def test_git(self, _0):
        cb = ChartBuilder({'name': 'foo',
                           'source': {'location': 'test',
                                      'type': 'git',
                                      'subpath': 'foo'}})
        self.assertEqual(cb.source_directory, '/test/foo')
        cb._logger.info.assert_called()
        cb._logger.exception.assert_not_called()

    @mock.patch('pyhelm.chartbuilder.repo.from_repo', return_value='/test')
    def test_repo(self, _0):
        cb = ChartBuilder({'name': 'foo',
                           'source': {'location': 'test', 'type': 'repo'}})
        self.assertEqual(cb.source_directory, '/test/')
        cb._logger.info.assert_called()
        cb._logger.exception.assert_not_called()

    def test_directory(self):
        cb = ChartBuilder({'name': 'foo',
                           'source': {'location': 'dir', 'type': 'directory'}})
        self.assertEqual(cb.source_directory, 'dir/')
        cb._logger.info.assert_called()
        cb._logger.exception.assert_not_called()

    @mock.patch('pyhelm.chartbuilder.codecs.open', return_value=_chart)
    @mock.patch(_mock_source_clone, return_value='')
    def test_get_metadata(self, _0, _1):
        m = ChartBuilder({}).get_metadata()
        self.assertIsInstance(m, Metadata)

    @mock.patch('pyhelm.chartbuilder.codecs.open', return_value=_file)
    @mock.patch('pyhelm.chartbuilder.os.walk', return_value=_files_walk)
    @mock.patch(_mock_source_clone, return_value='test')
    def test_get_files(self, _0, _1, _2):
        f = ChartBuilder({}).get_files()
        self.assertEqual(len(f), 1)
        self.assertIsInstance(f[0], Any)

    @mock.patch(_mock_source_clone, return_value='test')
    def test_get_values_not_found(self, _0):
        ChartBuilder({}).get_values()
        ChartBuilder._logger.warn.assert_called()

    @mock.patch('pyhelm.chartbuilder.codecs.open', return_value=_values)
    @mock.patch('pyhelm.chartbuilder.os.path.exists', return_value=True)
    @mock.patch(_mock_source_clone, return_value='test')
    def test_get_values(self, _0, _1, _2):
        v = ChartBuilder({}).get_values()
        self.assertIsInstance(v, Config)

    @mock.patch('pyhelm.chartbuilder.codecs.open', return_value=_template)
    @mock.patch('pyhelm.chartbuilder.os.walk', return_value=_templates_walk)
    @mock.patch(_mock_source_clone, return_value='test')
    def test_get_templates(self, _0, _1, _2):
        t = ChartBuilder({'name': 'foo'}).get_templates()
        ChartBuilder._logger.warn.assert_called()
        self.assertEqual(len(t), 1)
        self.assertIsInstance(t[0], Template)

    @mock.patch('pyhelm.chartbuilder.ChartBuilder.get_metadata')
    @mock.patch('pyhelm.chartbuilder.ChartBuilder.get_templates')
    @mock.patch('pyhelm.chartbuilder.ChartBuilder.get_values')
    @mock.patch('pyhelm.chartbuilder.ChartBuilder.get_files')
    @mock.patch('pyhelm.chartbuilder.Chart')
    def test_get_helm_chart_exists(self, _0, _1, _2, _3, _4):
        cb = ChartBuilder({'name': 'foo', 'source': {}, 'dependencies': [
            {'name': 'bar', 'source': {}}
        ]})
        cb._helm_chart = '123'
        self.assertEqual(cb.get_helm_chart(), '123')
        cb._helm_chart = None
        cb.get_helm_chart()
        cb._logger.info.assert_called()

    @mock.patch('pyhelm.chartbuilder.repo')
    def test_source_cleanup(self, mock_repo):
        ChartBuilder({'name': 'foo',
                      'source': {'type': 'directory', 'location': 'test'}}
                     ).source_cleanup()
        mock_repo.source_cleanup.assert_called()
