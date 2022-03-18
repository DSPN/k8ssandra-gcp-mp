from argparse import ArgumentParser
import sys

import helpers

valid_operations = (
    'build',
    'push',
    'remove',
)

def build():
    print(f"building 'deployer'")
    version, short_version = helpers.get_versions()
    cp = helpers.run(
        f"""
        docker build -t {helpers.dev_staging_repo}/deployer:{version} {helpers.tools_dir}/../..
        docker tag {helpers.dev_staging_repo}/deployer:{version} {helpers.dev_staging_repo}/deployer:{short_version}
        """
        )
    if cp.returncode != 0:
        raise Exception(
            f"""
            failed to build deployer image:
            {cp.stdout}
            """
            )
    print(cp.stdout)

def push():
    print("pushing 'deployer'")
    cp = helpers.run(
        f"""
        docker image push --all-tags {helpers.dev_staging_repo}/deployer
        """
        )
    if cp.returncode != 0:
        raise Exception(
            f"""
            pushing deployer image failed:
            {cp.stdout}
            """
            )
    print(cp.stdout)

def remove(version):
    print("removing 'deployer' from local repo")
    short_version = helpers.get_short_version(version)
    cp = helpers.run(
        f"""
        docker image rm {helpers.dev_staging_repo}/deployer:{version}
        docker image rm {helpers.dev_staging_repo}/deployer:{short_version}
        """
        )
    if cp.returncode != 0:
        print(
            f"""
            failed to remove one or more of the local 'deployer' images':
            {cp.stdout}
            """
            )
    print(cp.stdout)


def main():
    parser = ArgumentParser()
    parser.add_argument(
        '--operation',
        '-o',
        choices=valid_operations,
        required=True)
    parser.add_argument(
        '--version',
        '-v')

    args = parser.parse_args()

    if args.operation == 'build':
        build()

    if args.operation == 'push':
        push()

    if args.operation == 'remove':
        if not args.version:
            print("<version> is required for the 'remove' operation")
            sys.exit(1)
        remove(args.version)


if __name__ == '__main__':
    main()
