from argparse import ArgumentParser
import sys

import helpers

valid_operations = (
    'dev-install',
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

    if args.operation == 'dev-install':
        if not args.version:
            print("<version> is required for the 'dev-install' operation")
            sys.exit(1)
        dev_install(args.version)

if __name__ == '__main__':
    main()
