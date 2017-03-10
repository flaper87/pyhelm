# Armada [![Docker Repository on Quay](https://quay.io/repository/attcomdev/armada/status "Docker Repository on Quay")](https://quay.io/repository/attcomdev/armada) [![Build Status](https://travis-ci.org/att-comdev/armada.svg?branch=master)](https://travis-ci.org/att-comdev/armada)

A python orchestrator for a installing, upgrading, and managing a collection of helm charts, dependencies, and values overrides.

Note that this project is pre-alpha and under active development. It may undergo drastic changes to support the long-term vision but contributions are welcome.


# Overview

The armada python library and command line tool provides a way to synchronize a helm (tiller) target with an operators intended state, consisting of several charts, dependencies, and overrides using a single file or directory with a collection of files. This allows operators to define many charts, potentially with different namespaces for those releases, and their overrides in a central place.  With a single command, deploy and/or upgrade them where applicable.

Armada also supports fetching helm chart source and then building charts from source from various local and remote locations, such as git/github endpoints.  In the future, it may supprot other mechanisms as well.

It will also give the operator some indication of what is about to change by assisting with diffs for both values, values overrides, and actual template changes.

Its functionality may extend beyond helm, assisting in interacting with kubernetes directly to perform basic pre and post steps, such as removing completed or failed jobs, running backup jobs,  blocking on chart readiness, or deleting resources that do not support upgrades. However, primarily, it will be an interface to support orchestrating Helm.


## Running Armada 

To use this container, use these simple instructions:

```
docker run quay.io/attcomdev/armada:latest
```

# Installation

The installation is fairly straight forward:

```
 virtualenv --no-site-packages ~/armada-env
 source ~/armada-env/bin/activate
 pip install -r ./requirements.txt
 python ./setup.py install
 ```

To run armada, simply supply it with your YAML based intention for any number of charts:

```
 ~/armada-env/bin/aramda -c examples/armada.yaml
```

Your output will look something like this:

```
$ ~/armada-env/bin/armada -c examples/armada.yaml
2017-02-10 09:42:36,753 armada       INFO     Cloning git://github.com/att-comdev/openstack-helm/keystone for release keystone
2017-02-10 09:42:39,238 armada       INFO     Building dependency chart common for release keystone
2017-02-10 09:42:39,238 armada       INFO     Cloning git://github.com/att-comdev/openstack-helm/common for release None
2017-02-10 09:42:41,459 armada       INFO     Installing release keystone
```

If you were to run it a second time, modifying the shared values override example in examples/armada.conf:

```
endpoints: &endpoints
  glance:
    this: is an example
```

to:

```
endpoints: &endpoints
  glance:
    this: is an example
    that: is another example
```

And re-run armada, we will notice it will upgrade the keystone release, instead of install it on this pass, as well as report back the values changes as a unified diff.  A unified diff for any template changes would also be shown had those occurred.

```
alan@hpdesktop:~/Workbench/att/attcomdev/armada$ /tmp/armada/bin/armada -c examples/armada.yaml
2017-02-10 09:44:43,396 armada       INFO     Cloning git://github.com/att-comdev/openstack-helm/keystone for release keystone
2017-02-10 09:44:47,640 armada       INFO     Building dependency chart common for release keystone
2017-02-10 09:44:47,640 armada       INFO     Cloning git://github.com/att-comdev/openstack-helm/common for release None
2017-02-10 09:44:49,701 armada       INFO     Upgrading release keystone
2017-02-10 09:44:49,704 armada       INFO     Values Unified Diff (keystone)
---

+++

@@ -1,3 +1,3 @@

 endpoints:
-  glance: {this: is an example}
+  glance: {that: is another example, this: is an example}

```

# Helm gRPC

The helm gRPC libraries are located in the hapi directory.  They were generated with the grpc_tools.protoc utility against Helm 2.1.3.  Should you wish to re-generate them you can easily do so:

```
    git clone https://github.com/kubernetes/helm ./helm
    python -m grpc_tools.protoc -I helm/_proto --python_out=. --grpc_python_out=. helm/_proto/hapi/chart/*
    python -m grpc_tools.protoc -I helm/_proto --python_out=. --grpc_python_out=. helm/_proto/hapi/services/*
    python -m grpc_tools.protoc -I helm/_proto --python_out=. --grpc_python_out=. helm/_proto/hapi/release/*
    python -m grpc_tools.protoc -I helm/_proto --python_out=. --grpc_python_out=. helm/_proto/hapi/version/*
```
