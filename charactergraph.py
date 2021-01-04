#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
  -n --number=N    Number of characters (y-axis) [default: 25]
  -o --output=file Output file. If not specified then use GUI to display.
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
import sys
from codecs import open

import ebooklib
import matplotlib.pyplot as plt
import nltk
from bs4 import BeautifulSoup
from docopt import docopt
from ebooklib import epub
from nltk import FreqDist

__version__ = "1.0.0"
__date__ = "2021-01-04"
__updated__ = "2021-01-04"
__author__ = "Ixtalo"
__email__ = "ixtalo@gmail.com"
__license__ = "AGPL-3.0+"
__status__ = "Production"

DEBUG = 0
TESTRUN = 0
PROFILE = 0
__script_dir = os.path.dirname(os.path.realpath(__file__))

## check for Python3
if sys.version_info < (3, 0):
    sys.stderr.write("Minimum required version is Python 3.x!\n")
    sys.exit(1)


class Charactergraph:
    """
    Build a 'charactergraph' or 'charactermeter' which records the 'activity' of
    all persons/characters in the novel and outputs a 'charactergram'.
    """
    __tokens = None

    def __init__(self, filepath):
        """
        Charactergraph for the given e-book file.
        :param filepath: EPUB e-book file
        """
        self.filepath = filepath
        self.book = self.__read()

    def __read(self):
        return epub.read_epub(self.filepath)

    @staticmethod
    def tokenize_book(book):
        """
        Word-punkt tokenization.
        :param book: ebooklib book object
        :return: tokenized book, listed of words
        """
        tokens = []
        chapters = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        for i, item in enumerate(chapters):
            logging.debug("Processing chapter item %d/%d ...", i, len(chapters))

            bs = BeautifulSoup(item.content, features='lxml')
            ## skip non-chapters
            if len(bs.text) < 3000:
                logging.debug("Skipping too-small chapter item (%d).", len(bs.text))
                continue

            tokens += nltk.word_tokenize(bs.text)

        logging.debug("#%d tokens.", len(tokens))
        return tokens

    def __get_tokens(self):
        if not self.__tokens:
            assert self.book
            self.__tokens = self.tokenize_book(self.book)
        return self.__tokens

    def plot(self, n=25):
        """
        Charactergram plotting.
        :param n: n-th most common characters/persons
        :return: frequency distribution for all persons/character names
        """
        logging.info("Tokenization...")
        tokens = self.__get_tokens()
        assert tokens, "tokens must not be None!"
        logging.info("POS tagging (could take long)...")
        tagged = nltk.pos_tag(tokens)
        logging.info("NE chunking (could take *very* long!)...")
        entities = nltk.chunk.ne_chunk(tagged)

        logging.info("Person/character name frequencies...")
        names = []
        for tag, ne_name in entities.pos():
            if ne_name == 'PERSON':
                person = tag[0]
                names.append(person)

        ## frequency distribution for all persons/character names
        characters_fdist = FreqDist(names)

        ## the top N most frequent names
        most_common_names = [name for name, _ in characters_fdist.most_common(n)]

        ## list of the top N most frequrent names but in the order they were seen
        names_chronologically = []
        for name in names:
            if name in most_common_names and name not in names_chronologically:
                names_chronologically.append(name)
            if len(names_chronologically) >= n:
                break

        logging.info("Matplotlib NTLK dispersion plot...")
        nltk.draw.dispersion_plot(tokens, names_chronologically, title=self.book.title)
        return characters_fdist

    def savefig(self, outputfilename, n=25):
        """
        Charactergram plotting into output file.
        :param outputfilename: output file name and path
        :param n: n-th most common characters/persons
        :return: frequency distribution for all persons/character names
        """
        ## https://stackoverflow.com/questions/15713279/calling-pylab-savefig-without-display-in-ipython
        import matplotlib
        matplotlib.use('Agg')
        plt.ioff()
        plt.rcParams["figure.figsize"] = (20, 10)
        plt.figure()
        res = self.plot(n)
        plt.savefig(outputfilename, bbox_inches='tight')
        return res


def main():
    arguments = docopt(__doc__, version="Charactergram %s (%s)" % (__version__, __updated__))
    #print(arguments)

    filepath_arg = arguments['<ebook.epub>']
    output_arg = arguments['--output']
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

    cg = Charactergraph(filepath_arg)
    if output_arg:
        cg.savefig(output_arg, n_arg)
    else:
        cg.plot(n_arg)

    return 0


if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-v")
        # sys.argv.append("--debug")
        # sys.argv.append("-h")
        pass
    if TESTRUN:
        import doctest

        doctest.testmod()
    if PROFILE:
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
