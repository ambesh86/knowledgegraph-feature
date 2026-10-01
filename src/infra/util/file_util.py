import hashlib
import logging
import os
from io import BufferedReader
from pathlib import Path

from infra.llm.prompt.prompt_response import PromptResponse

logger = logging.getLogger(__name__)


def ensure_path_exists(path: Path) -> None:
    logger.info(f"ensure path exists {path}")
    Path(path).mkdir(parents=True, exist_ok=True)


def ensure_parent_exists(file_path: Path) -> None:
    ensure_exists(file_path=file_path)


def ensure_exists(file_path: Path) -> None:
    """
    take parent of path given and create all parents
    """
    dir_path = os.path.dirname(file_path)
    logger.info(f"ensure parent folder exists {dir_path}")
    Path(dir_path).mkdir(parents=True, exist_ok=True)


def write_lines(file_path: Path, lines: list[str]) -> None:
    ensure_exists(file_path=file_path)
    with open(file_path, "w+") as report:
        for line in lines:
            report.write(f"{line}\n")


def write_answers(report_name: str, all_responses: list[PromptResponse]) -> None:
    ensure_exists(file_path=Path(report_name))
    with open(report_name, "w+") as report:
        report.write("# Analysis\n\n")
        for response in all_responses:
            report.write(f"## Answer\n\n {response.llm_response}\n\n")


def write_report(report_name: str, all_responses: list[PromptResponse]) -> None:
    ensure_exists(file_path=Path(report_name))
    with open(report_name, "w+") as report:
        report.write("# Analysis\n\n")
        for response in all_responses:
            report.write(f"## {response.title}\n\n")
            report.write(f"### Question\n\n {response.question}\n\n")
            report.write(f"### Answer\n\n {response.llm_response}\n\n")


def to_buffered_reader(file: str) -> BufferedReader:
    return open(file, "rb")


def read_contents(file: os.PathLike) -> str:
    with open(file, "r") as f:
        content = f.read()
    return content


def list_data_files(data_dir: str | Path, file_extensions: set[str]) -> list[str]:
    found = []
    for file in os.listdir(data_dir):
        extension = parse_for_file_ext(file)
        if extension in file_extensions:
            found.append(os.path.join(data_dir, file))
    return found


def parse_for_file_ext(path: str) -> str:
    if path.find(".") == -1:
        return path
    return path[path.rindex(".") :]


def generate_report_name(path: str, datasource: str | None = None) -> str:
    digest = generate_path_hash(path)
    base = "output"
    return (
        f"{base}/{datasource}/{digest}"
        if datasource is not None
        else f"{base}/{digest}"
    )


def generate_path_hash(path: str) -> str:
    return hashlib.md5(path.encode("utf-8")).hexdigest()


def move_succeeded(path: os.PathLike) -> None:
    _move_file(path, "succeeded")


def move_failed(path: os.PathLike) -> None:
    _move_file(path, "failed")


def _move_file(path: os.PathLike, state: str) -> None:
    dir_name = os.path.dirname(path)
    base_name = os.path.basename(path)
    processed_state_dir = Path(dir_name) / state
    dest = processed_state_dir / base_name
    ensure_exists(dest)
    os.rename(path, dest)
