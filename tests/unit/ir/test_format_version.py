"""Tests for the shared format-version reader (capability ir/format-version)."""

import pytest

from morphir.ir import diagnostics as d
from morphir.ir.diagnostics import DiagnosticError
from morphir.ir.format_version import (
    SUPPORT_TABLE,
    V3_TABLE,
    FormatVersion,
    dump_json,
    parse_json,
    read_document,
    read_format_version,
    recognize_format_version,
    table_to_string,
    write_format_version,
)


def codes(value: object, table=SUPPORT_TABLE) -> tuple[str, ...]:
    with pytest.raises(DiagnosticError) as info:
        read_format_version(value, table)
    return info.value.codes


class TestRecognition:
    @pytest.mark.parametrize("value", [3, "3", "3.0.0"])
    def test_spellings_normalize_to_3_0_0(self, value: object) -> None:
        assert read_format_version(value) == FormatVersion(3, 0, 0)

    @pytest.mark.parametrize("value", [4, "4", "4.0.0", "4.0.7"])
    def test_v4_spellings(self, value: object) -> None:
        assert read_format_version(value).major == 4

    @pytest.mark.parametrize("value", [True, False, None, 3.0, -3, [3], {"v": 3}])
    def test_invalid_type(self, value: object) -> None:
        assert codes(value) == (d.INVALID_FORMAT_VERSION_TYPE,)

    @pytest.mark.parametrize(
        "value",
        [
            "3.0.0-alpha",
            " 3.0.0",
            "3.0.0 ",
            "+3.0.0",
            "03.0.0",
            "3.00.0",
            "3.0",
            "3.0.0.0",
            "4.0.0+build",
            "",
            0,
            "0",
            "1",
            "2.0.0",
        ],
    )
    def test_invalid_syntax(self, value: object) -> None:
        assert codes(value) == (d.INVALID_FORMAT_VERSION_SYNTAX,)

    @pytest.mark.parametrize("value", [4294967296, "3.4294967296.0", "4294967296"])
    def test_out_of_range(self, value: object) -> None:
        assert codes(value) == (d.FORMAT_VERSION_OUT_OF_RANGE,)

    def test_historical_integers_are_recognized(self) -> None:
        assert recognize_format_version(1) == FormatVersion(1, 0, 0)
        assert recognize_format_version(2) == FormatVersion(2, 0, 0)


class TestSupport:
    @pytest.mark.parametrize("value", [1, 2])
    def test_historical_versions_are_follow_up_work(self, value: int) -> None:
        with pytest.raises(DiagnosticError) as info:
            read_format_version(value)
        assert info.value.codes == (d.UNSUPPORTED_FORMAT_VERSION_MAJOR,)
        assert "formats 1 and 2 are follow-up work" in str(info.value)

    def test_ir_3_1_is_refused(self) -> None:
        with pytest.raises(DiagnosticError) as info:
            read_format_version("3.1.0")
        assert info.value.codes == (d.UNSUPPORTED_FORMAT_VERSION_MINOR,)
        assert "issues/28" in str(info.value)

    def test_v4_minor_is_refused(self) -> None:
        assert codes("4.1.0") == (d.UNSUPPORTED_FORMAT_VERSION_MINOR,)

    def test_unknown_major(self) -> None:
        assert codes(5) == (d.UNSUPPORTED_FORMAT_VERSION_MAJOR,)

    def test_family_table_refuses_other_family(self) -> None:
        with pytest.raises(DiagnosticError) as info:
            read_format_version(4, V3_TABLE)
        assert info.value.codes == (d.UNSUPPORTED_FORMAT_VERSION_MAJOR,)
        assert "only 3.0.x" in str(info.value)

    def test_table_spelling(self) -> None:
        assert table_to_string(SUPPORT_TABLE) == "[3.0.0,3.1.0),[4.0.0,4.1.0)"


class TestWriting:
    def test_baseline_is_integer(self) -> None:
        assert write_format_version(read_format_version("3.0.0")) == 3

    def test_patch_is_string(self) -> None:
        assert write_format_version(FormatVersion(4, 0, 2)) == "4.0.2"

    def test_str(self) -> None:
        assert str(FormatVersion(3, 0, 0)) == "3.0.0"

    def test_dump_json_is_compact(self) -> None:
        assert (
            dump_json({"formatVersion": 3, "a": [1]}) == '{"formatVersion":3,"a":[1]}'
        )


class TestDocument:
    def test_missing_version(self) -> None:
        with pytest.raises(DiagnosticError) as info:
            read_document('{"distribution": []}')
        assert info.value.codes == (d.MISSING_FORMAT_VERSION,)
        assert "regenerate" in str(info.value)

    def test_duplicate_version(self) -> None:
        with pytest.raises(DiagnosticError) as info:
            read_document('{"formatVersion": 3, "formatVersion": 4}')
        assert info.value.codes == (d.DUPLICATE_FORMAT_VERSION,)

    def test_duplicate_nested_member(self) -> None:
        with pytest.raises(DiagnosticError) as info:
            parse_json('{"formatVersion": 3, "x": {"a": 1, "a": 2}}')
        assert info.value.codes == (d.DUPLICATE_MEMBER,)

    def test_invalid_json(self) -> None:
        with pytest.raises(DiagnosticError) as info:
            read_document("{not json")
        assert info.value.codes == (d.INVALID_JSON,)

    def test_root_must_be_object(self) -> None:
        with pytest.raises(DiagnosticError) as info:
            read_document("[3]")
        assert info.value.codes == (d.INVALID_JSON,)

    def test_version_after_distribution_is_accepted(self) -> None:
        version, root = read_document('{"distribution": 1, "formatVersion": "3"}')
        assert version == FormatVersion(3, 0, 0)
        assert root["distribution"] == 1

    def test_decoded_value_input(self) -> None:
        version, _ = read_document({"formatVersion": 4})
        assert version.major == 4

    def test_diagnostic_render(self) -> None:
        diagnostic = d.Diagnostic("c", "X", ("a", 1), "msg")
        assert diagnostic.render() == "c at a/1: msg"
        assert d.Diagnostic("c", "X", (), "msg").render() == "c at <root>: msg"
