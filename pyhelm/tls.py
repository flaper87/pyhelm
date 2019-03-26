import os


class TlsConfig(object):
    def __init__(self, key_path, cert_path, ca_path):
        self.key_path = key_path
        self.cert_path = cert_path
        self.ca_path = ca_path

    @classmethod
    def from_env(cls):
        """
        Create a TlsConfig object from environment variables, emulating
        what the Helm cli does.
        """

        helm_home = os.getenv('HELM_HOME')

        if helm_home:
            return cls(
                key_path=os.path.join(helm_home, 'key.pem'),
                cert_path=os.path.join(helm_home, 'cert.pem'),
                ca_path=os.path.join(helm_home, 'ca.pem'),
            )
        else:
            return cls(
                key_path=os.getenv('HELM_TLS_KEY'),
                cert_path=os.getenv('HELM_TLS_CERT'),
                ca_path=os.getenv('HELM_TLS_CA_CERT'),
            )

    @property
    def key_data(self):
        with open(self.key_path, 'rb') as fobj:
            return fobj.read()

    @property
    def cert_data(self):
        with open(self.cert_path, 'rb') as fobj:
            return fobj.read()

    @property
    def ca_data(self):
        with open(self.ca_path, 'rb') as fobj:
            return fobj.read()
