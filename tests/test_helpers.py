from coalesc.cdhit import MODES, allowed_filename, auto_word_size, count_members, sniff_seq_type


def test_every_mode_maps_to_a_real_program():
    assert {m.program for m in MODES.values()} == {"cd-hit", "cd-hit-est", "cd-hit-2d", "cd-hit-est-2d"}
    assert MODES["h-cd-hit"].levels and MODES["h-cd-hit-est"].levels and not MODES["cd-hit"].levels


def test_auto_word_size_stays_in_cdhit_limits():
    for ident in [i / 100 for i in range(40, 101)]:
        assert 2 <= auto_word_size(ident, False) <= 5
    for ident in [i / 100 for i in range(80, 101)]:
        assert 4 <= auto_word_size(ident, True) <= 11
    assert auto_word_size(0.9, False) == 5 and auto_word_size(0.5, False) == 3


def test_filenames():
    assert allowed_filename("a.FASTA") and allowed_filename("a.faa")
    assert not allowed_filename("a.exe") and not allowed_filename("noext")


def test_sniff(tmp_path):
    p = tmp_path / "a.fa"
    p.write_text(">a\n" + "ACGT" * 20 + "\n")
    assert sniff_seq_type(p) == "nuc"
    p.write_text(">a\n" + "MKVLAAGIVGLLLAQPSDEFHYWRKK" * 3 + "\n")
    assert sniff_seq_type(p) == "prot"
    p.write_text(">a\nACGT\n")
    assert sniff_seq_type(p) is None
    assert sniff_seq_type(tmp_path / "missing") is None


def test_count_members():
    assert count_members(">Cluster 0\n0\t10aa, >a... *\n1\t9aa, >b... at 90%\n") == 2
