======
PyHelm
======

Python bindings for the Helm package manager

How to use PyHelm
-----------------
In order to install a Helm chart using PyHelm, you can perform the following steps:

**Loading a chart using ChartBuilder**

.. code-block:: python

    from pyhelm.chartbuilder import ChartBuilder

    chart = ChartBuilder({"name": "nginx-ingress", "source": {"type": "repo", "location": "https://kubernetes-charts.storage.googleapis.com"}}) 
    
This will cause the chart to cloned locally, and any additional use of ``chart`` will reference the local copy.
You can also used a local chart by using ``"type": "directory"``, as well as cloning from a git repo using ``"type": "git"``

**Installing a chart**

.. code-block:: python

    from pyhelm.chartbuilder import ChartBuilder
    from pyhelm.tiller import Tiller

    tiller = Tiller(TILLER_HOST)
    chart = ChartBuilder({"name": "nginx-ingress", "source": {"type": "repo", "location": "https://kubernetes-charts.storage.googleapis.com"}}) 
    tiller.install_release(chart.get_helm_chart(), dry_run=False, namespace='default')

This snippet will install the ``nginx-ingress`` chart on a Kubernetes cluster where Tiller is installed (assuming ``TILLER_HOST`` points to a live Tiller instance). Take note that in most Helm installations Tiller isn't accessible in such a manner, and you will need to perform a Kubernetes port-forward operation to access Tiller.
The ``Tiller`` class supports other operations other than installation, including release listing, release updating, release uninstallation and getting release contents.


Package versions
----------------
In order to support multiple versions of Helm versions, which in turn require different gRPC prototypes, we maintain different PyHelm package versions.

========================= =========================
Helm version              PyHelm dependency version
------------------------- -------------------------
2.11 (and lower)          pyhelm>=2.11,<2.12
2.14                      pyhelm>=2.14,<2.15
========================= =========================

Additional Helm versions can be supported as shown in the following section.

Helm gRPC
---------
The helm gRPC libraries are located in the hapi directory.  They were generated with the grpc_tools.protoc utility against Helm 2.14.  Should you wish to re-generate them you can easily do so:

.. code-block:: shell

    git clone https://github.com/kubernetes/helm ./helm
    python -m grpc_tools.protoc -I helm/_proto --python_out=. --grpc_python_out=. _proto/hapi/chart/*
    python -m grpc_tools.protoc -I helm/_proto --python_out=. --grpc_python_out=. _proto/hapi/services/*
    python -m grpc_tools.protoc -I helm/_proto --python_out=. --grpc_python_out=. _proto/hapi/release/*
    python -m grpc_tools.protoc -I helm/_proto --python_out=. --grpc_python_out=. _proto/hapi/version/*
