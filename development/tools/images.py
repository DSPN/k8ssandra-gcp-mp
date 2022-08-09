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

# See this issue for why we used k8s.gcr.io/ingress-nginx/kube-webhook-certgen:v1.1.1
# instead of jettech/kube-webhook-certgen:
# https://github.com/jet/kube-webhook-certgen/issues/30
image_map = {
    'stargate-wait-for-cassandra': 'alpine:3.12.2',
    'cassandra-jmx-credentials': 'busybox:1.35.0',
    'cassandra-config-builder': 'datastax/cass-config-builder:1.0.4-ubi7',
    'grafana': 'grafana/grafana:7.5.11',
    helpers.application_name: 'k8ssandra/cass-management-api:4.0.0-v0.1.37',
    'cass-operator': 'k8ssandra/cass-operator:v1.10.4',
    'cleaner': 'k8ssandra/k8ssandra-tools:latest',
    'client': 'k8ssandra/k8ssandra-tools:latest',
    'reaper-operator': 'k8ssandra/reaper-operator:v0.3.5',
    'cassandra-system-logger': 'k8ssandra/system-logger:6c64f9c4',
    'medusa-operator': 'k8ssandra/medusa-operator:v0.4.0',
    'medusa': 'k8ssandra/medusa:0.12.2',
    'stargate': 'stargateio/stargate-4_0:v1.0.61',
    'reaper': 'thelastpickle/cassandra-reaper:3.1.1',
    'kube-prometheus-stack-admission-patch': 'k8s.gcr.io/ingress-nginx/kube-webhook-certgen:v1.1.1',
    'grafana-sidecar': 'quay.io/kiwigrid/k8s-sidecar:1.19.2',
    'prometheus-config-reloader': 'quay.io/prometheus-operator/prometheus-config-reloader:v0.52.0',
    'prometheus-operator': 'quay.io/prometheus-operator/prometheus-operator:v0.52.0',
    'prometheus': 'quay.io/prometheus/prometheus:v2.28.1',
    'admission-controller': 'tawamudu/admission-controller:1',
    'ubbagent': 'tawamudu/ubbagent:1',
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
            if name == helpers.application_name:
                image_ref = helpers.dev_staging_repo
            else:
                image_ref = f'{helpers.dev_staging_repo}/{name}'
            cp = helpers.run(
                f"""
                docker tag {image} {image_ref}:{version}
                docker tag {image} {image_ref}:{short_version}
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
            if name == helpers.application_name:
                image_ref = helpers.dev_staging_repo
            else:
                image_ref = f'{helpers.dev_staging_repo}/{name}'
            version, short_version = helpers.get_versions()
            cp = helpers.run(
                f"""
                docker image push {image_ref}:{version}
                docker image push {image_ref}:{short_version}
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

    def publish(self, version, deployer_only):
        short_version = helpers.get_short_version(version)
        items = dict(image_map)
        items['deployer'] = 'deployer'
        for name in items.keys():
            if deployer_only and name != 'deployer':
                continue
            if name == helpers.application_name:
                dev_staging_name = helpers.dev_staging_repo
                prod_staging_name = helpers.prod_staging_repo
            else:
                dev_staging_name = f"{helpers.dev_staging_repo}/{name}"
                prod_staging_name = f"{helpers.prod_staging_repo}/{name}"
            print(f"creating tag. Source: '{dev_staging_name}:{version}', Dest: '{prod_staging_name}:{version}'")
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
            if name == helpers.application_name:
                image_ref = helpers.dev_staging_repo
            else:
                image_ref = f'{helpers.dev_staging_repo}/{name}'
            cp = helpers.run(
                f"""
                docker image rm {image_ref}:{version}
                docker image rm {image_ref}:{short_version}
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
    parser.add_argument(
        '--deployer_only',
        '-d',
        action='store_true')

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
        ImagePublisher().publish(version, args.deployer_only)

if __name__ == '__main__':
    main()
