#!/usr/bin/python 
#-*- coding: UTF-8 -*-
# File: glyphviewer.py 
# Goal - to read the unicode points for a font and pass it as a map.
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

from blocks import blockbyint, namefromindex, indexfromname, numblocks;
from fontTools import ttLib;
import os.path;
import urllib;
import datetime;
import urllib2

PLAT_STANDARD_ID = 3; # Never changes.
PLAT_UNIENC_ID = 1; # We're only interested in Unicode encodings.
PLAT_UCS4_ID = 10; # We're only interested in Unicode encodings.
ALL_CHAR_BLOCK = u"All Unicode Characters";
FONT_NAME_PLATID = 1; # Used with getting Font name info. Do not change.
FONT_NAME_ENCID = 0; # Used with getting Font name info. Do not change.

# The following constants are taken from
# http://developer.apple.com/fonts/TTRefMan/RM06/Chap6name.html

FONT_NAME_CPY = 0; # Copyright notice.
FONT_NAME_FFY = 1; # Font Family. 
FONT_NAME_SFY = 2; # Font Subfamily.
FONT_NAME_USI = 3; # Unique subfamily identification.
FONT_NAME_FNM = 4; # Full name of the font.
FONT_NAME_VSN = 5; # Version of the name table.
FONT_NAME_PSC = 6; # PostScript name of the font. 
FONT_NAME_TMK = 7; # Trademark notice.
FONT_NAME_MFC = 8; # Manufacturer name.
FONT_NAME_DES = 9; # Designer; name of the designer of the typeface.
FONT_NAME_DCS = 10; # Description; description of the typeface. 
FONT_NAME_URL = 11; # URL of the font vendor (e.g., http://, ftp://). 
FONT_NAME_URD = 12; # URL of the font designer (e.g., http://, ftp://)
FONT_NAME_LDS = 13; # Description of how the font may be legally used.
FONT_NAME_LIU = 14; # License information URL

# These are error codes from GlyphCatcher. I like to give numeric values - 
# blame my C/C++ heritage.

GC_NOERROR = 0;
GC_NORESOURCE = 1; # Can't even open the resource.
GC_RETFAIL = 2; # Can't retrive the resource.
GC_TIMEOUT = 3; # Timeout
GC_TOOBIG = 4; # Resource too big.
GC_NOTAFONT = 5; # Not a font.
GC_NOHEADER = 6; # No font header.
GC_NOUNICODE = 7; # Symbol font or other dodginess.
GC_OTHERERROR = 8; # Exception thrown somewhere else or other.
GC_WARNCORS = 9; # Problem with CORS and remote resources.

# These are the limitations on the function, so it won't accept some
# excessively sized object.

FONT_MAX_SIZE = 3*1024*1024; # 3 Meg - probably more than necessary.
FONT_TIMEOUT = 120; # 120 seconds - probably more than necessary.
FONT_TIMEOUT_DELTA = datetime.timedelta(seconds=FONT_TIMEOUT);

# It's quicker to interpolate error strings outside the template.

GC_ERRORMSG = ["", # No error message for status 0,
    "It cannot be opened.",
    "It cannot be accessed or retrieved.",
    "It too more than %d seconds to retrieve it." % FONT_TIMEOUT,
    "It exceeds %d bytes in size. " % FONT_MAX_SIZE,
    "It does not appear to be a legitimate font file.",
    "There is no font header found.",
    "The font does not appear to be a legitimate Unicode font. Did you select a 'Symbol' or \
    'Wingdings' font for processing? If so, shame on you.",
    "We don't know what's happened, but some error has arisen. Sorry about that.",
    "It is possible to analyse the font header, but CORS prevents the \
    display of the glyphs in the font. In this case, the browser will display characters \
    using some fall-back font, which should not be used as a guide to the appearance of the \
    font selected here."];


# For characters that shouldn't be printed.

DODGY = "Invalid HTML Characters"

def isvalhtml(ichar):
    ''' Input: numerical value for character. Returns True if it corresponds
    to a legitimate HTML character; False otherwise.
    
    Note 1: not tested for characters beyond 65536.
    Note 2: makes 0 a dodgy character as well.
    '''
