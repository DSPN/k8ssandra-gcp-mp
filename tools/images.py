from argparse import ArgumentParser
import sys

import yaml

import helpers

valid_operations = (
    'find',
    'pull',
    'tag',
    'push',
    'remove'
)

image_map = {
    'stargate-wait-for-cassandra': 'alpine:3.12.2',
    'cassandra-jmx-credentials': 'busybox:1.33.1',
    'grafana-test': 'bats/bats:v1.4.1',
    'cassandra-config-builder': 'datastax/cass-config-builder:1.0.4',
    'cass-operator-manager-config-builder': 'datastax/cass-config-builder:1.0.4-ubi7',
    'grafana': 'grafana/grafana:7.5.11',
    'cassandra': 'k8ssandra/cass-management-api:4.0.1-v0.1.33',
    'cass-operator': 'k8ssandra/cass-operator:v1.9.0',
    'cleaner': 'k8ssandra/k8ssandra-tools:latest',
    'crd-upgrader': 'k8ssandra/k8ssandra-tools:latest',
    'reaper-operator': 'k8ssandra/reaper-operator:v0.3.5',
    'cassandra-system-logger': 'k8ssandra/system-logger:6c64f9c4',
    'cass-operator-manager-system-logger': 'k8ssandra/system-logger:v1.9.0',
    'medusa-operator': 'k8ssandra/medusa-operator:v0.4.0',
    'medusa': 'k8ssandra/medusa:0.11.3',
    'stargate': 'stargateio/stargate-4_0:v1.0.40',
    'reaper': 'thelastpickle/cassandra-reaper:3.0.0',
    'kube-prometheus-stack-admission-create-certgen': 'k8s.gcr.io/ingress-nginx/kube-webhook-certgen:v1.0@sha256:f3b6b39a6062328c095337b4cadcefd1612348fdd5190b1dcbcb9b9e90bd8068',
    'kube-prometheus-stack-admission-patch-certgen': 'k8s.gcr.io/ingress-nginx/kube-webhook-certgen:v1.0@sha256:f3b6b39a6062328c095337b4cadcefd1612348fdd5190b1dcbcb9b9e90bd8068',
    'grafana-sidecar': 'quay.io/kiwigrid/k8s-sidecar:1.14.2',
    'prometheus-config-reloader': 'quay.io/prometheus-operator/prometheus-config-reloader:v0.52.0',
    'prometheus-operator': 'quay.io/prometheus-operator/prometheus-operator:v0.52.0',
    'prometheus': 'quay.io/prometheus/prometheus:v2.28.1',
    'thanos': 'quay.io/thanos/thanos:v0.17.2',
}

class ImageFinder:

    known_registries = [
        'docker.io',
        'quay.io',
        'k8s.gcr.io'
    ]

    def count_whitespace(self, text):
        count = 0
        for i in text:
            if i.isspace():
                count += 1
            else:
                break
        return count

    def render_template(self):
        cp = helpers.run(
            f"""
            helm template k8ssandra-mp {helpers.tools_dir}/../chart/k8ssandra-mp \
                --set k8ssandra.reaper.enabled=true \
                --set k8ssandra.reaper-operator.enabled=true \
                --set k8ssandra.stargate.enabled=true \
                --set k8ssandra.kube-prometheus-stack.enabled=true \
                --set k8ssandra.medusa.enabled=true
            """
            )

        if cp.returncode != 0:
            raise Exception(
                f"""
                Failed to render chart template:
                {cp.stdout}
                """
                )

        return cp.stdout

    class NotApplicableError(Exception):pass
    def extract_image(self, line, delim=':'):
        chars = ' \t"\''
        stripped = line.strip(chars)
        split = stripped.split(delim, maxsplit=1)
        try:
            path = split[1].strip(chars)
        except IndexError:
            raise NotApplicableError
        image = path.split(':')[0]
        tag = ':'.join(path.split(':')[1:])
        if image.split('/')[0] not in self.known_registries:
            image = "docker.io/" + image
        return f"{image}:{tag}"

    def find_images(self, template):
        images_section = False
        images_section_indent = 0
        for line in template.split('\n'):
            l = line.lower()
            if images_section:
                if self.count_whitespace(l) <= images_section_indent or \
                    not l.strip():
                    images_section = False
                    images_section_indent = 0
                else:
                    self.images.add(self.extract_image(l))
                    continue
            if 'image:' in l:
                self.images.add(self.extract_image(l))
                continue
            if 'quay.io' in l:
                try:
                    self.images.add(self.extract_image(l, delim='='))
                except NotApplicableError:
                    pass
            if 'images:' in l:
                images_section = True
                images_section_indent = self.count_whitespace(l)
                continue

    def __init__(self):
        self.images = set()

    def find(self):
        template = self.render_template()
        self.find_images(template)
        return sorted(self.images)


class ImagePuller:

    def pull(self):
        images = ImageFinder().find()

        for image in images:
            if 'docker.io' in image:
                image = image.replace('docker.io/', '')
            if '@sha256:' in image:
                path = image.split(':', maxsplit=1)
                image = path[0] + '@' + path[1].split('@')[1]
            cp = helpers.run(f"docker image ls -q {image}")
            if not cp.stdout and cp.returncode == 0:
                print(f"pulling image: {image}")
                cp = helpers.run(f"docker pull {image}")


class ImageTagger:

    def tag(self):
        version, short_version = helpers.get_versions()
        for name, image in image_map.items():
            print(f"tagging '{name}'")
            tag = ':'.join(image.split(':')[1:])
            cp = helpers.run(
                f"""
                docker tag {image} {helpers.dev_staging_repo}/{name}:{version}
                docker tag {image} {helpers.dev_staging_repo}/{name}:{short_version}
                """
                )
            if cp.returncode != 0:
                raise Exception(
                    f"""
                    Failed to tag image '{name}'
                    {cp.stdout}
                    """
                    )


class ImagePusher:

    def push(self):
        for name, image in image_map.items():
            print(f"pushing '{name}'")
            cp = helpers.run(
                f"""
                docker image push --all-tags {helpers.dev_staging_repo}/{name}
                """
                )
            if cp.returncode != 0:
                raise Exception(
                    f"""
                    failed to push image '{name}':
                    {cp.stdout}
                    """
                    )


class ImageRemover:

    def remove(self, version):
        short_version = helpers.get_short_version(version)
        for name, image in image_map.items():
            print(f"removing '{name}' from local repo")
            cp = helpers.run(
                f"""
                docker image rm {helpers.dev_staging_repo}/{name}:{version}
                docker image rm {helpers.dev_staging_repo}/{name}:{short_version}
                """
                )
            if cp.returncode != 0:
                print(
                    f"""
                    failed to remove image '{name}':
                    {cp.stdout}
                    """
                    )


def main():
    parser = ArgumentParser()
    parser.add_argument(
        '--operation',
        '-o',
        choices=valid_operations)
    parser.add_argument(
        '--version',
        '-v')

    args = parser.parse_args()

    if args.operation == 'find':
        for i in ImageFinder().find():
            print(i)

    if args.operation == 'pull':
        ImagePuller().pull()

    if args.operation == 'tag':
        ImageTagger().tag()

    if args.operation == 'push':
        ImagePusher().push()

    if args.operation == 'remove':
        if not args.version:
            print("<version> is required for the 'remove' operation")
            sys.exit(1)
        version = args.version
        ImageRemover().remove(version)

if __name__ == '__main__':
    main()
