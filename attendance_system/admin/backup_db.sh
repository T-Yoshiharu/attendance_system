#!/usr/bin/bash

# CWDの設定
cd ~/Yt24_attendance/

cp attendance.db $1
chmod 544 $1
mv $1 ~/backup-DB/
