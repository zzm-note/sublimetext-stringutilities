# @author          Avtandil Kikabidze
# @copyright       Copyright (c) 2008-2016, Avtandil Kikabidze aka LONGMAN (akalongman@gmail.com)
# @link            http://longman.me
# @license         The MIT License (MIT)

import sublime
import sublime_plugin
import string
import re
import sys
import time
import base64
import html.entities as htmlentitydefs
from cgi import escape
from hashlib import md5, sha1, sha224, sha256, sha384, sha512
from datetime import datetime
from random import sample, choice, randrange
import os, socket, urllib
import binascii
import json
import pprint

sys.path.append(os.path.dirname(__file__))

import sqlparse

if sys.hexversion >= 0x3000000:
    def unichr(c):
        return chr(c)

class StringUtilitiesExpandStringCommand(sublime_plugin.TextCommand):
    """If the region is contained in a string scope, expands the region to
    the whole string. If the region is not contained in a string scope, this
    command does nothing. It is applied to all regions in the current
    selection."""

    def run(self, edit):
        for region in self.view.sel():
            self._run(edit, region)

    def _run(self, edit, region):
        if (not self.view.match_selector(region.a, "string") or
            not self.view.match_selector(region.b, "string")):
            return
        selector = "string punctuation.definition.string"
        p = region.begin()
        while not self.view.match_selector(p, selector):
            p = self.view.find_by_class(p, False, sublime.CLASS_PUNCTUATION_START)
        q = region.end()
        while not self.view.match_selector(q, selector):
            # sublime.CLASS_PUNCTUATION_END is broken
            # this works too
            q = self.view.find_by_class(q, True, sublime.CLASS_PUNCTUATION_START)
        self.view.sel().add(sublime.Region(p, q + 1))

class ConvertSelection(sublime_plugin.TextCommand):
    """Abstract class to implement a command that modifies the current text
    select. Subclasses must implement the convert method which accepts the
    selected text and returns a replacement value."""

    def run(self, edit):
        for region in self.view.sel():
            if not region.empty():
                text = self.view.substr(region).encode(self.enc())
                self.view.replace(edit, region, self.convert(text))

    def enc(self):
        if self.view.encoding() == 'Undefined':
            return self.view.settings().get('default_encoding', 'UTF-8')
        else:
            return self.view.encoding()

    def convert(self, text):
        raise NotImplementedError("Subclass must implement convert")


class ConvertTabsToSpacesCommand(sublime_plugin.TextCommand):
    #Convert Tabs To Spaces
    def run(self, edit):
        sublime.status_message('Convert tabs to spaces.')
        tab_size = int(self.view.settings().get('tab_size', 4))

        for region in self.view.sel():
            if not region.empty():
                self.view.replace(edit, region, self.view.substr(region).expandtabs(tab_size))
        else:
            self.view.run_command('select_all')
            self.view.replace(edit, self.view.sel()[0], self.view.substr(self.view.sel()[0]).expandtabs(tab_size))
            self.view.sel().clear()


class ConvertSpacesToTabsCommand(sublime_plugin.TextCommand):
    #Convert Spaces To Tabs
    def run(self, edit):
        sublime.status_message('Convert spaces to tabs.')
        tab_size = str(self.view.settings().get('tab_size', 4))

        for region in self.view.sel():
            if not region.empty():
                self.view.replace(edit, region, re.sub(r' {' + tab_size + r'}', r'\t', self.view.substr(region)))
        else:
            self.view.run_command('select_all')
            self.view.replace(edit, self.view.sel()[0], re.sub(r' {' + tab_size + r'}', r'\t', self.view.substr(self.view.sel()[0])))
            self.view.sel().clear()


class ConvertSpacesToNonBreaking(sublime_plugin.TextCommand):
    #Convert Spaces into Non-breaking Spaces
    def run(self, edit):
        for region in self.view.sel():
            if not region.empty():
                text = self.view.substr(region)
                text = text.replace(" ", "&nbsp;")
                self.view.replace(edit, region, text)


