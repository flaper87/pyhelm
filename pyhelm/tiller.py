from hapi.services.tiller_pb2 import ReleaseServiceStub, ListReleasesRequest, \
    InstallReleaseRequest, UpdateReleaseRequest, UninstallReleaseRequest
from hapi.chart.config_pb2 import Config
import grpc

from logutil import LOG
from k8s import K8s

TILLER_PORT = 44134
TILLER_VERSION = b'2.1.3'
TILLER_TIMEOUT = 300

class Tiller(object):
    '''
    The Tiller class supports communication and requests to the Tiller Helm
    service over gRPC
    '''

    def __init__(self):

        # init k8s connectivity
        self.k8s = K8s()

        # init tiller channel
        self.channel = self.get_channel()

        # init timeout for all requests
        # and assume eventually this will
        # be fed at runtime as an override
        self.timeout = TILLER_TIMEOUT

    @property
    def metadata(self):
        '''
        Return tiller metadata for requests
        '''
        return [(b'x-helm-api-client', TILLER_VERSION)]

    def get_channel(self):
        '''
        Return a tiller channel
        '''
        tiller_ip = self._get_tiller_ip()
        tiller_port = self._get_tiller_port()
        return grpc.insecure_channel('%s:%s' % (tiller_ip, tiller_port))

    def _get_tiller_pod(self):
        '''
        Search all namespaces for a pod beginning with tiller-deploy*
        '''
        ret = self.k8s.client.list_pod_for_all_namespaces()
        for i in ret.items:
            # TODO(alanmeadows): this is a bit loose
            if i.metadata.name.startswith('tiller-deploy'):
                return i

    def _get_tiller_ip(self):
        '''
        Returns the tiller pod's IP address by searching all namespaces
        '''
        pod = self._get_tiller_pod()
        return pod.status.pod_ip

    def _get_tiller_port(self):
        '''Stub method to support arbitrary ports in the future'''
        return TILLER_PORT

    def list_releases(self):
        '''
        List Helm Releases
        '''
        stub = ReleaseServiceStub(self.channel)
        req = ListReleasesRequest()
        return stub.ListReleases(req, self.timeout, metadata=self.metadata)

    def list_charts(self):
        '''
        List Helm Charts from Latest Releases

        Returns list of (name, version, chart, values)
        '''
        charts = []
        for x in self.list_releases():
            try:
                latest_release = x.releases[-1]
                charts.append((latest_release.name, latest_release.version,
                               latest_release.chart,
                               latest_release.config.raw))
            except IndexError:
                continue
        return charts

    def update_release(self, chart, dry_run, name, disable_hooks=False,
                       values=None):
        '''
        Update a Helm Release
        '''

        if values is None:
            values = Config(raw='')
        else:
            values = Config(raw=values)

        # build release install request
        stub = ReleaseServiceStub(self.channel)
        release_request = UpdateReleaseRequest(
            chart=chart,
            dry_run=dry_run,
            disable_hooks=disable_hooks,
            values=values,
            name=name)
        return stub.UpdateRelease(release_request, self.timeout,
                                  metadata=self.metadata)

    def install_release(self, chart, dry_run, name, namespace, prefix,
                        values=None):
        '''
        Create a Helm Release
        '''

        if values is None:
            values = Config(raw='')
        else:
            values = Config(raw=values)

        # build release install request
        stub = ReleaseServiceStub(self.channel)
        release_request = InstallReleaseRequest(
            chart=chart,
            dry_run=dry_run,
            values=values,
            name="{}-{}".format(prefix, name),
            namespace=namespace)
        return stub.InstallRelease(release_request,
                                   self.timeout,
                                   metadata=self.metadata)

    def uninstall_release(self, release, disable_hooks=False, purge=True):
        '''
        :params - release - helm chart release name
        :params - purge - deep delete of chart

        deletes a helm chart from tiller
        '''

        # build release install request
        stub = ReleaseServiceStub(self.channel)
        release_request = UninstallReleaseRequest(name=release,
                                                  disable_hooks=disable_hooks,
                                                  purge=purge)
        return stub.UninstallRelease(release_request,
                                     self.timeout,
                                     metadata=self.metadata)

    def chart_cleanup(self, prefix, charts, known_releases):
        '''
        :params charts - list of yaml charts
        :params known_release - list of releases in tiller

        :result - will remove any chart that is not present in yaml
        '''
        def release_prefix(prefix, chart):
            return "{}-{}".format(prefix, chart["chart"]["release_name"])

        valid_charts = [release_prefix(prefix, chart) for chart in charts]
        actual_charts = [x.name for x in self.list_releases()]
        chart_diff = list(set(actual_charts) - set(valid_charts))

        for chart in chart_diff:
            if chart.startswith(prefix):
                LOG.debug("Release: %s will be removed", chart)
                self.uninstall_release(chart)
