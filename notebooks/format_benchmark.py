import os
import re
import json
from dateutil import parser


def convert_benchmark(output_dir, monitoring_log):
    """
    converts and Saves a downloaded monitoring log to a formated JSON
    The monitoring script can be found here gs://broad-gdr-encode-caas-execution/scripts/monitoring.sh
    :param output_dir: the desired output directory to store the combined monitoring log json file
    :param monitoring_log: monitoring log downloaded from the googgle bucket (JSON)
    """

    with open(monitoring_log, "r") as bm:
        # read json in a dict and
        call_logs = json.load(bm)

    # for each task call in dict
    converted_call_logs = {}

    for name, info in call_logs.items():
        # summary
        num_of_cores = None
        total_mem = {"size": None, "unit": None}
        total_disk_sapce = {"size": None, "unit": None}

        # log info
        logs = []
        time_stamp = None
        cpu_usage = None
        mem_usage = None
        disk_usage = None

        # for each line in the task call info
        lines = info.split("\n")
        for line in lines:
            # if a line contains the desired info
            if '#CPU:' in line:
                # get that info
                info = get_info("\d+", line)

                # if the info is of correct format
                if info is not None:
                    # save that info
                    num_of_cores = int(info[0])

            elif 'Total Memory:' in line:
                # $ for matching at the end of the string
                info = get_info("(\d*\.\d+|\d+)(M|G|T)$", line)

                if info is not None:
                    total_mem = {"size": float(info[0]), "unit": str(info[1]) + "B"}

            elif 'Total Disk space: ' in line:
                info = get_info("(\d*\.\d+|\d+)(M|G|T)$", line)

                if info is not None:
                    total_disk_sapce = {
                        "size": float(info[0]),
                        "unit": str(info[1]) + "B",
                    }

            elif '[' in line:
                time_stamp = str(
                    parser.parse(line.replace("[", '').replace("]", '').strip())
                )

            elif "CPU usage: " in line:
                info = get_info("(\d*\.\d+|\d+)(%)$", line)

                if info is not None:
                    cpu_usage = float(info[0])

            elif '* Memory usage: ' in line:
                info = get_info("(\d*\.\d+|\d+)(%)$", line)

                if info is not None:
                    mem_usage = float(info[0])

            # if you have read disk usage, one time stamp has been read so save that information in the log
            elif '* Disk usage: ' in line:
                info = get_info("(\d*\.\d+|\d+)(%)$", line)

                if info is not None:
                    disk_usage = float(info[0])

                log = {
                    "time": time_stamp,
                    "cpu_usage": cpu_usage,
                    "memory_usage": mem_usage,
                    "disk_usage": disk_usage,
                }
                logs.append(log)

                disk_usage = None
                time_stamp = None
                cpu_usage = None
                mem_usage = None

        # add the task call name, summary and logs to a dict
        call_log = {"id": name}
        summary = {
            "cores": num_of_cores,
            "memory": total_mem,
            "disk_space": total_disk_sapce,
        }

        call_log["summary"] = summary
        call_log["logs"] = logs
        converted_call_logs.setdefault("calls", []).append(call_log)

    name = os.path.splitext(os.path.basename(monitoring_log))[0]
    file_name = get_path(name + "_formatted.json", output_dir)
    store_benchmark(converted_call_logs, file_name)


def get_info(prefix, string):
    """
    :param prefix: the regex to match the info you are trying to obtain
    :param string: the string where the info is contained (can have new line character)
    :return: the matches within the line
    """

    info = None

    # find and return the matches based on the prefix and if there is a match (not empty)
    matches = re.findall(prefix, string)
    if len(matches) > 0:

        info = matches[0]

    return info


def store_benchmark(call_logs, file_name):
    """
    dumps the information of each call task in dictionary format into one JSON file
    :param call_logs: the information of each call task in dictionary format
    :param file_name: name of the file with absolute path to dump the dictionay into
    """

    with open(file_name, "w") as logs:

        json.dump(call_logs, logs, sort_keys=False, indent=4)


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
