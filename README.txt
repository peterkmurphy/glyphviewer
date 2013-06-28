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

Installation and Dependencies
-----------------------------

**Glyphviewer** depends on the following software:

* `Python 2.x <http://www.python.org/>`_
* `Django 1.x <http://www.djangoproject.com/>`_
* The `FontTools <http://sourceforge.net/projects/fonttools/>`_ for parsing TrueType and OpenType files.
* The `WoffTools <http://code.typesupply.com/wiki/woffTools>`_, built on top of FontTools, for parsing WOFF files.
* `Numerical Python (numpy) <http://sourceforge.net/projects/numpy/>`_, which is a dependency for both FontTools and WoffTools.

Once these libraries have been installed, the next stage is to install **Glyphviewer** 
from PyPI through the command:

    pip install glyphviewer

The next stage is to add "glyphviewer" to your INSTALLED_APPS list in settings.py, 
and add the desired URL in one of the urls.py files.

The final stage is to populate the directory with fonts where you display your chosen
font or fonts. Choose one directory from STATICFILES_DIRS, and add the subdirectory 
'glyphviewer/fonts/'. The Glyphviewer application comes with its own set of fonts 
adapted from the `Free UCS Outline Fonts <https://savannah.gnu.org/projects/freefont/>`_; they have been converted to WOFF form 
for quicker download. These can be moved into the correct directory via the 
following shell command:

    python manage.py collectstatic

The HTML template files in this application have been redesigned to work with the 
`Mezzanine <http://mezzanine.jupo.org/>`_ CMS. The redesign removed any explicit 
references to particular stylesheets found with earlier versions. 
The app (and the fonts) are released under a 
`GNU general public license. <http://www.gnu.org/copyleft/gpl.html>`_


Versions
--------

* 0.1 (June 11th 2011) - Initial release. 

* 0.2 (June 28th 2011) - Added setup script to create a PyPI package. Removed bugs.

Copyright
---------

The **chordgenerator** app is copyright (c) 2008-2013 
`Peter Murphy <http://www.pkmurphy.com.au/>`_ 
<peterkmurphy@gmail.com>.




