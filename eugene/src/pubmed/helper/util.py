from Bio import Entrez

from pubmed.helper.const import DEFAULT_BIO_EMAIL


def apply_bio_email(email: str = DEFAULT_BIO_EMAIL) -> None:
    """
    To make use of NCBI's E-utilities, NCBI requires you to specify your
    email address with each request.  As an example, if your email address
    is A.N.Other@example.com, you can specify it as follows:
        from Bio import Entrez
        Entrez.email = 'A.N.Other@example.com'
    In case of excessive usage of the E-utilities, NCBI will attempt to contact
    a user at the email address provided before blocking access to the
    E-utilities.
    """
    Entrez.email = email
