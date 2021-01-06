#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=C0301
"""charactergraph.py - Charactergram graphical representation of novel characters occurence over time.

A charactergram depicts the dispersion of novel characters over time.
This graphical representations shows when which characters or persons
occur in the novel, analogously to a lexical dispersion plot.
The x-axis depicts the word number in the source text,
the y-axis the n-th most common words.

This 'charactergraph' outputs such a charactergram.
The input is an EPUB file (.epub).

Usage:
  charactergraph.py [options] <ebook.epub>
  charactergraph.py -h | --help
  charactergraph.py --version

Arguments:
  ebook.epub       EPUB file.

Options:
  -h --help        Show this screen.
  -e --ner=file    Named-entities helper file with additional names.
  -n --number=N    Number of characters (y-axis) [default: 25]
  -o --output=file Output file. If not specified then use GUI to display.
  -s --stop=file   Stopwords file [default: stopwords.txt].
  -v --verbose     More logging output.
  --version        Show version.
"""
import logging
##
## LICENSE:
##
## Copyright (C) 2021 Alexander Streicher
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU Affero General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Affero General Public License for more details.
##
## You should have received a copy of the GNU Affero General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.
##
import os
import re
import sys
from codecs import open  # pylint: disable=W0622
from collections import Counter
from io import StringIO
from math import ceil

import ebooklib
import matplotlib.pyplot as plt
import nltk
import spacy
from bs4 import BeautifulSoup
from docopt import docopt
from ebooklib import epub

__version__ = "1.3.0"
__date__ = "2021-01-04"
__updated__ = "2021-01-06"
__author__ = "Ixtalo"
__email__ = "ixtalo@gmail.com"
__license__ = "AGPL-3.0+"
__status__ = "Production"

## https://spacy.io/models
SPACY_LANGUAGE_MODEL = 'en_core_web_sm'

DEBUG = 0
TESTRUN = 0
PROFILE = 0
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

## check for Python3
if sys.version_info < (3, 0):
    sys.stderr.write("Minimum required version is Python 3.x!\n")
    sys.exit(1)


