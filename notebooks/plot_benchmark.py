import json
import re
import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from dateutil import parser


def plot_benchmark(monitoring_log, parent_workflow_name, cromwell_id, output_dir):
    """
    Plots the converted/formated monitoring log (JSON)
    :param monitoring_log: monitoring log in JSON format
    :param parent_workflow_name: the name of the workflow being run
    :param cromwell_id: the cromwell id for the workflow being run
    :param output_dir: the desired output directory to save the plot
    """

    with open(monitoring_log, "r") as ml:
        calls_dict = json.load(ml)

    plot_memory_usage(calls_dict, parent_workflow_name, cromwell_id, output_dir)


def plot_memory_usage(calls_dict, parent_workflow_name, cromwell_id, output_dir):
    """
    plots a graph of the max cpu, disk and mem usage for each call
    :param calls_dict: dictionary data structure of monitoring log
    :param parent_workflow_name: the name of the workflow being run
    :param cromwell_id: the cromwell id for the workflow being run
    :param output_dir: the desired output directory to save the plot
    """

    task_calls = []
    total_memories = []
    start_times = []
    max_memory_usages = []

    # for all the calls (dict)
    for key, calls in calls_dict.items():
        # for each call (list)
        for call in calls:
            task_call = ""
            total_mem = ""
            time_stamps = []
            memory_usages = []

            # for each set of info for the call
            for name, info in call.items():
                if name == "id":
                    match = re.findall(r"(shard-\d+)$", info)

                    # if task is not a shard
                    if len(match) == 0:
                        # get the name of the task
                        task_call = os.path.basename(info)

                    # if task is a shard
                    else:
                        # get the name of the task that was scattered plus the shard
                        task_call = os.path.basename(os.path.dirname(info)) + " " + os.path.basename(info)

                if name == "summary":
                    total_mem = str(info["memory"]["size"]) + str(info["memory"]["unit"])

                if name == "logs":
                    # for the log of each time stamp
                    for log in info:
                        for log_type, value in log.items():
                            if log_type == "time":
                                time = parser.parse(value)
                                time_stamps.append(time)

                            if log_type == "memory_usage":
                                memory_usages.append(value)

            # add the information to the lists
            task_calls.append(task_call)
            total_memories.append(total_mem)

            start_time = None
            if len(time_stamps) > 0:
                start_time = min(time_stamps)

            start_times.append(start_time)

            max_memory_usage = None
            if len(memory_usages) > 0:
                max_memory_usage = max(memory_usages)

            max_memory_usages.append(max_memory_usage)

    # create data frame / format for plotting
    data_frame = pd.DataFrame({"task calls": task_calls,
                               "total memories": total_memories,
                               "start times": start_times,
                               "max memory usages": max_memory_usages})

    if len(task_calls) > 0:
        data_frame = data_frame.sort_values("task calls")

    # plot figure for mem usage
    fig = plt.figure()
    fig.tight_layout()
    fig.suptitle("Memory Usage of " + parent_workflow_name + " '" + cromwell_id + "'")
    bars_index = np.arange(len(calls_dict["calls"]))

    # set up left axis
    ax1 = fig.add_subplot(111)
    ax1.barh(bars_index, data_frame["max memory usages"])
    ax1.set_yticks(bars_index)
    ax1.set_yticklabels(data_frame["task calls"])
    ax1.set_xlim([0, 100])
    ax1.tick_params(axis="both", labelsize=4)
    ax1.set_xlabel("Max Memory Usage (%)")

    # set up right axis
    ax2 = ax1.twinx()
    ax2.barh(bars_index, data_frame["max memory usages"])
    ax2.set_yticks(bars_index)
    ax2.set_yticklabels(data_frame["total memories"])
    ax2.set_ylabel("Total Memory Available")
    ax2.yaxis.set_label_position("right")
    ax2.tick_params(axis="both", labelsize=4)

    # save plot
    filename = get_path(parent_workflow_name + "_" + cromwell_id + "_memory_usage_plot.png", output_dir)
    plt.savefig(filename, dpi=1000, bbox_inches="tight")


def get_path(filename, output_dir):
    """
    :param filename: the filename to be saved in the output directory
    :param output_dir: the desired output directory to store the monitoring log, plots and json file
    :return: returns the combined path of file name and  output directory
    """

    # get the combined path of output dir path, filename and sub dir path
    path = os.path.join(output_dir, filename)

    # if the combined path exist
    if os.path.isfile(path):
        # delete that current path
        os.remove(path)

    # return combined path
    return path
