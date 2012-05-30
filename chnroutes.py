#!/usr/bin/env python

import re
import urllib2
import sys
import argparse
import math
import textwrap

def generate_ovpn(metric):
    results = fetch_ip_data()

    upscript_header = """\
#!/bin/bash -

OLDGW=$(ip route show 0/0 | head -n1 | grep 'via' | grep -Po '\d+\.\d+\.\d+\.\d+')

ip -batch - <<EOF
"""
    downscript_header = """\
#!/bin/bash -

ip -batch - <<EOF
"""

    upfile = open('vpn-up.sh', 'w')
    downfile = open('vpn-down.sh', 'w')

    upfile.write(upscript_header)
    downfile.write(downscript_header)

    for ip, _, mask in results:
        upfile.write('route add %s/%s via $OLDGW metric %s\n' % (ip, mask, metric))
        downfile.write('route del %s/%s\n' % (ip, mask))

    upfile.write('EOF\n')
    downfile.write('EOF\n')

    upfile.close()
    downfile.close()

    print """\
Place vpn-{up,down}.sh into /etc/openvpn/, chmod +x, and add
    script-security 2
    up vpnup.sh
    down vpndown.sh
to your openvpn.conf."""

def generate_linux(metric):
    results = fetch_ip_data()

    upscript_header = """\
#!/bin/bash -

OLDGW=$(ip route show 0/0 | head -n1 | grep 'via' | grep -Po '\d+\.\d+\.\d+\.\d+')

if [ $OLDGW == '' ]; then
    exit 0
fi

if [ ! -e /tmp/vpn_oldgw ]; then
    echo $OLDGW > /tmp/vpn_oldgw
fi

ip -batch - <<EOF
"""

    downscript_header = """\
#!/bin/bash
export PATH="/bin:/sbin:/usr/sbin:/usr/bin"

OLDGW=$(cat /tmp/vpn_oldgw)

ip -batch - <<EOF
"""

    upfile = open('ip-pre-up', 'w')
    downfile = open('ip-down', 'w')

    upfile.write(upscript_header)
    downfile.write(downscript_header)

    for ip, _, mask in results:
        upfile.write('route add %s/%s via $OLDGW metric %s\n' % (ip, mask, metric))
        downfile.write('route del %s/%s\n' % (ip, mask))

    upfile.write('EOF\n')
    downfile.write('''\
EOF

rm /tmp/vpn_oldgw
''')

    print "For pptp only, please copy the file ip-pre-up to /etc/ppp/," \
          "and copy the file ip-down to /etc/ppp/ip-down.d/."

def generate_mac(metric):
    results=fetch_ip_data()

    upscript_header = """\
#!/bin/sh
export PATH="/bin:/sbin:/usr/sbin:/usr/bin"

OLDGW=`netstat -nr | grep '^default' | grep -v 'ppp' | sed 's/default *\\([0-9\.]*\\) .*/\\1/'`

if [ ! -e /tmp/pptp_oldgw ]; then
    echo "${OLDGW}" > /tmp/pptp_oldgw
fi

dscacheutil -flushcache
"""

    downscript_header = """\
#!/bin/sh
export PATH="/bin:/sbin:/usr/sbin:/usr/bin"

if [ ! -e /tmp/pptp_oldgw ]; then
        exit 0
fi

OLDGW=`cat /tmp/pptp_oldgw`
"""

    upfile = open('ip-up','w')
    downfile = open('ip-down','w')

    upfile.write(upscript_header)
    downfile.write(downscript_header)

    for ip, _, mask in results:
        upfile.write('route add %s/%s "${OLDGW}"\n' % (ip, mask))
        downfile.write('route delete %s/%s ${OLDGW}\n' % (ip, mask))

    downfile.write('\n\nrm /tmp/pptp_oldgw\n')
    upfile.close()
    downfile.close()

    print "For pptp on mac only, please copy ip-up and ip-down to the /etc/ppp folder," \
          "don't forget to make them executable with the chmod command."

