import fitz,re,sys
doc=fitz.open('/home/jhan/workspace/titan/cache-perf/crb/refs/arm-cmn-s3-r2p3-trm-107858.pdf')
print('pages',len(doc))
def n(s): return re.sub(r'\s+',' ',s).strip().lower()
Q=[
(51,"Each XP in the following figure also has two device ports for connecting devices, P0 and P1"),
(51,"Depending on the configuration, the XP can have a maximum of four device ports for mesh configurations"),
(51,"MXPs with 4 mesh ports"),(51,"Can support up to 2 device ports"),
(51,"MXPs on the edge of the mesh with 3 mesh ports"),(51,"Can support up to 3 device ports"),
(51,"MXPs on the corners of the mesh with 2 mesh ports"),(51,"Can support up to 4 device ports"),
(15,"Mesh Crosspoints (MXPs) can support up to 4 devices: 4 device ports on the corner MXPs, 3 device ports on edge MXPs"),
(17,"In a mesh configuration, each XP can have up to four device ports for connecting CHI-compliant devices."),
(93,"You can expand the number of device ports on an MXP beyond the default number of two"),
(93,"The maximum permitted number of device ports per MXP is configuration-dependent."),
(1642,"por_mxp_device_port_connect_info_p0-5"),
(1655,"There are 6 iterations of this register. The index ranges from 0 to 5."),
(434,"por_mxp_device_port_connect_info_p3"),
(18,"Request Nodes (RNs) reside outside of the mesh and connect to CMN S3(AE) ports. Requesters with coherent caches, which includes processors, GPUs, or processing elements with internal coherent caches, are referred to as RN-F devices. They connect directly to the CMN S3(AE) interconnect mesh using a CHI RN-F port."),
(364,"Internal XPs and external RN-F or SN-F devices can generate a trace tag."),
(99,"All CPUs, RN-Fs, are present on compute chiplet."),
(17,"256 CHI RN-F ports"),
(19,"There are three types of HN devices within the CMN S3(AE) system"),
(19,"HN-S device instances, act as HN-F nodes for local coherent memory and Local Coherency Nodes (LCNs) for remote coherent memory"),
(19,"Each HN-S can contain an SF and an SLC"),
(55,"The Super Home Node (HN-S) is responsible for managing part of the local address space and managing local coherency for part of the remote address space"),
(55,"In this book any descriptions related to the HN-F also apply to the HN-S."),
(434,"Isolation status indication for HN-F or HN-S, bit[30]"),
(434,"the device port connection information register for the device port that the child node is connected to"),
(96,"HN-F or HN-S devices attached to a CAL2 can be logically isolated from the corresponding MXP and mesh."),
(63,"A Component Aggregation Layer (CAL) allows multiple devices to connect to a single device port on an XP."),
(63,"CAL that can connect to two identical devices."),
(64,"CAL that can connect to four identical devices."),
(64,"A special CAL that can support two different device types"),
(64,"A special CAL that can support three devices."),
(65,"All devices that are connected to a single CAL must be of the same type and must be configured identically."),
(64,"SN-FG, SN-FF, SN-FE, RN-FG_ESAM, RN-FF_ESAM, RN-FE_ESAM, RN-FD_ESAM, HN-S, HN-P, HN-F"),
(64,"RN-FG_ESAM, RN-FG_ESAM, HN-I"),(64,"RN-FF_ESAM, RN-FF_ESAM, HN-I"),(64,"RN-FE_ESAM, RN-FE_ESAM, HN-I"),
(26,"CAL4 is supported from RN-F CHI-D or later"),
(65,"CAL4 is a physical block that has 4 devices, of all the same type device, attached to it"),
(1655,"Number of devices connected to this port (0 to 4)"),
(130,"CMN S3(AE) does not support CAL4 in configurations where an SMXP has more than two device port connections."),
(131,"If using CAL in a CMN S3(AE) mesh configuration with extra device ports, only CAL2 configurations are permitted."),
(26,"The number of RN-Fs in the system."),(26,"0-256 with no CAL, CAL2 or CAL4"),
(26,"0-64 without CAL"),(26,"2-128 with CAL2"),(26,"4-128 with CAL4"),(26,"When CAL is present, the number of HN-Ss must be even."),
(26,"CMN S3(AE) does not support a mixed configuration of HN-F and HN-S device types"),
(1647,"Connected device type"),(1648,"0b100001 RN-F_CHIF_ESAM"),(1648,"0b011010 HN-S"),(1648,"0b100000 RN-F_CHIF"),(1648,"0b100100 RN-F_CHIG_ESAM"),
(1655,"ESAM enable"),
(1646,"When set, CAL is connected on port"),(1646,"Number of CAL credited slices connected to port"),
(1646,"Number of device credited slices connected to port #{index} device 3"),
(1655,"Total number of RN-F AXIU interfaces at this port (0 to 4)"),
(1642,"por_mxp_p0-5_info"),
(23,"DEVICE_ISO_EN"),(23,"MXP Device Isolation Enable"),(23,"HN-F and HN-S devices are isolated out of reset when enabled"),
(96,"This isolation occurs by default if the DEVICE_ISO_EN configuration parameter is enabled."),
(96,"Configuration writes to the MXP por_mxp_device_port_disable registers are required to remove the isolation after reset"),
(97,"Configure CMN SAMs and overall system address map to avoid disabled HN-F or HN-S devices."),
(97,"The HN-F or HN-S isolation status can be determined by the discovery process, indication is in the corresponding child_pointer[30] register.bit for each HN-F and HN-S."),
(1653,"Child node owned by an isolated device"),(1653,"Indicates this child points is isolated. Thus, the child node cannot be read or accessed."),
(1667,"Controls whether a device port attached to the SMXP is disabled"),(1667,"0xA70"),(1668,"p5_device_disable"),(1668,"Disable device 0"),
(95,"The AXU is connected to RN-F and SN-F node locations as an AXI5 requester port."),
(96,"each DSU occupies a 1MB, 4MB, 16MB, or 64MB fixed space"),
]
pages=[n(p.get_text()) for p in doc]
for pg,q in Q:
    qq=n(q)
    if qq in pages[pg-1]: print('OK  ',pg,q[:60])
    else:
        hits=[i+1 for i,t in enumerate(pages) if qq in t][:8]
        print('MISS',pg,q[:70],'-> found on',hits)
