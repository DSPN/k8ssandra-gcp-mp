from argparse import ArgumentParser
import sys

import yaml

import helpers

valid_operations = (
    'find',
    'pull',
    'tag',
    'push',
    'remove',
    'publish',
)

image_map = {
    'stargate-wait-for-cassandra': 'alpine:3.12.2',
    'cassandra-jmx-credentials': 'busybox:1.33.1',
    'grafana-test': 'bats/bats:v1.1.0',
    'cassandra-config-builder': 'datastax/cass-config-builder:1.0.4',
    'grafana': 'grafana/grafana:7.3.5',
    'cassandra': 'k8ssandra/cass-management-api:4.0.0-v0.1.28',
    'cass-operator': 'k8ssandra/cass-operator:v1.7.1',
    'cleaner': 'k8ssandra/k8ssandra-tools:latest',
    'crd-upgrader': 'k8ssandra/k8ssandra-tools:latest',
    'reaper-operator': 'k8ssandra/reaper-operator:v0.3.3',
    'cassandra-system-logger': 'k8ssandra/system-logger:9c4c3692',
    'medusa-operator': 'k8ssandra/medusa-operator:v0.3.3',
    'medusa': 'k8ssandra/medusa:0.11.0',
    'stargate': 'stargateio/stargate-4_0:v1.0.29',
    'reaper': 'thelastpickle/cassandra-reaper:2.3.1',
    'kube-prometheus-stack-admission-create-certgen': 'jettech/kube-webhook-certgen:v1.5.0',
    'kube-prometheus-stack-admission-patch-certgen': 'jettech/kube-webhook-certgen:v1.5.0',
    'grafana-sidecar': 'kiwigrid/k8s-sidecar:1.1.0',
    'prometheus-config-reloader': 'quay.io/prometheus-operator/prometheus-config-reloader:v0.44.0',
    'prometheus-operator': 'quay.io/prometheus-operator/prometheus-operator:v0.44.0',
    'prometheus': 'quay.io/prometheus/prometheus:v2.22.1',
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
        template = helpers.render_template()
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


class ImagePublisher:

    def publish(self, version):
        short_version = helpers.get_short_version(version)
        items = dict(image_map)
        items['deployer'] = 'deployer'
        for name in items.keys():
            dev_staging_name = f"{helpers.dev_staging_repo}/{name}"
            prod_staging_name = f"{helpers.prod_staging_repo}/{name}"
            print(f"creating tag. Source: '{dev_staging_name}', Dest: '{prod_staging_name}'")
            cp = helpers.run(
                f"""
                docker tag {dev_staging_name}:{version} {prod_staging_name}:{version}
                docker tag {dev_staging_name}:{version} {prod_staging_name}:{short_version}
                """
                )
            if cp.returncode != 0:
                raise Exception(
                    f"""
                    Failed to tag image '{name}'
                    {cp.stdout}
                    """
                    )
            print(f"pushing image versions for '{name}'")
            cp = helpers.run(
                f"""
                docker push {prod_staging_name}:{version}
                docker push {prod_staging_name}:{short_version}
                """
                )
            if cp.returncode != 0:
                raise Exception(
                    f"""
                    Failed to push image '{name}'
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

    if args.operation == 'publish':
        if not args.version:
            print("<version is required for the 'publish' operation")
            sys.exit(1)
        version = args.version
        ImagePublisher().publish(version)

if __name__ == '__main__':
    main()
