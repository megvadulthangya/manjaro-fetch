#!/bin/env bash

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

clear

window_icon=/usr/share/icons/hicolor/32x32/apps/dcmi.svg

main=/usr/bin/manjaro-iso-downloader
iso_dir=$HOME/Manjaro-Iso
gpg_log=$(mktemp)
check_sums_log=$(mktemp)
iso_list=$iso_dir/.iso.list
iso_dev_list=$iso_dir/.iso-dev.list
missing_prog=$(mktemp)
missing_manj_de=$(mktemp)
iso_ver_url='https://gitlab.manjaro.org/webpage/iso-info/-/raw/master/file-info.json' 
iso_ver=$(curl -s $iso_ver_url | grep -m1 'image' | grep -oP '(?<=kde/).*(?=/manjaro)')
version='full\!minimal'
type='direct\!torrent'
is_dev=false
iso_full_link_dev=$(mktemp)
iso_minimal_link_dev=$(mktemp)
isos_downloaded=$(mktemp)

#work dir
[[ ! -d $HOME/$iso_dir ]] && mkdir -p $iso_dir

#list of essential programs
check_prog=(curl wget aria2c zenity yad awk sed)

#Upated Manjaro flavour list
manj_de=(xfce gnome kde i3 cinnamon budgie mate)

#Manjaro dev Iso list
manj_dev_de=(gnome plasma xfce)

#grab iso link
curl -s $iso_ver_url | grep 'image' | grep 'download.manjaro.org' | awk '{print $2}' | tr -d '",' > "$iso_list"

trap 'rm -Rf $iso_dir/.tmp $check_sums_log $gpg_log $missing_prog $missing_manj_de $isos_downloaded ; killall aria2c ; exit' ERR EXIT

#Main Window settings
gui() {
    icon=/usr/share/icons/hicolor/32x32/apps/dcmi.svg

    if [[ -r "$icon" ]] ; then
        GDK_BACKEND=x11 /usr/bin/yad --center --window-icon="$icon" --title="Manjaro Isos $iso_ver Downloader and Checker" "$@"
    else
        GDK_BACKEND=x11 /usr/bin/yad --center --title="Manjaro Isos Downloader and Checker" "$@"
    fi
}

Welcome() {
    ISO=$(gui --image="$window_icon" --text-align=center --text="<b>Welcome to Manjaro Isos Downloader and Checker</b>\nA simple <b>GUI</b> for download lastes Isos and check the integrity" \
    --form --separator=" " \
    --field="Edition::CB" $edition \
    --field="Version::CB" $version \
    --field="Type::CB" $type)
    
    is_done=$?
}

Welcome_dev() {
    is_dev=true
    edition='Xfce\!Plasma\!Plasma-daily\!Gnome'
    ISO=$(gui --image="$window_icon" --text-align=center --text="<b>Welcome to Manjaro Isos Downloader and Checker</b>\nA simple <b>GUI</b> for download lastes Isos and check the integrity" \
    --form --separator=" " \
    --field="Edition::CB" $edition \
    --field="Version::CB" $version)

    is_done=$?
}

