"""Tests for morphir.sdk.uuid (Morphir.SDK.UUID)."""

import uuid as stdlib_uuid

import pytest

from morphir.sdk import uuid as uuid_
from morphir.sdk.basics import Order
from morphir.sdk.maybe import Just, Nothing
from morphir.sdk.result import Err, Ok
from morphir.sdk.uuid import UUID, Error

DNS = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"


class TestType:
    def test_uuid_is_the_standard_library_uuid(self) -> None:
        assert UUID is stdlib_uuid.UUID

    def test_error_has_the_elm_constructor_names(self) -> None:
        assert [e.name for e in Error] == [
            "WrongFormat",
            "WrongLength",
            "UnsupportedVariant",
            "IsNil",
            "NoVersion",
        ]


class TestNamespaces:
    """The Elm `namespaceTests`."""

    def test_dns_namespace(self) -> None:
        assert uuid_.to_string(uuid_.dns_namespace) == DNS
        assert uuid_.dns_namespace == stdlib_uuid.NAMESPACE_DNS

    def test_url_namespace(self) -> None:
        assert (
            uuid_.to_string(uuid_.url_namespace)
            == "6ba7b811-9dad-11d1-80b4-00c04fd430c8"
        )
        assert uuid_.url_namespace == stdlib_uuid.NAMESPACE_URL

    def test_oid_namespace(self) -> None:
        assert (
            uuid_.to_string(uuid_.oid_namespace)
            == "6ba7b812-9dad-11d1-80b4-00c04fd430c8"
        )
        assert uuid_.oid_namespace == stdlib_uuid.NAMESPACE_OID

    def test_x500_namespace(self) -> None:
        assert (
            uuid_.to_string(uuid_.x500_namespace)
            == "6ba7b814-9dad-11d1-80b4-00c04fd430c8"
        )
        assert uuid_.x500_namespace == stdlib_uuid.NAMESPACE_X500


class TestNil:
    """The Elm `toStringTests`."""

    def test_nil_string(self) -> None:
        assert uuid_.nil_string == "00000000-0000-0000-0000-000000000000"

    def test_is_nil_string(self) -> None:
        assert uuid_.is_nil_string(uuid_.nil_string) is True

    def test_is_nil_string_other_forms(self) -> None:
        assert uuid_.is_nil_string("0" * 32) is True
        assert uuid_.is_nil_string("{" + uuid_.nil_string + "}") is True
        assert uuid_.is_nil_string("urn:uuid:" + uuid_.nil_string) is True

    def test_is_nil_string_false(self) -> None:
        assert uuid_.is_nil_string(DNS) is False
        assert uuid_.is_nil_string("") is False
        assert uuid_.is_nil_string("0" * 31) is False
        assert uuid_.is_nil_string("nil") is False


class TestFromString:
    """The Elm `fromStringTests`."""

    def test_from_string_basic_uuid(self) -> None:
        assert uuid_.from_string(DNS) == Just(stdlib_uuid.UUID(DNS))

    def test_from_string_invalid_uuid(self) -> None:
        assert uuid_.from_string("c72c207b-0847-386d-bdbc-2e5def81cg81") == Nothing()

    def test_from_string_incorrect_length(self) -> None:
        assert uuid_.from_string("6ba7b811-9dad-11d1-80b4-00c04fd430d80") == Nothing()


class TestParse:
    """The Elm `parseTests`."""

    def test_parse_basic_uuid(self) -> None:
        assert uuid_.parse(DNS) == Ok(uuid_.dns_namespace)

    def test_parse_invalid_uuid(self) -> None:
        assert uuid_.parse("c72c207b-0847-386d-bdbc-2e5def81cg81") == Err(
            Error.WrongFormat
        )

    def test_parse_incorrect_length(self) -> None:
        assert uuid_.parse("6ba7b811-9dad-11d1-80b4-00c04fd430d80") == Err(
            Error.WrongLength
        )

    def test_parse_uuid_version_mapping(self) -> None:
        match uuid_.parse("c72c207b-0847-386d-bdbc-2e5def81cf81"):
            case Ok(value):
                assert uuid_.version(value) == 3
            case Err(error):
                pytest.fail(f"parse failed: {error}")


