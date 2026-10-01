import logging
from pathlib import Path

from dotenv import load_dotenv

from graph.analyze.knowledge_graph_dir_analyzer import KnowledgeGraphDirAnalyzer
from graph.conf.conf import eugene_graph_summary_orchestrator, stored_triples_loader
from graph.analyze.eugene_graph_summary_orchestrator import (
    EugeneGraphSummaryOrchestrator,
)
from infra.util.file_util import generate_path_hash
from pubmed.helper.util import extract_pmcid

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    """
    process pubmed articles and link them to existing foundational nodes
    """
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="Link existing pubmed articles from either on disk or by pmcid, stores nodes into the euGENE db"
    )
    parser.add_argument(
        "--use-checkpoints",
        action="store_true",
        required=False,
        help="ingest articles and link by existing preprocessed checkpoints, otherwise reads files from disk",
    )

    args = parser.parse_args()

    load_dotenv()

    max_workers = 3
    summary_orchestrator = eugene_graph_summary_orchestrator(max_workers=max_workers)
    if args.use_checkpoints:
        checkpoint_dir = "output"
        process_checkpoints(
            checkpoint_dir=checkpoint_dir, summary_orchestrator=summary_orchestrator
        )
    else:
        data_dir = "./resources/data/pubmed"
        include_file_extensions = {".pdf"}
        max_documents_to_process = 9999
        build_knowledge_graph(
            data_dir,
            include_file_extensions,
            max_documents_to_process,
            summary_orchestrator=summary_orchestrator,
        )


def process_checkpoints(
    checkpoint_dir: str, summary_orchestrator: EugeneGraphSummaryOrchestrator
) -> None:
    """
    FIXME: verify pubmed summary nodes are reloaded correctly
    """
    files_to_load = generate_files_to_load()
    print(f"Generating files to load: {files_to_load}")
    triples_loaders = stored_triples_loader()
    base_dir = Path(checkpoint_dir)
    missing_checkpoints = 0
    num_checkpoints = len(files_to_load)
    logger.info(f"loading {len(files_to_load)} files")
    for file_to_load in files_to_load:
        pmcid = file_to_load["pmcid"]
        file_hash = file_to_load["file_hash"]
        processed_checkpoint = base_dir / file_hash
        # logger.info(
        #     f"processing checkpoint {processed_checkpoint}, pmcid: {pmcid}, file_name: {file_to_load["file_name"]}"
        # )
        if not processed_checkpoint.exists():
            logger.warning(f"{processed_checkpoint} does not exist, moving on...")
            missing_checkpoints += 1
            continue
        extraction = triples_loaders.load([processed_checkpoint])
        summary_orchestrator.load_from_entities(
            pmcid=pmcid, entities=extraction.entities
        )
        summary_orchestrator.summarize_communities(
            pmcid=pmcid,
            report_base=str(processed_checkpoint),
            doc_extraction=extraction,
        )

    logger.info(
        f"loaded {num_checkpoints - missing_checkpoints}/{num_checkpoints} checkpoint(s)"
    )


def build_knowledge_graph(
    data_dir: str,
    include_file_extensions: set[str],
    max_documents_to_process: int,
    summary_orchestrator: EugeneGraphSummaryOrchestrator,
):
    dir_analyzer = KnowledgeGraphDirAnalyzer(
        data_dir,
        include_file_extensions,
        summary_orchestrator=summary_orchestrator,
        max_documents_to_process=max_documents_to_process,
    )
    dir_analyzer.analyze_dir()


def generate_files_to_load() -> list[dict[str, str]]:
    """
    we need to generate files to load
      since the checkpoint folders do not contain the pmcid
    """
    file_names = [
        "11759061.10.1038_s41409-023-02109-x.pdf",
        "11759780.10.3390_biomedicines13010163.pdf",
        "11765694.10.3390_ijms26020856.pdf",
        "11780712.10.1016_j.reth.2025.01.002.pdf",
        "11781120.bmjopen-15-1.pdf",
        "11782851.10.1016_j.reth.2024.12.017.pdf",
        "11787463.10.1182_bloodadvances.2024014762.pdf",
        "11787516.10.1016_j.omtm.2024.101399.pdf",
        "11787635.10.1016_j.rpth.2024.102673.pdf",
        "11787650.10.1016_j.omtn.2024.102442.pdf",
        "11788621.10.3324_haematol.2024.285291.pdf",
        "11788778.10.30476_ijcbnm.2024.101885.2449.pdf",
        "11788946.JPN3-80-271.pdf",
        "11790519.CGE-107-341.pdf",
        "11792258.10.1186_s12911-025-02901-3.pdf",
        "11792665.10.1186_s40364-025-00736-8.pdf",
        "11794699.10.1038_s41419-025-07377-7.pdf",
        "11795545.10.1016_j.idcr.2025.e02160.pdf",
        "11796136.10.1186_s13054-025-05283-0.pdf",
        "11796191.10.1186_s13058-024-01950-2.pdf",
        "11796319.FEBS-292-582.pdf",
        "11796389.mbio.02683-24.pdf",
        "11798761.EJH-114-556.pdf",
        "11798763.EJH-114-508.pdf",
        "11800340.CJAS_52_2369953.pdf",
        "11800379.10.1021_acs.biochem.4c00704.pdf",
        "11800397.10.1021_acs.biochem.4c00703.pdf",
        "11801364.jmcp.2025.31.2.214.pdf",
        "11801798.elife-86931.pdf",
        "11802235.10.2169_internalmedicine.3334-23.pdf",
        "11802543.10.3389_fcimb.2024.1410506.pdf",
        "11803641.10.1177_19160216251315057.pdf",
        "11803812.10.12669_pjms.41.2.8775.pdf",
        "11804970.10.1016_j.neuron.2019.02.017.pdf",
        "11805391.pone.0318564.pdf",
        "11805675.CCR3-13-e70180.pdf",
        "11805716.CCR3-13-e70190.pdf",
        "11805920.10.1038_s41467-025-56603-5.pdf",
        "11806117.10.1038_s41392-024-02104-8.pdf",
        "11806235.med-2024-1137.pdf",
        "11806339.10.1016_j.identj.2024.12.013.pdf",
        "11806481.10.1177_03000605251315359.pdf",
        "11806493.10.1177_17562848251314820.pdf",
        "11806600.10.1186_s13287-025-04187-8.pdf",
        "11806621.10.1186_s13052-025-01862-7.pdf",
        "11806646.10.7759_cureus.77184.pdf",
        "11806675.10.2147_IDR.S501622.pdf",
        "11806677.10.2147_IJN.S505591.pdf",
        "11806705.10.2147_JIR.S502980.pdf",
        "11806711.10.2147_JIR.S480911.pdf",
        "11806729.10.2147_IJN.S510339.pdf",
        "11806736.10.2147_IJN.S508781.pdf",
        "11806757.10.2147_JIR.S497201.pdf",
        "11806790.10.1186_s13063-024-08715-4.pdf",
        "11806872.JMV-97-e70222.pdf",
    ]

    list = []
    base_name = "./resources/data"
    for file_name in file_names:
        pmcid = extract_pmcid(file_name)
        if pmcid is None:
            logger.warning(
                f"cannot extract pmcid from file name {file_name}. Dropping record..."
            )
            continue
        attribs = {
            "pmcid": int(pmcid),
            "file_name": file_name,
            "file_hash": generate_path_hash(f"{base_name}/{file_name}"),
        }
        list.append(attribs)
    return list


if __name__ == "__main__":
    main()
