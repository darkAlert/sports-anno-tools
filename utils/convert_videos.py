import argparse
import os
import subprocess
from datetime import datetime
from subprocess import check_output
import json


TEMPLATE_FILE_SUFFIX = '_template.txt'
MAX_VIDEO_BITRATE = 3500000
TARGET_VIDEO_HEIGHT = 720


def change_ext(name, new_ext):
    name = '.'.join(name.split('.')[:-1])
    return name + new_ext


def get_video_info(src, verbose=False):
    cmd = 'ffprobe -loglevel 0 -print_format json -show_format -show_streams ' + src
    out = check_output(cmd.split()).decode("utf-8")
    info = json.loads(out)
    if verbose:
        print (out)

    return info


def run_ffmpeg(src, dst, params):
    if src is not None:
        cmd = ['ffmpeg', '-i', src]
    else:
        cmd = ['ffmpeg']
    params = params.split()
    if len(params):
        cmd += params
    cmd += [dst]
    print(' '.join(cmd))
    subprocess.Popen(cmd).wait()


def run_video_concat_with_ffmpeg(src_files, dst_file, target_fps=None, preset='medium', scale_720=False, max_bitrate=None):
    # convert to temp files of same parameters
    temp_names = []
    for i, name in enumerate(src_files):
        temp_name = "temp{}.mp4".format(i+1)
        run_video_with_ffmpeg(name, temp_name, target_fps=target_fps, preset=preset, scale_720=scale_720, max_bitrate=max_bitrate)
        temp_names.append(temp_name)

    # make temporary concat.txt for merging clips
    file = open("concat.txt", "w")
    for name in temp_names:
        file.write('file ' + name + '\n')
    file.close()

    # convert to a single file
    params = "-f concat -safe 0 -i concat.txt -c copy"
    run_ffmpeg(None, dst_file, params)

    # remove temp files
    for name in temp_names:
        os.remove(name)
    os.remove("concat.txt")


def run_video_with_ffmpeg(src_file, dst_file, target_fps=None, preset='medium', scale_720=False, max_bitrate=None):
    '''
    :param src_file:   Source video path
    :param dst_file:   Destination video path
    :param target_fps: Target FPS
    :param preset:     Encoding speed (ultrafast, superfast, veryfast, faster, fast,
                                       medium (the default), slow, slower, veryslow)
    :param scale_720:  Scale to 720 pixels in height, and automatically choose width

    see more: https://askubuntu.com/questions/352920/fastest-way-to-convert-videos-batch-or-single
    '''
    if max_bitrate is None:
        max_bitrate = MAX_VIDEO_BITRATE

    info = get_video_info(src_file)

    # Get container info:
    format = info['format']['format_name']

    # Get video codec info:
    v_codec, v_start_time, v_bit_rate, v_pix_fmt, v_height = None, None, None, None, None
    for stream in info['streams']:
        codec_type = stream['codec_type']
        if codec_type == 'video':
            v_codec = stream['codec_name'] if 'codec_name' in stream else None
            v_pix_fmt = stream['pix_fmt'] if 'pix_fmt' in stream else None
            if 'bit_rate' in stream and stream['bit_rate'] is not None:
                v_bit_rate = int(stream['bit_rate'])
            if 'start_time' in stream and stream['start_time'] is not None:
                v_start_time = float(stream['start_time'])
            if 'height' in stream and stream['height'] is not None:
                v_height = int(stream['height'])
    assert v_codec is not None, 'Video codec not found!'

    # Get audio codec info:
    a_codec = None
    for stream in info['streams']:
        codec_type = stream['codec_type']
        if codec_type == 'audio':
            a_codec = stream['codec_name'] if 'codec_name' in stream else None

    # Generate params:
    params, filters = '', ''

    # Required video filters:
    if v_pix_fmt is None or v_pix_fmt != 'yuv420p':
        filters += 'format=yuv420p'
    if target_fps is not None:
        filters += ',fps=' + str(target_fps) if len(filters) > 0 else 'fps=' + str(target_fps)
    if scale_720 and (v_height is None or v_height != TARGET_VIDEO_HEIGHT):
        filters += ',scale=-2:720' if len(filters) > 0 else 'scale=-2:720'
    if len(filters) > 0:
        filters = ' -vf {}'.format(filters)

    # Re-encoding video params:
    if  len(filters) > 0:
        params += ' -codec:v libx264' + filters
    elif 'h264' not in v_codec:
        params += ' -codec:v libx264'
    elif v_bit_rate is None or v_bit_rate > max_bitrate:
        params += ' -codec:v libx264'
    elif v_start_time is not None and v_start_time != 0:
        params += ' -codec:v libx264'
    else:
        params += ' -c:v copy'

    # Re-encoding audio params:
    if a_codec is None:
        params += ' -an'
    else:
        params += ' -bsf:a aac_adtstoasc'

    # Encoding speed:
    if preset != 'medium':
        params += ' -preset {}'.format(preset)

    # Run ffmpeg:
    run_ffmpeg(src_file, dst_file, params)


