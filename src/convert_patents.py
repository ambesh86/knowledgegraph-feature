import logging

from argparse import Namespace
from pathlib import Path
from dotenv import load_dotenv

from patent.conf.conf import application_converter_provider, pgpub_converter_provider

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    """
    convert uspto patents to txt store them on disk
    """
    load_dotenv()

    args = build_args()
    input = Path(args.input)
    output = Path(args.output)
    convert_applications(input, output)
    convert_pgpubs(input, output)


def convert_pgpubs(input: Path, output: Path):
    converter = pgpub_converter_provider()
    pgpub_dir = "pgpub"
    converter.convert(
        input_path=input / pgpub_dir,
        out_path_base=output / pgpub_dir,
    )


def convert_applications(input: Path, output: Path):
    converter = application_converter_provider()
    application_dir = "application"
    converter.convert(
        input_path=input / application_dir,
        out_path_base=output / application_dir,
    )


def build_args() -> Namespace:
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="convert recent USPTO medical pregrant patents fron json to txt. Stores on disk"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("resources/data/json"),
        required=False,
        help="base input directory, defaults to resources/data/json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("resources/data/txt"),
        required=False,
        help="base output directory, defaults to resources/data/txt",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
