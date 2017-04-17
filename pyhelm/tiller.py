from hapi.services.tiller_pb2 import ReleaseServiceStub, ListReleasesRequest, \
    InstallReleaseRequest, UpdateReleaseRequest, UninstallReleaseRequest
from hapi.chart.config_pb2 import Config
import grpc

from k8s import K8s
from logutil import LOG

TILLER_PORT = 44134
TILLER_VERSION = b'2.1.3'
TILLER_TIMEOUT = 300
RELEASE_LIMIT = 64

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
        for i in self.k8s.get_namespace_pod('kube-system').items:
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
        releases = []
        stub = ReleaseServiceStub(self.channel)
        req = ListReleasesRequest(limit=RELEASE_LIMIT)
        release_list = stub.ListReleases(req, self.timeout,
                                         metadata=self.metadata)
        for y in release_list:
            releases.extend(y.releases)
        return releases

    def list_charts(self):
        '''
        List Helm Charts from Latest Releases

        Returns list of (name, version, chart, values)
        '''
        charts = []
        for latest_release in self.list_releases():
            try:
                charts.append((latest_release.name, latest_release.version,
                               latest_release.chart,
                               latest_release.config.raw))
            except IndexError:
                continue
        return charts

    def _pre_update_actions(self, actions, namespace):
        '''
        :params actions - array of items actions
        :params namespace - name of pod for actions
        '''
        try:
            for action in actions.get('delete', []):
                name = action.get("name")
                action_type = action.get("type")
                if "job" in action_type:
                    LOG.info("Deleting %s in namespace: %s", name, namespace)
                    self.k8s.delete_job_action(name, namespace)
                    continue
                LOG.error("Unable to execute name: %s type: %s ", name, type)
        except Exception:
            LOG.debug("PRE: Could not delete anything, please check yaml")

        try:
            for action in actions.get('create', []):
                name = action.get("name")
                action_type = action.get("type")
                if "job" in action_type:
                    LOG.info("Creating %s in namespace: %s", name, namespace)
                    self.k8s.create_job_action(name, action_type)
                    continue
        except Exception:
            LOG.debug("PRE: Could not create anything, please check yaml")

    def _post_update_actions(self, actions, namespace):
        try:
            for action in actions.get('create', []):
                name = action.get("name")
                action_type = action.get("type")
                if "job" in action_type:
                    LOG.info("Creating %s in namespace: %s", name, namespace)
                    self.k8s.create_job_action(name, action_type)
                    continue
        except Exception:
            LOG.debug("POST: Could not create anything, please check yaml")

    def update_release(self, chart, dry_run, name, namespace,
                       pre_actions=None, post_actions=None,
                       disable_hooks=False, values=None):
        '''
        Update a Helm Release
        '''

        if values is None:
            values = Config(raw='')
        else:
            values = Config(raw=values)

        self._pre_update_actions(pre_actions, namespace)

        # build release install request
        stub = ReleaseServiceStub(self.channel)
        release_request = UpdateReleaseRequest(
            chart=chart,
            dry_run=dry_run,
            disable_hooks=disable_hooks,
            values=values,
            name=name)

        stub.UpdateRelease(release_request, self.timeout,
                           metadata=self.metadata)

        self._post_update_actions(post_actions, namespace)

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
