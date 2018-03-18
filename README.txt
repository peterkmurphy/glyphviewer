===============
Glyphviewer
===============

About
-----

**Glyphviewer** is a web application that analyses web font files. This app will
parse any web font file provided as input, and will display its general information
(such as name and copyright details) to the user. Glyphviewer also provides a testbed
where users can enter text, and have it displayed using the font. Finally, this
application can display the characters supported by the font along with their Unicode
codepoints. A demonstration is available `here <http://www.pkmurphy.com.au/glyphviewer/>`_.

Installation
-----------------------------

**Glyphviewer** and its dependencies can be installed via the command:

``pip install glyphviewer``

The next stage is to add "glyphviewer" to your INSTALLED_APPS list in settings.py,
and add the desired URL in one of the urls.py files.

The final stage is to populate the directory with fonts where you display your chosen font or fonts.
The Glyphviewer application comes with its own set of fonts adapted from the `Free UCS Outline Fonts <https://savannah.gnu.org/projects/freefont/>`_;
they have been converted to WOFF form for quicker download. These can be moved into the correct directory via the following shell command:

``python manage.py collectstatic``

The font files wil then be moved into the {STATIC_ROOT}/glyphviewer/fonts/ directory, and the browser will
read the files from the {STATIC_URL}/glyphviewer/fonts/ folder.

The HTML template files in this application have been redesigned to work with the
`Mezzanine <http://mezzanine.jupo.org/>`_ CMS. The redesign removed any explicit
references to particular stylesheets found with earlier versions.
The app (and the fonts) are released under a
`GNU general public license. <http://www.gnu.org/copyleft/gpl.html>`_ If you wish to do any changes,
pop over to the `GitHub repository <https://github.com/peterkmurphy/glyphviewer>`_ for the app.


Versions
--------

* 0.1 (June 11th 2011) - Initial release.

* 0.2 (June 28th 2013) - Added setup script to create a PyPI package. Removed bugs.

* 0.3 (February 15th 2014) - Made compatible with Mezzanine and Bootstrap, changed styles for errors, now handles empty local directories.

* 0.4 (January 16th 2016) - Now handles cases where remote fonts are inaccessible using CORS; removed the limitation that restricted characters to the BMP; added documentation for above.

* 0.5 (March 31st 2017) - Updated to be compatible with Django 1.10. Now automatically install dependencies using pip.

* 0.6 (March 18th 2018) - Add WOFF2 compatibility.

Copyright
---------

The **Glyphviewer** app is copyright (c) 2011-2018
`Peter Murphy <http://www.pkmurphy.com.au/>`_
<peterkmurphy@gmail.com>.
