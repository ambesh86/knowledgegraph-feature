import logging
import os
from pathlib import Path

from marko import Markdown
from marko.block import FencedCode
from marko.inline import RawText

from graph.mapper.summaries_parser import SummariesParser
from graph.model.summary import Summary
from infra.util.file_util import list_data_files

logger = logging.getLogger(__name__)


class StoredSummariesLoader:
    def __init__(self, summaries_parser: SummariesParser):
        self.summaries_parser = summaries_parser

    def load(self, data_dirs: list[Path]) -> list[Summary]:
        if data_dirs is None or len(data_dirs) < 1:
            return None

        summaries = []
        for dir in data_dirs:
            logger.debug(f"searching {dir}")
            summary_files = self._find_summary_files(dir)
            if summary_files is None or len(summary_files) < 1:
                logger.warning(
                    f"No summaries file found in {dir}. Moving on to next dir..."
                )
                continue

            for summary_file in summary_files:
                summaries.extend(self.read_summaries_from_file(summary_file))

        logger.info(f"total summaries: {len(summaries)}")
        for summary in summaries:
            logger.debug(f"found summary for file: {summary.id}")
        return summaries

    def read_summaries_from_file(self, summary_file: str) -> list[Summary]:
        if summary_file is None:
            return []
        json_payloads = self._read_summary_json_payloads(summary_file=summary_file)
        logger.info(f"json payloads {json_payloads}")
        summaries = []
        # logger.debug(f"reading summary file {summary_file}")
        for json in json_payloads:
            path_id = self._split_all(summary_file)[-2]
            summary = self.summaries_parser.parse(json_payload=json)
            logger.info(
                f"parsed file {path_id} summary title: {summary.title} findings: {summary.findings}"
            )
            summary.id = path_id
            summaries.append(summary)
        return summaries

    def _read_summary_json_payloads(self, summary_file: str) -> list[str]:
        json_payloads = []
        with open(summary_file, mode="r") as markdown_in:
            text = markdown_in.read()
            markdown_parser = Markdown()
            ast = markdown_parser.parse(text=text)
            for node in ast.children:
                if isinstance(node, FencedCode):
                    child_text = self._extract_from_ast(node)
                    text = "".join(child_text)
                    json_payloads.append(text)

        return json_payloads

    def _extract_from_ast(self, element) -> list[str]:
        raw_texts = []
        if isinstance(element, RawText):
            raw_texts.append(element.children)
        elif hasattr(element, "children"):
            for child in element.children:
                return self._extract_from_ast(child)
        return raw_texts

    def _find_summary_files(self, data_dir: Path) -> list[str]:
        summary_files = []
        files = list_data_files(data_dir, {".md"})
        for file in files:
            basename = os.path.basename(file)
            if basename.startswith("communities_level") and basename.endswith(".md"):
                summary_files.append(file)

        return summary_files

    def _split_all(self, path) -> list[str]:
        # https://www.oreilly.com/library/view/python-cookbook/0596001673/ch04s16.html
        allparts = []
        while 1:
            parts = os.path.split(path)
            if parts[0] == path:  # sentinel for absolute paths
                allparts.insert(0, parts[0])
                break
            elif parts[1] == path:  # sentinel for relative paths
                allparts.insert(0, parts[1])
                break
            else:
                path = parts[0]
                allparts.insert(0, parts[1])
        return allparts
