from argparse import ArgumentParser
import sys

import helpers

valid_operations = (
    'dev-install',
    'prod-install',
)

def dev_install(version):
    cp = helpers.run(
        """
        mpdev install --deployer={deployer} \
                      --parameters='{{"name": "{app_name}", "namespace": "default"}}'
        """.format(deployer=f"{helpers.dev_staging_repo}/deployer:{version}",
                   app_name=helpers.application_name)

        )
    print(cp.stdout)

def prod_install(version):
    cp = helpers.run(
        """
        mpdev install --deployer={deployer} \
                      --parameters='{{"name": "{app_name}", "namespace": "default"}}'
        """.format(deployer=f"{helpers.prod_staging_repo}/deployer:{version}",
                   app_name=helpers.application_name)

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

    if args.operation in ('dev-install', 'prod-install') and \
        not args.version:
            print(f"<version> is required for the '{args.operation}' operation")
            sys.exit(1)

    if args.operation == 'dev-install':
        dev_install(args.version)

    if args.operation == 'prod-install':
        prod_install(args.version)

if __name__ == '__main__':
    main()