def generate_win(metric):
    results = fetch_ip_data()

    upscript_header = """\
@echo off
for /F "tokens=3" %%* in ('route print ^| findstr "\\<0.0.0.0\\>"') do set "gw=%%*"
"""

    upfile = open('vpnup.bat','w')
    downfile = open('vpndown.bat','w')

    upfile.write(upscript_header)
    upfile.write('ipconfig /flushdns\n\n')

    downfile.write("@echo off")
    downfile.write('\n')

    for ip, mask, _ in results:
        upfile.write('route add %s mask %s %s metric %d\n' % (ip, mask, "%gw%", metric))
        downfile.write('route delete %s\n' % ip)

    upfile.close()
    downfile.close()

#    up_vbs_wrapper=open('vpnup.vbs','w')
#    up_vbs_wrapper.write('Set objShell = CreateObject("Wscript.shell")\ncall objShell.Run("vpnup.bat",0,FALSE)')
#    up_vbs_wrapper.close()
#    down_vbs_wrapper=open('vpndown.vbs','w')
#    down_vbs_wrapper.write('Set objShell = CreateObject("Wscript.shell")\ncall objShell.Run("vpndown.bat",0,FALSE)')
#    down_vbs_wrapper.close()

    print "For pptp on windows only, run vpnup.bat before dialing to vpn," \
          "and run vpndown.bat after disconnected from the vpn."

def generate_android(metric):
    results = fetch_ip_data()

    upscript_header = """\
#!/bin/sh
alias nestat='/system/xbin/busybox netstat'
alias grep='/system/xbin/busybox grep'
alias awk='/system/xbin/busybox awk'
alias route='/system/xbin/busybox route'

OLDGW=`netstat -rn | grep ^0\.0\.0\.0 | awk '{print $2}'`
"""

    downscript_header = """\
#!/bin/sh
alias route='/system/xbin/busybox route'
"""

    upfile = open('vpnup.sh','w')
    downfile = open('vpndown.sh','w')

    upfile.write(upscript_header)
    upfile.write('\n')
    downfile.write(downscript_header)
    downfile.write('\n')

    for ip, mask, _ in results:
        upfile.write('route add -net %s netmask %s gw $OLDGW\n' % (ip, mask))
        downfile.write('route del -net %s netmask %s\n' % (ip, mask))

    upfile.close()
    downfile.close()

    print "Old school way to call up/down script from openvpn client. " \
          "use the regular openvpn 2.1 method to add routes if it's possible"


def fetch_ip_data():
    #fetch data from apnic
    print "Fetching data from apnic.net, it might take a few minutes, please wait..."
    url = r'http://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest'
    data = urllib2.urlopen(url).read()

    cnregex = re.compile(r'apnic\|cn\|ipv4\|[0-9\.]+\|[0-9]+\|[0-9]+\|a.*', re.IGNORECASE)
    cndata = cnregex.findall(data)

    results = []

    for item in cndata:
        unit_items = item.split('|')
        starting_ip = unit_items[3]
        num_ip = int(unit_items[4])

        imask = 0xffffffff ^ (num_ip - 1)
        #convert to string
        imask = hex(imask)[2:]
        mask = [0] * 4
        mask[0] = imask[0:2]
        mask[1] = imask[2:4]
        mask[2] = imask[4:6]
        mask[3] = imask[6:8]

        #convert str to int
        mask = [int(i, 16) for i in mask]
        mask = "%d.%d.%d.%d" % tuple(mask)

        #mask in *nix format
        mask2 = 32 - int(math.log(num_ip, 2))

        results.append((starting_ip, mask, mask2))

    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate routing rules for vpn.")
    parser.add_argument('-p','--platform',
                        dest='platform',
                        default='openvpn',
                        nargs='?',
                        help="Target platforms, it can be openvpn, mac, linux," 
                        "win, android. openvpn by default.")
    parser.add_argument('-m','--metric',
                        dest='metric',
                        default=5,
                        nargs='?',
                        type=int,
                        help="Metric setting for the route rules")

    args = parser.parse_args()

    if args.platform.lower() == 'openvpn':
        generate_ovpn(args.metric)
    elif args.platform.lower() == 'linux':
        generate_linux(args.metric)
    elif args.platform.lower() == 'mac':
        generate_mac(args.metric)
    elif args.platform.lower() == 'win':
        generate_win(args.metric)
    elif args.platform.lower() == 'android':
        generate_android(args.metric)
    else:
        print >>sys.stderr, "Platform %s is not supported." % args.platform
        exit(1)
