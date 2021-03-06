#!/usr/bin/python2

import commands
from subprocess import Popen,PIPE,call,STDOUT
import os, sys
import getopt
import parted
sys.path.append('/usr/lib/mintstick')
from mountutils import *

def raw_format(device_path, fstype, volume_label, uid, gid):

    do_umount(device_path)

    # First erase MBR and partition table , if any
    call(["dd", "if=/dev/zero", "of=%s" % device_path, "bs=512", "count=1"])

    device = parted.getDevice(device_path)

    # Create a default partition set up
    disk = parted.freshDisk(device, 'msdos')
    disk.commit()
    regions = disk.getFreeSpaceRegions()

    if len(regions) > 0:
        # Start partition at sector 2048
        offset = 2048
        # 1Mib grain size
        grain_size = kib_to_sectors(device, 1024)
        # Get first region
        region = regions[0]
        start = region.start
        end = region.end - start + 1

        align = parted.Alignment(offset=offset, grainSize=grain_size)
        if not align.isAligned(region, start):
            start = align.alignNearest(region, start)

        align = parted.Alignment(offset=offset -1, grainSize=grain_size)
        if not align.isAligned(region, end):
            end = align.alignNearest(region, end)
        try:
            geometry = parted.Geometry(device=device, start=start, end=end)
        except:
            print "Geometry error - Can't create partition"
            sys.exit(5)

        # fstype
        fs = parted.FileSystem(type=fstype, geometry=geometry)

        # Create partition
        partition = parted.Partition(disk=disk, type=parted.PARTITION_NORMAL, geometry=geometry, fs=fs)
        constraint = parted.Constraint(exactGeom=geometry)
        disk.addPartition(partition=partition, constraint=constraint)
        partition.setFlag(parted.PARTITION_BOOT)
        disk.commit()

        # Format partition according to the fstype specified
        if fstype == "fat32":
            call(["mkdosfs", "-F", "32", "-n", volume_label, partition.path])
        if fstype == "ntfs":
            call(["mkntfs", "-f", "-L", volume_label, partition.path])
        elif fstype == "ext4":
            call(["mkfs.ext4", "-E", "root_owner=%s:%s" % (uid, gid), "-L", volume_label, partition.path])
    sys.exit(0)


def kib_to_sectors(device, kib):
    return parted.sizeToSectors(kib, 'KiB', device.sectorSize)


def main():
    # parse command line options
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hd:f:l:u:g:", ["help", "device=","filesystem=","label=","uid=","gid="])
    except getopt.error, msg:
        print msg
        print "for help use --help"
        sys.exit(2)

    for o, a in opts:
        if o in ("-h", "--help"):
            print "Usage: %s -d device -f filesystem -l volume_label\n"  % sys.argv[0]
            print "-d|--device          : device path"
            print "-f|--filesystem      : filesystem\n"
            print "-l|--label           : volume label\n"
            print "-u|--uid             : uid of user\n"
            print "-g|--gid             : gid of user\n"
            print "Example : %s -d /dev/sdj -f fat32 -l \"USB Stick\" -u 1000 -g 1000" % sys.argv[0]
            sys.exit(0)
        elif o in ("-d"):
            device = a
        elif o in ("-f"):
            if a not in [ "fat32", "ntfs", "ext4" ]:
                print "Specify fat32, ntfs or ext4"
                sys.exit(3)
            fstype = a
        elif o in ("-l"):
            label = a
        elif o in ("-u"):
            uid = a
        elif o in ("-g"):
            gid = a

    argc = len(sys.argv)
    if argc < 11:
      print "Too few arguments"
      print "for help use --help"
      exit(2)

    raw_format(device, fstype, label, uid, gid)

if __name__ == "__main__":
    main()
