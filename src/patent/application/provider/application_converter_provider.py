import logging
from pathlib import Path

from patent.application.loader.application_loader import ApplicationLoader
from patent.application.writer.txt_writer import TxtWriter

logger = logging.getLogger(__name__)


class ApplicationConverterProvider:

    def __init__(self, loader: ApplicationLoader, writer: TxtWriter):
        self.loader = loader
        self.writer = writer

    def convert(self, input_path: Path, out_path_base: Path) -> None:
        if input_path is None:
            return

        applications = self.loader.load_all(data_dir=input_path)
        logger.info(f"found applications {len(applications)}")
        self.writer.write(applications=applications, out_path_base=out_path_base)
        logger.info(f"done converting {len(applications)}")