# It's easier to mark line break characters as illegitimate.
#
#    if ((ichar < 9) or (ichar == 11)):
#        return False;
#    if ((ichar >= 14) and (ichar <= 31)):
#        return False;

    if (ichar <= 31):
        return False;
    if ((ichar >= 127) and (ichar <= 159)):
        return False;
    if ((ichar == 65535) or (ichar == 65534)):
        return False;
    if ((ichar >= 64976) and (ichar <= 65007)):
        return False;
    return True;


# Here's the code that polices the size limitation.

class TooBigException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

# Here's the code that polices the time limitation.

class TimeoutException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def sizecheck(count, blockSize, totalSize):
    sizeread = 0;
    blocksize = blockSize;
#    if datetime.datetime.now() - nowtime > FONT_TIMEOUT_DELTA:
#        raise TimeoutException;    
    if totalSize > FONT_MAX_SIZE:
        raise TooBigException(totalSize);
    if count * blocksize > FONT_MAX_SIZE:
        raise TooBigException(count * blocksize);


class glyphArray():
    ''' Represents a array of unicode character with the name of its block
        (or "All Unicode Characters" if there is no particular block. 
    '''
    def __init__(self, blockName, codePoints):
        self.blockName = blockName;
        self.codePoints = codePoints;
        
    def __unicode__(self):
        return self.blockName + ": " + unicode(self.codePoints) + u"\n";
        
    def __str__(self):
        return unicode(self);

class fontHeader():
    ''' Represents the header of a font - in a form presentable in HTML. '''
    def __init__(self, ournametable):
        def stringex(font_name_id):
            our_data = ournametable.getName(font_name_id, FONT_NAME_PLATID,
                FONT_NAME_ENCID);
            self.ournametable = ournametable
            if our_data:
                return our_data.string;
            else:
                return None;
                
        self.copyright = stringex(FONT_NAME_CPY); # Copyright notice.
        self.fontfamily = stringex(FONT_NAME_FFY); # Font Family. 
        self.subfamily = stringex(FONT_NAME_SFY); # Font Subfamily.
        self.usi = stringex(FONT_NAME_USI); # Unique subfamily identification.
        self.fullname = stringex(FONT_NAME_FNM); # Full name of the font.
        self.version = stringex(FONT_NAME_VSN); # Version of the name table.
        self.ps = stringex(FONT_NAME_PSC); # PostScript name of the font. 
        self.trademark = stringex(FONT_NAME_TMK); # Trademark notice.
        self.manufac = stringex(FONT_NAME_MFC); # Manufacturer name.
        self.designer = stringex(FONT_NAME_DES); # Designer name.
        self.description = stringex(FONT_NAME_DCS); # Description.
        self.urlfontven = stringex(FONT_NAME_URL); # font vendor URL. 
        self.urlfontdes = stringex(FONT_NAME_URD); # font designer URL.
        self.descrip = stringex(FONT_NAME_LDS); # Legal use information.
        self.licenseurl = stringex(FONT_NAME_LIU); # License information URL.
        
    def __unicode__(self):
        return self.fullname;
        
    def __str__(self):
        return unicode(self);

def glyphCatcher(fontName, bStoreInBlocks = False, debugMode = False, bCheckCORS=False):
    ''' This is the main meat of the glyphviewer application. The function
        takes a font, extracts the header and a list of the glyphs it
        supports. Or attempts to...
        
        Return values are of the form:
        (error code, fontHeader, sequence of glyphArray,)
        
        Arguments:
        fontName: the file name or URL for a font.
        bStoreInBlocks: if False, the function returns a stored sequence of
        integers for the glyphs. if True, the function returns a sequence of
        sequences, each corresponding to blocks in Unicode. 
        debugMode: if True, fontName can be a file name. If False, fontName
        must be a URL. This is generally the same value as settings.DEBUG.
        bCheckCORS: whether to check for Cross Origin Resource Sharing
    '''

    def _cleanup(arg):
        ''' Only called in the routine. '''
        if bUseTempFile:
            if os.path.exists(resourceName):
                os.unlink(resourceName);
        return arg;


    DodgyGlyphArray = glyphArray(DODGY, []);

    bUseTempFile = False;
    retrievalInfo = None;
    bCORSBlues = False
    
