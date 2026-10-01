from enum import Enum


class TheraputicAreaEnum(Enum):
    UNKNOWN = 0, "Unknown"
    VACCINES = (
        1,
        "Encompasses the prevention of infectious diseases by stimulating the immune system to recognize and combat specific pathogens, including viruses and bacteria, and extends to emerging applications in oncology and therapeutic immunomodulation.",
    )
    TRANSPLANT_AND_IMMUNOLOGY = (
        2,
        "Focuses on managing immune responses to prevent organ rejection in transplant patients and treating immune-related conditions, including autoimmune diseases and immunodeficiencies, through immunomodulation and immune system regulation.",
    )
    CARDIOVASCULAR_AND_RENAL = (
        3,
        "Encompasses the prevention, diagnosis, and treatment of diseases affecting the heart, blood vessels, and kidneys, including conditions such as hypertension, heart failure, chronic kidney disease, and atherosclerosis.",
    )
    HEMATOLOGY = (
        4,
        "Involves blood-related disorders like anemia, leukemia, lymphoma, and clotting abnormalities such as hemophilia. Research focuses on blood cell regeneration, stem cell therapies, and treatments for blood cancers using immunotherapy and gene editing technologies.",
    )
    IMMUNOGLOBULIN = (
        5,
        "The therapeutic area of immunoglobulin encompasses the treatment of primary and secondary immunodeficiency disorders, autoimmune diseases, and inflammatory conditions, leveraging its role in immune modulation and passive immunity.",
    )
