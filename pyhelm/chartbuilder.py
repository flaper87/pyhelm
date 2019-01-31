import os

import yaml
from google.protobuf.any_pb2 import Any
from supermutes.dot import dotify

import pyhelm.logger as logger
from hapi.chart.chart_pb2 import Chart
from hapi.chart.config_pb2 import Config
from hapi.chart.metadata_pb2 import Metadata
from hapi.chart.template_pb2 import Template
from hapi.services.tiller_pb2 import GetReleaseContentRequest
from pyhelm import repo


try:
    import pathlib
except ImportError:
    import pathlib2 as pathlib


class ChartBuilder(object):
    '''
    This class handles taking chart intentions as a paramter and
    turning those into proper protoc helm charts that can be
    pushed to tiller.

    It also processes chart source declarations, fetching chart
    source from external resources where necessary
    '''

    _logger = logger.get_logger('ChartBuilder')

    def __init__(self, chart, parent=None):
        '''
        Initialize the ChartBuilder class

        Note that tthis will trigger a source pull as part of
        initialization as its necessary in order to examine
        the source service many of the calls on ChartBuilder
        '''

        # cache for generated protoc chart object
        self._helm_chart = None

        # record whether this is a dependency based chart
        self.parent = parent

        # store chart schema
        self.chart = dotify(chart)

        # extract, pull, whatever the chart from its source
        self.source_directory = self.source_clone()

    def source_clone(self):
        '''
        Clone the charts source

        We only support a git source type right now, which can also
        handle git:// local paths as well
        '''

        subpath = self.chart.source.get('subpath', '')

        if not 'type' in self.chart.source:
            self._logger.exception("Need source type for chart %s",
                                   self.chart.name)
            return

        if self.parent:
            self._logger.info("Cloning %s/%s as dependency for %s",
                              self.chart.source.location,
                              subpath, self.parent)
        else:
            self._logger.info("Cloning %s/%s for release %s",
                              self.chart.source.location,
                              subpath, self.chart.name)

        if self.chart.source.type == 'git':
            if 'reference' not in self.chart.source:
                self.chart.source.reference = 'master'
            if 'path' not in self.chart.source:
                self.chart.source.path = ''
            self._source_tmp_dir = repo.git_clone(self.chart.source.location,
                                                  self.chart.source.reference,
                                                  self.chart.source.path)

        elif self.chart.source.type == 'repo':
            if 'version' not in self.chart:
                self.chart.version = None
            if 'headers' not in self.chart.source:
                self.chart.source.headers = None
            self._source_tmp_dir = repo.from_repo(self.chart.source.location,
                                                  self.chart.name,
                                                  self.chart.version,
                                                  self.chart.source.headers)
        elif self.chart.source.type == 'directory':
            self._source_tmp_dir = self.chart.source.location

        else:
            self._logger.exception("Unknown source type %s for chart %s",
                                   self.chart.name,
                                   self.chart.source.type)
            return
        return os.path.join(self._source_tmp_dir, subpath)


    def source_cleanup(self):
        '''
        Cleanup source
        '''
        repo.source_cleanup(self._source_tmp_dir)

    def get_metadata(self):
        '''
        Process metadata
        '''
        # extract Chart.yaml to construct metadata
        chart_yaml = dotify(yaml.load(pathlib.Path(self.source_directory, 'Chart.yaml').read_text()))

        # construct Metadata object
        return Metadata(
            description=chart_yaml.description,
            name=chart_yaml.name,
            version=chart_yaml.version
        )

    def get_files(self):
        '''
        Return (non-template) files in this chart
        '''
        # TODO(yanivoliver): add support for .helmignore
        # TODO(yanivoliver): refactor seriously to be similar to what Helm does
        #                    (https://github.com/helm/helm/blob/master/pkg/chartutil/load.go)
        chart_files = []

        template_dir = pathlib.Path(self.source_directory, 'templates')

        if not template_dir.exists():
            self._logger.warn("Chart %s has no templates directory, no templates will be deployed", self.chart.name)

        for f in template_dir.glob('**/*'):
            if not f.is_file():
                continue

            if f.name in (".helmignore", "Chart.yaml", "values.toml", "values.yaml"):
                continue

            chart_files.append(
                Any(
                    type_url=f.relative_to(self.source_directory).as_posix(),
                    value=f.read_bytes(),
                )
            )

        return chart_files

    def get_values(self):
        '''
        Return the chart (default) values
        '''

        values_path = pathlib.Path(self.source_directory, 'values.yaml')

        if not values_path.exists():
            self._logger.warn("No values.yaml in %s, using empty values",
                              self.source_directory)
            raw_values = ''
        else:
            raw_values = values_path.read_text()

        return Config(raw=raw_values)

    def get_templates(self):
        '''
        Return all the chart templates
        '''

        # process all files in templates/ as a template to attach to the chart
        # building a Template object
        templates = []
        template_dir = pathlib.Path(self.source_directory, 'templates')

        if not template_dir.exists():
            self._logger.warn("Chart %s has no templates directory, no templates will be deployed", self.chart.name)

        for f in template_dir.glob('**/*'):
            if not f.is_file():
                continue

            templates.append(
                Template(
                    name=f.relative_to(self.source_directory).as_posix(),
                    data=f.read_bytes(),
                )
            )

        return templates

    def get_helm_chart(self):
        '''
        Return a helm chart object
        '''

        if self._helm_chart:
            return self._helm_chart

        dependencies = []

        for chart in self.chart.get('dependencies', []):
            self._logger.info("Building dependency chart %s for release %s",
                              chart.name, self.chart.name)
            dependencies.append(ChartBuilder(chart).get_helm_chart())

        helm_chart = Chart(
            metadata=self.get_metadata(),
            templates=self.get_templates(),
            dependencies=dependencies,
            values=self.get_values(),
            files=self.get_files(),
        )

        self._helm_chart = helm_chart
        return helm_chart

    def dump(self):
        '''
        This method is used to dump a chart object as a
        serialized string so that we can perform a diff

        It should recurse into dependencies
        '''
        return self.get_helm_chart().SerializeToString()
