import os
import subprocess
import sys

FFMPEG_PATH = 'ffmpeg'
FILE_TO_ENCODE = 'tmp/DVS_PANDEMONIUM_TEASER_BW.mp4'
OUTPUT_PATH = 'tmp/'

ENCODE_FORMATS = {

	# VP8 encoded webm
	# crf	-- Constant Rate Factor from 4 (best quality), 10 (default) to 63 (worst quality)
	# b:v 	-- Average bit rate (no matter the CRF, the bitrate cannot surpass this value)
	'webm': {'codec': 'libvpx', 'args': ['-crf', '4', '-b:v', '1200K']},

	# H.264 encoded mp4
	# crf 	-- Constant Rate Factor from 0 (lossless), 23 (default) to 51 (worst quality)
	# b:v 	-- Average bit rate
	'mp4': {'codec': 'libx264', 'args': ['-crf', '33', '-b:v', '500k']},

	# Theora Vorbis encoded ogv
	# b:v 	-- Average bit rate
	'ogv': {'codec': 'libtheora', 'args': ['-b:v', '1M']},

}


def thumb(input_file, output_directory):
	base_name = os.path.splitext(os.path.basename(input_file))[0]
	output_file_name = '{}-frame.{}'.format(os.path.join(output_directory, base_name), 'jpg')
	args = [FFMPEG_PATH, '-ss', '2', '-i', input_file, '-vframes', '1', '-f', 'image2', output_file_name]
	try:
		subprocess.call(args)
	except OSError:
		raise ImportError("Couldn't find ffmpeg! Please make sure it's installed. See https://gist.github.com/foxxyz/626a9f58174840417905")
	return open(output_file_name, 'rb')


def encode(input_file, output_directory, formats=None):
	formats = {k: v for k, v in ENCODE_FORMATS.items() if k in formats} if formats else ENCODE_FORMATS
	base_name = os.path.splitext(os.path.basename(input_file))[0]
	try:
		for fmt, params in formats.items():
			output_file_name = os.path.join(output_directory, '{}-encoding.{}'.format(base_name, fmt))
			args = [FFMPEG_PATH, '-i', input_file, '-c:v', params['codec']] + params['args'] + ['-an', '-y', output_file_name]
			subprocess.call(args)
			# Change filename from 'encoding' to 'encoded' when finished
			os.rename(output_file_name, output_file_name.replace('encoding', 'encoded'))

	except OSError:
		raise ImportError("Couldn't find ffmpeg! Please make sure it's installed. See https://gist.github.com/foxxyz/626a9f58174840417905")


if __name__ == '__main__':
	if len(sys.argv) <= 1:
		raise ValueError('Specify the file to encode.')
	_, input_file, output_dir = sys.argv
	if not os.path.isabs(input_file):
		input_file = os.path.join(os.getcwd(), input_file)
	if not os.path.isabs(output_dir):
		output_dir = os.path.join(os.getcwd(), output_dir)
	encode(input_file, output_dir)
