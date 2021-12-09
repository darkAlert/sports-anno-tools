#!/bin/bash

VIDEO_DIR=/media/darkalert/c02b53af-522d-40c5-b824-80dfb9a11dbb/sota/football/video
FRAMES_DIR=/media/darkalert/c02b53af-522d-40c5-b824-80dfb9a11dbb/sota/football/manual_annotation/07-09-2021/frames

video2frame () {
    game=$1
    start_time=$2
    stop_time=$3
    target_num_frames=$4

    # Calculate FPS based on the target number of frames:
    start_sec=$(date --date $start_time +%s)
    stop_sec=$(date --date $stop_time +%s)
    delta=$((stop_sec - start_sec))
    fps=$(echo "$target_num_frames/$delta" | bc -l)

    src_path=$VIDEO_DIR/$game/$game.mp4
    dst_dir=$FRAMES_DIR/$game
    mkdir $dst_dir
    yes | ffmpeg -i $src_path -r $fps -ss $start_time -to $stop_time -qscale:v 2 $dst_dir/img-%5d.jpeg
}

## Convert (Dinamo Mol):
#video2frame VTB_mol_Ahmat_at_Dinamo 00:11:35.0 02:02:00.0 125
#video2frame VTB_mol_Arsenal_at_Dinamo 00:14:28.0 02:07:28.0 125
#video2frame VTB_mol_KrylyaSovetov_at_Dinamo 00:16:18.0 02:07:41.0 125
#video2frame VTB_mol_Rotor_at_Dinamo 00:14:37.0 02:08:04.0 125
#video2frame VTB_mol_Spartak_at_Dinamo 00:10:33.0 02:05:21.0 125
#video2frame VTB_mol_AkademiyaKonopleva_at_Dinamo 00:14:41.0 02:10:07.0 125
#video2frame VTB_mol_Chertanovo_at_Dinamo 00:12:00.0 01:59:22.0 125

# Convert:
#video2frame BC_DinamoMh_at_SPA 00:00:15.0 01:38:21.0 125
#video2frame FNL_Alaniya2_at_DinamoMh 00:00:07.0 01:35:17.0 125
#video2frame FNL_DinamoMh_at_Tuapse 00:00:05.0 01:32:33.0 125
#video2frame FNL_KubanKholding_at_DinamoMh 00:00:05.0 01:39:31.0 125
#video2frame FNL_Rotor2_at_DinamoMh 00:00:05.0 01:33:52.0 125
#video2frame PFL_MashukKMV_at_DinamoMh 00:00:03.0 01:34:08.0 125
video2frame RPL_Dinamo_at_Ural 00:00:01.0 01:37:09.0 150
video2frame RPL_CSKA_at_Dinamo 00:00:07.0 01:38:27.0 150
#video2frame FNL_Druzhba_at_DinamoMh 00:00:06.0 01:36:47.0 125



