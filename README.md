wtpa2-python
============

python implementation of the WTPA2 sample packer/extractor

Commands take the form of ``python wtpa2.py COMMAND ARGUMENTS``

Currently supported commands:

* **pack** - create a WTPA2 readable binary file from a list of AIFF files and directories
* **extract** - extract all samples from a WTPA2 formatted binary file or raw device to a target directory. An optional argument can be supplied to limit the number of sample slots examined

Usage
====

Here are some example uses:

    python wtpa2.py pack samples.bin file1.aiff dir1/ dir2/ file2.aiff
    python wtpa2.py extract samples.bin samples/
    python wtpa2.py extract --slots 8 /dev/sdc samples/

