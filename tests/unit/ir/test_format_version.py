"""Tests for the shared format-version reader (capability ir/format-version)."""

import pytest

from morphir.ir import diagnostics as d
from morphir.ir.diagnostics import DiagnosticError
from morphir.ir.format_version import (
    SUPPORT_TABLE,
    V3_1,
    V3_TABLE,
    FormatVersion,
    Interval,
    LegacyFormat,
    dump_json,
    parse_json,
    read_document,
    read_document_with_legacy,
    read_format_version,
    read_legacy_document,
    recognize_format_version,
    recognize_legacy_format,
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
    def test_legacy_versions_are_outside_the_table(self, value: int) -> None:
        with pytest.raises(DiagnosticError) as info:
            read_format_version(value)
        assert info.value.codes == (d.UNSUPPORTED_FORMAT_VERSION_MAJOR,)
        assert "legacy" in str(info.value)
        assert "codec_v1" in str(info.value)

    @pytest.mark.parametrize("value", ["3.1.0", "3.1.4"])
    def test_ir_3_1_is_supported(self, value: str) -> None:
        version = read_format_version(value)
        assert (version.major, version.minor) == (3, 1)

    def test_v3_1_names_the_release_that_added_specs(self) -> None:
        assert FormatVersion(3, 1, 0) == V3_1
        assert write_format_version(V3_1) == "3.1.0"

    def test_later_v3_minor_is_refused(self) -> None:
        with pytest.raises(DiagnosticError) as info:
            read_format_version("3.2.0")
        assert info.value.codes == (d.UNSUPPORTED_FORMAT_VERSION_MINOR,)
        message = str(info.value)
        assert "3.0.x, 3.1.x and draft 4.0.x" in message
        assert "[3.0.0,3.2.0),[4.0.0,4.1.0)" in message
        assert "issues/28" not in message

    def test_v4_minor_is_refused(self) -> None:
        assert codes("4.1.0") == (d.UNSUPPORTED_FORMAT_VERSION_MINOR,)

    def test_unknown_major(self) -> None:
        assert codes(5) == (d.UNSUPPORTED_FORMAT_VERSION_MAJOR,)

    def test_family_table_refuses_other_family(self) -> None:
        with pytest.raises(DiagnosticError) as info:
            read_format_version(4, V3_TABLE)
        assert info.value.codes == (d.UNSUPPORTED_FORMAT_VERSION_MAJOR,)
        assert "only 3.0.x and 3.1.x ([3.0.0,3.2.0))" in str(info.value)

    def test_custom_table_description_names_its_lowest_family(self) -> None:
        table = (
            Interval(FormatVersion(3, 0, 0), FormatVersion(3, 0, 5)),
            Interval(FormatVersion(4, 0, 0), FormatVersion(5, 0, 0)),
        )
        with pytest.raises(DiagnosticError) as info:
            read_format_version(6, table)
        assert "only 3.0.x and draft 4.0.x" in str(info.value)

    def test_table_spelling(self) -> None:
        assert table_to_string(SUPPORT_TABLE) == "[3.0.0,3.2.0),[4.0.0,4.1.0)"


class TestWriting:
    def test_baseline_is_integer(self) -> None:
        assert write_format_version(read_format_version("3.0.0")) == 3

    @pytest.mark.parametrize("major", [1, 2])
    def test_legacy_formats_are_never_written(self, major: int) -> None:
        with pytest.raises(ValueError, match="never written"):
            write_format_version(FormatVersion(major, 0, 0))

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


class TestLegacy:
    @pytest.mark.parametrize(
        ("value", "expected"), [(1, LegacyFormat.V1), (2, LegacyFormat.V2)]
    )
    def test_integers_are_legacy(self, value: int, expected: LegacyFormat) -> None:
        assert recognize_legacy_format(value) is expected
        assert str(expected) == str(value)

    @pytest.mark.parametrize("value", [True, "1", "2", "1.0.0", 1.0, 3, 0, None])
    def test_other_spellings_are_not_legacy(self, value: object) -> None:
        assert recognize_legacy_format(value) is None

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (1, LegacyFormat.V1),
            (2, LegacyFormat.V2),
            (3, FormatVersion(3, 0, 0)),
            ("4.0.0", FormatVersion(4, 0, 0)),
        ],
    )
    def test_document_with_legacy(
        self, value: object, expected: FormatVersion | LegacyFormat
    ) -> None:
        version, root = read_document_with_legacy({"formatVersion": value, "x": 1})
        assert version == expected
        assert root["x"] == 1

    @pytest.mark.parametrize(
        ("document", "code"),
        [
            ('{"distribution": []}', d.MISSING_FORMAT_VERSION),
            ('{"formatVersion": "1"}', d.INVALID_FORMAT_VERSION_SYNTAX),
            ('{"formatVersion": true}', d.INVALID_FORMAT_VERSION_TYPE),
            ('{"formatVersion": 5}', d.UNSUPPORTED_FORMAT_VERSION_MAJOR),
            ('{"formatVersion": 1, "formatVersion": 3}', d.DUPLICATE_FORMAT_VERSION),
        ],
    )
    def test_document_with_legacy_keeps_diagnostics(
        self, document: str, code: str
    ) -> None:
        with pytest.raises(DiagnosticError) as info:
            read_document_with_legacy(document)
        assert info.value.codes == (code,)

    def test_legacy_document(self) -> None:
        root = read_legacy_document('{"formatVersion": 2, "x": 1}', LegacyFormat.V2)
        assert root["x"] == 1

    @pytest.mark.parametrize(
        ("value", "found"), [(2, "2"), (3, "3.0.0"), ("3.1.0", "3.1.0"), (4, "4.0.0")]
    )
    def test_legacy_document_refuses_other_formats(
        self, value: object, found: str
    ) -> None:
        with pytest.raises(DiagnosticError) as info:
            read_legacy_document({"formatVersion": value}, LegacyFormat.V1)
        assert info.value.codes == (d.UNSUPPORTED_FORMAT_VERSION_MAJOR,)
        assert f"format version {found} " in str(info.value)
        assert "only legacy format 1" in str(info.value)

    def test_legacy_document_keeps_recognition_errors(self) -> None:
        with pytest.raises(DiagnosticError) as info:
            read_legacy_document({"formatVersion": "1"}, LegacyFormat.V1)
        assert info.value.codes == (d.INVALID_FORMAT_VERSION_SYNTAX,)

    def test_legacy_document_missing_version(self) -> None:
        with pytest.raises(DiagnosticError) as info:
            read_legacy_document("{}", LegacyFormat.V1)
        assert info.value.codes == (d.MISSING_FORMAT_VERSION,)

    def test_support_table_stays_in_the_release_grammar(self) -> None:
        assert all(interval.lower.major >= 3 for interval in SUPPORT_TABLE)