class ConvertCharsToHtmlCommand(sublime_plugin.TextCommand):
    #Convert Chars into XML/HTML Entities
    def run(self, edit):
        for region in self.view.sel():
            if not region.empty():
                self.view.replace(edit, region, escape(self.view.substr(region), True))


class ConvertHtmlToCharsCommand(sublime_plugin.TextCommand):
    #Convert XML/HTML Entities into Chars
    def run(self, edit):
        for region in self.view.sel():
            if not region.empty():
                text = re.sub('&(%s);' % '|'.join(htmlentitydefs.name2codepoint),
                    lambda m: unichr(htmlentitydefs.name2codepoint[m.group(1)]), self.view.substr(region))
                self.view.replace(edit, region, text)


class ConvertCamelUnderscoresCommand(sublime_plugin.TextCommand):
    #Convert camelCase to under_scores and vice versa
    def run(self, edit):
        for region in self.view.sel():
            if not region.empty():
                text = self.view.substr(region)
                text = self.toCamelCase(text) if '_' in text and text[0].islower() else (text[0].islower() and self.toUnderscores(text))
                self.view.replace(edit, region, text)

    def toUnderscores(self, name):
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def toCamelCase(self, name):
        return ''.join(ch.capitalize() if i > 0 else ch for i, ch in enumerate(name.split('_')))

class ConvertCamelDashCommand(sublime_plugin.TextCommand):
    #Convert camelCase to dash and vice versa
    def run(self, edit):
        for region in self.view.sel():
            if not region.empty():
                text = self.view.substr(region)
                text = self.toCamelCase(text) if '-' in text and text[0].islower() else (text[0].islower() and self.toDash(text))
                self.view.replace(edit, region, text)

    def toDash(self, name):
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1).lower()

    def toCamelCase(self, name):
        return ''.join(ch.capitalize() if i > 0 else ch for i, ch in enumerate(name.split('-')))


class ConvertPascalUnderscoresCommand(sublime_plugin.TextCommand):
    #Convert PascalCase to under_scores and vice versa
    def run(self, edit):
        for region in self.view.sel():
            if not region.empty():
                text = self.view.substr(region)
                text = self.toPascalCase(text) if '_' in text and text[0].islower() else (text[0].isupper() and self.toUnderscores(text))
                self.view.replace(edit, region, text)

    def toUnderscores(self, name):
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def toPascalCase(self, name):
        return ''.join(map(lambda x: x.capitalize(), name.split('_')))


class ConvertToUnicodeNotationCommand(sublime_plugin.TextCommand):
    #Convert string to Unicode notation
    def run(self, edit):
        pattern = re.compile(r'\s+')

        for region in self.view.sel():
            if not region.empty():
                text = ''
                for c in self.view.substr(region):
                    if not re.match(pattern, c) and (ord(c) < 0x20 or ord(c) > 0x7e):
                        text += '\\u{0:04X}'.format(ord(c))
                    else:
                        text += c

                self.view.replace(edit, region, text)


class ConvertFromUnicodeNotationCommand(sublime_plugin.TextCommand):
    #Convert string from Unicode notation
    def run(self, edit):
        pattern = re.compile(r'(\\u)([0-9a-fA-F]{2,4})')

        for region in self.view.sel():
            if not region.empty():
                text = re.sub(pattern, lambda m: unichr(int(m.group(2), 16)), self.view.substr(region))
                self.view.replace(edit, region, text)


class StringEncode(sublime_plugin.TextCommand):
    def run(self, edit, **kwargs):
        regions = self.view.sel()

        if kwargs.get('source') == 'clipboard':
            del kwargs['source']
            text = sublime.get_clipboard()
            replacement = self.encode(text, **kwargs)
            for region in regions:
                if region.empty():
                    self.view.insert(edit, region.begin(), replacement)
                else:
                    self.view.replace(edit, region, replacement)
            return

        elif 'source' in kwargs:
            sublime.status_message('Unsupported source {0!r}'.format(kwargs['source']))
            return

        if any(map(lambda region: region.empty(), regions)):
            regions = [sublime.Region(0, self.view.size())]
        for region in regions:
            text = self.view.substr(region)
            replacement = self.encode(text, **kwargs)
            self.view.replace(edit, region, replacement)