# Is the font a local resource, or accessed by http?        
    
    if os.path.exists(fontName) & debugMode:
        resourceName = fontName;
    else:
        opener = urllib.FancyURLopener({})
        try:
            print ("Wow")
            print (fontName)
            nowtime = datetime.datetime.now();
            retrievalInfo = opener.retrieve(fontName, reporthook=sizecheck)
            if bCheckCORS:
                if "Access-Control-Allow-Origin" not in retrievalInfo[1]:
                    bCORSBlues = True
                elif retrievalInfo[1]["Access-Control-Allow-Origin"] != "*":
                    bCORSBlues = True
            
        except TooBigException:
            return (GC_TOOBIG, None, None,);
        except TimeoutException:
            return (GC_TIMEOUT, None, None,);
        except:
            return (GC_RETFAIL, None, None);
        resourceName = retrievalInfo[0];
        bUseTempFile = True;
    
    try:
        ourFont = ttLib.TTFont(resourceName);
    except (ttLib.TTLibError):
        print ttLib.TTLibError.message
        return _cleanup((GC_NOTAFONT, None, None,));
    except:
        return _cleanup((GC_OTHERERROR, None, None,));
    
# Since TTFont (and WOFFFont) are "lazy", non-fonts may not be detected until
# an explicit attempt is done to read the cmap table.

    if bCORSBlues:
        ourgoodoutcome = GC_WARNCORS
    else:
        ourgoodoutcome = GC_NOERROR

    try:
        cmaptable = ourFont['cmap'].getcmap(PLAT_STANDARD_ID, PLAT_UCS4_ID);
        if cmaptable is None:
            cmaptable = ourFont['cmap'].getcmap(PLAT_STANDARD_ID, PLAT_UNIENC_ID);
            if cmaptable is None:
                return _cleanup((GC_NOUNICODE, None, None,));
        ourheader = fontHeader(ourFont['name']);
    except:
        return _cleanup((GC_NOHEADER, None, None,));
    if bStoreInBlocks:
        blockcontents = [[] for i in range(numblocks())];
        for i in cmaptable.cmap.keys():
            if not isvalhtml(i):
                DodgyGlyphArray.codePoints.append(i);
            else:
                (blockcontents[indexfromname(blockbyint(i))]).append(i);
        [i.sort() for i in blockcontents];
        blockarrangements = [DodgyGlyphArray];
        for i in range(numblocks()):
            if len(blockcontents[i]) > 0:
                blockarrangements.append(glyphArray(namefromindex(i), 
                    blockcontents[i]));
        return _cleanup((ourgoodoutcome,ourheader,blockarrangements,));
    else:
        blockcontents = list(cmaptable.cmap.keys());
        blockcontents.sort();
        ExcellentGlyphArray = glyphArray(ALL_CHAR_BLOCK,[])
        for i in blockcontents:
            if isvalhtml(i):
                ExcellentGlyphArray.codePoints.append(i);                
            else:
                DodgyGlyphArray.codePoints.append(i);
        return _cleanup((ourgoodoutcome, ourheader,[DodgyGlyphArray, ExcellentGlyphArray],));

if __name__ == '__main__':
    print glyphCatcher("", True);
    content = glyphCatcher("http://themes.googleusercontent.com/static/fonts/robotoslab/v1/y7lebkjgREBJK96VQi37ZobN6UDyHWBl620a-IRfuBk.woff", False); #""http://127.0.0.1:8000/static/glyphviewer/fonts/Essays1743.woff", True);
    header = content[1];
    print header; 
    print header.urlfontven 
    print header.urlfontdes 
    body = content[2];
    for i in body:
        print i;
 #   content = glyphCatcher("http://127.0.0.1:8000/static/glyphviewer/fonts/Essays1743.woff", False);
 #   body = content[2];
 #   for i in body:
 #       print i;        
