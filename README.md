# Glyphviewer

## About

**Glyphviewer** is a web application that analyses web font files. The user
chooses a font file, either by file path or URL, and Glyphviewer will try to
parse it. If successful, it will:

- Display general information about the font file, such as name and copyright
  details, stored in its header.
- Provide a testbed where users can enter text and display it using the font.
- Display characters supported by the font along with their Unicode code points,
  if the user checks the **Shows characters in font** checkbox. This option is
  turned off by default, as this may result in a very long page.

A demonstration is available [here](http://www.pkmurphy.com.au/glyphviewer/).

## Installation and Dependencies

**Glyphviewer** and its dependencies can be installed via:

```bash
pip install glyphviewer
```

Glyphviewer requires [Django](https://www.djangoproject.com/) ≥ 5.2,
[FontTools](https://github.com/fonttools/fonttools) ≥ 4,
[numpy](https://numpy.org/) ≥ 2, [brotli](https://github.com/google/brotli) ≥ 1,
and [chardet](https://github.com/chardet/chardet) ≥ 7.

### Setting up

Once installed, add `"glyphviewer"` to your `INSTALLED_APPS` list in `settings.py`,
and add the desired URL in one of the `urls.py` files.

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    path("this_is_the_path_to_glyphviewer/", include("glyphviewer.urls")),
]
```

This provides three routes:

| Path | Name | Role |
|------|------|------|
| `…/` | (index) | Form and analysis |
| `…/doc/` | | In-app documentation |
| `…/font/` | `glyphviewer:font-proxy` | Same-origin serve of remote fonts |

The `font/` route is explained more in **Remote fonts, the same-origin policy, and CORS** below.

### Adding local fonts (including symbolic links)

Glyphviewer's **Local** dropdown lists every `*.ttf`, `*.otf`, `*.woff`, and `*.woff2`
file it finds in the `{STATIC_ROOT}/glyphviewer/fonts/` directory. You can:

- Copy any font files into that directory; or,
- Add symbolic links that point at fonts stored elsewhere on the same file system. Fonts from
  other directories are not normally accessible by Glyphviewer, but it will
  follow symbolic links created in `{STATIC_ROOT}/glyphviewer/fonts/` that lead to font files
  elsewhere on your machine.

Either way, your browser will list these fonts as coming from the `{STATIC_URL}/glyphviewer/fonts/` folder.

Glyphviewer already comes with its own set of fonts from the
[Free UCS Outline Fonts](https://savannah.gnu.org/projects/freefont/). Those bundled
fonts remain under their own GPL terms; the Glyphviewer application code is BSD-3-Clause
(see [LICENSE.txt](LICENSE.txt)). In production, the fonts can be moved into the correct
directory via:

```bash
python manage.py collectstatic
```

### Remote fonts, the same-origin policy and CORS

Glyphviewer's **Remote** text field allows the user to provide a full URL of a remote font. For
earlier versions of Glyphviewer — 0.8 and before — the application could *download* remote fonts. It
could even analyse them for their header information and the characters they supported. The problem
was that the browser could not generally download the font to *display* it as it was designed.

The reason for this is that web browsers enforce the
[Same-origin policy](https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Same-origin_policy):
resources from one website are generally restricted from being used in another website unless
[Cross-Origin Resource Sharing](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS) is enabled
on the source website.

Some websites, such as [Google Fonts](https://fonts.google.com/), are happy to share their
fonts directly with others. When these files are downloaded, they are downloaded with these
HTTP response headers that say CORS is permitted.

```http
access-control-allow-origin: *
```

The asterisk means that requesting code from any origin can access the resource. So this means
that you can embed the font in your site, and everyone is happy.

Not everyone has the budget that Google does. Some websites may use their own proprietary font
that they spent a lot of money on. So when your website (or Glyphviewer 0.8 or before) tries to
access it in the site, it will almost certainly not be sent with those `access-control-allow-origin`
headers. That means CORS is not enabled, and the browser will refuse to display it as it was designed.
Instead, the browser will use a fallback font for the user's browser and operating system instead;
you are expecting *Roboto*, but it is displayed as *Arial* or *Helvetica*. Since
this may mislead users as to the appearance of the font, Glyphviewer would then warn them about the
situation.

(The
*Same-origin policy* was originally intended for JavaScript; enforcement would reduce the
number of malicious scripts executed on a webpage. But when
[Web fonts](https://drafts.csswg.org/css-fonts-3/#same-origin-restriction) were introduced, the
*Same-origin policy* also applied to fonts accessed by CSS `@font-face` rules in your webpages.)

Version 0.9 of Glyphviewer overcomes this limitation: it introduces a proxy for web fonts. The
web page creates a same-origin URL that goes through Glyphviewer's font proxy; to the browser, it
appears that the font is local, and so CORS permits the font to be loaded. To give more detail:

1. The user submits a remote font URL, using either the HTTP or HTTPS schemes;
2. The index view sets `fontpath` to `/this_is_the_path_to_glyphviewer/font/?url=<urlencoded-remote-url>`;
3. The HTML template's `@font-face` refers to that same-origin URL; and,
4. The `font-proxy` view — `glyphviewer:font-proxy` — downloads the remote file
   with `fetch_remote_font()` in `font_fetch.py`, and with an appropriate `Content-Type`. This
   could be `font/woff2`, `font/woff`, `font/otf`, or `font/ttf`.

### Safety limits

All font fetches are capped by size (3 MB) and timeout (120s).

The proxy is not an open relay. Before fetching, `validate_remote_font_url()`
rejects:

- Schemes other than `http` / `https`;
- URLs with embedded credentials;
- Hostnames such as `localhost`, `*.local`, `*.internal`; and,
- Private, loopback, link-local, and other non-public addresses.

## Versions

* 0.1 (June 11th 2011) - Initial release.
* 0.2 (June 28th 2013) - Added setup script to create a PyPI package. Fixed bugs.
* 0.3 (February 15th 2014) - Made compatible with Mezzanine and Bootstrap, changed styles for errors, now handles empty local directories.
* 0.4 (January 16th 2016) - Now handles cases where remote fonts are inaccessible using CORS; removed the limitation that restricted characters to the BMP; added documentation for above.
* 0.5 (March 31st 2017) - Updated to be compatible with Django 1.10. Now automatically install dependencies using pip.
* 0.6 (March 18th 2018) - Add WOFF2 compatibility.
* 0.7 (December 6th 2020) - Updated for Python 3 compatibility.
* 0.8 (December 10th 2020) - Better representation of font header information as text; better use of urllib for Python 3.
* 0.9 (September 25th 2026) - Same-origin remote-font proxy for preview (CORS bypass); ship glyph table / preview styles as package static CSS; add tests; migrate README to Markdown; clarify app license as BSD-3-Clause (bundled FreeFonts remain GPL); align copyright years and changelogs.

## Copyright

The **Glyphviewer** application code is copyright (c) 2011-2026
[Peter Murphy](http://www.pkmurphy.com.au/)
<peterkmurphy@gmail.com>, and is licensed under the BSD-3-Clause terms in
[LICENSE.txt](LICENSE.txt). Bundled [Free UCS Outline Fonts](https://savannah.gnu.org/projects/freefont/)
remain under their own GPL terms.
