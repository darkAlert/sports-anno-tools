# Sports Annotation Tools
This repository contains tools for manual data annotation by operators.

It contains the following tools:
* Sports OCR Annotating Tool
* Sports Court Mapping Tool
* [Sports Tracks Editing Tool](#sports-tracks-editing-tool)

## Installation
1. Clone the repository:
```
git clone https://github.com/darkAlert/sports-anno-tools.git
cd sports-anno-tools
```
2. Install the `virtualenv` package and create a new virtual environment variable named `sportsvirt` and then activate it:
```
pip3 install virtualenv
python3 -m venv sportsvirt
source sportsvirt/bin/activate
```
3. Install requirements:
```
pip3 install -r requirements.txt
```



# Sports Tracks Editing Tool
The tool is intended for manual editing of  predicted players tracks.
<p align="center">
<img src="boost-tracks-editing-tool.png" width=600>
</p>

## How To Use
Run the tool:
```
python3 run_tracking_tool.py --data_dir=/path/to/your/videos
```

The directory `/path/to/your/videos` has to contain the video clips to be annotated.

After data annotation is complete, the results will be saved to `/path/to/your/videos/edited_tracks.json`.

If the directory `/path/to/your/videos` already contains `edited_tracks.json`, then during the running you will be prompted to load the results from it.

## Control Keys
The following hotkeys can be used:
* `[` - go to the previous clip
* `]` - go to the next clip
* `Space` - go to the next frame of the clip
* `Backspace` - go to the previous frame of the clip
* `Enter` - autoplay / pause
* `t` - mark the frame as "True Positive" (by default)
* `f` - mark the frame as "False Positive"
* `s` - save the results to output json
* `Left Mouse Click` on the frame area - mark the new position of the player
* `Right Mouse Click` - delete the marked player position
* `Esc` - quit (you will be prompted to save the results).

