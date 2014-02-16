#!/usr/bin/python 
#-*- coding: UTF-8 -*-
# File: glyphtable.py 
# Goal - to provide a nice template tag to represent tables of glyphs.
# Copyright (C) 2013, Peter Murphy <peterkmurphy@gmail.com>
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


from glyphviewer.glyphviewer import glyphCatcher, glyphArray, fontHeader, DODGY;
from django import template;
from django.utils.safestring import mark_safe

DEFAULT_GLYPHTABLE_SIZE = 16; # 16 is a nice round number.

# The following constants are nice for interpolation.

TABSUM = u"<table style=\"table-layout: fixed; width:100%;\" class=\"glyphtable table-bordered table-styled\">\n";
TABCAP = u"<caption class=\"glyphcaption\"><strong>%s</strong></caption>\n<tbody \
class=\"glyphtbody\">\n";

#TABCAP = u"<thead><tr><th rowspan=\"8\">%s</th></tr></thead>\n<tbody \
#class=\"glyphtbody\">\n";


#<td rowspan="number"> 


CELLMAKER = "<td class = \"glyphtd\"><p class = \"glyphchar text-center\">&#%s;<br />\n\
<p class = \"glyphnum text-center\"><strong>U+%04X</strong></p></td>";
REMAINDER = "<td class = \"glyphempty\"><p class=\"glyphchar text-center\">&nbsp;</p>\
<p class=\"glyphnum text-center\">&nbsp;</p></td>";

register = template.Library();

@register.filter(name="glyphtable")
def glyphtable(value, arg = DEFAULT_GLYPHTABLE_SIZE):
    ''' Takes an argument (value) that is assumed to be of type glyphArray.
    The function returns HTML that represents all the glyphs as a table. The
    arg argument indicates the number of columns for the table.
    
    Note: many of the generated entries are given HTML classes - all the 
    better for CSS styling.    
    
    '''
    try:
        
# Note: for HTML validity, font characters that are control or line break are
# not represented in table form nor displayed, but are listed by their 
# numerical code points.
        
        if (value.blockName == DODGY):
            if (len(value.codePoints) == 0):
                return "";
            output = "<p><em>Note: the following numbers listed are the code ";
            output += "point values of characters in the font that would ";
            output += "normally not be printed, such as control characters. ";
            output += "For that reason, they are represented separately.</em></p>\n";
            output += "<ul>\n";
            for i in value.codePoints:
                output += "<li>U+%04X</li>\n" % i;
            output += "</ul>\n";            
            return mark_safe(output);
        
# Any exception - any at all - returns an empty string.

        blocksize = len(value.codePoints);
        numfullrows = blocksize / arg;
        remainder = (blocksize % arg);
        output = TABSUM + TABCAP % value.blockName;
        
# It's more efficient to create output whole rows.         
        
        for i in range(numfullrows):
            output += "<tr class = \"glyphtr\">"
            for j in range(arg):
                ournumber = value.codePoints[j + i * arg];
                output += CELLMAKER % (str(ournumber), ournumber,);
            output += "</tr>\n";

# And then deliver the last row at the end (if any).

        if remainder == 0:
            output += "</tbody>\n</table>\n";
            return mark_safe(output);
        output += "<tr class = \"glyphtr\">"
        for j in range(remainder):
            ournumber = value.codePoints[j + numfullrows * arg]; 
            output += CELLMAKER % (str(ournumber), ournumber,);
        for j in range(arg - remainder):
            output += REMAINDER;
        output += "</tr>\n";
        output += "</tbody>\n</table>\n";
        return mark_safe(output);

# And if it all turns to shit...

    except:
        return "";
glyphtable.is_safe = False

@register.inclusion_tag('glyphviewer/showheader.html')
def showheader(value):
    return {'value': value}






