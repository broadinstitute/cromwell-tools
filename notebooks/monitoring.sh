#!/bin/bash
echo ==================================
echo =========== MONITORING ===========
echo ==================================
echo --- General Information ---
# number of cores
echo \#CPU: $(nproc)

# multiply by 10^-6 to convert KB to GB
echo Total Memory: $(cat /proc/meminfo | grep MemTotal | awk 'BEGIN { FS=" " } ; { print $2/1000000 }')G
echo Total Disk space: $(df -h | grep cromwell_root | awk '{ print $2}')
echo


function runtime_info() {
        echo [$(date)]
        echo \* CPU usage: "$(get_cpu_usage)"%
        echo \* Memory usage: "$(get_mem_usage)"%
        echo \* Disk usage: $(df | grep cromwell_root | awk '{ print $5 }')
}


function get_cpu_usage() {
        # get the cpu usage since a given time (w/o idle or iowait)
        # user+nice+system+irq+softirq+steal
        cpu_used_cur=$(cat /proc/stat | grep "cpu " | awk 'BEGIN { FS=" " } ; { print $2+$3+$4+$7+$8+$9 }')

        # get the total cpu usage since a given time (including idle and iowait)
        # user+nice+system+idle+iowait+irq+softirq+steal
        cpu_total_cur=$(cat /proc/stat | grep "cpu " | awk 'BEGIN { FS=" " } ; { print $2+$3+$4+$5+$6+$7+$8+$9 }')

        # read in previous cpu usage values
        read -r -a cpu_prev < ${TEMP}
        cpu_used_prev=cpu_prev[0]
        cpu_total_prev=cpu_prev[1]

        # usage = 100 * (cpu_used_cur - cpu_used_prev) / (cpu_total_cur-cpu_total_prev)
        echo "$cpu_used_cur" "$cpu_used_prev" "$cpu_total_cur" "$cpu_total_prev" | awk 'BEGIN {FS=" "} ; { print 100*(($1-$2)/($3-$4)) }'

        # save current values as prev values for next iteration
        cpu_prev[0]=cpu_used_cur
        cpu_prev[1]=cpu_total_cur
        echo "${cpu_prev[@]}" > ${TEMP}
}


function get_mem_usage() {
    #memTotal and #memAvailable fields from /proc/meminfo
    mem_total=$(cat /proc/meminfo | grep MemTotal | awk 'BEGIN { FS=" " } ; { print $2}')
    mem_unused=$(cat /proc/meminfo | grep MemAvailable | awk 'BEGIN { FS=" " } ; { print $2}')

    #usage = 100 * mem_used / mem_total
    mem_used=$(($mem_total-$mem_unused))
    echo "$mem_used" "$mem_total" | awk '{ print 100*($1/$2) }'
}


# create variable to store cpu being used (cpu_prev[0]) and total cpu total (cpu_prev[1])
declare -a cpu_prev

# get the cpu usage since a given time (w/o idle or iowait)
# user+nice+system+irq+softirq+steal
cpu_prev[0]=$(cat /proc/stat | grep "cpu " | awk 'BEGIN { FS=" " } ; { print $2+$3+$4+$8+$9 }')

# get the total cpu usage since a given time (including idle and iowait)
# user+nice+system+idle+iowait+irq+softirq+steal
cpu_prev[1]=$(cat /proc/stat | grep "cpu " | awk 'BEGIN { FS=" " } ; { print $2+$3+$4+$5+$6+$8+$9 }')

# save values to temp file to allow passing in values to a function
TEMP=$(mktemp /temp_monitoring.XXXXXXXX)
echo "${cpu_prev[@]}" > ${TEMP}

echo --- Runtime Information ---
while true; do runtime_info; sleep 5; done
