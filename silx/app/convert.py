# coding: utf-8
# /*##########################################################################
# Copyright (C) 2017 European Synchrotron Radiation Facility
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# ############################################################################*/
"""Convert silx supported data files into HDF5 files"""

import ast
import os
import argparse
from glob import glob
import logging
import numpy
import re
import time

import silx.io.fabioh5


__authors__ = ["P. Knobel"]
__license__ = "MIT"
__date__ = "12/09/2017"


_logger = logging.getLogger(__name__)
"""Module logger"""


def c_format_string_to_re(pattern_string):
    """

    :param pattern_string: C style format string with integer patterns
        (e.g. "%d", "%04d").
        Not supported: fixed length padded with whitespaces (e.g "%4d", "%-4d")
    :return: Equivalent regular expression (e.g. "\d+", "\d{4}")
    """
    # escape dots
    pattern_string = pattern_string.replace(".", "\.")

    # %d
    pattern_string = pattern_string.replace("%d", "[-+]?\d+")

    # %0nd
    for sub_pattern in re.findall("%0\d+d", pattern_string):
        print(sub_pattern)
        n = int(re.search("%0(\d+)d", sub_pattern).group(1))
        if n == 1:
            re_sub_pattern = "[+-]?\d"
        else:
            re_sub_pattern = "[\d+-]\d{%d}" % (n - 1)
        pattern_string = pattern_string.replace(sub_pattern, re_sub_pattern, 1)

    # add EOL ($)
    return pattern_string + "$"


