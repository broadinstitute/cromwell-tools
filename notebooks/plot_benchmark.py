import json
import re
import os
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

matplotlib.use('TkAgg')


def plot_benchmark(monitoring_log, parent_workflow_name, cromwell_id, output_dir):
    """
    plots the converted/formatted monitoring log (JSON)
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

    tasks = {}
    for key, calls in calls_dict.items():
        for call in calls:
            # get the id/name of each task call
            name = str(call["id"])
            # if there the task call is an attempt
            match = re.findall(r"(attempt-\d+)$", name)
            if len(match) > 0:
                # remove attempt from the task call name
                name = os.path.dirname(name)

            match = re.findall(r"(shard-\d+)$", name)
            # if task is not a shard
            if len(match) == 0:
                # get the name of the task
                # i.e: os.path.basename(/workflow/cromwell_id/call) == call
                task_name = os.path.basename(name)

            # if task is a shard
            else:
                # get the name of the task that was scattered plus the shard
                # i.e: os.path.dirname(/workflow/cromwell_id/call/shard) == /workflow_/cromwell_id/call/
                task_name = os.path.basename(os.path.dirname(name))

            # if no other shards of the task have been stored in dict
            if task_name not in tasks:
                # store total memory and max memory of current task call
                total_memory = str(call["summary"]["memory"]["size"]) + str(
                    call["summary"]["memory"]["unit"]
                )
                tasks[task_name] = {"max_memory": 0.0, "total_memory": total_memory}

            # get max memory usage of current task call
            max_memory = 0.0
            logs = call["logs"]
            for log in logs:
                memory_usage = log["memory_usage"]
                if memory_usage > max_memory:
                    max_memory = memory_usage

            # if max memory usage of current task call is > than max usage from other shards
            if max_memory > tasks[task_name]["max_memory"]:
                # save total memory and max memory of current task call
                tasks[task_name]["max_memory"] = max_memory
                tasks[task_name]["total_memory"] = str(
                    call["summary"]["memory"]["size"]
                ) + str(call["summary"]["memory"]["unit"])

    task_calls = []
    total_memories = []
    max_memory_usages = []
    # store in arrays to put in data frame for plotting
    for name, mem_info in tasks.items():
        task_calls.append(name)
        max_memory_usages.append(mem_info["max_memory"])
        total_memories.append(mem_info["total_memory"])

    # create data frame / format for plotting
    data_frame = pd.DataFrame(
        {
            "task calls": task_calls,
            "total memories": total_memories,
            "max memory usages": max_memory_usages,
        }
    )

    if len(task_calls) > 0:
        data_frame = data_frame.sort_values("task calls")

    # plot figure for mem usage
    fig = plt.figure()
    fig.tight_layout()
    fig.suptitle("Memory Usage of " + parent_workflow_name + " '" + cromwell_id + "'")
    bars_index = np.arange(len(task_calls))

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
    filename = get_path(
        parent_workflow_name + "_" + cromwell_id + "_memory_usage_plot.png", output_dir
    )
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
