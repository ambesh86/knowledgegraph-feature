from patent.application.provider.application_orchestrator import ApplicationOrchestator
from patent.pgpub.provider.pgpub_orchestrator import PgpubOrchestrator
from patent.provider.patent_orchestrator import PatentOrchestrator
from patent.application.conf.conf import application_orchestrator
from patent.pgpub.conf.conf import pgpub_orchestrator
from patent.pgpub.writer.json_writer import JsonWriter as PgpubJsonWriter
from patent.application.writer.json_writer import JsonWriter


def pgpub_json_writer() -> PgpubJsonWriter:
    return PgpubJsonWriter()


def application_json_writer() -> JsonWriter:
    return JsonWriter()


def patent_orchestrator() -> PatentOrchestrator:
    return _patent_orchestrator(
        application_orchestrator=application_orchestrator(),
        pgpub_orchestrator=pgpub_orchestrator(),
        application_json_writer=application_json_writer(),
        pgpub_json_writer=pgpub_json_writer(),
    )


def _patent_orchestrator(
    application_orchestrator: ApplicationOrchestator,
    pgpub_orchestrator: PgpubOrchestrator,
    application_json_writer: JsonWriter,
    pgpub_json_writer: PgpubJsonWriter,
) -> PatentOrchestrator:
    return PatentOrchestrator(
        application_orchestrator=application_orchestrator,
        pgpub_orchestrator=pgpub_orchestrator,
        application_json_writer=application_json_writer,
        pgpub_json_writer=pgpub_json_writer,
    )
