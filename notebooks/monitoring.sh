#!/bin/bash


declare -a TEMP=$(mktemp /temp_monitoring.XXXXXXXX)


function get_disk_info() {
        # df command and cromwell root field
        disk_info=$(df | grep cromwell_root)
        echo "$disk_info"
}


function get_disk_usage() {
        # get disk usage field
        echo $(get_disk_info | awk '{ print $5 }')
}


function get_mem_info() {
        # /proc/meminfo
        mem_info=$(cat /proc/meminfo)
        echo "$mem_info"
}


function get_mem_available() {
        # mem unused from /proc/meminfo
        mem_available=$(get_mem_info | grep MemAvailable | awk 'BEGIN { FS=" " } ; { print $2 }')
        echo "$mem_available"
}


function get_mem_total() {
        # mem total from /proc/meminfo
        mem_total=$(get_mem_info | grep MemTotal | awk 'BEGIN { FS=" " } ; { print $2 }')
        echo "$mem_total"
}


function get_mem_usage() {
        # memTotal and memAvailable
        mem_total=$(get_mem_total)
        mem_available=$(get_mem_available)

        # usage = 100 * mem_used / mem_total
        mem_used=$(($mem_total-$mem_available))
        echo "$mem_used" "$mem_total" | awk '{ print 100*($1/$2) }'
}


function get_cpu_info() {
        # cpu info from /proc/stat
        cpu_info=$(cat /proc/stat | grep "cpu ")
        echo "$cpu_info"
}


function get_cpu_total() {
        # get the total cpu usage since a given time (including idle and iowait)
        # user+nice+system+idle+iowait+irq+softirq+steal
        cpu_total=$(get_cpu_info| awk 'BEGIN { FS=" " } ; { print $2+$3+$4+$5+$6+$7+$8+$9 }')
        echo "$cpu_total"
}


function get_cpu_used() {
        # get the cpu usage since a given time (w/o idle or iowait)
        # user+nice+system+irq+softirq+steal
        cpu_used=$(get_cpu_info | awk 'BEGIN { FS=" " } ; { print $2+$3+$4+$7+$8+$9 }')
        echo "$cpu_used"
}


function get_cpu_usage() {
        # get the cpu usage since a given time (w/o idle or iowait)
        # user+nice+system+irq+softirq+steal
        cpu_used_cur=$(get_cpu_used)

        # get the total cpu usage since a given time (including idle and iowait)
        # user+nice+system+idle+iowait+irq+softirq+steal
        cpu_total_cur=$(get_cpu_total)

        # read in previous cpu usage values
        read -r -a cpu_prev < ${TEMP}
        cpu_used_prev=${cpu_prev[0]}
        cpu_total_prev=${cpu_prev[1]}

        # save current values as prev values for next iteration
        cpu_prev[0]=$cpu_used_cur
        cpu_prev[1]=$cpu_total_cur
        echo "${cpu_prev[@]}" > ${TEMP}

        # usage = 100 * (cpu_used_cur - cpu_used_prev) / (cpu_total_cur-cpu_total_prev)
        echo "$cpu_used_cur" "$cpu_used_prev" "$cpu_total_cur" "$cpu_total_prev" | awk 'BEGIN {FS=" "} ; { print 100*(($1-$2)/($3-$4)) }'

}


function get_date() {
    # i.e: Fri Oct 19 15:49:30 UTC 2018
    echo $(date)
}


function get_usage() {
        echo [$(get_date)]
        echo \* CPU usage: "$(get_cpu_usage)"%
        echo \* Memory usage: "$(get_mem_usage)"%
        echo \* Disk usage: $(get_disk_usage)%
}


function get_summary() {
        # display header information
        echo ==================================
        echo =========== MONITORING ===========
        echo ==================================

        # summary info
        echo --- General Information ---
        # number of cores
        echo \#CPU: $(nproc)
        # multiply by 10^-6 to convert KB to GB
        echo Total Memory: $(echo $(get_mem_total) 1000000 | awk '{ print $1/$2 }')G
        echo Total Disk space: $(df -h | grep cromwell_root | awk '{ print $2}')
}


function main() {
        # disk, mem and cpu general statisitcs
        get_summary

        # create variable to store cpu being used (cpu_prev[0]) and total cpu total (cpu_prev[1])
        # save variable to a temp file to allow passing in values to a function
        declare -a cpu_prev
        cpu_prev[0]=$(get_cpu_used)
        cpu_prev[1]=$(get_cpu_total)
        # save global values to temp file to allow passing in values to a function
        echo "${cpu_prev[@]}" > ${TEMP}

        # sleep b/w getting usage and intially storing the cpu_previous usage values
        # this is b/c cpu usage values are time dependent
        # to calculate cpu usage, values must be determined from 2 diff time stamps
        sleep 1

        # get usage of disk, cpu and mem every 30 sec
        echo
        echo --- Runtime Information ---
        while true; do get_usage; sleep 30; done
}

main
