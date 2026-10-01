import logging
from pathlib import Path
import requests
import tqdm
import urllib3
import certifi
from infra.util.file_util import ensure_exists

logger = logging.getLogger(__name__)


class PubmedDownloadProvider:
    """
    this class will download a pubmed pdf file
    """

    PDF_URI_TEMPLATE = "https://pmc.ncbi.nlm.nih.gov/articles/PMC{}/pdf/{}"

    def __init__(self, download_dest: Path = Path("/tmp")):
        self.download_dest = download_dest
        self.headers = {
            "Referer": "https://pmc.ncbi.nlm.nih.gov/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        }

    def download(self, pmcid: str, pdf_name: str) -> None:
        """
        pdfs are available from pmc

        see, https://pmc.ncbi.nlm.nih.gov/articles/PMC11781120/pdf/bmjopen-15-1.pdf
        """
        if self.download_dest is None:
            msg = f"please set download destination before downloading"
            logger.warning(msg)
            raise Exception(msg)
        else:
            ensure_exists(self.download_dest)

        logger.info(f"downloading {pmcid} {pdf_name}...")
        pdf_name = self._clean_uri(pdf_name)
        pdf_uri = self._build_uri(pmcid=pmcid, pdf_name=pdf_name)
        response = None
        try:
            pdf_name = self._fix_pdf_name_suffix(pdf_name)
            logger.debug(f"starting pdf download {pmcid} {pdf_name}")
            urllib3.disable_warnings()
            
            #response = requests.get(pdf_uri,headers=self.headers,stream=True,verify=certifi.where(),timeout=60)
            response = requests.get(pdf_uri,headers=self.headers,allow_redirects=True, stream=True,verify=False,timeout=60)
            print("=" * 50)
            print("URL:", pdf_uri)
            print("Status:", response.status_code)
            print("Content-Type:", response.headers.get("Content-Type"))
            print("Content-Length:", response.headers.get("Content-Length"))
            print("Response URL:", response.url)
            print("=" * 50)
            if response.status_code == 200:
                self._stream_response(response, pmcid, pdf_name)
            else:
                logger.warning(
                    f"failed to download {pdf_name}. Status code: {response.status_code}"
                )

        except Exception as e:
            logger.error(f"An error occurred: {e}")
        finally:
            if response is not None:
                response.close()

    def _stream_response(self, response, pmcid: str, pdf_name: str) -> None:
        block_size = 1024
        t_progress = None
        try:
            total_size = int(response.headers.get("content-length", 0))
            t_progress = tqdm.tqdm(total=total_size, unit=".", unit_scale=True)
            file_name = f"{pmcid}.{pdf_name}"
            output_path = self.download_dest / file_name
            with open(output_path, "wb") as file:
                for chunk in response.iter_content(block_size):
                    if chunk:
                        file.write(chunk)
                        t_progress.update(len(chunk))
        finally:
            if t_progress is not None:
                t_progress.close()
        logger.info(f"downloaded {pdf_name} successfully!")

    def _clean_uri(self, pdf_uri: str = "") -> str:
        if pdf_uri is None:
            return pdf_uri

        prefixes = ["file://", "file:"]
        pdf = pdf_uri
        for prefix in prefixes:
            if pdf_uri.startswith(prefix):
                pdf = pdf_uri[len(prefix) :]

        pdf = pdf.replace("/", "_")
        return pdf

    def _build_uri(self, pmcid: str, pdf_name: str) -> str:
        return PubmedDownloadProvider.PDF_URI_TEMPLATE.format(pmcid, pdf_name)

    def _fix_pdf_name_suffix(self, pdf_name: str) -> str:
        pdf_suffix = ".pdf"
        has_suffix = pdf_name.endswith(pdf_suffix)
        if not has_suffix:
            pdf_name = f"{pdf_name}{pdf_suffix}"
        return pdf_name
