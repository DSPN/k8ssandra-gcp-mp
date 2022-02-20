from argparse import ArgumentParser
import sys

import helpers

valid_operations = (
    'dev-install',
    'prod-install',
)

def dev_install(version, namespace="default"):
    cp = helpers.run(
        """
        mpdev install --deployer={deployer} \
                      --parameters='{{"name": "{app_name}", "namespace": "{namespace}"}}'
        """.format(deployer=f"{helpers.dev_staging_repo}/deployer:{version}",
                   app_name=helpers.application_name,
                   namespace=namespace)

        )
    print(cp.stdout)

def prod_install(version, namespace="default"):
    cp = helpers.run(
        """
        mpdev install --deployer={deployer} \
                      --parameters='{{"name": "{app_name}", "namespace": "{namespace}"}}'
        """.format(deployer=f"{helpers.prod_staging_repo}/deployer:{version}",
                   app_name=helpers.application_name,
                   namespace=namespace)

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
    parser.add_argument(
        '--namespace',
        '-n',
        default='default')

    args = parser.parse_args()

    if args.operation in ('dev-install', 'prod-install') and \
        not args.version:
            print(f"<version> is required for the '{args.operation}' operation")
            sys.exit(1)

    if args.operation == 'dev-install':
        dev_install(args.version, args.namespace)

    if args.operation == 'prod-install':
        prod_install(args.version, args.namespace)

if __name__ == '__main__':
    main()
