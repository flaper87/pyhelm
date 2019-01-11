from unittest import TestCase
try:
    from unittest import mock
except ImportError:
    import mock

from supermutes.dot import dotify
import pyhelm.tiller as tiller

class TestTiller(TestCase):

    def setUp(self):
        tiller.Tiller._logger = mock.Mock()

    @mock.patch('pyhelm.tiller.grpc')
    def test_get_channel(self, mock_grpc):
        tiller.Tiller('test')
        mock_grpc.insecure_channel.assert_called()

    @mock.patch('pyhelm.tiller.grpc')
    def test_tiller_status(self, _0):
        t1 = tiller.Tiller('')
        self.assertFalse(t1.tiller_status())
        t2 = tiller.Tiller('test')
        self.assertTrue(t2.tiller_status())

    @mock.patch('pyhelm.tiller.ReleaseServiceStub')
    @mock.patch('pyhelm.tiller.grpc')
    def test_list_releases(self, _0, mock_release_service_stub):
        mock_release_service_stub.ListReleases.return_value = iter([])
        tiller.Tiller('test').list_releases()

    @mock.patch('pyhelm.tiller.Tiller.list_releases')
    @mock.patch('pyhelm.tiller.grpc')
    def test_list_charts(self, _0, mock_list_releases):
        mock_list_releases.return_value = [
            dotify({'name': 'foo', 'version': '0.1.0', 'chart': 'bar',
                    'config': {'raw': 'foo: bar'}})
        ]
        charts = tiller.Tiller('test').list_charts()
        self.assertEquals(len(charts), 1)
        self.assertEquals(charts[0], ('foo', '0.1.0', 'bar', 'foo: bar'))

    @mock.patch('pyhelm.tiller.ReleaseServiceStub')
    @mock.patch('pyhelm.tiller.UpdateReleaseRequest')
    @mock.patch('pyhelm.tiller.grpc')
    def test_update_release(self, _0, _1, mock_release_service_stub):
        mock_release_service_stub.UpdateRelease.return_value = True
        mock_release_service_stub.GetReleaseStatus.return_value = dotify(
            {'namespace': 'testing'})
        t = tiller.Tiller('test').update_release('foo', 'mynamespace',
                                                 install=True)
        tiller.Tiller._logger.warn.assert_called()
        self.assertTrue(t)

    @mock.patch('pyhelm.tiller.ReleaseServiceStub')
    @mock.patch('pyhelm.tiller.InstallReleaseRequest')
    @mock.patch('pyhelm.tiller.grpc')
    def test_install_release(self, _0, _1, mock_release_service_stub):
        mock_release_service_stub.InstallRelease.return_value = True
        t = tiller.Tiller('test').install_release('foo', 'test')
        self.assertTrue(t)

    @mock.patch('pyhelm.tiller.ReleaseServiceStub')
    @mock.patch('pyhelm.tiller.grpc')
    def test_uninstall_release(self, _0, mock_release_service_stub):
        mock_release_service_stub.UninstallRelease.return_value = True
        t = tiller.Tiller('test').uninstall_release('foo')
        self.assertTrue(t)

    @mock.patch('pyhelm.tiller.ReleaseServiceStub')
    @mock.patch('pyhelm.tiller.grpc')
    def test_get_release_status(self, _0, mock_release_service_stub):
        mock_release_service_stub.GetReleaseStatus.return_value = True
        t = tiller.Tiller('test').get_release_status('foo')
        self.assertTrue(t)

    @mock.patch('pyhelm.tiller.ReleaseServiceStub')
    @mock.patch('pyhelm.tiller.grpc')
    def test_get_release_content(self, _0, mock_release_service_stub):
        mock_release_service_stub.GetReleaseContent.return_value = True
        t = tiller.Tiller('test').get_release_content('foo')
        self.assertTrue(t)

    @mock.patch('pyhelm.tiller.Tiller.uninstall_release')
    @mock.patch('pyhelm.tiller.Tiller.list_releases')
    @mock.patch('pyhelm.tiller.grpc')
    def test_chart_cleanup_no_releases(self, _0, mock_list, mock_uninstall):
        mock_list.return_value = [dotify({'name': 'test-baz'})]
        tiller.Tiller('test').chart_cleanup('test', [
            {'chart': {'release_name': 'foo'}},
            {'chart': {'release_name': 'bar'}},
        ])
        tiller.Tiller._logger.debug.assert_called()
        mock_uninstall.assert_called_once_with('test-baz')
