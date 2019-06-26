# Lib
import argparse
import logging
from pathlib import Path
import sys
# App
from .files import get_sample_sheet
from .models import ArrayType
from .processing import run_pipeline


class DefaultParser(argparse.ArgumentParser):
    def error(self, message):
        self._print_message('[Error]:\n')
        self._print_message(f'{message}\n\n')
        self.print_help()
        self.exit(status=2)


def build_parser():
    parser = DefaultParser(
        prog='methpype',
        description="""Utility to process methylation data from Illumina IDAT files.
        There are two types of processing: "process" IDAT files or read a "sample_sheet" contents.
        Example of usage: `python -m methpype -v process -d <path to your samplesheet.csv and idat files>`\n
        Try our demo dataset: `python -m methpype -v process -d docs/example_data/GSE69852`""",
    )

    parser.add_argument(
        '-v', '--verbose',
        help='Enable verbose logging. Reports the path(s) where processed files are stored.',
        action='store_true',
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    process_parser = subparsers.add_parser('process', help='process help')
    process_parser.set_defaults(func=cli_process)

    sample_sheet_parser = subparsers.add_parser('sample_sheet', help='sample sheet help')
    sample_sheet_parser.set_defaults(func=cli_sample_sheet)

    parsed_args, func_args = parser.parse_known_args(sys.argv[1:])
    if parsed_args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    parsed_args.func(func_args)
    return parser


def cli_sample_sheet(cmd_args):
    parser = DefaultParser(
        prog='methpype sample_sheet',
        description='Process Illumina sample sheet file',
    )

    parser.add_argument(
        '-d', '--data_dir',
        required=True,
        type=Path,
        help='Base directory of the sample sheet and associated IDAT files.',
    )

    parsed_args = parser.parse_args(cmd_args)

    sample_sheet = get_sample_sheet(parsed_args.data_dir)
    for sample in sample_sheet.get_samples():
        sys.stdout.write(f'{sample}\n')


def cli_process(cmd_args):
    parser = DefaultParser(
        prog='methpype idat',
        description='Process Illumina IDAT files',
    )

    parser.add_argument(
        '-d', '--data_dir',
        required=True,
        type=Path,
        help='Base directory of the sample sheet and associated IDAT files. If IDAT files are in nested directories, this will discover them.',
    )

    parser.add_argument(
        '-a', '--array_type',
        choices=list(ArrayType),
        required=False,
        type=ArrayType,
        help='Type of array being processed. If omitted, this will autodetect it.',
    )

    parser.add_argument(
        '-m', '--manifest',
        required=False,
        type=Path,
        help='File path of the array manifest file. If omitted, this will download the appropriate file from `s3`.',
    )

    parser.add_argument(
        '-s', '--sample_sheet',
        required=False,
        type=Path,
        help='File path of the sample sheet. If omitted, this will discover it. There must be only one CSV file in the data_dir for discovery to work.',
    )

    parser.add_argument(
        '-n', '--sample_name',
        required=False,
        nargs='*',
        help='Sample(s) to process',
    )

    parser.add_argument(
        '-e', '--no_export',
        required=False,
        action='store_false', # if -e passed, this suppresses data export (if running as part of pipeline or something)
        default=True, # if False, CLI returns nothing.
        help='Default is to export data to csv in same folder where IDAT file resides. Pass in --no_export to suppress this.',
    )

    args = parser.parse_args(cmd_args)

    array_type = args.array_type
    manifest_filepath = args.manifest

    if not array_type and not manifest_filepath:
        #print("This will attempt to autodetect your methylation array_type and download the corresponding manifest file.")
        logging.info('This will attempt to autodetect your methylation array_type and download the corresponding manifest file.')
        #return

    run_pipeline(
        args.data_dir,
        array_type=args.array_type,
        export=args.no_export,
        manifest_filepath=args.manifest,
        sample_sheet_filepath=args.sample_sheet,
        sample_names=args.sample_name,
    )


def cli_app():
    build_parser()