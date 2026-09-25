# File: views.py
# Copyright (c) 2011-2026 Peter Murphy <peterkmurphy@gmail.com>
#
# Redistribution and use permitted under the BSD-3-Clause terms in LICENSE.txt.

import fnmatch
import os
import random
import urllib.parse

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse

from .font_fetch import (
    FontFetchError,
    FontTimeoutError,
    FontTooLargeError,
    UnsafeFontURLError,
    fetch_remote_font,
)
from .glyphviewer import FONT_MAX_SIZE, FONT_TIMEOUT, GC_ERRORMSG, glyphCatcher

FONTS_DIR_ADD = "glyphviewer/fonts/";
FIND_LOCAL_NAME = 0;
FIND_LOCAL_RANDOM = 1;
FIND_REMOTE = 2;
localfontfiles = [];
fontnametodirectory = {};
localfontempty = True;
# Loads the documentation.

def doc(request):
    return render(request, 'glyphviewer/doc.html', {});

# Gets a list of the local font files (and their internal directory). This
# should never be exposed to the user.

def getLocalFontFiles():
    ''' Initialises localfontfiles to the list of fonts in the static directories,
        if there are any fonts to be found. This saves us reinitialising the
        same array.
    '''
    global localfontempty;
    if localfontfiles != []:
        localfontempty = False;
        return (localfontfiles, fontnametodirectory,);
    search_dirs = []
    if settings.STATIC_ROOT:
        search_dirs.append(os.path.join(settings.STATIC_ROOT, FONTS_DIR_ADD))
    search_dirs.append(os.path.join(os.path.dirname(__file__), "static", FONTS_DIR_ADD))
    for font_dir in search_dirs:
        if not os.path.isdir(font_dir):
            continue
        listdir = os.listdir(font_dir);
        filtereddir = [x for x in listdir if fnmatch.fnmatch(x, '*.ttf') or
            fnmatch.fnmatch(x, '*.otf') or fnmatch.fnmatch(x, '*.woff') or
            fnmatch.fnmatch(x, '*.woff2')];
        for j in filtereddir:
            if j not in fontnametodirectory:
                localfontfiles.append(j);
                fontnametodirectory[j] = font_dir;
    localfontfiles.sort();
    if localfontfiles != []:
        localfontempty = False;
    else:
        localfontempty = True;
    return (localfontfiles, fontnametodirectory,);


def local_font_paths(filename, fontnametodirectory, localfontdir_url):
    '''Return (filesystem_path, public_url) for a bundled local font.'''
    if not filename:
        return "", ""
    safe_name = os.path.basename(filename)
    font_dir = fontnametodirectory.get(safe_name)
    if not font_dir:
        return "", ""
    fs_path = os.path.join(font_dir, safe_name)
    if not os.path.isfile(fs_path):
        return "", ""
    font_url = urllib.parse.urljoin(localfontdir_url, safe_name)
    return fs_path, font_url


FONT_CONTENT_TYPES = {
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".otf": "font/otf",
    ".ttf": "font/ttf",
}


def remote_font_display_url(request, remote_url):
    '''Same-origin URL for @font-face when the source font lacks CORS headers.'''
    if not remote_url:
        return ""
    query = urllib.parse.urlencode({"url": remote_url})
    proxy_path = reverse("glyphviewer:font-proxy")
    return request.build_absolute_uri(f"{proxy_path}?{query}")


def font_proxy(request):
    '''Fetch a remote font server-side and serve it to the browser same-origin.'''
    remote_url = request.GET.get("url", "").strip()
    if not remote_url:
        return HttpResponseBadRequest("Missing font URL.")
    try:
        temp_path, _headers = fetch_remote_font(
            remote_url,
            max_size=FONT_MAX_SIZE,
            timeout=FONT_TIMEOUT,
        )
        try:
            with open(temp_path, "rb") as font_file:
                data = font_file.read()
        finally:
            os.unlink(temp_path)
    except UnsafeFontURLError:
        return HttpResponseForbidden("Font URL not allowed.")
    except FontTooLargeError:
        return HttpResponse("Font too large.", status=413)
    except FontTimeoutError:
        return HttpResponse("Font request timed out.", status=504)
    except FontFetchError:
        return HttpResponseBadRequest("Could not fetch font.")

    lower_url = remote_url.lower()
    content_type = "application/octet-stream"
    for ext, mime in FONT_CONTENT_TYPES.items():
        if lower_url.endswith(ext):
            content_type = mime
            break

    response = HttpResponse(data, content_type=content_type)
    response["Cache-Control"] = "private, max-age=3600"
    return response


