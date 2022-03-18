from argparse import ArgumentParser
import sys

import helpers

valid_operations = (
    'print',
)

def print_manifest(include_crds=False):
    manifest = helpers.render_template(include_crds=include_crds)
    print(manifest)

def main():
    parser = ArgumentParser()
    parser.add_argument(
        '--operation',
        '-o',
        choices=valid_operations,
        required=True)
    parser.add_argument(
        '--include-crds',
        '-c',
        action='store_true',
        default=False)

    args = parser.parse_args()

    if args.operation == 'print':
        print_manifest(include_crds=args.include_crds)


if __name__ == '__main__':
    main()