def sort_by_name(names):
    sorted_names = {}
    for name in names:
        base_name = name.split('__')[0]
        num = int(name.split('__')[-1].split('.')[0])
        if base_name not in sorted_names:
            sorted_names[base_name] = {}
        sorted_names[base_name][num] = name
    sorted_sorted_names = {}
    for unique, files in sorted_names.items():
        sorted_files = [files[key] for key in sorted(files.keys())]
        sorted_sorted_names[unique] = sorted_files
    return sorted_sorted_names


def main(src_folder, dst_folder, preset='medium', max_bitrate=None, scale_720=False, dst_format='.mp4'):

    start_time = datetime.now()

    src_files = [f for f in os.listdir(src_folder)
                 if not f.endswith(TEMPLATE_FILE_SUFFIX)]

    single_src_files = [name for name in src_files if '__' not in name]
    multiple_files = sort_by_name([name for name in src_files if '__' in name])

    if not os.path.exists(dst_folder):
        os.makedirs(dst_folder)

    results = []
    # convert single file games
    for name in single_src_files:
        src = os.path.join(src_folder, name)
        dst = os.path.join(dst_folder, change_ext(name, dst_format))
        dst = dst.replace('_orig', '')
        run_video_with_ffmpeg(src, dst, preset=preset, scale_720=scale_720, max_bitrate=max_bitrate)
        results.append(dst)

    # convert games recorded in multiple files
    for base_name, sources in multiple_files.items():
        sources = [os.path.join(src_folder, name) for name in sources]
        dst = os.path.join(dst_folder, base_name + dst_format)
        dst = dst.replace('_orig', '')
        run_video_concat_with_ffmpeg(sources, dst, preset=preset, scale_720=scale_720, max_bitrate=max_bitrate)
        results.append(dst)

    end_time = datetime.now()
    print(f'Time elapsed: {end_time - start_time}')


def parse_args():
    parser = argparse.ArgumentParser("Tool to run source video(-s) with ffmpeg based converter")
    parser.add_argument('source_video_folder',
                        help='Folder with source video(-s)')
    parser.add_argument('destination_video_folder',
                        help='Folder where to save resulting video file(-s)')
    parser.add_argument('-s720', '--scale_720', action='store_true', default=True,
                        help='Scale to 720 pixels in height, and automatically choose width')
    parser.add_argument('-b', '--max_bitrate', type=int, default=MAX_VIDEO_BITRATE,
                        help='Max video bitrate above which re-encoding will be performed')
    parser.add_argument('-p', '--preset', type=str, default='medium',
                        help='Encoding speed (see run_video_with_ffmpeg() function for details)')
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args.source_video_folder, args.destination_video_folder,
         preset=args.preset, max_bitrate=args.max_bitrate, scale_720=args.scale_720)