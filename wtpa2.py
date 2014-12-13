import argparse
import os
import aifc
import struct
import stat
import platform

class WTPA2:
	r"""WTPA2 Sample Packer/Unpacker
	"""

	def __init__(self):
		r"""Initialize the WTPA2 object
		"""
		self.num_samples = 0
		self.toc_offset = 16
		self.header = bytearray(512)

	def pack(self, outfile, infiles):
		r""" Pack AIFF samples into the WTPA2 format.

		outfile is the file to be written. infiles is a list of files and 
		directories to process for AIFFs in the proper format.
		"""
		self.header[0:3] = "WTPA"
		self.header[4:7] = "SAMP"
		self.outfile = open(outfile, "wb")
		self.outfile.seek(512)
		
		for infile in infiles:
			if os.path.exists(infile):
				if os.path.isdir(infile):
					self.process_dir(infile)
				else:
					self.process_file(infile)
			else:
				print("{} does not exist, skipping...".format(infile))

		self.outfile.seek(0)
		self.outfile.write(self.header)
		self.outfile.close()

	def unpack(self, src, dest, samples=512):
		r""" Extract samples from the provided file/device.

		The src parameter is a binary file or device to attempt to extract 
		samples from. dest is a directory where any extracted samples 
		will be written. samples is an optional argument to limit the number 
		of slots to examine (default is to look at all of them).
		"""
		if not os.path.exists(src):
			print("ERROR: {} does not exist.".format(src))
			src = ""
		elif os.path.isfile(src):
			print("Reading from file {}.".format(src))
		else:
			if platform.system() == "Windows":
				if len(src) == 2 and os.path.isdir(src):
					src = "\\\\.\\" + src
					print("Reading from drive {}.".format(src))
				else:
					print("ERROR: {} is not a drive.".format(src))
					src = ""
			elif platform.system() == "Darwin" or platform.system() == "Linux":
				mode = os.stat(src).st_mode
				if stat.S_ISBLK(mode):
					print("Reading from device {}.".format(src))
				else:
					print("ERROR: {} is not a device".format(src))
					src = ""

		if not os.path.exists(dest):
			try:
				os.makedirs(dest)
			except OSError:
				print("ERROR: Creating directory {} failed.".format(dest))
				dest = ""
				pass
		elif not os.path.isdir(dest):
			print("ERROR: {} exists, but is not a directory.".format(dest))
			dest = ""

		if not (src == "" or dest == ""):
			self.outfile = open(src, "rb")
			self.header = self.outfile.read(512)

			if self.header[0:4] != "WTPA":
				print("ERROR: WTPA data not found.")
			elif self.header[4:8] != "SAMP":
				print("ERROR: WTPA Sample data not found.")
			else:
				for x in range(0, samples):
					if self.sample_in_slot(x):
						self.seek_to_slot(x)
						
						f = os.path.join(dest, "%03d.aiff" % (x))
						size = struct.unpack('>I', self.outfile.read(4))

						print("Writing Sample from slot {} to {}.".format(x, f))

						s = aifc.open(f, "w")
						s.aiff()
						s.setnchannels(1)
						s.setsampwidth(1)
						s.setframerate(22050)
						s.setnframes(size[0])
						s.writeframes(self.outfile.read(size[0]))
						s.close()

			self.outfile.close()

	def seek_to_slot(self, slot):
		r""" Seeks to the target slot in current file/device being processed.
		"""
		self.outfile.seek(512)
		self.outfile.seek(((512*1024)*slot),  1)

	def sample_in_slot(self, slot):
		r""" Returns true if the header indicates a sample is present in the target slot.
		"""
		if ord(self.header[self.toc_offset  + (slot/8)]) & (1 << slot):
			return True
		else:
			return False


	def process_dir(self, path):
		r""" Process a directory passed to the pack function.

		Any files found in the target directory will be processed first, in 
		alphabetical order. Any sub-directories will then be processed, also 
		in alphabetical order.
		"""
		print("Processing directory {}...".format(path))
		files = [ f for f in os.listdir(path) if os.path.isfile(os.path.join(path,f)) ]
		dirs  = [ f for f in os.listdir(path) if os.path.isdir(os.path.join(path,f)) ]

		files.sort()
		dirs.sort()

		for f in files:
			self.process_file(os.path.join(path,f))

		for d in dirs:
			self.process_dir(os.path.join(path,d))

	def process_file(self, path):
		r""" Process a file to be packed.

		A file is packed only if it is an AIFF with the following properties:
			- sample width of 1 byte (8 bits)
			- mono
			- less than 512K
		An AIFF with an non-recommended sample rate is still packed, but a 
		warning is displayed.
		"""
		print("Processing file {}...".format(path))

		try:
			s = aifc.open(path)

			if s.getsampwidth() != 1:
				print("    SKIPPED: Sample width = {}, should be 1.".format(s.getsampwidth()))
			elif s.getnchannels() != 1:
				print("    SKIPPED: Number of channels = {}, should be 1.".format(s.getnchannels()))
			elif s.getnframes() > 512*1024:
				print("    SKIPPED: Sample too long, length = {}, max is {}.".format(s.getnframes(), 512*1024))
			else:
				if s.getframerate() != 22050:
					print("    WARNING: Incorrect sample rate, rate = {} target is 22050".format(s.getframerate()))

				print("    OK: Wrote sample to slot {}".format(self.num_samples))

				self.header[self.toc_offset + ((self.num_samples)/8)] |= (1 << (self.num_samples%8))
				self.num_samples+=1

				self.outfile.write(struct.pack('>I', s.getnframes()))
				self.outfile.write(s.readframes(s.getnframes()))
				self.outfile.seek(512*1024 - s.getnframes() - 4, 1)
		
			s.close()
		except aifc.Error:
			print("    SKIPPED: Not an AIFF".format(path))
			pass


def slot_type(x):
    x = int(x)
    if x <= 0 or x > 512:
        raise argparse.ArgumentTypeError("Valid slot range 1 - 512")
    return x

parser  = argparse.ArgumentParser(description="WTPA2 file utility. Pack/Extract samples to/from the WTPA2 format.")
sparsers = parser.add_subparsers(dest="command", title="sub-commands")

p_parser = sparsers.add_parser("pack", help="pack AIFFs into a WTPA2 readable binary file")
p_parser.add_argument("outfile", type=str, help="output file name")
p_parser.add_argument("infiles", nargs="+", type=str, help="input directories/files")

e_parser = sparsers.add_parser("extract", help="extract samples from a WTPA2 formatted binary file or device")
e_parser.add_argument("-s", "--slots", default=512, type=slot_type, help="limit sample slots read")
e_parser.add_argument("src", type=str, help="input file or path to device")
e_parser.add_argument("dest", type=str, help="output directory")

args = parser.parse_args()

wtpa = WTPA2()

if args.command == "pack":	
	wtpa.pack(args.outfile, args.infiles)
elif args.command == "extract":
	wtpa.unpack(args.src, args.dest, samples=args.slots)
