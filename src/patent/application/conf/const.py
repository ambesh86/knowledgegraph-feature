USPTO_API_BASE_URI = "https://api.uspto.gov/api/v1/patent/applications"
USPTO_FILES_BASE_URI = "https://api.uspto.gov/api/v1/datasets/products/files"
USPTO_SEARCH_URI = "https://api.uspto.gov/api/v1/patent/applications/search"


def build_list_assoc_docs_uri(application_number_text: str) -> str:
    if application_number_text is None:
        raise ValueError("application number text cannot be None")
    return f"{USPTO_API_BASE_URI}/{application_number_text}/associated-documents"
