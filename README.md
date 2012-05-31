# chnroutes

利用来自[APNIC](http://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest)的数据生成路由命令脚本，让VPN客户端在连接时自动执行。通过这些路由脚本，可以让用户在使用VPN作为默认网关时，不使用VPN访问中国国内IP，从而减轻VPN负担，并提高访问国内网站的速度。

## 基本约定

在使用这些脚本之前，请确保你在自己的电脑上已经成功配置好一个VPN（PPTP或OpenVPN），并且让之以默认网关的方式运行（通常是默认配置），即VPN连接之后所有网络流量都通过VPN。

### 注意事项

* 因为这些IP数据不是固定不变的，建议每隔一个月更新一次；
* 使用此法之后，可能导致Google Music等服务无法访问，因为连上VPN之后，使用的DNS也是国外的，因此google.cn解析出的是国外的IP。

## OpenVPN

如安装有`iproute2`软件包，请尽量使用此方式。自带方式在路由表条目较多时执行极慢。

### iproute2

1. 执行`python chnroutes.py`，这将生成`vpn-up.sh`和`vpn-down.sh`两个文件；
2. 将这两个文件移入`/etc/openvpn/`；
3. 在OpenVPN配置文件中加入：
```    script-security 2
    up vpn-up.sh
    down vpn-down.sh```
4. 重新连接VPN，观察日志测试。

### 自带方式

1. 执行`python chnroutes.py -p old`, 这将生成`routes.txt`文本文件；
2. 将该文件内容加在OpenVPN配置文件的尾部；
3. 重新连接VPN，观察日志测试。

## PPTP
### Mac OS X

1. 在终端中执行`python chnroutes.py -p mac`，这将生成`ip-up`和`ip-down`两个文件；
2. 将这两个文件移入`/etc/ppp/`；
3. 重新连接VPN，观察测试。

### Linux

1. 执行`python chnroutes.py -p linux`，这将生成`ip-pre-up`和`ip-down`两个文件；
2. 将`ip-pre-up`移入`/etc/ppp/`，`ip-down`移入`/etc/ppp/ip-down.d/`；
3. 重新连接VPN，观察测试。

### Windows

1. 在命令提示符中执行`python chnroutes.py -p win`，这将生成`vpnup.bat`和`vpndown.bat`两个文件；
2. 在拨号前手动执行`vpnup.bat`文件设置路由表；在断开VPN后，可运行`vpndown.bat`清理路由表。

## 基于Linux的第三方系统的路由器

一些基于Linux系统的第三方路由器系统如OpenWRT、DD-WRT、Tomato都带有VPN（PPTP/OpenVPN）客户端的，也就是说，我们只需要在路由器进行VPN拨号，并利用本项目提供的路由表脚本就可以把VPN针对性翻墙扩展到整个局域网。当然，使用这个方式也是会带来副作用，即局域网的任何机器都不适合使用Emule或者BT等P2P下载软件。但对于那些不使用P2P，希望在路由器上设置针对性翻墙的用户，这方法十分有用，因为只需要一个VPN帐号，局域网内的所有机器，包括使用Wi-Fi的手机都能自动翻墙。详细配置方式请参考[Autoddvpn](http://code.google.com/p/autoddvpn/)项目。

## 信息反馈

本项目的脚本都是在使用路由器进行拨号的情况下测试通过的，如果在其它拨号方式下，脚本不能运作，请添加新的Issue。另外，在配合OpenVPN使用的时候，可能会出现因为网络质量不好，OpenVPN非主动断开，这时候`vpn-down.sh`脚本也会被自动调用，但重新连上之后，可能会找不到默认路由而添加失败，这时候你可以通过停止OpenVPN，并手动设置好原来的默认路由再重新进行OpenVPN拨号。
