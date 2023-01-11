# gr-tacmac
This repo contains tools and configurations to run a full fletched over the air demo with low latency and high reliability. Possibly, we use multiple distributed USRPs to improve the overall reliability via spatial diversity.

This OOT provides functionality to handle incoming PDUs. The idea is to use a `GNU Radio Socket PDU` block that handles the connection. PDUs from this block go into a `gr-tacmac MAC controller` before they are transmitted and are received by the same block.

## CRC++
We use [CRC++](https://github.com/d-bahr/CRCpp) to perform CRC calculations. In order to do so, we just copied `CRC.h` from `CRCpp/inc/CRC.h`.

Currently, we use `CRC16_XMODEM`. See the details in the CRC++ documentation.

## TacMAC demo collection

The repository evolved into a collection of TacMAC demo tools and flowgraphs.
AS a side-effect the repo depends on a couple of GNU Radio modules. Most of them are publicly available and easily installable via PyBOMBS

The core functionality is:

* [GNU Radio v3.9+](https://github.com/gnuradio/gnuradio)
    * [VOLK v2.4+](https://github.com/gnuradio/volk)
* [UHD v4.1](https://github.com/EttusResearch/uhd)

A list of public repos

* [gr-symbolmapping](https://github.com/ant-uni-bremen/gr-symbolmapping)
* [gr-gfdm](https://github.com/jdemel/gr-gfdm)
* [XFDMSync](https://github.com/jdemel/XFDMSync)
* [polar-codes](https://github.com/ant-uni-bremen/polar-codes), needs some extra love. Build with <br>`cmake -DCMAKE_INSTALL_PREFIX=[GNURADIO_INSTALL_PREFIX] ..`<br>
* [gr-polarwrap](https://github.com/jdemel/gr-polarwrap)
* [network-tools](https://github.com/nick-schwarzenberg/network-tools)

## Network tools usage
Generally, we assume one basestation with `id=0` and several clients with `id=40, 41, 42, ...` We'll probably stop here. These `id`s are set such that the PHY works. The assumption that the basestation assumes `id=0` is integrated into the system.

For the sake of simpler debugging, and because we do things manually at the moment, we assume client IPs end in `.40, .41`. Thus, their IP ends in their PHY id.

For the sake of this manual, we assume, we use `10.0.0.0/24` as our subnet. The FOU config assumes that we use `PORT 4000 + id`.

### Client
We use [network-tools](https://github.com/nick-schwarzenberg/network-tools) on the client. This is quite simple. We start with

```bash
sudo ./udp-tunnel.sh up 4040 4000 10.0.0.0/24 84
```
We listen on port 4040, remember Port 4000 + `id`.
We transmit to the base station with `id=0`, thus port `4000`.
We tell the host that `10.0.0.0/24` is reachable through this inteface. Finally, the MTU is 84.

Now, a new interface appears with `ip a`. It's called `fou1` (delete them and redo this step if there's more than one). We assign an IP address to the interface `fou1`.

```bash
sudo ip addr add 10.0.0.40/24 dev fou1
```
Now, the host knows that `10.0.0.40` is its new IP address and will respond accordingly.

#### Debugging hints

Sometimes this approach does not work because ICMP pings never receive a reply. Investigate the source address in this case. It is quite possible that the `fouX` interface you use didn't receive an IP address. In this case, your source IP is probably in a completely different subnet and any ICMP reply will end up in your network nirvana.

### Base station
This one is a bit trickier. We need a new interface for each client.

```bash
sudo ./udp-tunnel.sh up 4000 4040 10.0.0.40 84
```
Here, this interface is for `10.0.0.40`. We'd add more lines like this:
```bash
sudo ./udp-tunnel.sh up 4001 4041 10.0.0.41 84
sudo ./udp-tunnel.sh up 4002 4042 10.0.0.42 84
```
With that, we let the host know where to send packets to for different IP addresses. So is this it? Na. It ain't. We need to assign an IP address to the interface. Otherwise, the host doesn't send an IP address and eventually, we don't receive a response.


## IP Forwarding Firewall

Docker is a great tool sometimes. However, it relies heavily on fiddling with `iptables`. This might interfere with IP forwarding.

This command:
```bash
$ sudo iptables -I FORWARD -j ACCEPT
```
fixes all the IP forwarding issues.

See: https://serverfault.com/questions/1005648/docker-changes-iptables-forward-policy-to-drop
```bash
$ sudo iptables -I DOCKER-USER -j ACCEPT
$ sudo iptables -I FORWARD -j ACCEPT
```
In most cases, the second line suffices.

## UHD

### benchmark_rate
Find the location of `benchmark_rate` and then run this tool. It helps a lot in spotting connection issues.
```bash
./benchmark_rate --pps external --ref external --rx_channels "0,4" --tx_channels "2,6" --rx_rate 61.44e6 --tx_rate 61.44e6 --args="addr0=192.168.21.218,addr1=192.168.20.213,master_clock_rate=122.88e6" --duration=10
```
Or just for one device
```bash
./benchmark_rate --rx_channels "0,1" --tx_channels "2,3" --rx_rate 61.44e6 --tx_rate 61.44e6 --args="addr0=192.168.20.215,master_clock_rate=122.88e6" --duration=10
```


## Elasticsearch + Kibana hints
An elasticsearch + Kibana Docker container composition helps to visualize and gather data.

### Visualization
Use "Kibana -> Visualize -> Timelion"

Timelion expression reference

```js
.es(index=measurements-*,timefield=timestamp, metric=avg:qos.snr_lin).log(base=10).multiply(10).yaxis(label='SNR (dB)').label(label='RX estimate'),
.es(index=measurements-*,timefield=timestamp,metric=avg:qos.scale_factor),
```
These are some of the stripped down visualization commands.

### Kibana delete index
Go to "Management -> Elasticsearch/Index Management".
Select check box in front of index. A new button "Manage Index" appears. Select "Delete index" from drop-down menu.

### Kibana Discover
Here we can inspect all the values etc.

### Dev Tools - Edit Templates
This is important to edit templates. Just go to "Dev Tools".

Here is a reference to transform our timestamps to the correct data format!
```js
PUT _template/measurement_template
{
  "index_patterns": [
    "measurements-*"
  ],
  "settings": {
    "index.mapping.total_fields.limit": 1000000
  },
  "mappings": {
    "properties": {
      "timestamp": {
        "type": "date"
      }
    }
  }
}
```

## Anaconda notes
It is possible to install GNU Radio via Anaconda with conda etc. thanks to Ryan Volz. However, Anaconda3 integrates with `bash` by default only. Since we are notorious `zsh` powerlevel10k users, we need to follow [Anaconda3 ZSH integration instructions](https://stackoverflow.com/a/60996850).

[GNU Radio Conda Installation](https://wiki.gnuradio.org/index.php/CondaInstall)
For OOTs, it might be wise to skip the `conda install gnuradio-build-deps` step. So far, it tends to break things only. Needs further investigation. Instead, `conda install -c conda-forge fmt pybind11` is sufficient. Without the correct `pybind11` installation, funny messages about "missing base type gr::sync_block" arise because there seems to be version mismatches.