class TestParseForms:
    """The text forms that `UUID.fromString` of TSFoster/elm-uuid accepts."""

    @pytest.mark.parametrize(
        "text",
        [
            DNS,
            DNS.upper(),
            DNS.replace("-", ""),
            "{" + DNS + "}",
            "{" + DNS.replace("-", "") + "}",
            "urn:uuid:" + DNS,
            "URN:UUID:" + DNS.upper(),
            "  " + DNS + "\n",
            "6ba7b810 9dad 11d1 80b4 00c04fd430c8",
            "6ba7b810\t9dad\t11d1\t80b4\t00c04fd430c8",
            "6b-a7b8109dad11d1-80b400c0-4fd430c8",
            "-{6ba7b810-9dad-11d1-80b4-00c04fd430c8}-",
        ],
    )
    def test_accepted(self, text: str) -> None:
        assert uuid_.parse(text) == Ok(uuid_.dns_namespace)

    @pytest.mark.parametrize(
        ("text", "error"),
        [
            ("", Error.WrongLength),
            ("6ba7b810", Error.WrongLength),
            (DNS + "0", Error.WrongLength),
            ("{" + DNS, Error.WrongLength),
            (DNS + "}", Error.WrongLength),
            ("urn:uuid:{" + DNS + "}", Error.WrongLength),
            ("{urn:uuid:" + DNS + "}", Error.WrongLength),
            ("uuid:" + DNS, Error.WrongLength),
            ("6ba7b810\r9dad-11d1-80b4-00c04fd430c8", Error.WrongLength),
            ("0x" + DNS.replace("-", "")[2:], Error.WrongFormat),
            ("6ba7b810_9dad-11d1-80b4-0c04fd430c8", Error.WrongFormat),
            (
                "6ba7b810-9dad-11d1-80b4-00c04fd430c\N{FULLWIDTH DIGIT EIGHT}",
                Error.WrongFormat,
            ),
            ("\N{GRINNING FACE}" + DNS.replace("-", "")[2:], Error.WrongFormat),
            ("00000000-0000-0000-0000-000000000000", Error.IsNil),
            ("6ba7b810-9dad-91d1-80b4-00c04fd430c8", Error.NoVersion),
            ("6ba7b810-9dad-f1d1-80b4-00c04fd430c8", Error.NoVersion),
            ("6ba7b810-9dad-11d1-00b4-00c04fd430c8", Error.UnsupportedVariant),
            ("6ba7b810-9dad-11d1-c0b4-00c04fd430c8", Error.UnsupportedVariant),
            ("6ba7b810-9dad-11d1-e0b4-00c04fd430c8", Error.UnsupportedVariant),
        ],
    )
    def test_rejected(self, text: str, error: Error) -> None:
        assert uuid_.parse(text) == Err(error)
        assert uuid_.from_string(text) == Nothing()

    def test_the_version_check_comes_before_the_variant_check(self) -> None:
        assert uuid_.parse("6ba7b810-9dad-f1d1-00b4-00c04fd430c8") == Err(
            Error.NoVersion
        )

    @pytest.mark.parametrize("version", range(9))
    def test_versions_0_to_8_are_accepted(self, version: int) -> None:
        text = f"6ba7b810-9dad-{version:x}1d1-80b4-00c04fd430c8"
        match uuid_.parse(text):
            case Ok(value):
                assert uuid_.version(value) == version
                assert uuid_.to_string(value) == text
            case Err(error):
                pytest.fail(f"parse failed: {error}")


class TestForName:
    """The Elm `forNameTests`, with the expected values of RFC 4122 version 5."""

    def test_for_name_dns_namespace(self) -> None:
        assert uuid_.for_name("foo", uuid_.dns_namespace) == stdlib_uuid.uuid5(
            stdlib_uuid.NAMESPACE_DNS, "foo"
        )

    def test_for_name_url_namespace(self) -> None:
        assert uuid_.for_name("foo", uuid_.url_namespace) == stdlib_uuid.uuid5(
            stdlib_uuid.NAMESPACE_URL, "foo"
        )

    def test_for_name_oid_namespace(self) -> None:
        assert uuid_.for_name("foo", uuid_.oid_namespace) == stdlib_uuid.uuid5(
            stdlib_uuid.NAMESPACE_OID, "foo"
        )

    def test_for_name_x500_namespace(self) -> None:
        assert uuid_.for_name("foo", uuid_.x500_namespace) == stdlib_uuid.uuid5(
            stdlib_uuid.NAMESPACE_X500, "foo"
        )

    def test_examples_from_the_elm_documentation(self) -> None:
        api = uuid_.for_name("https://api.example.com/v2/", uuid_.dns_namespace)
        assert uuid_.to_string(api) == "bad122ad-b5b6-527c-b544-4406328d8b13"
        widget = uuid_.for_name("Widget", api)
        assert uuid_.to_string(widget) == "7b0db628-d793-550b-a883-937a276f4908"

    def test_known_value(self) -> None:
        assert (
            uuid_.to_string(uuid_.for_name("python.org", uuid_.dns_namespace))
            == "886313e1-3b8a-5372-9b90-0c9aee199e5d"
        )

    def test_version_is_5(self) -> None:
        assert uuid_.version(uuid_.for_name("foo", uuid_.dns_namespace)) == 5

    def test_name_is_encoded_as_utf_8(self) -> None:
        assert uuid_.for_name("héllo \N{GRINNING FACE}", uuid_.url_namespace) == (
            stdlib_uuid.uuid5(stdlib_uuid.NAMESPACE_URL, "héllo \N{GRINNING FACE}")
        )


class TestToString:
    def test_canonical_lower_case(self) -> None:
        assert uuid_.to_string(stdlib_uuid.UUID(DNS.upper())) == DNS

    def test_round_trip(self) -> None:
        value = uuid_.for_name("round trip", uuid_.oid_namespace)
        assert uuid_.parse(uuid_.to_string(value)) == Ok(value)


class TestVersion:
    def test_version(self) -> None:
        assert uuid_.version(uuid_.dns_namespace) == 1
        assert uuid_.version(stdlib_uuid.uuid4()) == 4

    def test_version_of_the_nil_uuid(self) -> None:
        assert uuid_.version(stdlib_uuid.UUID(int=0)) == 0


class TestCompare:
    def test_compare(self) -> None:
        assert uuid_.compare(uuid_.dns_namespace, uuid_.url_namespace) is Order.LT
        assert uuid_.compare(uuid_.url_namespace, uuid_.dns_namespace) is Order.GT
        assert uuid_.compare(uuid_.dns_namespace, uuid_.dns_namespace) is Order.EQ

    def test_compare_is_unsigned(self) -> None:
        low = stdlib_uuid.UUID("7fffffff-ffff-4fff-bfff-ffffffffffff")
        high = stdlib_uuid.UUID("80000000-0000-4000-8000-000000000000")
        assert uuid_.compare(low, high) is Order.LT

    def test_compare_uses_the_last_part(self) -> None:
        a = stdlib_uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
        b = stdlib_uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c9")
        assert uuid_.compare(a, b) is Order.LT