def main(argv):
    """
    Main function to launch the converter as an application

    :param argv: Command line arguments
    :returns: exit status
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'input_files',
        nargs="*",
        help='Input files (EDF, SPEC).')
    # input_files and --filepattern are mutually exclusive
    parser.add_argument(
        '--file-pattern',
        help='File name pattern for loading a series of indexed files'
             '(toto_%%04d.edf). Incompatible with argument input_files')
    parser.add_argument(
        '-o', '--output-uri',
        default=time.strftime("%Y%m%d-%H%M%S") + '.h5',
        help='Output file name (HDF5). An URI can be provided to write'
             ' the data into a specific group in the output file: '
             '/path/to/file::/path/to/group. '
             'By default, the filename uses the current date and time:'
             ' YYYYmmdd-HHMMSS.h5')
    parser.add_argument(
        '-m', '--mode',
        default="w-",
        help='Write mode: "r+" (read/write, file must exist), '
             '"w" (write, existing file is lost), '
             '"w-" (write, fail if file exists) or '
             '"a" (read/write if exists, create otherwise)')
    parser.add_argument(
        '--no-root-group',
        action="store_true",
        help='This option disables the default behavior of creating a '
             'root group (entry) for each file to be converted. When '
             'merging multiple input files, this can cause conflicts '
             'when datasets have the same name (see --overwrite-data). '
             'This option has no effect when using --file-pattern.')
    parser.add_argument(
        '--overwrite-data',
        action="store_true",
        help='If the output path exists and an input dataset has the same'
             ' name as an existing output dataset, overwrite the output '
             'dataset (in modes "r+" or "a").')
    parser.add_argument(
        '--min-size',
        type=int,
        default=500,
        help='Minimum number of elements required to be in a dataset to '
             'apply compression or chunking (default 500).')
    parser.add_argument(
        '--chunks',
        nargs="?",
        const="auto",
        help='Chunk shape. Provide an argument that evaluates as a python '
             'tuple (e.g. "(1024, 768)"). If this option is provided without '
             'specifying an argument, the h5py library will guess a chunk for '
             'you. Note that if you specify an explicit chunking shape, it '
             'will be applied identically to all datasets with a large enough '
             'size (see --min-size). ')
    parser.add_argument(
        '--compression',
        nargs="?",
        const="gzip",
        help='Compression filter. By default, the datasets in the output '
             'file are not compressed. If this option is specified without '
             'argument, the GZIP compression is used. Additional compression '
             'filters may be available, depending on your HDF5 installation.')

    def check_gzip_compression_opts(value):
        ivalue = int(value)
        if ivalue < 0 or ivalue > 9:
            raise argparse.ArgumentTypeError(
                "--compression-opts must be an int from 0 to 9")
        return ivalue

    parser.add_argument(
        '--compression-opts',
        type=check_gzip_compression_opts,
        help='Compression options. For "gzip", this may be an integer from '
             '0 to 9, with a default of 4. This is only supported for GZIP.')
    parser.add_argument(
        '--shuffle',
        action="store_true",
        help='Enables the byte shuffle filter, may improve the compression '
             'ratio for block oriented compressors like GZIP or LZF.')
    parser.add_argument(
        '--fletcher32',
        action="store_true",
        help='Adds a checksum to each chunk to detect data corruption.')
    parser.add_argument(
        '--debug',
        action="store_true",
        default=False,
        help='Set logging system in debug mode')

    options = parser.parse_args(argv[1:])

    if options.debug:
        logging.root.setLevel(logging.DEBUG)

    # Import after parsing --debug
    try:
        # it should be loaded before h5py
        import hdf5plugin  # noqa
    except ImportError:
        _logger.debug("Backtrace", exc_info=True)
        hdf5plugin = None

    try:
        import h5py
        from silx.io.convert import write_to_h5
    except ImportError:
        _logger.debug("Backtrace", exc_info=True)
        h5py = None
        write_to_h5 = None

    if h5py is None:
        message = "Module 'h5py' is not installed but is mandatory."\
            + " You can install it using \"pip install h5py\"."
        _logger.error(message)
        return -1

    if hdf5plugin is None:
        message = "Module 'hdf5plugin' is not installed. It supports additional hdf5"\
            + " compressions. You can install it using \"pip install hdf5plugin\"."
        _logger.debug(message)

    # Process input arguments (mutually exclusive arguments)
    if bool(options.input_files) == bool(options.file_pattern is not None):
        if not options.input_files:
            message = "You must specify either input files (at least one), "
            message += "or a file pattern."
        else:
            message = "You cannot specify input files and a file pattern"
            message += " at the same time."
        _logger.error(message)
        return -1
    elif options.input_files:
        # some shells (windows) don't interpret wildcard characters (*, ?, [])
        old_input_list = list(options.input_files)
        options.input_files = []
        for fname in old_input_list:
            globbed_files = glob(fname)
            if not globbed_files:
                # no files found, keep the name as it is, to raise an error later
                options.input_files += [fname]
            else:
                options.input_files += globbed_files
    else:
        # File series
        dirname = os.path.dirname(options.file_pattern)
        file_pattern_re = c_format_string_to_re(options.file_pattern)
        files_in_dir = glob(os.path.join(dirname, "*"))
        matching_files_in_dir = list(filter(lambda name: re.match(file_pattern_re, name),
                                            files_in_dir))
        _logger.debug("""
            Processing file_pattern
            dirname: %s
            file_pattern_re: %s
            files_in_dir: %s
            matching_files_in_dir: %s
            """, dirname, file_pattern_re, files_in_dir, matching_files_in_dir)
        if not matching_files_in_dir:
            _logger.error("No file matching --file-pattern found.")
            return -1
        options.input_files = sorted(matching_files_in_dir)

    # Test that the output path is writeable
    if "::" in options.output_uri:
        output_name, hdf5_path = options.output_uri.split("::")
    else:
        output_name, hdf5_path = options.output_uri, "/"

    if os.path.isfile(output_name):
        if options.mode == "w-":
            _logger.error("Output file %s exists and mode is 'w-'"
                          " (write, file must not exist). Aborting.",
                          output_name)
            return -1
        elif not os.access(output_name, os.W_OK):
            _logger.error("Output file %s exists and is not writeable.",
                          output_name)
            return -1
        elif options.mode == "w":
            _logger.info("Output file %s exists and mode is 'w'. "
                         "Overwriting existing file.", output_name)
        elif options.mode in ["a", "r+"]:
            _logger.info("Appending data to existing file %s.",
                         output_name)
    else:
        if options.mode == "r+":
            _logger.error("Output file %s does not exist and mode is 'r+'"
                          " (append, file must exist). Aborting.",
                          output_name)
            return -1
        else:
            _logger.info("Creating new output file %s.",
                         output_name)

    # Test that all input files exist and are readable
    bad_input = False
    for fname in options.input_files:
        if not os.access(fname, os.R_OK):
            _logger.error("Cannot read input file %s.",
                          fname)
            bad_input = True
    if bad_input:
        _logger.error("Aborting.")
        return -1

    # create_dataset special args
    create_dataset_args = {}
    if options.chunks is not None:
        if options.chunks.lower() in ["auto", "true"]:
            create_dataset_args["chunks"] = True
        else:
            try:
                chunks = ast.literal_eval(options.chunks)
            except (ValueError, SyntaxError):
                _logger.error("Invalid --chunks argument %s", options.chunks)
                return -1
            if not isinstance(chunks, (tuple, list)):
                _logger.error("--chunks argument str does not evaluate to a tuple")
                return -1
            else:
                nitems = numpy.prod(chunks)
                nbytes = nitems * 8
                if nbytes > 10**6:
                    _logger.warning("Requested chunk size might be larger than"
                                    " the default 1MB chunk cache, for float64"
                                    " data. This can dramatically affect I/O "
                                    "performances.")
                create_dataset_args["chunks"] = chunks

    if options.compression is not None:
        create_dataset_args["compression"] = options.compression

    if options.compression_opts is not None:
        create_dataset_args["compression_opts"] = options.compression_opts

    if options.shuffle:
        create_dataset_args["shuffle"] = True

    if options.fletcher32:
        create_dataset_args["fletcher32"] = True

    with h5py.File(output_name, mode=options.mode) as h5f:
        if options.file_pattern is not None:
            # File series
            input_group = silx.io.fabioh5.File(file_series=options.input_files)
            if hdf5_path != "/":
                # we want to append only data and headers to an existing file
                input_group = input_group["/scan_0/instrument/detector_0"]
            write_to_h5(input_group, h5f,
                        h5path=hdf5_path,
                        overwrite_data=options.overwrite_data,
                        create_dataset_args=create_dataset_args,
                        min_size=options.min_size)

        else:
            # single file or unrelated files
            for input_name in options.input_files:
                hdf5_path_for_file = hdf5_path
                if not options.no_root_group:
                    hdf5_path_for_file = hdf5_path.rstrip("/") + "/" + os.path.basename(input_name)
                write_to_h5(input_name, h5f,
                            h5path=hdf5_path_for_file,
                            overwrite_data=options.overwrite_data,
                            create_dataset_args=create_dataset_args,
                            min_size=options.min_size)

        # append the convert command to the creator attribute, for NeXus files
        creator = h5f.attrs.get("creator", b"").decode()
        convert_command = " ".join(argv)
        if convert_command not in creator:
            h5f.attrs["creator"] = \
                numpy.string_(creator + "; convert command: %s" % " ".join(argv))

    return 0
