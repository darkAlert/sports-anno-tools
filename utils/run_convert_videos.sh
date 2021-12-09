#!/bin/bash

# Convert all videos in the folder:
SRC_VIDEO_DIR=/media/darkalert/c02b53af-522d-40c5-b824-80dfb9a11dbb/sota/football/raw_video
DST_VIDEO_DIR=/media/darkalert/c02b53af-522d-40c5-b824-80dfb9a11dbb/sota/football/video
python3 ./utils/convert_videos.py $SRC_VIDEO_DIR $DST_VIDEO_DIR


## Convert a specific video:
#GAME='game1'
#python3 ./utils/convert_videos.py $SRC_VIDEO_DIR/$GAME $DST_VIDEO_DIR/$GAME
