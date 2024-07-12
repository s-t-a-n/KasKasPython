#!/bin/bash

# this script exists because repeatedly updating an `st.image` leaks
# todo: checkout using an RTC like stream alternative to `st.image`
# https://github.com/streamlit/streamlit/issues/6354#issuecomment-1533893073

memory_usage() {
    mem=$(smem | grep "$1" | grep -v grep | tr -s ' '| cut -d\  -f7)
    if [ "$1" = "" ] || [ "$mem" = "" ]; then
        mem=0
    fi
    echo $(( mem / 1024 ))
}

free_memory() {
    awk '/MemFree/ { printf "%.0f \n", $2/1024 }' /proc/meminfo
}

available_memory() {
    awk '/MemAvailable/ { printf "%.0f \n", $2/1024 }' /proc/meminfo
}

total_memory() {
    awk '/MemTotal/ { printf "%.0f \n", $2/1024 }' /proc/meminfo
}

while true; do
    used=$(memory_usage "$(pgrep -x streamlit)")
    if [ "$used" -gt 1500 ];then
        echo "Streamlit used too much memory, killing process!"
        pkill -x streamlit
    fi
    
    available=$(available_memory)
    if [ "$available" -lt 200 ]; then
        echo "Not enough free memory left, killing process!"
        pkill -x streamlit
    fi
    echo "DEBUG: used/available: $used/$available"
    sleep 1
done