class JsonEscapeCommand(StringEncode):
    def encode(self, text):
        return json.dumps(text)[1:-1]


class JsonUnescapeCommand(StringEncode):
    def encode(self, text):
        if text[:1] == "'" and text[-1:] == "'":
            return self.encode(text[1:-1])
        if text[:1] != '"' and text[-1:] != '"':
            return self.encode('"' + text + '"')
        return json.loads(text)


class ConvertToBase64Command(sublime_plugin.TextCommand):
    #Encode string with base64
    def run(self, edit):
        for region in self.view.sel():
            if not region.empty():
                text = self.view.substr(region).encode(self.enc())
                t = base64.b64encode(text)
                txt = str(t, self.enc())
                self.view.replace(edit, region, txt)

    def enc(self):
        if self.view.encoding() == 'Undefined':
            return self.view.settings().get('default_encoding', 'UTF-8')
        else:
            return self.view.encoding()


class ConvertFromBase64Command(sublime_plugin.TextCommand):
    #Decode string with base64
    def run(self, edit):
        for region in self.view.sel():
            if not region.empty():
                text = self.view.substr(region).encode(self.enc())
                t = base64.b64decode(text)
                txt = str(t, self.enc())
                self.view.replace(edit, region, txt)

    def enc(self):
        if self.view.encoding() == 'Undefined':
            return self.view.settings().get('default_encoding', 'UTF-8')
        else:
            return self.view.encoding()

class ConvertToHexCommand(sublime_plugin.TextCommand):
    #Convert string to hex
    def run(self, edit):
        for region in self.view.sel():
            if not region.empty():
                text = self.view.substr(region).encode(self.enc())
                t = binascii.hexlify(text)
                txt = str(t,'ascii')
                self.view.replace(edit, region, txt)

    def enc(self):
        if self.view.encoding() == 'Undefined':
            return self.view.settings().get('default_encoding', 'UTF-8')
        else:
            return self.view.encoding()


class ConvertFromHexCommand(sublime_plugin.TextCommand):
    #Convert string from hex
    def run(self, edit):
        for region in self.view.sel():
            if not region.empty():
                text = self.view.substr(region).encode(self.enc())
                t = binascii.unhexlify(text)
                txt = str(t,'ascii')
                self.view.replace(edit, region, txt)

    def enc(self):
        if self.view.encoding() == 'Undefined':
            return self.view.settings().get('default_encoding', 'UTF-8')
        else:
            return self.view.encoding()