get_iso() {
    iso_full_link=$(grep "$DE" $iso_list | grep -v 'minimal')
    iso_minimal_link=$(grep "$DE" $iso_list | grep 'minimal')
    iso_full_torrent=$(grep "$DE" $iso_list | grep -v 'minimal').torrent
    iso_minimal_torrent=$(grep "$DE" $iso_list | grep 'minimal').torrent
    iso_full_sha1=$(grep "$DE" $iso_list | grep -v 'minimal').sha1
    iso_minimal_sha1=$(grep "$DE" $iso_list | grep 'minimal').sha1
    iso_full_sig=$(grep "$DE" $iso_list | grep -v 'minimal').sig
    iso_minimal_sig=$(grep "$DE" $iso_list | grep 'minimal').sig

    mkdir -p $iso_dir/.tmp

    [[ $DE == 'sway' ]] && get_sway

    if [[ $TYPE == 'direct' ]] ; then
        [[ $VERSION == 'full' ]] && \
        wget -nc -P "$iso_dir/.tmp" "$iso_full_link" "$iso_full_sha1" "$iso_full_sig" 2>&1 | \
        sed -u 's/.* \([0-9]\+%\)\ \+\([0-9.]\+.\) \(.*\)/\1\n# Downloading at \2\/s, ETA \3/' | \
        gui --image=download --progress --pulsate --title="Downloading $DE $iso_ver..." --auto-close --no-buttons --width=550 --height=150 || \
        wget -nc -P "$iso_dir/.tmp" "$iso_minimal_link" "$iso_minimal_sha1" "$iso_minimal_sig" 2>&1 | \
        sed -u 's/.* \([0-9]\+%\)\ \+\([0-9.]\+.\) \(.*\)/\1\n# Downloading at \2\/s, ETA \3/' | \
        gui --image=download --progress --pulsate --title="Downloading $DE $iso_ver..." --auto-close --no-buttons --width=550 --height=150
     else
        [[ $VERSION == 'full' ]] && \
        wget -nc -P "$iso_dir/.tmp" "$iso_full_torrent" 2>&1 | \
        sed -u 's/.* \([0-9]\+%\)\ \+\([0-9.]\+.\) \(.*\)/\1\n# Downloading at \2\/s, ETA \3/' | \
        gui --image=download --progress --pulsate --title="Downloading $DE $iso_ver torrent..." --auto-close --no-buttons --width=550 --height=150 || \
        wget -nc -P "$iso_dir/.tmp" "$iso_minimal_torrent" 2>&1 | \
        sed -u 's/.* \([0-9]\+%\)\ \+\([0-9.]\+.\) \(.*\)/\1\n# Downloading at \2\/s, ETA \3/' | \
        gui --image=download --progress --pulsate --title="Downloading $DE $iso_ver torrent..." --auto-close --no-buttons --width=550 --height=150
    fi          

    if [[ $TYPE == 'torrent' ]] ; then
        [[ $VERSION == 'full' ]] && \
        wget -nc -P "$iso_dir/.tmp" "$iso_full_sha1" "$iso_full_sig" "$iso_full_torrent" 2>&1 | \
        sed -u 's/.* \([0-9]\+%\)\ \+\([0-9.]\+.\) \(.*\)/\1\n# Downloading at \2\/s, ETA \3/' | \
        gui --image=download --progress --pulsate --title="Downloading $DE $iso_ver..." --auto-close --no-buttons --width=550 --height=150 || \
        wget -nc -P "$iso_dir/.tmp" "$iso_minimal_sha1" "$iso_minimal_sig" "$iso_minimal_torrent" 2>&1 | \
        sed -u 's/.* \([0-9]\+%\)\ \+\([0-9.]\+.\) \(.*\)/\1\n# Downloading at \2\/s, ETA \3/' | \
        gui --image=download --progress --pulsate --title="Downloading $DE $iso_ver..." --auto-close --no-buttons --width=550 --height=150

        cd $iso_dir/.tmp
        (aria2c --continue=true --max-concurrent-downloads=5 --max-connection-per-server=4 --min-split-size=10M --split=5 --disable-ipv6=true \
        --seed-time=0 --summary-interval=0 --console-log-level=warn --dir="$iso_dir/.tmp" $iso_dir/.tmp/*.torrent 2>&1) &
        pid=$!; while kill -0 $pid 2>&1; do echo 'working'; done | zenity --progress --pulsate --text="Waiting for Torrent download..." \
        --title="Manjaro Isos $iso_ver Downloader and Checker" --auto-close --no-cancel
    fi
        
    cd $iso_dir/.tmp
    iso_name=$(ls *.iso)
    sha1_name=$(ls *.sha*)
    sig_name=$(ls *.sig)
    date +"$iso_name downloaded at %d/%m/%Y - %R" >> $iso_dir/history
    mv *.iso *.sha* *.sig $iso_dir
    rm -Rf $iso_dir/.tmp 
}

get_iso_dev() {

    grep "$DE" "$iso_dev_list" | grep -v 'minimal' | grep 'z' | tr "\n" " " > "$iso_full_link_dev"
    grep "$DE" "$iso_dev_list" | grep 'minimal' | grep 'z' | tr "\n" " " > "$iso_minimal_link_dev"
    iso_full_sha256=$(grep "$DE" "$iso_dev_list" | grep -v 'minimal' | grep '.sha256')
    iso_minimal_sha256=$(grep "$DE" "$iso_dev_list" | grep 'minimal' | grep '.sha256')

    mkdir -p $iso_dir/.tmp

    [[ $DE -eq 'plasma-daily' ]] && VERSION=full

    [[ $VERSION == 'full' ]] && \
    wget -nc -P "$iso_dir/.tmp" $(cat $iso_full_link_dev) "$iso_full_sha256" 2>&1 | \
    sed -u 's/.* \([0-9]\+%\)\ \+\([0-9.]\+.\) \(.*\)/\1\n# Downloading at \2\/s, ETA \3/' | \
    gui --image=download --progress --pulsate --title="Downloading $DE development version..." --auto-close --no-buttons --width=550 --height=150 || \
    wget -nc -P "$iso_dir/.tmp" $(cat $iso_minimal_link_dev) "$iso_minimal_sha256" 2>&1 | \
    sed -u 's/.* \([0-9]\+%\)\ \+\([0-9.]\+.\) \(.*\)/\1\n# Downloading at \2\/s, ETA \3/' | \
    gui --image=download --progress --pulsate --title="Downloading $DE development version..." --auto-close --no-buttons --width=550 --height=150
}

get_sway() {
    gui --text="You have choice Sway edition; press the button for open the external link " --button="Exit":0 --button="Sway download":1 --button="New Iso":2
        case $? in
            0) exit 1 ;;
            1) xdg-open 'https://manjaro-sway.download/' &  exec $main ;;
            2) exec $main
        esac
}

check_programs() {
    for i in "${check_prog[@]}"; do
        command -v "$i" >/dev/null 2>&1 || echo "$i" >> "$missing_prog"
    done
    
    if [[ -s $missing_prog ]]; then
        gui --width=850 --height=270 --image=dialog-error --button=Ok --text-align=center --text='You need the following programs for continue' --text-info < "$missing_prog"
        exit 1
    fi
}

check_manj_de() {
    for i in "${manj_de[@]}"; do
        grep "$i" "$iso_list" >/dev/null 2>&1 || echo "$i" >> "$missing_manj_de"
    done
    
    if [[ -s $missing_manj_de ]]; then
        gui --width=850 --height=270 --image=dialog-error --button=Ok --text-align=center --text='The following DE are temporary not avaiable:' --text-info < "$missing_manj_de"
    fi
}

check_integrity() {
    if [[ "$(ls -A $iso_dir)" ]]; then
        cd $iso_dir

        gui --timeout=5 --timeout-indicator=top --text='Next step: checksums integrity' --button=Skip:0 --width=550 --height=150

        if [[ $? != 0 ]]; then
            (sha1sum -c $sha1_name > $check_sums_log) &
            pid=$!
            
            while kill -0 $pid 2>&1; do echo 'working'; done | zenity --progress --pulsate --text="Waiting for SHA1SUM check..." \
            --title="Manjaro Isos $iso_ver Downloader and Checker" --auto-close --no-cancel

            gui --width=850 --height=270 --button=Ok --image=dialog-error --text-align=center --text='SHA1SUM check result:' --text-info < $check_sums_log
        fi

        gui --timeout=5 --timeout-indicator=top --text='Next step: GPG integrity' --button=Skip:0 --width=550 --height=150

        if [[ $? != 0 ]]; then
            (gpg --verify $sig_name $iso_name &> $gpg_log) &
            pid=$!
            
            while kill -0 $pid 2>&1; do echo 'working'; done | zenity --progress --pulsate --text="Waiting for GPG check..." \
            --title="Manjaro Isos $iso_ver Downloader and Checker" --auto-close --no-cancel

            gui --width=850 --height=270 --button=Ok --image=dialog-error --text-align=center --text='GPG signatur result:' --text-info < $gpg_log
        fi    
    fi     
}

check_integrity_dev() {
    if [[ "$(ls -A $iso_dir)" ]]; then
        cd $iso_dir
      
        gui --timeout=5 --timeout-indicator=top --text='Next step: checksums integrity' --button=Skip:0 --width=550 --height=150

        if [[ $? != 0 ]]; then
            (sha256sum -c $iso_name.sha* > $check_sums_log) &
            pid=$!
            
            while kill -0 $pid 2>&1; do echo 'working'; done | zenity --progress --pulsate --text="Waiting for SHA256SUM check..." \
            --title="Manjaro Isos $iso_ver Downloader and Checker" --auto-close --no-cancel

            gui --width=850 --height=270 --button=Ok --image=dialog-error --text-align=center --text='SHA256SUM check result:' --text-info < $check_sums_log
        fi   
    fi     
}

check_connection() {
    wget -q --tries=10 --timeout=20 --spider https://google.com
    if [[ $? != 0 ]]; then
        gui --text-align=center --text="Check your internet connection \nyou are offline" --button="Ok":0 --button="Exit":1
        case $? in
            0) exec $main ;;
            1) exit 1
        esac
    fi
}

check_edition() {
    gui --image="$window_icon" --text-align=center --text="Download <b>Official</b>, <b>Community</b> or <b>Development</b> ISOs:" --button='Official':0 \
    --button='Community':1 --button='Development':3 --button='Restart':2 --button='Exit':4

    sel_ed=$?
    case $sel_ed in
        0) edition='Xfce\!Plasma\!Gnome' ;;
        1) edition='Budgie\!Cinnamon\!I3\!Mate\!Sway' ;;
        2) exec $main ;;
        3) dev_iso_list && Welcome_dev ;;
        *) exit 1
    esac
}

final_msg() {
    gui --text="Done, the Iso can be found at $iso_dir " --button="Exit":0 --button="Open folder":1 --button="New Iso":2
        case $? in
            0) exit 1 ;;
            1) xdg-open $iso_dir ;;
            2) exec $main
        esac
}

dev_iso_list() {
#grab iso dev download link #####################################################################
    rm -f "$iso_dev_list"
    for i in "${manj_dev_de[@]}"; do
        iso_ver_dev_url="https://api.github.com/repos/manjaro-${i}/download/releases"
        curl -s "$iso_ver_dev_url"/latest | jq -r ".assets[] | .browser_download_url " >> "$iso_dev_list"
    done

    curl -s https://api.github.com/repos/manjaro/plasma-daily/releases/latest | jq -r ".assets[] | .browser_download_url" >> "$iso_dev_list"
#################################################################################################
}

build_iso() {
    cd $iso_dir/.tmp
    7z t *.zip &> /dev/null &
    while pkill -0 7z; do
    	echo 'Checking'
    done | zenity --progress --pulsate --text="Checking..." --title="Manjaro Isos $iso_ver Downloader and Checker" --auto-close --no-cancel
    if [[ $i -eq 0 ]]; then
        7z x -y *.zip &> /dev/null & 
        while pkill -0 7z; do
            echo 'Unzipping... '
        done | zenity --progress --pulsate --text="Unzipping..." --title="Manjaro Isos $iso_ver Downloader and Checker" --auto-close --no-cancel
    else gui --text-aligned=center --text='Iso corrupted: choice again an Iso' --button='Change version':0 --button='Exit':1
        if [[ $? -eq 0 ]]; then
            exec $main
        else exit 1
        fi
    fi
    iso_name=$(ls *.iso)
    date +"$iso_name downloaded at %d/%m/%Y - %R" >> $iso_dir/history
    mv *.iso *.sha* $iso_dir
    rm -Rf $iso_dir/.tmp
}

downloaded_iso() {
    cd $iso_dir
    ls *iso > $isos_downloaded
    gui --width=850 --height=270 --button='Exit':1 --button='Next':0 --image=dialog-error --text-align=center --text="ISOs in the <b>$iso_dir</b> folder:" --text-info < $isos_downloaded
}

#Main program

check_programs
check_connection
check_manj_de
if [[ ! -z "$(ls -A "$iso_dir")" ]]; then
    downloaded_iso 
    [[ $? -eq 1 ]] && exit 1
fi
check_edition

[[ $is_dev = 'false' ]] && Welcome

if [[ $is_dev = 'false' ]]; then
    [[ $is_done == 1 ]] && exec $main
    DE=$(echo $ISO | awk '{print $1}' | tr '[:upper:]' '[:lower:]')
    VERSION=$(echo $ISO | awk '{print $2}')
    TYPE=$(echo $ISO | awk '{print $3}')

    [[ $DE == 'plasma' ]] && DE=kde
else 
    [[ $is_done == 1 ]] && exec $main
    DE=$(echo $ISO | awk '{print $1}' | tr '[:upper:]' '[:lower:]')
    VERSION=$(echo $ISO | awk '{print $2}')
fi

[[ $is_dev == false ]] && get_iso
[[ $is_dev == true ]] && get_iso_dev
[[ $is_dev == true ]] && build_iso
[[ $is_dev == false ]] && check_integrity || check_integrity_dev

final_msg

$main

#Done