def index(request):

# DANGER! We must be careful of the following things:
# 1. Parsing the GET request from the user. It takes the form.
# Location=[Local|Remote]&fonturl=fonturlval&fontname=fontnameval&blocks=blocks
# 2. Allowing the user to access arbitrary files on the server.
# 3. Handling errors.
# We start by handling the GET request.

# 'shtables': whether tables of Unicode characters are present in the result
# not.

    if "shtables" not in request.GET:
        shtables = False;
    else:
        shtables = True;

# "blocks": whether Unicode characters should be split up by blocks.

    if "blocks" not in request.GET:
        blocks = False;
    else:
        blocks = True;

# "locchoice": indicates the location where to find the font. Values are
# FIND_LOCAL_NAME: from the fontname field: a local font chosen by the user.
# FIND_LOCAL_RANDOM: from the fontname field: a local font chosen randomly.
# FIND_REMOTE: from the fonturl field: a remote font chosen by URL.

    if "Location" in request.GET:
        if request.GET["Location"] == "Local":
            locchoice = FIND_LOCAL_NAME;
        else:
            locchoice = FIND_REMOTE;
    else:
        if "fonturl" in request.GET:
            locchoice = FIND_REMOTE;
        else:
            locchoice = FIND_LOCAL_RANDOM;

# "fontlocal": the value of the drop down box containing local values.
# "fontremote": the value of the remote url field.

    fontlocal = request.GET.get("fontname", None);
    fontremote = request.GET.get("fonturl", None);

# "localfontfiles" is a list of local font files.
# "fontnametodirectory" is a key-value pairs of font files to their directory.

    (localfontfiles, fontnametodirectory,) = getLocalFontFiles();
    schemestart = request.scheme + "://"

# The "localfontdir_url" is an URL to where font files are stored.

    localbase_url = urllib.parse.urljoin(schemestart + request.META["HTTP_HOST"],
        settings.STATIC_URL);
    localfontdir_url = urllib.parse.urljoin(localbase_url, FONTS_DIR_ADD);

# Now we have to set:
# (i) 'is_remote': False if the returned page has "Local" selected; True for
# "Remote".
# (ii) 'chosenitem': the value to set the "File" drop down list.
# (iii) 'remoteurl': the value to set the "URL" text box.
# (iv) 'fetchpath': filesystem path or remote URL used to analyse the font.
# (v) 'displayfont': what font info is actually displayed to the user.
# (vi) 'fonturl': browser-facing URL for @font-face (local static URL or remote).
# Preview uses the same-origin font proxy for remote fonts, so bCheckCORS stays
# False here; glyphCatcher still accepts True for direct/API use and tests.

    if locchoice == FIND_LOCAL_NAME:
        is_remote = False;
        chosenitem = fontlocal;
        remoteurl = "";
        fetchpath, fonturl = local_font_paths(
            fontlocal, fontnametodirectory, localfontdir_url
        );
        displayfont = fontlocal;
        bCheckCORS = False
    elif locchoice == FIND_REMOTE:
        is_remote = True;
        chosenitem = "";
        remoteurl = fontremote;
        fetchpath = fontremote;
        fonturl = remote_font_display_url(request, fontremote);
        displayfont = fontremote;
        bCheckCORS = False
    else: # locchoice == FIND_LOCAL_RANDOM:
        is_remote = False;
        bCheckCORS = False
        random.seed();
        if len(localfontfiles):
            chosenitem = random.choice(localfontfiles);
        else:
            chosenitem = "";
        remoteurl = "";
        fetchpath, fonturl = local_font_paths(
            chosenitem, fontnametodirectory, localfontdir_url
        );
        displayfont = chosenitem;

# Now we analyse the font!

    ourtuples = glyphCatcher(fetchpath, blocks, settings.DEBUG, bCheckCORS);

# The 'ourerror' variable contains the error message (if relevant).

    ourerror = ourtuples[0];

# The 'ourheader' variable contains the header information for the font.

    ourheader = ourtuples[1];

# The 'ourglyphs' variable contains the characters for the font (if relevant).

    ourglyphs = ourtuples[2];
    return render(request, 'glyphviewer/index.html', {'ourheader': ourheader,
        'ourglyphs': ourglyphs,'reslistdir':localfontfiles,
        'chosenitem': chosenitem, 'displayfont': displayfont, 'blocks': blocks,
        'ourerror': ourerror, 'ermsg': GC_ERRORMSG[ourerror],
        'fontpath': fonturl, 'shtables': shtables,
        'remoteurl':remoteurl, 'is_remote':is_remote, 'localfontempty': localfontempty});
