# Glyphviewer: a tool to examine web fonts online.
# Copyright (c) 2011-2026 Peter Murphy <peterkmurphy@gmail.com>
#
# Redistribution and use permitted under the BSD-3-Clause terms in LICENSE.txt.

import os
import tempfile
import urllib.parse
from pathlib import Path
from typing import ClassVar
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, TestCase

from glyphviewer.font_fetch import (
    FontTooLargeError,
    UnsafeFontURLError,
    fetch_remote_font,
    validate_remote_font_url,
)
from glyphviewer.glyphviewer import (
    DODGY,
    GC_ERRORMSG,
    GC_NOERROR,
    GC_NOTAFONT,
    GC_WARNCORS,
    glyphArray,
    glyphCatcher,
)
from glyphviewer.templatetags.glyphtable import glyphtable
from glyphviewer.views import font_proxy, getLocalFontFiles, index, local_font_paths


class FontFetchValidationTests(SimpleTestCase):
    def test_blocks_non_http_schemes(self):
        with self.assertRaises(UnsafeFontURLError):
            validate_remote_font_url("file:///etc/passwd")

    def test_blocks_localhost(self):
        with self.assertRaises(UnsafeFontURLError):
            validate_remote_font_url("http://localhost/font.woff")

    def test_blocks_private_ip_literals(self):
        with self.assertRaises(UnsafeFontURLError):
            validate_remote_font_url("http://127.0.0.1/font.woff")

    def test_blocks_credentials_in_url(self):
        with self.assertRaises(UnsafeFontURLError):
            validate_remote_font_url("https://user:pass@example.com/font.woff")

    def test_allows_public_https_url(self):
        validate_remote_font_url("https://example.com/fonts/sample.woff2")


class FontFetchDownloadTests(SimpleTestCase):
    def test_rejects_responses_larger_than_limit(self):
        class FakeResponse:
            headers: ClassVar[dict[str, str]] = {"Content-Type": "font/woff2"}

            def read(self, size=-1):
                return b"x" * 1024

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with (
            patch("glyphviewer.font_fetch.urlopen", return_value=FakeResponse()),
            self.assertRaises(FontTooLargeError),
        ):
            fetch_remote_font("https://example.com/font.woff2", max_size=512, timeout=5)


class LocalFontViewTests(TestCase):
    def test_local_font_paths_rejects_path_traversal(self):
        files, font_dirs = getLocalFontFiles()
        if not files:
            self.skipTest("No bundled local fonts")
        fs_path, font_url = local_font_paths(
            "../../etc/passwd",
            font_dirs,
            "http://example.com/static/glyphviewer/fonts/",
        )
        self.assertEqual(fs_path, "")
        self.assertEqual(font_url, "")

    def test_local_font_paths_returns_filesystem_and_url(self):
        files, font_dirs = getLocalFontFiles()
        if not files:
            self.skipTest("No bundled local fonts")
        fs_path, font_url = local_font_paths(
            files[0],
            font_dirs,
            "http://example.com/static/glyphviewer/fonts/",
        )
        self.assertTrue(fs_path.endswith(files[0]))
        self.assertIn(files[0], font_url)

    def test_glyph_catcher_reads_local_font_file(self):
        files, font_dirs = getLocalFontFiles()
        if not files:
            self.skipTest("No bundled local fonts")
        fs_path = local_font_paths(
            files[0],
            font_dirs,
            "http://example.com/static/glyphviewer/fonts/",
        )[0]
        error, header, _glyphs = glyphCatcher(fs_path, False, False, False)
        self.assertEqual(error, GC_NOERROR)
        self.assertIsNotNone(header)

    def test_index_uses_local_font_without_remote_validation(self):
        files, _font_dirs = getLocalFontFiles()
        if not files:
            self.skipTest("No bundled local fonts")
        request = RequestFactory().get("/glyphviewer/", HTTP_HOST="127.0.0.1")
        response = index(request)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "remote font URL is not allowed")


class RemoteFontProxyTests(TestCase):
    def test_font_proxy_rejects_blocked_url(self):
        request = RequestFactory().get(
            "/glyphviewer/font/",
            {"url": "http://127.0.0.1/font.woff2"},
            HTTP_HOST="127.0.0.1",
        )
        response = font_proxy(request)
        self.assertEqual(response.status_code, 403)

    def test_font_proxy_serves_fetched_font(self):
        request = RequestFactory().get(
            "/glyphviewer/font/",
            {"url": "https://example.com/fonts/sample.woff2"},
            HTTP_HOST="127.0.0.1",
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".woff2") as temp:
            temp.write(b"font-bytes")
            temp_name = temp.name
        with patch("glyphviewer.views.fetch_remote_font", return_value=(temp_name, {})):
            response = font_proxy(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"font-bytes")
        self.assertEqual(response["Content-Type"], "font/woff2")

    def test_index_uses_same_origin_proxy_for_remote_font(self):
        remote_url = "https://static.example.com/fonts/sample.woff2"
        request = RequestFactory().get(
            "/glyphviewer/",
            {
                "Location": "Remote",
                "fonturl": remote_url,
            },
            HTTP_HOST="127.0.0.1",
        )
        with patch("glyphviewer.views.glyphCatcher", return_value=(0, object(), [])):
            response = index(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/glyphviewer/font/?")
        self.assertContains(response, urllib.parse.quote(remote_url, safe=""))
        self.assertNotContains(response, "CORS prevents the display")


def _sample_local_font_path() -> str:
    files, font_dirs = getLocalFontFiles()
    if not files:
        return ""
    return local_font_paths(
        files[0],
        font_dirs,
        "http://example.com/static/glyphviewer/fonts/",
    )[0]


def _copy_font_to_temp(source: str) -> str:
    data = Path(source).read_bytes()
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(source).suffix) as temp:
        temp.write(data)
        return temp.name


