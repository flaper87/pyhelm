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

    _chart = io.StringIO(u'''
description: testing
name: foobar
version: 1.2.3
''')

    _values = io.StringIO(u'''
---
foo:
  bar: baz
''')

    _file = io.BytesIO(bytes(''))

    _files_walk = (x for x in [
        ('charts', '', []),
        ('templates', '', []),
        ('files', '', ['.helmignore', 'Chart.yaml', 'data']),
    ])

    _template = io.BytesIO(bytes('''
---
apiVersion: v1
kind: Deployment
metadata:
  name: {{ include "foo.fullname" . }}
  namespace: "{{ .Values.namespace }}"
'''))

    _templates_walk = (x for x in [
        ('t', '', ['deployment.yaml'])
    ])

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
        self.assertEquals(cb.source_directory, '/test/foo')
        cb._logger.info.assert_called()
        cb._logger.exception.assert_not_called()

    @mock.patch('pyhelm.chartbuilder.repo.from_repo', return_value='/test')
    def test_repo(self, _0):
        cb = ChartBuilder({'name': 'foo',
                           'source': {'location': 'test', 'type': 'repo'}})
        self.assertEquals(cb.source_directory, '/test/')
        cb._logger.info.assert_called()
        cb._logger.exception.assert_not_called()

    def test_directory(self):
        cb = ChartBuilder({'name': 'foo',
                           'source': {'location': 'dir', 'type': 'directory'}})
        self.assertEquals(cb.source_directory, 'dir/')
        cb._logger.info.assert_called()
        cb._logger.exception.assert_not_called()

    @mock.patch('pyhelm.chartbuilder.open', return_value=_chart)
    def test_get_metadata(self, _0):
        cb = ChartBuilder({'name': '', 'source': {}})
        cb.source_directory = ''
        m = cb.get_metadata()
        self.assertIsInstance(m, Metadata)

    @mock.patch('pyhelm.chartbuilder.open', return_value=_file)
    @mock.patch('pyhelm.chartbuilder.os.walk', return_value=_files_walk)
    def test_get_files(self, _0, _1):
        cb = ChartBuilder({'name': '', 'source': {}})
        cb.source_directory = 'test'
        f = cb.get_files()
        self.assertEquals(len(f), 1)
        self.assertIsInstance(f[0], Any)

    def test_get_values_not_found(self):
        cb = ChartBuilder({'name': '', 'source': {}})
        cb.source_directory = 'test'
        cb.get_values()
        cb._logger.warn.assert_called()

    @mock.patch('pyhelm.chartbuilder.open', return_value=_values)
    @mock.patch('pyhelm.chartbuilder.os.path.exists', return_value=True)
    def test_get_values(self, _0, _1):
        cb = ChartBuilder({'name': '', 'source': {}})
        cb.source_directory = 'test'
        v = cb.get_values()
        self.assertIsInstance(v, Config)

    @mock.patch('pyhelm.chartbuilder.open', return_value=_template)
    @mock.patch('pyhelm.chartbuilder.os.walk', return_value=_templates_walk)
    def test_get_templates(self, _0, _1):
        cb = ChartBuilder({'name': '', 'source': {}})
        cb.source_directory = 'test'
        t = cb.get_templates()
        cb._logger.warn.assert_called()
        self.assertEquals(len(t), 1)
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
        self.assertEquals(cb.get_helm_chart(), '123')
        cb._helm_chart = None
        cb.get_helm_chart()
        cb._logger.info.assert_called()

    @mock.patch('pyhelm.chartbuilder.repo')
    def test_source_cleanup(self, mock_repo):
        ChartBuilder({'name': 'foo',
                      'source': {'type': 'directory', 'location': 'test'}}
                     ).source_cleanup()
        mock_repo.source_cleanup.assert_called()
