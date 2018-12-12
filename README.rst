======
PyHelm
======

Python bindings for the Helm package manager

Helm gRPC
---------

The helm gRPC libraries are located in the hapi directory.  They were generated with the grpc_tools.protoc utility against Helm 2.11.  Should you wish to re-generate them you can easily do so::

    git clone https://github.com/kubernetes/helm ./helm
    python -m grpc_tools.protoc -I helm/_proto --python_out=. --grpc_python_out=. _proto/hapi/chart/*
    python -m grpc_tools.protoc -I helm/_proto --python_out=. --grpc_python_out=. _proto/hapi/services/*
    python -m grpc_tools.protoc -I helm/_proto --python_out=. --grpc_python_out=. _proto/hapi/release/*
    python -m grpc_tools.protoc -I helm/_proto --python_out=. --grpc_python_out=. _proto/hapi/version/*