class GlyphTableFilterTests(SimpleTestCase):
    def test_renders_table_for_normal_block(self):
        glyphs = glyphArray("Basic Latin", [0x41, 0x42, 0x43])
        html = glyphtable(glyphs, 2)
        self.assertIn('class="glyphtable', html)
        self.assertIn("<caption", html)
        self.assertIn("Basic Latin", html)
        self.assertIn("U+0041", html)
        self.assertIn("U+0042", html)
        self.assertIn("U+0043", html)
        self.assertIn("glyphtd", html)
        self.assertIn("glyphempty", html)  # third cell leaves a remainder pad

    def test_dodgy_codepoints_listed_as_ul(self):
        glyphs = glyphArray(DODGY, [0x0, 0x9, 0x1F])
        html = glyphtable(glyphs)
        self.assertIn("<ul>", html)
        self.assertIn("U+0000", html)
        self.assertIn("U+0009", html)
        self.assertNotIn("glyphtable", html)

    def test_empty_dodgy_block_returns_empty(self):
        self.assertEqual(glyphtable(glyphArray(DODGY, [])), "")

    def test_invalid_input_returns_empty(self):
        self.assertEqual(glyphtable(None), "")
        self.assertEqual(glyphtable("not-a-glyph-array"), "")


class CorsWarningPathTests(TestCase):
    def test_glyph_catcher_warns_when_cors_header_missing(self):
        font_path = _sample_local_font_path()
        if not font_path:
            self.skipTest("No bundled local fonts")
        temp_name = _copy_font_to_temp(font_path)
        remote_url = "https://fonts.example.com/sample.woff"
        with patch(
            "glyphviewer.glyphviewer.fetch_remote_font",
            return_value=(temp_name, {"content-type": "font/woff"}),
        ):
            error, header, glyphs = glyphCatcher(remote_url, False, False, True)
        self.assertEqual(error, GC_WARNCORS)
        self.assertIsNotNone(header)
        self.assertIsNotNone(glyphs)
        self.assertIn("CORS prevents", GC_ERRORMSG[GC_WARNCORS])

    def test_glyph_catcher_ok_when_cors_star_present(self):
        font_path = _sample_local_font_path()
        if not font_path:
            self.skipTest("No bundled local fonts")
        temp_name = _copy_font_to_temp(font_path)
        remote_url = "https://fonts.example.com/sample.woff"
        with patch(
            "glyphviewer.glyphviewer.fetch_remote_font",
            return_value=(
                temp_name,
                {"content-type": "font/woff", "access-control-allow-origin": "*"},
            ),
        ):
            error, header, _glyphs = glyphCatcher(remote_url, False, False, True)
        self.assertEqual(error, GC_NOERROR)
        self.assertIsNotNone(header)

    def test_index_shows_cors_warning_message(self):
        request = RequestFactory().get(
            "/glyphviewer/",
            {"Location": "Remote", "fonturl": "https://example.com/font.woff"},
            HTTP_HOST="127.0.0.1",
        )
        with patch(
            "glyphviewer.views.glyphCatcher",
            return_value=(GC_WARNCORS, object(), []),
        ):
            response = index(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "alert-warning")
        self.assertContains(response, "CORS prevents the display")
        self.assertContains(response, "Warning")


class CorruptFontFixtureTests(TestCase):
    def test_random_bytes_are_not_a_font(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".woff") as temp:
            temp.write(os.urandom(256))
            temp_name = temp.name
        try:
            error, header, glyphs = glyphCatcher(temp_name, False, False, False)
        finally:
            os.unlink(temp_name)
        self.assertEqual(error, GC_NOTAFONT)
        self.assertIsNone(header)
        self.assertIsNone(glyphs)

    def test_empty_file_is_not_a_font(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ttf") as temp:
            temp_name = temp.name
        try:
            error, header, glyphs = glyphCatcher(temp_name, False, False, False)
        finally:
            os.unlink(temp_name)
        self.assertEqual(error, GC_NOTAFONT)
        self.assertIsNone(header)
        self.assertIsNone(glyphs)

    def test_truncated_woff_is_not_a_font(self):
        font_path = _sample_local_font_path()
        if not font_path:
            self.skipTest("No bundled local fonts")
        data = Path(font_path).read_bytes()[:64]
        with tempfile.NamedTemporaryFile(delete=False, suffix=".woff") as temp:
            temp.write(data)
            temp_name = temp.name
        try:
            error, header, glyphs = glyphCatcher(temp_name, False, False, False)
        finally:
            os.unlink(temp_name)
        self.assertEqual(error, GC_NOTAFONT)
        self.assertIsNone(header)
        self.assertIsNone(glyphs)
