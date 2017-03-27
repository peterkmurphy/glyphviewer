#!/usr/bin/python
#-*- coding: UTF-8 -*-
# File: views.py
# Copyright (C) 2013-2016 Peter Murphy <peterkmurphy@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os, fnmatch;
import urlparse;
from django.template import Context, RequestContext, loader
from django.http import HttpResponse, Http404, HttpResponseRedirect;
from django.template.response import TemplateResponse;
from django.shortcuts import render_to_response;
from django.conf import settings
from glyphviewer import glyphCatcher, glyphArray, GC_ERRORMSG;
import random;
from django.shortcuts import render
#from theproject.settings import STATIC_URL

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
    global localfontfiles;
    global fontnametodirectory;
    global localfontempty;
    if localfontfiles != []:
        localfontempty = False;
        return (localfontfiles, fontnametodirectory,);
    for i in [settings.STATIC_ROOT]:
        font_dir = os.path.join(i, FONTS_DIR_ADD);
        listdir = os.listdir(font_dir);
        filtereddir = filter(lambda(x): fnmatch.fnmatch(x, '*.ttf') or
            fnmatch.fnmatch(x, '*.otf') or fnmatch.fnmatch(x, '*.woff'),
            listdir);
        for j in filtereddir:
            if not fontnametodirectory.has_key(j):
                localfontfiles.append(j);
                fontnametodirectory[j] = font_dir;
    localfontfiles.sort();
    if localfontfiles != []:
        localfontempty = False;
    else:
        localfontempty = True;
    return (localfontfiles, fontnametodirectory,);


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

# The "localfontdir_url" is an URL to where font files are stored.

    localbase_url = urlparse.urljoin("http://" + request.META["HTTP_HOST"],
        settings.STATIC_URL);
    localfontdir_url = urlparse.urljoin(localbase_url, FONTS_DIR_ADD);
    print localfontdir_url;

# Now we have to set:
# (i) 'is_remote': False if the returned page has "Local" selected; True for
# "Remote".
# (ii) 'chosenitem': the value to set the "File" drop down list.
# (iii) 'remoteurl': the value to set the "URL" text box.
# (iv) 'fetchpath': the URL which is used to analyse the font (whereever it is).
# (v) 'displayfont': what font info is actually displayed to the user.


    if locchoice == FIND_LOCAL_NAME:
        is_remote = False;
        chosenitem = fontlocal;
        remoteurl = "";
        fetchpath = urlparse.urljoin(localfontdir_url, fontlocal);
        displayfont = fontlocal;
        bCheckCORS = False
    elif locchoice == FIND_REMOTE:
        is_remote = True;
        chosenitem = "";
        remoteurl = fontremote;
        fetchpath = fontremote;
        displayfont = fontremote;
        bCheckCORS = True
    else: # locchoice == FIND_LOCAL_RANDOM:
        is_remote = False;
        bCheckCORS = False
        random.seed();
        if len(localfontfiles):
            chosenitem = random.choice(localfontfiles);
        else:
            chosenitem = "";
        remoteurl = "";
        fetchpath = urlparse.urljoin(localfontdir_url, chosenitem);
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
        'fontpath': fetchpath, 'shtables': shtables,
        'remoteurl':remoteurl, 'is_remote':is_remote, 'localfontempty': localfontempty});