class Charactergraph:
    """
    Build a 'charactergraph' or 'charactermeter' which records the 'activity' of
    all persons/characters in the novel and outputs a 'charactergram'.
    """
    stopwords = None
    stopwords_ignore_case = False
    ner_names = []
    _names = []
    _tokens = []

    def __init__(self,
                 filepath: str,
                 ner_names_file: str = None,
                 stopwords_file: str = None,
                 stopwords_ignore_case: bool = False):
        """
        Charactergraph for the given e-book file.
        :param filepath: EPUB e-book file
        :param ner_names_file: file with additional names for NER
        :param stopwords_file: file with stopwords, i.e., names to ignore
        :param stopwords_ignore_case: case-sensitivity for stopwords string comparison
        """
        self.filepath = filepath
        self.book = self._read_ebook()
        self.stopwords_ignore_case = stopwords_ignore_case
        if stopwords_file:
            logging.info("Loading stopwords from '%s' ...", os.path.abspath(stopwords_file))
            self.stopwords = self.read_file_lines(stopwords_file, lowercase=stopwords_ignore_case)
            logging.info("#%d stop words", len(self.stopwords))
        if ner_names_file:
            logging.info("Loading NER extra names from '%s' ...", os.path.abspath(ner_names_file))
            self.ner_names = self.read_file_lines(ner_names_file, lowercase=False)
            logging.info("#%d extra names for NER", len(self.ner_names))

    @staticmethod
    def read_file_lines(filename: str, lowercase: bool = False):
        """
        Read a text file line-by-line into a list.
        Commented lines (starting with '#') are ignored.
        :param filename text file name/path
        :param lowercase: convert words to lowercase
        """
        filepath = filename
        if not os.path.isabs(filepath):
            filepath = os.path.abspath(os.path.join(SCRIPT_DIR, filename))
        result = set()
        for line in open(filepath):
            line = line.strip()
            if line.startswith('#'):
                continue
            if lowercase:
                line = line.lower()
            if line:
                result.add(line)
        return result

    @staticmethod
    def segment_text(text: str, segment_size: int, separator: str = ' '):
        """
        Partition or segment a text considering the separator character.
        A typical text should not be divided in the middle of a word but between words,
        i.e., considering spaces.
        """
        i = 0
        while i < len(text):
            ## partition into (before, separator, after)
            before, _, after = text[i:i + segment_size].rpartition(separator)
            ## increase position by segment_size but reduce by the length of the rest
            i += segment_size - len(after)
            ## right strip any remaining separator
            yield before.rstrip(separator)

    @staticmethod
    def get_ebook_text(book: ebooklib.epub):
        """
        Get all the chapter text of an EPUB file.
        """
        text = StringIO()
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.content, features='lxml')
            ## skip non-chapters
            if len(soup.text) < 3000:
                continue
            text.write(soup.text)
        return text.getvalue()

    @staticmethod
    def replace_space_underscore_fornames(text: str, ner_names: set):
        """
        Because of tokenization spaces need to be replaced.
        """
        for word in ner_names:
            ## https://stackoverflow.com/questions/4893506/fastest-python-method-for-search-and-replace-on-a-large-string
            reg = re.compile('(%s)' % word)
            repl = word.replace(' ', '_')
            ## TODO use stream for speed-up
            text = reg.sub(repl, text)
        return text

    @staticmethod
    def get_most_frequent_items_inorder(items: list, top_n: int):
        """
        For a list of items return the top N most frequent retaining the original item-order.
        """
        ## top N most frequent items
        most_frequent_dist = Counter(items).most_common(top_n)
        logging.info("Most %d frequent: %s", top_n, list(most_frequent_dist))

        ## get just the names
        most_frequent_names = [item for item, _ in most_frequent_dist]

        ## list of the top N most frequent items but in the order they were seen
        items_chronologically = []
        for item in items:
            if item in most_frequent_names and item not in items_chronologically:
                items_chronologically.append(item)
            if len(items_chronologically) >= top_n:
                break
        return items_chronologically

    @staticmethod
    def names_to_rulepatterns(names: list):
        """
        Translate a list of names into Spacey NER EntityRuler patterns.
        """
        patterns = []
        for name in names:
            name = name.strip()
            if name:
                patterns.append({'label': 'PERSON', 'pattern': name})
        return patterns

    @staticmethod
    def get_person_names(text, ner_names: set = None, stopwords: set = None):
        """
        Using NLP find all PERSON named-entities in the given *text*.
        Additional NER rules can be given by *ner_names*.
        Names to ignore can be given by *stopwords*.
        """
        if ner_names is None:
            ner_names = []
        if stopwords is None:
            stopwords = []

        ## convert to lowercase
        stopwords_lower = [word.lower() for word in stopwords]

        ## load Spacy models, i.e., tokenizer, tagger, parser, NER and word vectors
        ## `python -m spacy download en_core_web_sm`
        logging.info("Spacy: %s", spacy.cli_info(silent=True))
        try:
            nlp = spacy.load(SPACY_LANGUAGE_MODEL)
        except IOError:
            spacy.cli.download(SPACY_LANGUAGE_MODEL)
            nlp = spacy.load(SPACY_LANGUAGE_MODEL)

        logging.info("NLP model: %s", nlp.meta['name'])

        ## additional names for NER
        if ner_names:
            ## spaces need to be replaced because of tokenization
            ner_names_sub = [word.replace(' ', '_') for word in ner_names]
            text = Charactergraph.replace_space_underscore_fornames(text, ner_names)
            ## extra NER rules
            ruler = spacy.pipeline.EntityRuler(nlp)
            patterns = Charactergraph.names_to_rulepatterns(ner_names_sub)
            ruler.add_patterns(patterns)
            nlp.add_pipe(ruler, before='ner')

        ## segment the text because spacey.nlp accepts max. 100000 bytes only
        segment_size = 100000
        logging.info("Partition book text into segments of size %d ...", segment_size)
        segments = Charactergraph.segment_text(text, segment_size)

        ## find all person names which are not in the stoplist
        names = []
        for i, segment in enumerate(segments):
            logging.debug("NLP for book segment %d/%d...", i + 1, ceil(len(text) / float(segment_size)))
            doc = nlp(segment)
            names += [ent.text for ent in doc.ents if
                      ent.label_ == 'PERSON' and ent.text.lower() not in stopwords_lower]

        return names

    def _read_ebook(self):
        return epub.read_epub(self.filepath)

    def _process(self):
        logging.debug("Reading e-book as plain text...")
        text = Charactergraph.get_ebook_text(self.book)

        logging.info("Tokenization...")
        self._tokens = nltk.word_tokenize(text)

        logging.info("Preprocessing text...")
        text = Charactergraph.replace_space_underscore_fornames(text, self.ner_names)

        logging.info("Using NLP, getting person names...")
        self._names = Charactergraph.get_person_names(text, ner_names=self.ner_names, stopwords=self.stopwords)

    def plot(self, top_n: int):
        """
        Charactergram plotting.
        :param top_n: n-th most frequent characters / persons
        """
        if not self._tokens or not self._names:
            self._process()
        most_frequent_names = Charactergraph.get_most_frequent_items_inorder(self._names, top_n)
        nltk.draw.dispersion_plot(self._tokens, most_frequent_names, title=self.book.title)

    def savefig(self, output_filename: str, top_n: int):
        """
        Charactergram plotting into output file.
        :param output_filename: output file name and path
        :param top_n: n-th most frequent characters / persons
        """
        ## configure matplotlib to not show the picture
        ## https://stackoverflow.com/questions/15713279/calling-pylab-savefig-without-display-in-ipython
        import matplotlib  # pylint: disable=import-outside-toplevel
        matplotlib.use('Agg')
        plt.ioff()
        plt.rcParams["figure.figsize"] = (20, 10)
        plt.figure()
        self.plot(top_n)
        plt.savefig(output_filename, bbox_inches='tight')


