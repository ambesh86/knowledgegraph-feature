import logging
from pathlib import Path

from patent.pgpub.loader.pgpub_loader import PgpubLoader
from patent.pgpub.writer.txt_writer import TxtWriter

logger = logging.getLogger(__name__)


class PgpubConverterProvider:

    def __init__(self, loader: PgpubLoader, writer: TxtWriter):
        self.loader = loader
        self.writer = writer

    def convert(self, input_path: Path, out_path_base: Path) -> None:
        if input_path is None:
            return

        pgpubs = self.loader.load_all(data_dir=input_path)
        logger.info(f"found pgpubs {len(pgpubs)}")
        self.writer.write(pgpubs=pgpubs, out_path_base=out_path_base)
        logger.info(f"done converting {len(pgpubs)}")