class ConvertHexToRgbCommand(sublime_plugin.TextCommand):
    #Convert hex to rgb color
    def run(self, edit):
        for region in self.view.sel():
            if not region.empty():
                text = self.view.substr(region)
                self.view.replace(edit, region, self.hexToRgb(text))

    def enc(self):
        if self.view.encoding() == 'Undefined':
            return self.view.settings().get('default_encoding', 'UTF-8')
        else:
            return self.view.encoding()

    def hexToRgb(self, value):
        value = value.lstrip('#')
        lv = len(value)
        if lv == 6:
            rgb = tuple(str(int(value[i:i+lv//3], 16)) for i in range(0, lv, lv//3))
        if lv == 3:
            rgb = tuple(str(int(value[i:i+1], 16)*17) for i in range(0, 3))
        if lv == 1:
            v = str(int(value, 16)*17)
            rgb = v, v, v
        return 'rgb(' + ','.join(rgb) + ')'


class ConvertRgbToHexCommand(sublime_plugin.TextCommand):
    #Convert rgb to hex color
    def run(self, edit):
        for region in self.view.sel():
            if not region.empty():
                text = self.view.substr(region)
                str_len = len(text)
                reg_rgb = '^rgb[a]?\((\s*\d+\s*),(\s*\d+\s*),(\s*\d+\s*),?(\s*(0?.?\d)+\s*)?\)$'
                rgb_match = re.match(reg_rgb, text)
                if rgb_match is not None:
                    self.view.replace(edit, region, self.rgbToHex(rgb_match))

    def enc(self):
        if self.view.encoding() == 'Undefined':
            return self.view.settings().get('default_encoding', 'UTF-8')
        else:
            return self.view.encoding()

    def rgbToHex(self, rgb_match):
        """Converts an rgb(a) value to a hex value.

        Attributes:
            self: The Regionset object.
            rgb_match: The reg exp collection of matches.

        """

        # Convert all values to 10-base integers, strip the leading characters,
        # convert to hex and fill with leading zero's.
        val_1 = hex(int(rgb_match.group(1), 10))[2:].zfill(2)
        val_2 = hex(int(rgb_match.group(2), 10))[2:].zfill(2)
        val_3 = hex(int(rgb_match.group(3), 10))[2:].zfill(2)

        # Return the proformatted string with the new values.
        return '#%s%s%s' % (val_1, val_2, val_3)


class ConvertSingleQuotesToDoubleCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        for region in self.view.sel():
            if not region.empty():
                text = self.view.substr(region)
                text = text.replace("'", "\"")
                self.view.replace(edit, region, text)

class ConvertDoubleQuotesToSingleCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        for region in self.view.sel():
            if not region.empty():
                text = self.view.substr(region)
                text = text.replace("\"", "'")
                self.view.replace(edit, region, text)

class UrlDecodeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        for region in self.view.sel():
            if not region.empty():
                text = self.view.substr(region)
                text = urllib.parse.unquote(text)
                self.view.replace(edit, region, text)

class UrlEncodeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        for region in self.view.sel():
            if not region.empty():
                text = self.view.substr(region)
                text = urllib.parse.quote(text)
                self.view.replace(edit, region, text)


class ConvertMd5Command(ConvertSelection):
    """Calculate the MD5 hash of the selected text"""
    def convert(self, text):
        return md5(text).hexdigest()

class ConvertSha1Command(ConvertSelection):
    """Calculate the SHA1 hash of the selected text"""
    def convert(self, text):
        return sha1(text).hexdigest()

class ConvertSha224Command(ConvertSelection):
    """Calculate the SHA224 hash of the selected text"""
    def convert(self, text):
        return sha224(text).hexdigest()

class ConvertSha256Command(ConvertSelection):
    """Calculate the SHA256 hash of the selected text"""
    def convert(self, text):
        return sha256(text).hexdigest()

class ConvertSha384Command(ConvertSelection):
    """Calculate the SHA384 hash of the selected text"""
    def convert(self, text):
        return sha384(text).hexdigest()

class ConvertSha512Command(ConvertSelection):
    """Calculate the SHA512 hash of the selected text"""
    def convert(self, text):
        return sha512(text).hexdigest()


class ConvertTimeFormatCommand(sublime_plugin.TextCommand):
    #This will allow you to convert epoch to human readable date
    def run(self, edit):
        for region in self.view.sel():
            if not region.empty():
                text = self.view.substr(region)

                if re.match('^([0-9]+)$', text):
                    result = self.fromUnix(text)
                else:
                    result = self.toUnix(text)

                if result:
                    self.view.replace(edit, region, result)
                else:
                    sublime.status_message('Convert error.')

    def fromUnix(self, timestamp):
        sublime.status_message('Convert from epoch to human readable date.')
        timestamp = float(timestamp)
        stamp = datetime.fromtimestamp(timestamp)
        return stamp.strftime("%Y-%m-%d %H:%M:%S")

    def toUnix(self, timestr):
        sublime.status_message('Convert from human readable date to epoch.')
        try:
            datetime_to_convert = datetime.strptime(timestr, "%Y-%m-%d %H:%M:%S")
            return '%d' % (time.mktime(datetime_to_convert.timetuple()))
        except:
            return False


class InsertTimestampCommand(sublime_plugin.TextCommand):
    #This will allow you to insert timestamp to current position
    def run(self, edit):
        for region in self.view.sel():
            self.view.insert(edit, region.begin(), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class GeneratePasswordCommand(sublime_plugin.TextCommand):
    chars = "23456789abcdefghijkmnpqrstuvwxyzABCDEFGHKMNPQRSTUVWXYZ"

    def run(self, edit):
        self.view.window().show_input_panel("Enter Length(int≤54)", "", self.on_change, None, None)

    def on_change(self, length):
        if length:
            length = int(length)
            text = ''.join(sample(self.chars, length))
            self.view.run_command("insert", {"characters": text})


class GeneratePasswordSpecSymbolsCommand(sublime_plugin.TextCommand):
    chars = "0123456789abcdefghijkmnpqrstuvwxyzABCDEFGHKMNPQRSTUVWXYZ%*)?@#$~"

    def run(self, edit):
        self.view.window().show_input_panel("Enter Length(int≤64)", "", self.on_change, None, None)

    def on_change(self, length):
        if length:
            length = int(length)
            text = ''.join(sample(self.chars, length))
            self.view.run_command("insert", {"characters": text})

class DecodeHeidiSqlCommand(sublime_plugin.TextCommand):
    # Requires .strip('\x00') on output otherwise sublimetext adds a 'NUL' control chracter
    def run(self, edit):
        for region in self.view.sel():
            if not region.empty():
                text = self.view.substr(region)
                if text[0].isdigit(): text = self.decodeHeidi(text)
                self.view.replace(edit, region, text)

    def decodeHeidi(self, hex_in):
        shift = int(hex_in[-1])
        shifted_list = [int(hex_in[i:i+2], 16) for i in range(0, len(hex_in), 2)]
        return ''.join(chr(out_ch - shift) for out_ch in shifted_list).strip('\x00')


class StringUtilitiesExtIpCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        url = "https://myip.ipip.net/"
        request = urllib.request.Request(url)
        response = urllib.request.urlopen(request)
        for region in self.view.sel():
            self.view.insert(edit, region.begin(), response.read().decode(self.enc()))

    def enc(self):
        if self.view.encoding() == 'Undefined':
            return self.view.settings().get('default_encoding', 'UTF-8')
        else:
            return self.view.encoding()

class StringUtilitiesIntIpCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            int_ip = s.getsockname()[0]
        finally:
            s.close()
        for region in self.view.sel():
                self.view.insert(edit, region.begin(), int_ip)

    def enc(self):
        if self.view.encoding() == 'Undefined':
            return self.view.settings().get('default_encoding', 'UTF-8')
        else:
            return self.view.encoding()


class StringUtilitiesDecodeJsonCommand(sublime_plugin.TextCommand):
    output = ""
    i = 0

    def run(self, edit):

        try:
            self.view.erase_regions('json_errors')
            self.view.erase_status('json_errors')
            for region in self.view.sel():
                self.output = ""
                if region.empty():
                    selection = sublime.Region(0, self.view.size())
                else:
                    selection = region

                text = self.view.substr(selection).encode(self.enc())
                text = str(text, 'utf8')
                data = json.loads(text, encoding='utf8')
                output = json.dumps(data, indent=4, sort_keys=True)

                self.view.replace(edit, selection, output)

                    #self.recursivePrint(data)

                    #print(self.output)

                    #pp = pprint.PrettyPrinter(indent=4, width=1)
                    #data = pp.pformat(data)
                    #data = self.output
                    #data = data.replace('{   ', '{')
                    #data = data.replace('{', '\n   {\n')

                    #self.view.replace(edit, region, self.output)
        except Exception:
            exc = sys.exc_info()[1]
            sublime.status_message(str(exc))
            for region in self.view.sel():
                if region.empty():
                    self.highlight_error(str(exc))
                else:
                    startrow, startcol = self.view.rowcol(region.begin())
                    self.highlight_error(str(exc), lineBegin=startrow)

    def highlight_error(self, message, lineBegin=0):

        self.view.erase_regions('json_errors')
        self.view.erase_status('json_errors')

        json_error_matcher = re.compile(r"line (\d+)")
        m = json_error_matcher.search(message)
        if m:
            line = int(m.group(1)) + lineBegin - 1

            # sometime we need to highlight one line above
            if "','" in message and "delimiter" in message:
                line_content = self.view.substr(self.view.full_line(self.view.text_point(line - 1, 0)))
                if line_content.strip()[-1] != ',' and line_content.strip() != '{' and line_content.strip() != '}':
                    line -= 1

            if "control character '\\n'" in message:
                line_content = self.view.substr(self.view.full_line(self.view.text_point(line - 1, 0)))
                quotes = re.findall(r"\"", line_content)
                if len(quotes) % 2 != 0 and len(quotes) != 0:
                    line -= 1

            regions = [self.view.full_line(self.view.text_point(line, 0)), ]

            self.view.add_regions('json_errors', regions, 'invalid', 'dot',
                                  sublime.DRAW_OUTLINED)
            self.view.show(regions[0])
            self.view.set_status('json_errors', message)

    def enc(self):
        if self.view.encoding() == 'Undefined':
            return self.view.settings().get('default_encoding', 'UTF-8')
        else:
            return self.view.encoding()

    def recursivePrint(self, src, dpth = 0, key = ''):
        """ Recursively prints nested elements."""
        tabs = lambda n: '\t' * n * 1 # or 2 or 8 or...
        brace = lambda s, n: '%s%s%s' % ('['*n, s, ']'*n)

        if isinstance(src, dict):
            for key, value in src.items():
                if isinstance(value, dict) or (isinstance(value, list)):
                    self.output += tabs(dpth) + brace(key, dpth) + "\n"
                self.recursivePrint(value, dpth + 1, key)
        elif (isinstance(src, list)):
            self.i = 0
            for litem in src:
                self.recursivePrint(litem, dpth + 1)
        else:
            if key:
                self.output += tabs(dpth) + '[%s] => %s' % (key, src) + "\n"
            else:
                self.i = self.i + 1
                self.output += tabs(dpth) + str(self.i) + ' => %s' % src + "\n"



class StringUtilitiesTestCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        ext_ip = urllib2.urlopen('http://api.long.ge/sublimetext/ip.php').read()
        for region in self.view.sel():
            self.view.insert(edit, region.begin(), ext_ip.encode(self.enc()))

    def enc(self):
        if self.view.encoding() == 'Undefined':
            return self.view.settings().get('default_encoding', 'UTF-8')
        else:
            return self.view.encoding()


class PhpObjectToArrayCommand(sublime_plugin.TextCommand):
    """
    convertes PHP Object into PHP Array Access
    from $obj->variable into $obj['variable']
    """

    def run(self, edit):
        for region in self.view.sel():
            if not region.empty():
                source_text = self.view.substr(region)
                if "->" not in source_text:
                    # nothing to replace
                    pass

                fragments = source_text.split("->")
                result = "{}['{}']".format(fragments[0], fragments[1])

                self.view.replace(edit, region, result)


class SqlBeautifierCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        window = self.view.window()
        view = window.active_view()

        for region in self.view.sel():
            if region.empty():
                selection = sublime.Region(0, self.view.size())
            else:
                selection = region

            selected_text = self.view.substr(selection).encode(self.enc())
            selected_text = str(selected_text, 'utf8')
            try:
                foramtted_text  = sqlparse.format(selected_text, reindent=True, keyword_case='upper', indent_columns=True)
                self.view.replace(edit, selection, foramtted_text)
            except Exception:
                exc = sys.exc_info()[1]
                sublime.status_message(str(exc))

    def enc(self):
        if self.view.encoding() == 'Undefined':
            return self.view.settings().get('default_encoding', 'UTF-8')
        else:
            return self.view.encoding()