def main():
    """
    Main entry point.
    :return: exit code/return code
    """
    arguments = docopt(__doc__, version="Charactergram %s (%s)" % (__version__, __updated__))
    # print(arguments)

    filepath_arg = arguments['<ebook.epub>']
    output_arg = arguments['--output']
    ner_arg = arguments['--ner']
    stopwords_arg = arguments['--stop']
    n_arg = int(arguments['--number'])
    assert n_arg > 1, 'Number must be > 1!'

    ## setup logging
    logging.basicConfig(level=logging.INFO if not DEBUG else logging.DEBUG,
                        format='%(asctime)s %(levelname)-8s %(name)-10s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S'
                        )

    if arguments['--verbose']:
        logging.getLogger('').setLevel(logging.DEBUG)
        logging.getLogger('matplotlib').setLevel(logging.INFO)

    cgram = Charactergraph(filepath_arg,
                           ner_names_file=ner_arg,
                           stopwords_file=stopwords_arg,
                           stopwords_ignore_case=True)

    if output_arg:
        cgram.savefig(output_arg, n_arg)
    else:
        cgram.plot(n_arg)

    return 0


if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-v")
    if TESTRUN:
        import doctest

        doctest.testmod()
    if PROFILE:
        # pylint: disable=invalid-name,import-outside-toplevel
        import cProfile
        import pstats
        profile_filename = __file__ + '.profile.bin'
        cProfile.run('main()', profile_filename)
        with open("%s.txt" % profile_filename, "wb") as statsfp:
            p = pstats.Stats(profile_filename, stream=statsfp)
            stats = p.strip_dirs().sort_stats('cumulative')
            stats.print_stats()
        sys.exit(0)
    sys.exit(main())
