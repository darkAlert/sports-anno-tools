import os
import json


def test(anno_dir, anno_filename='manual_anno.json'):
    names = [n for n in os.listdir(anno_dir) if os.path.isdir(os.path.join(anno_dir, n))]

    time_wo_reset = {}
    time_after_reset = {}

    for game_name in names:
        game_anno_path = os.path.join(anno_dir, game_name, anno_filename)
        game_anno = json.load(open(game_anno_path, 'r'))

        time_wo_reset[game_name] = [0.0,0]
        time_after_reset[game_name] = [0.0, 0]

        for frame_id, anno in game_anno.items():
            frame_id = frame_id.split('\\')[-1]
            reset = anno['reset'] if 'reset' in anno else False
            elapsed = anno['elapsed']
            if reset:
                time_after_reset[game_name][0] += elapsed
                time_after_reset[game_name][1] += 1
            else:
                time_wo_reset[game_name][0] += elapsed
                time_wo_reset[game_name][1] += 1
            # print ('[{}] elapsed: {} sec, reset={}'.format(frame_id, elapsed, reset))

    total_time_wo_reset, total_time_after_reset = 0.0, 0.0
    total_count_wo_reset, total_count_after_reset = 0, 0
    for game_name in names:
        wo_reset = time_wo_reset[game_name]
        after_reset = time_after_reset[game_name]
        total_time_wo_reset += wo_reset[0]
        total_count_wo_reset += wo_reset[1]
        total_time_after_reset += after_reset[0]
        total_count_after_reset += after_reset[1]

        after_n = 1
        if after_reset[1] != 0:
            after_n = after_reset[1]
        wo_n = 1
        if wo_reset[1] != 0:
            wo_n = wo_reset[1]

        print ('==={}==='.format(game_name))
        print ('elapsed: {}, count: {}, mean: {}'.format(wo_reset[0], wo_reset[1],
                                                                    wo_reset[0]/wo_n))
        print('elapsed: {}, count: {}, mean: {}'.format(after_reset[0], after_reset[1],
                                                                   after_reset[0] / after_n))


    print ('Total time w/o reset: {}, total count: {}, mean time: {}'.format(total_time_wo_reset, total_count_wo_reset,
                                                                             total_time_wo_reset/total_count_wo_reset))
    print('Total time after reset: {}, total count: {}, mean time: {}'.format(total_time_after_reset, total_count_after_reset,
                                                                            total_time_after_reset / total_count_after_reset))


if __name__ == '__main__':
    # anno_dir = '/media/darkalert/c02b53af-522d-40c5-b824-80dfb9a11dbb/boost/experiments/court_mapping_tool/test_NCAA-2020-21_only23/operator_results/manual_anno_by_Vyacheslav/'
    anno_dir = '/media/darkalert/c02b53af-522d-40c5-b824-80dfb9a11dbb/boost/experiments/court_mapping_tool/test_NCAA-2020-21_only23/operator_results/manual_anno_by_Mihail/'
    test(anno_dir)

