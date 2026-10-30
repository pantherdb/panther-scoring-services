import pytest
from csnp_fixtures import edited, lines

from panther_engine.csnp.library import LibraryFormatError
from panther_engine.csnp.species import read_species

SPECIES = "species.nhx"


def test_each_taxon_has_its_age() -> None:
    ages = read_species(lines(SPECIES), SPECIES)

    assert ages == {"Homo-Pan": 6, "Euarchontoglires": 91, "LUCA": 4200}


def test_a_misspelt_tag_is_read_all_the_same() -> None:
    assert "[&&NXH:S=Euarchontoglires:A=91]" in lines(SPECIES)[0]

    assert read_species(lines(SPECIES), SPECIES)["Euarchontoglires"] == 91


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("[&&NHX:S=LUCA:A=4200]", "[&&XYZ:S=LUCA:A=4200]", "not NHX attributes"),
        ("A=4200", "A=4200.5", "isn't a whole number"),
        ("S=Homo-Pan", "S=LUCA", "LUCA appears twice"),
    ],
)
def test_bad_attributes_are_an_error(old: str, new: str, message: str) -> None:
    with pytest.raises(LibraryFormatError, match=message):
        read_species(edited(SPECIES, old, new), SPECIES)


def test_a_second_line_is_an_error() -> None:
    with pytest.raises(LibraryFormatError, match="more than one line"):
        read_species([*lines(SPECIES), "(A,B);\n"], SPECIES)
