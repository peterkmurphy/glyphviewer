# Glyphviewer: a tool to examine web fonts online.
# Copyright (c) 2011-2026 Peter Murphy <peterkmurphy@gmail.com>
#
# Redistribution and use permitted under the BSD-3-Clause terms in LICENSE.txt.

from django.urls import path

from glyphviewer.views import doc, font_proxy, index

app_name = "glyphviewer"

urlpatterns = [
    path("", index, name="index"),
    path("doc/", doc, name="doc"),
    path("font/", font_proxy, name="font-proxy"),
]
