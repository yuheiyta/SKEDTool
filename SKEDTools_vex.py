from schedule_text import normalize_text
from astropy.coordinates import SkyCoord, ICRS, ITRS, Galactic, FK4, FK5, EarthLocation, AltAz
from astropy.coordinates import get_sun
from astropy import constants as const
import astropy.units as u
import numpy as np
from astropy.time import Time, TimeDelta
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import dates as mdates
from astroquery.simbad import Simbad
import pickle, sys
from pathlib import Path

plt.rcParams['font.size'] = 12
plt.rcParams['xtick.direction'] = 'in'
plt.rcParams['ytick.direction'] = 'in'

#matplotlib.use("svg")
#matplotlib.use("Agg")

class VEX:
    def __init__(self, header=None, glob=None, exper=None, mode=None, procedures=None, freq=None, if_=None, bbc=None, station=None, das=None, source=None, sched=None, site=None, antenna=None):
        self.header = header
        self.glob = glob
        self.exper = exper
        self.mode = mode
        self.procedures = procedures
        self.freq = freq
        self.if_ = if_
        self.bbc = bbc
        self.station = station 
        self.das = das
        self.source = source
        self.sched = sched
        self.site = site
        self.antenna = antenna

    # have to be changed
    def read(self, filename):
        with open(filename, encoding="utf-8-sig") as stream:
            self.readtxt(stream.read())

    def readtxt(self, text):
        text = normalize_text(text)
        candidate = VEX()
        candidate._readtxt(text)
        self.__dict__.update(candidate.__dict__)

    def _readtxt(self, text):
        alllines = text.splitlines()
        lines = Ext_section(alllines,"HEADER",readcomment=True)
        self.header = VEX_Header(lines)
        lines = Ext_section(alllines,"GLOBAL",readcomment=True)
        glob = Read_globallines(lines)
        self.glob = glob
        lines = Ext_section(alllines,"EXPER",readcomment=True)
        exper = Read_experline(lines)
        self.exper = exper
        lines = Ext_section(alllines,"MODE",readcomment=True)
        mode = Read_modelines(lines)
        self.mode = mode
        lines = Ext_section(alllines,"PROCEDURES",readcomment=True)
        proc = Read_proclines(lines)
        self.procedures = proc
        lines = Ext_section(alllines,"FREQ",readcomment=True)
        freq = Read_freqlines(lines)
        self.freq = freq
        lines = Ext_section(alllines,"IF",readcomment=True)
        v_if = Read_IFlines(lines)
        self.if_ = v_if
        lines = Ext_section(alllines,"BBC",readcomment=True)
        bbc = Read_bbclines(lines)
        self.bbc = bbc
        lines = Ext_section(alllines,"STATION",readcomment=True)
        station = Read_stationlines(lines)
        self.station = station
        lines = Ext_section(alllines,"DAS",readcomment=True)
        das = Read_daslines(lines)
        self.das = das
        lines = Ext_section(alllines,"SOURCE",readcomment=True)
        source = Read_srclines(lines)
        self.source = source
        lines = Ext_section(alllines,"SCHED",readcomment=True)
        sched = Read_schedlines(lines)
        self.sched = sched
        lines = Ext_section(alllines,"SITE",readcomment=True)
        site = Read_sitelines(lines)
        self.site = site
        lines = Ext_section(alllines,"ANTENNA",readcomment=True)
        antenna = Read_antlines(lines)
        self.antenna = antenna
        self.adjust()
    def write(self, filename):
        text = self.output()
        if hasattr(filename, "write"):
            filename.write(text + "\n")
        else:
            Path(filename).write_text(text + "\n", encoding="utf-8")

    def output_sys(self):
        self.write(file=sys.stdout)
    def output(self):
        outtxt = self.header.output()+"\n"+self.glob.output()+"\n"+self.exper.output()+"\n"+self.mode.output()+"\n"+self.procedures.output()+"\n"+self.freq.output()+"\n"+self.if_.output()+"\n"+self.bbc.output()+"\n"+self.station.output()+"\n"+self.das.output()+"\n"+self.source.output()+"\n"+self.sched.output()+"\n"+self.site.output()+"\n"+self.antenna.output()
        return outtxt
    def shift(self,timedelta):
        self.sched.shift(timedelta)
    def dayshift(self,days):
        self.sched.dayshift(float(days))
    def sourceplot(self,coord="equitorial",showlabel=True):
        fig=self.source.plot(coord,showlabel)
        return fig
    def el_plot(self,srcnames=[],refant="",timezone="lst",ellim=[],timelim=[]):
        # If timezone="lst", timelim must be float (or numeric) object. If timezone = 'ut' or like that, timelim must be datetime object.
        locations = [antenna for antenna in self.site.list]
        if(refant!=""):
            for i,location in enumerate(locations):
                if(location.id==refant):
                    tmplocation = locations[0]
                    locations[0] = location
                    locations[i] = tmplocation                    
        refantname=locations[0].name
        srcs =[]
        for selsrcname in srcnames:
            for source in self.source.list:
                if(source.name==selsrcname or source.name2==selsrcname):
                    srcs.append(source)
        try:
            obsdate = self.sched.list[0].start.iso.split()[0]
        except:
            obsdate = '2024-04-01'
        start_time = Time(obsdate+'T00:00:0.0',location=locations[0].coord)
        time_length = 24.
        num=100
        dt=time_length*3600./num
        dt_time = TimeDelta(dt, format='sec')
        fig=plt.figure(figsize=(8,6*len(srcs)))
        ax=[]
        for ax_i,src in enumerate(srcs):
            j=0
            ax.append(fig.add_subplot(len(srcs), 1, ax_i+1))
            timelist = []
            for loc_i,location in enumerate(locations):
                el_array = []
                obstime = start_time
                for i in range(int(time_length*60*60/dt)):
                    altaz,az,el=trans_azel(src.coord,obstime,location.coord)
                    el_array.append(el)
                    if(j==0):
                        #print(ax_i,"check",timezone)
                        if(timezone=='lst'.casefold()):
                            #print("lst_check")
                            lsttime=obstime.sidereal_time('apparent')
                            timelist.append(lsttime.to_value())
                        elif(timezone.casefold()=='ut' or timezone.casefold()=='utc'):
                            timelist.append(obstime.datetime)
                        elif(timezone.casefold()=='jst'):
                            timelist.append((obstime+TimeDelta(9.*u.hour)).datetime)
                    obstime = obstime+dt_time
                #print(timelist, np.ma.masked_outside(el_array,0.5,90.))
                ax[-1].scatter(timelist, np.ma.masked_outside(el_array,0.5,90.),label=location.name)
                j+=1
            ax[-1].set_title(src.name)
            ax[-1].grid()
            if(timezone=='lst'.casefold()):
                ax[-1].set_xlabel("Time (LST), Reference = "+refantname)
            elif(timezone=='ut'.casefold() or timezone=='utc'.casefold()):
                ax[-1].set_xlabel("Time (UT) in "+obsdate)
            elif(timezone=='jst'.casefold()):
                ax[-1].set_xlabel("Time (JST) in "+obsdate)
            ax[-1].set_ylabel("Elevation (deg)")
            if(timezone=='lst'.casefold()):
                ax[-1].set_xlim(-0.1,24.1)
            else:
                ax[-1].set_xlim(timelist[0],timelist[-1])
                ax[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H"))            
            ax[-1].set_ylim(0,)
            ax[-1].xaxis.set_ticks_position('both')
            ax[-1].yaxis.set_ticks_position('both')
            if(len(ellim)>=1):
                for el in ellim:
                    ax[-1].axhline(y=el,color="black",ls="dashed")
            if(len(timelim)>=1):
                for time in timelim:
                    ax[-1].axvline(x=time,color="black",ls="dotted")
            ax[-1].legend()
            fig.tight_layout()
            #plt.savefig(objnames[0]+"_elplot.jpeg")
            #plt.show()
        return fig
    def uvplot(self,srcname,antcodes=[], td = 10., length = False): # td: sec
        obstimelist = []
        if(antcodes == []):
            check_antcodes = True
        else:
            check_antcodes = False
        freq = self.freq.list[0].chan_def[0].split()[1]*u.MHz
        wavelength = (const.c/freq).to(u.m).value
        for source in self.source.list:
            if(source.name==srcname or source.name2==srcname):
                src=source
        for sched in self.sched.list:
            if(sched.source1 == srcname or sched.source2 == srcname):
                num = int(sched.dur.to(u.s).value/td)
                obstime = sched.start + (TimeDelta(td*u.s) * np.arange(num))
                obstimelist = np.append(obstimelist,obstime)
                if(check_antcodes):
                    antcodes = sched.antcodes
                    check_antcodes = True
        sites = []
        x,y,z = [],[],[]
        for site in self.site.list:
            if(site.id in antcodes):
                sites.append(site.coord)
                x.append(site.coord.x.value)
                y.append(site.coord.y.value)
                z.append(site.coord.z.value)
        data = {"x":x,"y":y,"z":z}
        ref = calc_ant_center(sites)
        local_xyz = EarthLocation.from_geocentric(data["x"], data["y"], data["z"], u.m)
        enu_coords = np.array(earth_location_to_local_enu(local_xyz, ref))
        antenna_ids = np.arange(0, enu_coords.shape[1])
        n_antennas = len(antenna_ids)
        
        # Calculate combinations of pairs of antennas in ENU coordinates
        b_enu = enu_coords[..., np.newaxis] - enu_coords[:, np.newaxis,:]
        # We discard the diagonal which has no pairs
        b_enu = b_enu[:, ~np.eye(b_enu.shape[-1],dtype=bool)]
        
        # We calculate the distance between different pairs of antennas
        abs_b = np.sqrt(np.sum(b_enu**2, axis=0))
        baselines_distance_2d = np.sqrt(np.sum(b_enu[0:2]**2, axis=0))
        max_baseline = np.max(baselines_distance_2d)
        idx_nearest_zero = np.argmin(np.sqrt(np.sum(enu_coords[0:2]**2, axis=0)))
        antenna_nearest_zero = enu_coords[:, idx_nearest_zero]
        farthest_antenna = np.max(np.sqrt(np.sum((enu_coords[0:2] - antenna_nearest_zero[0:2, np.newaxis])**2, axis=0)))
        #print(max_baseline/1000) # km

        # For antenna location plot
        # fig, ax = plt.subplots(layout='constrained')
        
        # dish_circle = plt.Circle((antenna_nearest_zero[0]/1000, antenna_nearest_zero[1]/1000), farthest_antenna/1000, facecolor="white", edgecolor='r', alpha=0.25)
        # ax.plot(enu_coords[0]/1000, enu_coords[1]/1000, '.k')
        # ax.add_patch(dish_circle)
        # ax.set(
        #         aspect=1,
        #         xlabel='West-East / km',
        #         ylabel='South-North / km'
        # )
        # plt.show()
        # We convert coordinates from ENU to ALT-AZ
        azimuth, elevation = enu_to_local_altaz(b_enu, abs_b)
        # We get the latitude of the COA in radians
        latitude = ref.to_geodetic().lat.to(u.rad).value
        # We convert baselines coordinates from ALT-AZ to Equatorial
        x_equatorial = np.cos(latitude) * np.sin(elevation) - np.sin(latitude) * np.cos(elevation) * np.cos(azimuth)
        y_equatorial = np.cos(elevation) * np.sin(azimuth)
        z_equatorial = np.sin(latitude) * np.sin(elevation) + np.cos(latitude) * np.cos(elevation) * np.cos(azimuth)
        xyz_equatorial =  abs_b * np.vstack([x_equatorial, y_equatorial, z_equatorial])
        
        # We set the observed Hour Angle and the declination
        HA = []
        for obstime in obstimelist:
            HA.append((obstime.sidereal_time('mean', 'greenwich') - src.coord.ra.to(u.hourangle)).value % 24)
        HA = HA*u.hourangle
        dec = src.coord.dec
        # We calculate the rotation matrix
        R_matrix = calc_R(HA, dec)
        
        uvw_meters = np.sum(R_matrix[...,np.newaxis] * xyz_equatorial[np.newaxis,:,np.newaxis,:], axis=1)
        fig, ax = plt.subplots()
        ax.xaxis.set_ticks_position('both')
        ax.yaxis.set_ticks_position('both')
        if(length):
            range = max(np.max(uvw_meters[0]/1e3),np.max(uvw_meters[1]/1e3))
            ax.scatter(uvw_meters[0]/1e3,uvw_meters[1]/1e3, c="black", marker=".", s=0.4)
            ax.set_xlabel('u (km)') 
            ax.set_ylabel('v (km)')
        else:
            range = max(np.max(uvw_meters[0]/wavelength/1e6),np.max(uvw_meters[1]/wavelength/1e6))
            ax.scatter(uvw_meters[0]/wavelength/1e6,uvw_meters[1]/wavelength/1e6, c="black", marker=".", s=0.4)
            ax.set_xlabel('u (M$\\lambda$)') 
            ax.set_ylabel('v (M$\\lambda$)')
        range=range+(range*0.1)
        ax.set_xlim(-range, range)
        ax.set_ylim(-range, range)
        ax.set_aspect('equal')
        return fig
    def check(self):
        # Check Az, El limit and slew speed. Only at the beginning an end of each scan.
        # If obsmode = "2 beam", we check the separation angle.
        # sourcelist = self.source
        # antennalist = self.station
        prevtime=0
        numerror = 0
        msg = []
        if not self.sched.list:
            return ["No scans to check"]
        for scan in self.sched.list:
            if not getattr(scan, "antennas", None):
                raise ValueError("No antennas resolved for scan " + scan.defname)
        starttime = self.sched.list[0].start.yday.split(":")
        #print(starttime)
        if(int(starttime[2])==0 and int(starttime[3])<20):
            msg.append("Warning: Start time is too close to the start of the day.")
            numerror+=1
        for sked in self.sched.list:
            antprev_tmp = []
            i=0
            if(len(sked.src)==1):
                direction = sked.src[0].coord
            elif(len(sked.src)==2):
                first, second = sked.src[0].coord, sked.src[1].coord
                sep = first.separation(second)
                # Follow the great circle so RA wrapping and polar fields work.
                direction = first.directional_offset_by(
                    first.position_angle(second), sep / 2.0
                )
                for antenna in sked.antennas:
                    if(sep < antenna.beam_lim[0] or antenna.beam_lim[1] < sep):
                        msg.append("Souce separation is not within the range, {:.2f} deg".format(sep.deg))
                        numerror+=1
            else:
                msg.append("No souce in Sched")
                numerror+=1
            for sked_antenna in sked.antennas:
                altaz_i = direction.transform_to(AltAz(obstime=sked.start, location=sked_antenna.coord))
                altaz_e = direction.transform_to(AltAz(obstime=sked.start+sked.dur, location=sked_antenna.coord))
                if(altaz_i.alt.deg < float(sked_antenna.lim[1][0]) or float(sked_antenna.lim[1][1]) < altaz_i.alt.deg):
                    msg.append("antenna elevation limit, el ={:.2f} deg, {}, {}, {}".format(altaz_i.alt.deg, sked.source1, sked.start, sked_antenna.name))
                    numerror+=1
                if(altaz_e.alt.deg < float(sked_antenna.lim[1][0]) or float(sked_antenna.lim[1][1]) < altaz_e.alt.deg):
                    msg.append("antenna elevation limit, el ={:.2f} deg, {}, {}, {}".format(altaz_i.alt.deg, sked.source1, sked.start+sked.dur, sked_antenna.name))
                    numerror+=1
                if(abs(sked_antenna.lim[0][1]-sked_antenna.lim[0][0])< 360.):
                    if(altaz_i.az.deg < float(sked_antenna.lim[0][0]) or float(sked_antenna.lim[0][1]) < altaz_i.az.deg):
                        msg.append("antenna azimuth limit, az = {:.2f} deg, {}, {}, {}".format(altaz_i.az.deg, sked.source1, sked.start, sked_antenna.name))
                        numerror+=1
                    if(altaz_e.az.deg < float(sked_antenna.lim[0][0]) or float(sked_antenna.lim[0][1]) < altaz_e.az.deg):
                        msg.append("antenna azimuth limit, az = {:.2f} deg, {}, {}, {}".format(altaz_i.az.deg, sked.source1, sked.start+sked.dur, sked_antenna.name))
                        numerror+=1
                antprev_tmp.append(altaz_e)
                if(prevtime!=0):
                    if(abs(sked_antenna.lim[0][1]-sked_antenna.lim[0][0])< 360.):
                        if(np.abs((prevpos[i].az.deg - altaz_i.az.deg)/float(sked_antenna.rate[0])) > (sked.start - prevtime).sec/60.):
                            msg.append("antenna on-source delay (az), {}, {}".format(sked.start, sked_antenna.name))
                            numerror+=1
                        if(np.abs(prevpos[i].alt.deg - altaz_i.alt.deg)/float(sked_antenna.rate[1]) > (sked.start - prevtime).sec/60.):
                            msg.append("antenna on-source delay (el), {}, {}".format(sked.start, sked_antenna.name))
                            numerror+=1
                    else:
                        azdiff = np.abs(prevpos[i].az.deg - altaz_i.az.deg)
                        if(azdiff > 180.):
                            azdiff = 360.-azdiff
                        if(azdiff/float(sked_antenna.rate[0]) > (sked.start - prevtime).sec/60.):
                            msg.append("antenna on-source delay (az), {}, {}".format(sked.start, sked_antenna.name))
                            numerror+=1
                        if(np.abs(prevpos[i].alt.deg - altaz_i.alt.deg)/float(sked_antenna.rate[1]) > (sked.start - prevtime).sec/60.):
                            msg.append("antenna on-source delay (el), {}, {}".format(sked.start, sked_antenna.name))
                            numerror+=1
                i+=1
            prevtime = sked.start+sked.dur
            prevpos = antprev_tmp
        if(numerror==0):
            msg.append("check: OK")
        else:
            msg.append("End. NumError="+str(numerror))
        return msg
    def adjust(self,delete=False):
        for station in self.station.list:
            for antenna in self.antenna.list:
                if(station.antenna == antenna.defname):
                    for site in self.site.list:
                        if(site.name == station.site):
                            antenna.coord = site.coord
                            continue
        useantennas = []
        usesources = []
        if(delete):
            for sked in self.sched.list:
                for sked_antenna in sked.antcodes:
                    if(sked_antenna not in useantennas):
                        useantennas.append(sked_antenna)
                if(sked.source1 not in usesources):
                    usesources.append(sked.source1)
                if(sked.source2 not in usesources):
                    usesources.append(sked.source2)
            # for antenna in self.station.list:
            #     if(antenna.id not in useantennas):
            #         self.station.delete(antenna)
            # for source in self.source.sources:
            #     if(source.name not in usesources):
            #         self.source.delete(source)
        if(self.source!= None and self.sched!=None and self.station!=None):
            # corresponding source
            start_list=[]
            for sked in self.sched.list:
                start_list.append(sked.start.mjd)
                name1 = sked.source1
                name2 = sked.source2
                if(name2 != ""):
                    two_beam = True
                else:
                    two_beam = False
                sked_source1=None
                sked_source2=None
                for source in self.source.list:
                    if(name1 == source.name):
                        sked_source1 = source
                    if(name2 == source.name):
                        sked_source2 = source
                if(sked_source1==None):
                    raise ValueError("No corresponding source in schedule")
                if(two_beam and sked_source2==None):
                    raise ValueError("No corresponding source in schedule")
                if(two_beam):
                    sked_source = [sked_source1, sked_source2]
                else:
                    sked_source = [sked_source1]
                antcodes = sked.antcodes
                sked_antennas=[]
                for antcode in antcodes:
                    for station in self.station.list:
                        if(antcode == station.defname):
                            for antenna in self.antenna.list:
                                if(station.antenna == antenna.defname):
                                    sked_antennas.append(antenna)
                                    continue
                if(len(sked_antennas)!=len(sked.antcodes)):
                    raise ValueError("No corresponding antenna(s): " + ", ".join(antcodes))
                sked.src = sked_source
                sked.antennas = sked_antennas
            changeorder = False
            sorted_list=sorted(start_list)
            if(start_list!=sorted_list):
                changeorder = True
            for i, sked in enumerate(self.sched.list):
                if(i+1 != int(sked.defname.strip("No"))):
                    changeorder = True
            if(changeorder):
                arglist=np.argsort(start_list)
                self.sched.list = [self.sched.list[i] for i in arglist]
                for i,sked in enumerate(self.sched.list):
                    sked.defname = f"No{i+1:05d}"
                print("Changed sked order")

class VEX_Header:
    def __init__(self,headlines):
        self.list = headlines
    def add(self, append):
        self.list.append(append)
    def delete(self, remove):
        self.list.remove(remove)
    def output(self):
        lines=[]
        for s in self.list:
            lines.append(s)
        return "\n".join(lines)


class VEX_Exper:
    def __init__(self):
        self.list = []
    def add(self, append):
        self.list.append(append)
    def delete(self, remove):
        self.list.remove(remove)
    def output(self):
        lines=["$EXPER;\n"]
        for s in self.list:
            lines.append(s.output())
        return "*\n".join(lines)+"*"

class Exper:
    def __init__(self, defname, target_correlator="", exper_name="", exper_description="", exper_nominal_start="", exper_nominal_stop="", PI_name="", PI_email="", contact_name="",contact_email="", scheduler_name="", scheduler_email="",comment=""):
        self.defname = defname
        self.name = exper_name
        self.correlator = target_correlator
        self.description = exper_description
        self.start = exper_nominal_start
        self.stop = exper_nominal_stop
        self.pi_name = PI_name
        self.pi_email = PI_email
        self.contact_name = contact_name
        self.contact_email = contact_email
        self.scheduler_name = scheduler_name
        self.scheduler_email = scheduler_email     
        self.comment=comment
    def output(self):
        lines=[]
        if(self.comment != ""):
            lines.append(f"{self.comment:s}")
        lines.append(f"def {self.defname:s};")
        lines.append(f"     target_correlator = {self.correlator:s};")
        lines.append(f"     exper_name = {self.name:s};")
        lines.append(f"     exper_description = {self.description:s};")
        lines.append(f"     exper_nominal_start = {self.start:s};")
        lines.append(f"     exper_nominal_stop = {self.stop:s};")
        lines.append(f"     PI_name = {self.pi_name:s};")
        lines.append(f"     PI_email = {self.pi_email:s};")
        lines.append(f"     contact_name = {self.contact_name:s};")
        lines.append(f"     contact_email = {self.contact_email:s};")
        lines.append(f"     scheduler_name = {self.scheduler_name:s};")
        lines.append(f"     scheduler_email = {self.scheduler_email:s};")
        lines.append("enddef;")
        return "\n".join(lines)+"\n"

class VEX_Global:
    def __init__(self, exper, procedures, comment=""):
        self.exper = exper
        self.procedures = procedures
        self.comment = comment
    def output(self):
        lines=["$GLOBAL;"]
        if(self.comment != ""):
            lines.append(f"{self.comment:s}")
        lines.append(f"     ref $EXPER = {self.exper:s};")
        lines.append(f"     ref $PROCEDURES = {self.procedures:s};")
        return "\n".join(lines)+"\n"

class VEX_Procedures:
    def __init__(self):
        self.list = []
    def add(self, append):
        self.list.append(append)
    def delete(self, remove):
        self.list.remove(remove)
    def output(self):
        lines=["$PROCEDURES;\n"]
        for s in self.list:
            lines.append(s.output())
        return "*\n".join(lines)+"*"

class Procedure:
    def __init__(self, defname, tape_change=[], beam1=[], beam2=[], preob_cal=[], midob_cal=[], postob_cal=[], comment="" ):
        self.defname = defname
        self.comment = comment
        self.tape_change = tape_change
        self.beam1 = beam1
        self.beam2 = beam2
        self.preob_cal = preob_cal
        self.midob_cal = midob_cal
        self.postob_cal = postob_cal
    def output(self):
        lines=[]
        if(self.comment != ""):
            lines.append(f"{self.comment:s}")
        lines.append(f"def {self.defname:s};")
        if(self.tape_change != []):
            for ll in self.tape_change:
                lines.append(f"     tape_change =  {ll:s};")
        if(self.beam1 != []):
            for ll in self.beam1:
                lines.append(f"     beam1 =  {ll:s};")
        if(self.beam2 != []):
            for ll in self.beam2:
                lines.append(f"     beam2 =  {ll:s};")
        if(self.preob_cal != []):
            for ll in self.preob_cal:
                lines.append(f"     preob_cal =  {ll:s};")
        if(self.midob_cal != []):
            for ll in self.midob_cal:
                lines.append(f"     midob_cal =  {ll:s};")
        if(self.postob_cal != []):
            for ll in self.postob_cal:
                lines.append(f"     postob_cal =  {ll:s};")
        lines.append("enddef;")
        return "\n".join(lines)+"\n"
        
class VEX_Mode:
    def __init__(self):
        self.list = []
    def add(self, append):
        self.list.append(append)
    def delete(self, remove):
        self.list.remove(remove)
    def output(self):
        lines=["$MODE;\n"]
        for s in self.list:
            lines.append(s.output())
        return "*\n".join(lines)+"*"
class Mode:
    def __init__(self, defname, procedures, freq, if_, bbc, comment=""):
        self.defname = defname
        self.procedures = procedures
        self.freq = freq
        self.if_ = if_
        self.bbc = bbc
        self.comment = comment
    def output(self):
        lines=[]
        if(self.comment != ""):
            lines.append(f"{self.comment:s}")
        lines.append(f"def {self.defname:s};")
        lines.append(f"     ref $PROCEDURES = {self.procedures:s};")
        lines.append(f"     ref $FREQ = {self.freq:s};")
        lines.append(f"     ref $IF = {self.if_:s};")
        lines.append(f"     ref $BBC = {self.bbc:s};")
        lines.append("enddef;")
        return "\n".join(lines)+"\n"

class VEX_Station:
    def __init__(self):
        self.list = []
    def add(self, append):
        self.list.append(append)
    def delete(self, remove):
        self.list.remove(remove)
    def output(self):
        lines=["$STATION;\n"]
        for s in self.list:
            lines.append(s.output())
        return "*\n".join(lines)+"*"
class Station:
    def __init__(self, defname, site, antenna, das, comment=""):
        self.defname = defname
        self.site = site
        self.antenna = antenna
        self.das = das
        self.comment = comment
    def output(self):
        lines=[]
        if(self.comment != ""):
            lines.append(f"{self.comment:s}")
        lines.append(f"def {self.defname:s};")
        lines.append(f"     ref $SITE = {self.site:s};")
        lines.append(f"     ref $ANTENNA = {self.antenna:s};")
        lines.append(f"     ref $DAS = {self.das:s};")
        lines.append("enddef;")
        return "\n".join(lines)+"\n"
        
class VEX_Freq:
    def __init__(self):
        self.list = []
    def add(self, append):
        self.list.append(append)
    def delete(self, remove):
        self.list.remove(remove)
    def output(self):
        lines=["$FREQ;\n"]
        for s in self.list:
            lines.append(s.output())
        return "*\n".join(lines)+"*"
class Freq:
    def __init__(self, defname, sample_rate, chan_def, comment=""):
        self.defname = defname
        self.sample_rate = sample_rate
        self.chan_def = chan_def
        self.comment=comment
# chandef=[["&R1: 42834.000000 MHz: L: 16.00 MHz: &S01 : &BBCa : &NoCal"]]
    def output(self):
        lines=[]
        if(self.comment != ""):
            lines.append(f"{self.comment:s}")
        lines.append(f"def {self.defname:s};")
        lines.append(f"     sample_rate = {self.sample_rate:s};")
        for ll in self.chan_def:
            lines.append(f"     chan_def =  {ll:s};")
        lines.append("enddef;")
        return "\n".join(lines)+"\n"

class VEX_IF:
    def __init__(self):
        self.list = []
    def add(self, append):
        self.list.append(append)
    def delete(self, remove):
        self.list.remove(remove)
    def output(self):
        lines=["$IF;\n"]
        for s in self.list:
            lines.append(s.output())
        return "*\n".join(lines)+"*"
class IF:
    def __init__(self, defname, if_def, comment=""):
        self.defname = defname
        self.if_def = if_def
        self.comment=comment
#if_def = [["&IF_R1: B1: L: 2000.0 MHz: U"]]
    def output(self):
        lines=[]
        if(self.comment != ""):
            lines.append(f"{self.comment:s}")
        lines.append(f"def {self.defname:s};")
        for ll in self.if_def:
            lines.append(f"     if_def =  {ll:s};")
        lines.append("enddef;")
        return "\n".join(lines)+"\n"

class VEX_BBC:
    def __init__(self):
        self.list = []
    def add(self, append):
        self.list.append(append)
    def delete(self, remove):
        self.list.remove(remove)
    def output(self):
        lines=["$BBC;\n"]
        for s in self.list:
            lines.append(s.output())
        return "*\n".join(lines)+"*"
class BBC:
    def __init__(self, defname, bbc_assign, comment=""):
        self.defname = defname
        self.bbc_assign = bbc_assign
        self.comment=comment
#bbc_assign = [["&BBCa:  1: &IF_R1"]]
    def output(self):
        lines=[]
        if(self.comment != ""):
            lines.append(f"{self.comment:s}")
        lines.append(f"def {self.defname:s};")
        for ll in self.bbc_assign:
            lines.append(f"     BBC_assign = {ll:s};")
        lines.append("enddef;")
        return "\n".join(lines)+"\n"

class VEX_DAS:
    def __init__(self):
        self.list = []
    def add(self, append):
        self.list.append(append)
    def delete(self, remove):
        self.list.remove(remove)
    def output(self):
        lines=["$DAS;\n"]
        for s in self.list:
            lines.append(s.output())
        return "*\n".join(lines)+"*"
class DAS:
    def __init__(self, defname, record_transport_type="", electronics_rack_type="", number_drives="", tape_length="", tape_motion="", comment=""):
        self.defname = defname
        self.record = record_transport_type
        self.electronics = electronics_rack_type
        self.number_drives = str(number_drives)
        self.tape_length = tape_length
        self.tape_motion = tape_motion
        self.comment = comment
    def output(self):
        lines=[]
        if(self.comment != ""):
            lines.append(f"{self.comment:s}")
        lines.append(f"def {self.defname:s};")
        lines.append(f"     record_transport_type = {self.record:s};")
        lines.append(f"     electronics_rack_type = {self.electronics:s};")
        lines.append(f"     number_drives = {self.number_drives:s};")
        lines.append(f"     tape_length = {self.tape_length:s};")
        lines.append(f"     tape_motion = {self.tape_motion:s};")
        lines.append("enddef;")
        return "\n".join(lines)+"\n"
    
class VEX_Site:
    def __init__(self):
        self.list = []
    def add(self, append):
        self.list.append(append)
    def delete(self, remove):
        self.list.remove(remove)
    def output(self):
        lines=["$SITE;\n"]
        for s in self.list:
            lines.append(s.output())
        return "*\n".join(lines)+"*"
class Site:
    def __init__(self, defname, site_type, site_name, site_ID, site_position, comment=""):
        self.defname = defname
        self.comment = comment
        self.type = site_type
        self.name = site_name
        self.id = site_ID
        self.position = site_position
        x,y,z = site_position.split(":")
        self.coord = EarthLocation(x=float(x[:-1])*u.m, y=float(y[:-1])*u.m, z=float(z[:-1])*u.m)
    @property
    def position(self):
        return self._position
    @position.setter
    def position(self, value):
        self._position = value
        x,y,z = value.split(":")
        self.coord = EarthLocation(x=float(x[:-1])*u.m, y=float(y[:-1])*u.m, z=float(z[:-1])*u.m)
    def output(self):
        lines=[]
        if(self.comment != ""):
            lines.append(f"{self.comment:s}")
        lines.append(f"def {self.defname:s};")
        lines.append(f"     site_type = {self.type};")
        lines.append(f"     site_name = {self.name};")
        lines.append(f"     site_ID = {self.id};")
        lines.append(f"     site_position = {self.position};")
        lines.append("enddef;")
        return "\n".join(lines)+"\n"
        
class VEX_Antenna:
    def __init__(self):
        self.list = []
    def add(self, append):
        self.list.append(append)
    def delete(self, remove):
        self.list.remove(remove)
    def output(self):
        lines=["$ANTENNA;\n"]
        for s in self.list:
            lines.append(s.output())
        return "*\n".join(lines)+"*"
class Antenna:
    def __init__(self, defname, antenna_diam, antenna_name, axis_type, axis_offset, antenna_motion, pointing_sector, multi_beam_number, multi_beam_type, beam_separation, field_rotation, comment=""):
        self.defname = defname
        self.comment = comment
        self.diam = antenna_diam
        self.name = antenna_name
        self.axis_type = axis_type
        self.axis_offset = axis_offset
        self.motion = antenna_motion
        self.pointing_sector = pointing_sector
        self.multi_beam_number = multi_beam_number
        self.multi_beam_type = multi_beam_type
        self.beam_separation = beam_separation
        self.field_rotation = field_rotation
    @property
    def motion(self):
        return self._motion
    @motion.setter
    def motion(self, value):
        self._motion = value
        for line in value:
            line = line.replace(":","")
            if(line.split()[0] == "az"):
                if(line.split()[2] == "deg/min"):
                    rate1 = line.split()[1]
                else:
                    print("Unit may not be deg/min")
            if(line.split()[0] == "el"):
                if(line.split()[2] == "deg/min"):
                    rate2 = line.split()[1]
                else:
                    print("Unit may not be deg/min")
        self.rate = [float(rate1),float(rate2)]
    @property
    def pointing_sector(self):
        return self._pointing_sector
    @pointing_sector.setter
    def pointing_sector(self, value):
        self._pointing_sector = value
        for i,line in enumerate(value):
            line = line.replace(":","")
            if(i==0):
                lim1 = float(line.split()[2])
                lim2 = float(line.split()[3])
                lim3 = float(line.split()[5])
                lim4 = float(line.split()[6])
            else:
                if(float(line.split()[2])<lim1):
                    lim1 = float(line.split()[2])
                if(float(line.split()[3])>lim2):
                    lim2 = float(line.split()[3])                              
        self.lim = [[float(lim1),float(lim2)],[float(lim3),float(lim4)]]
    @property
    def beam_separation(self):
        return self._beam_separation
    @beam_separation.setter
    def beam_separation(self, value):
        self._beam_separation = value
        line = value
        line = line.replace(":","")
        lim1 = float(line.split()[0])*u.deg
        lim2 = float(line.split()[2])*u.deg                     
        self.beam_lim = [lim1,lim2]
    def output(self):
        lines=[]
        if(self.comment != ""):
            lines.append(f"{self.comment:s}")
        lines.append(f"def {self.defname:s};")
        lines.append(f"     antenna_diam = {self.diam:s};")
        lines.append(f"     antenna_name = {self.name:s};")
        lines.append(f"     axis_type = {self.axis_type:s};")
        lines.append(f"     axis_offset = {self.axis_offset:s};")
        for ll in self.motion:
            lines.append(f"     antenna_motion = {ll:s};")
        for ll in self.pointing_sector:
            lines.append(f"     pointing_sector = {ll:s};")
        lines.append(f"     multi_beam_number = {self.multi_beam_number:s};")
        lines.append(f"     multi_beam_type = {self.multi_beam_type:s};")
        lines.append(f"     beam_separation = {self.beam_separation:s};")
        lines.append(f"     field_rotation = {self.field_rotation:s};")
        lines.append("enddef;")
        return "\n".join(lines)+"\n"

class VEX_Source:
    def __init__(self):
        self.list = []
    def add(self, append):
        self.list.append(append)
    def delete(self, remove):
        self.list.remove(remove)
    def output(self):
        lines=["$SOURCE;\n"]
        for s in self.list:
            lines.append(s.output())
        return "*\n".join(lines)+"*"
    def plot(self,coord="equitorial",showlabel=True):
        fig=plt.figure(figsize=(8,6))
        ax = fig.add_subplot(111, projection="mollweide")
        ax.grid(True)
        for source in self.list:
            #print(source.coord.ra.radian, source.coord.dec.radian,source.name)
            if("gal".casefold() in coord.casefold()):
                source.coord.galactic.l.wrap_at('180d', inplace=True)
                ax.scatter(source.coord.galactic.l.radian, source.coord.galactic.b.radian, label=source.name)
                ax.set_xlabel("Galactic Longitude",fontsize=12)
                ax.set_ylabel("Galactic Latitude",fontsize=12)
            else:
                source.coord.ra.wrap_at('180d', inplace=True)
                ax.scatter(source.coord.icrs.ra.radian, source.coord.icrs.dec.radian, label=source.name)
                ax.set_xlabel("Right Ascension",fontsize=12)
                ax.set_ylabel("Declination",fontsize=12)
                ax.set_xticklabels(['14h','16h','18h','20h','22h','0h','2h','4h','6h','8h','10h'])
        if(showlabel):
            ax.legend(fontsize=11)
        ax.tick_params(axis='x', labelsize=11)
        ax.tick_params(axis='y', labelsize=11)
        #plt.show()
        return fig
    
class Source:
    def __init__(self, defname, source_name, ra, dec, ref_coord_frame, name2 = "", comment=""):
        self.defname = defname
        self.comment = comment
        self.name = source_name
        self.name2 = name2
        self._ra = ra  # _raをプライベート属性として定義
        self._dec = dec  # _decをプライベート属性として定義
        self._ref_coord_frame = ref_coord_frame  # _ref_coord_frameをプライベート属性として定義
        self.coord = self._create_coord(ra, dec, ref_coord_frame)
    @property
    def ra(self):
        return self._ra
    @ra.setter
    def ra(self, value):
        self._ra = value
        self.coord = self._create_coord(self._ra, self._dec, self._ref_coord_frame)
    @property
    def dec(self):
        return self._dec
    @dec.setter
    def dec(self, value):
        self._dec = value
        self.coord = self._create_coord(self._ra, self._dec, self._ref_coord_frame)
    @property
    def ref_coord_frame(self):
        return self._ref_coord_frame
    @ref_coord_frame.setter
    def ref_coord_frame(self, value):
        self._ref_coord_frame = value
        self.coord = self._create_coord(self._ra, self._dec, self._ref_coord_frame)
    def _create_coord(self, ra, dec, ref_coord_frame):
        if "J2000" in ref_coord_frame:
            coord = SkyCoord(ra + " " + dec)
        else:
            coord = SkyCoord(ra + " " + dec, frame="fk5", equinox=ref_coord_frame)
        return coord
    def output(self):
        lines=[]
        if(self.comment != ""):
            lines.append(f"{self.comment:s}")
        lines.append(f"def {self.defname:s};")
        lines.append(f"     source_name = {self.name:s};")
        if(self.name2 != ""):
            lines.append(f"     IAU_name = {self.name2:s};")
        ra_txt = self.coord.ra.to_string('hour')
        dec_txt = self.coord.dec.to_string('deg').replace("m","\'").replace("s","\"")
        lines.append(f"     ra = {ra_txt:s};")
        lines.append(f"     dec = {dec_txt:s};")
        lines.append(f"     ref_coord_frame = {self.ref_coord_frame:s};")
        lines.append("enddef;")
        return "\n".join(lines)+"\n"

class VEX_SCHED:
    def __init__(self):
        self.list = []
    def add(self, append):
        self.list.append(append)
    def delete(self, remove):
        self.list.remove(remove)
    def output(self):
        lines=["$SCHED;\n"]
        for s in self.list:
            lines.append(s.output())
        return "*\n".join(lines)+"*"
    def shift(self,timedelta):
        for sked in self.list:
            start_shift = sked.start+timedelta
            sked.start_txt = start_shift.yday_custom
    def dayshift(self,days):
        lstday = TimeDelta((23*u.hour)+(56*u.min)+(4*u.second))
        timed = float(days)*lstday
        self.shift(timed) 
class Sched:
    def __init__(self, defname, mode, start, source1, station, source2="", comment=""):
        self.defname = defname
        self.comment = comment
        self.mode = mode
        self.start_txt = start
        self.source1 = source1
        self.source2 = source2
        self.station = station
        self.name = source1
    @property
    def start_txt(self):
        return self._start_txt
    @start_txt.setter
    def start_txt(self, value):
        self._start_txt = value
        self.start = Time(value.translate(str.maketrans('ydhm', '::::','s')))  # startが更新されるたびにstartも更新される      
    @property
    def station(self):
        return self._station
    @station.setter
    def station(self, value):
        antennas = []
        dur = []
        self._station = value
        for line in value:
            stalist = line.split(":")
            antennas.append(stalist[0].strip())
            if("sec" in stalist[2]):
                dur.append(TimeDelta(float(stalist[2].replace("sec",""))*u.s))
            else:
                print("Unit is not second")
                break
        self.antcodes = antennas
        self.stations = antennas
        self.durlist = dur
        if(len(set(dur)) != 1):
            print("Caution: duration times are not same")
        self.dur = dur[0]
    def output(self):
        lines=[]
        if(self.comment != ""):
            lines.append(f"{self.comment:s}")
        lines.append(f"scan {self.defname:s};")
        lines.append(f"     mode = {self.mode:s};")
        lines.append(f"     start = {self.start_txt:s};")
        lines.append(f"     source1 = {self.source1:s};")
        if(self.source2 != ""):
            lines.append(f"     source2 = {self.source2:s};")
        for ll in self.station:
            lines.append(f"     station = {ll:s};")
        lines.append("endscan;")
        return "\n".join(lines)+"\n"


def Ext_section(lines,section,readcomment=False):
    if section not in ["HEADER","GLOBAL","EXPER","MODE","PROCEDURES","FREQ","IF","BBC","STATION", "DAS", "SOURCE", "SCHED", "SITE", "ANTENNA"]:
        print("Parameter %s is not correct. Please check if it is capitalized."%(section))
        return -1
    sectionlines=[]
    readmode=False
    readdef=False
    section="$"+section
    if(section =="$HEADER"):
        readhead=True
    else:
        readhead=False
    for line in lines:
        line=line.rstrip()
        if(readmode):
            if(line==""):
                continue
            if(line[0]=="$"):
                readmode=False
                continue
            if(section == "$GLOBAL"):
                if(line[0]=="*"):
                    if(readcomment):
                        sectionlines.append(line)
                        continue
                    else:
                        continue
                else:
                    sectionlines.append(line.strip(";"))
            else:
                if(line.split()[0]== "def" or line.split()[0]== "scan"):
                    defname = line.split()[1].strip(";")
                    #print(sectionlines)
                    sectionlines.append([defname])
                    deflines=[]
                    readdef=True
                elif(line.split()[0].strip(";")== "enddef" or line.split()[0].strip(";")== "endscan"):
                    sectionlines[-1].append(deflines)
                    readdef=False
                elif(readdef):
                    defline=line.strip().strip(";")
                    #print(defline)
                    deflines.append(defline)
                elif(line[0]=="*"):
                    if(readcomment):
                        sectionlines.append(line)
                        continue
                    else:
                        continue
        else:
            if(line==""):
                continue
            #print(line,section)
            if(line.strip(";")==section):
                readmode=True
                #if(readcomment):
                #    sectionlines.append(line)
            if(readhead and line[0]!="$"):
                sectionlines.append(line)
            else:
                readhead=False
    return sectionlines

def Read_experline(lines):
    vex_sec = VEX_Exper()
    deflist=[]
    comments=[]
    for line in lines:
        if(len(line)==2):
            ldict=dict()
            defname=line[0]
            for ll in line[1]:
                if(ll[0]=="*" and len(ll)>1):
                    comments.append(ll)
                elif(ll[0]!="*"):
                    ldict[ll.split("=")[0].replace(' ', '')]=ll.split("=")[1].strip()
            ldict["comment"]="\n".join(comments)
            deflist.append(Exper(defname=defname,**ldict))
            comments=[]
        else:
            if(line[0]=="*" and len(line)>1):
                comments.append(line)
    for d in deflist:
        vex_sec.add(d)
    return vex_sec

def Read_proclines(lines):
    vex_sec = VEX_Procedures()
    deflist=[]
    comments=[]
    for line in lines:
        if(len(line)==2):
            ldict=dict()
            defname=line[0]
            for ll in line[1]:
                if(ll[0]=="*" and len(ll)>1):
                    comments.append(ll)
                elif(ll[0]!="*"):
                    key = ll.split("=")[0].replace(' ', '')
                    if(key not in ldict):
                        #print(key,ll.split("=")[1].strip())
                        ldict[key]=[]
                        ldict[key].append(ll.split("=")[1].strip())
                    else:
                        ldict[key].append(ll.split("=")[1].strip())
            ldict["comment"]="\n".join(comments)
            deflist.append(Procedure(defname=defname,**ldict))
            comments=[]
        else:
            if(line[0]=="*" and len(line)>1):
                comments.append(line)
    for d in deflist:
        vex_sec.add(d)
    return vex_sec

def Read_daslines(lines):
    vex_sec = VEX_DAS()
    deflist=[]
    comments=[]
    for line in lines:
        if(len(line)==2):
            ldict=dict()
            defname=line[0]
            for ll in line[1]:
                if(ll[0]=="*" and len(ll)>1):
                    comments.append(ll)
                elif(ll[0]!="*"):
                    ldict[ll.split("=")[0].replace(' ', '')]=ll.split("=")[1].strip()
            ldict["comment"]="\n".join(comments)
            deflist.append(DAS(defname=defname,**ldict))
            comments=[]
        else:
            if(line[0]=="*" and len(line)>1):
                comments.append(line)
    for d in deflist:
        vex_sec.add(d)
    return vex_sec

def Read_freqlines(lines):
    vex_sec = VEX_Freq()
    deflist=[]
    comments=[]
    for line in lines:
        #print(line)
        if(len(line)==2):
            ldict=dict()
            defname=line[0]
            chan_def=[]
            for ll in line[1]:
                #print(ll)
                if(ll.lstrip()[0]=="*" and len(ll.lstrip())>1):
                    comments.append(ll)
                elif(ll[0]!="*"):
                    if(ll.split("=")[0].strip()=="chan_def"):
                        chan_def.append(ll.split("=")[1].strip())
                    else:
                        #print(ll)
                        ldict[ll.split("=")[0].replace(' ', '')]=ll.split("=")[1].strip()
            ldict["chan_def"]=chan_def
            ldict["comment"]="\n".join(comments)
            deflist.append(Freq(defname=defname,**ldict))
            comments=[]
        else:
            if(line[0]=="*" and len(line)>1):
                comments.append(line)
    for d in deflist:
        vex_sec.add(d)
    return vex_sec

def Read_bbclines(lines):
    vex_sec = VEX_BBC()
    deflist=[]
    comments=[]
    for line in lines:
        if(len(line)==2):
            ldict=dict()
            defname=line[0]
            BBC_assign=[]
            for ll in line[1]:
                if(ll[0]=="*" and len(ll)>1):
                    comments.append(ll)
                elif(ll[0]!="*"):
                    if(ll.split("=")[0].strip()=="BBC_assign"):
                        BBC_assign.append(ll.split("=")[1].strip())
                    else:
                        ldict[ll.split("=")[0].replace(' ', '')]=ll.split("=")[1].strip()
            ldict["bbc_assign"]=BBC_assign
            ldict["comment"]="\n".join(comments)
            deflist.append(BBC(defname=defname,**ldict))
            comments=[]
        else:
            if(line[0]=="*" and len(line)>1):
                comments.append(line)
    for d in deflist:
        vex_sec.add(d)
    return vex_sec

def Read_IFlines(lines):
    vex_sec = VEX_IF()
    deflist=[]
    comments=[]
    for line in lines:
        if(len(line)==2):
            ldict=dict()
            defname=line[0]
            if_def=[]
            for ll in line[1]:
                if(ll[0]=="*" and len(ll)>1):
                    comments.append(ll)
                elif(ll[0]!="*"):
                    if(ll.split("=")[0].strip()=="if_def"):
                        if_def.append(ll.split("=")[1].strip())
                    else:
                        ldict[ll.split("=")[0].replace(' ', '')]=ll.split("=")[1].strip()
            ldict["if_def"]=if_def
            ldict["comment"]="\n".join(comments)
            deflist.append(IF(defname=defname,**ldict))
            comments=[]
        else:
            if(line[0]=="*" and len(line)>1):
                comments.append(line)
    for d in deflist:
        vex_sec.add(d)
    return vex_sec

def Read_srclines(lines):
    vex_sec = VEX_Source()
    deflist=[]
    comments=[]
    for line in lines:
        if(len(line)==2):
            ldict=dict()
            defname=line[0]
            for ll in line[1]:
                if(ll[0]=="*" and len(ll)>1):
                    comments.append(ll)                
                elif(ll[0]!="*"):
                    ldict[ll.split("=")[0].replace(' ', '')]=ll.split("=")[1].replace(' ', '')
            ldict["comment"]="\n".join(comments)
            if("IAU_name" in ldict):
                name2=ldict["IAU_name"]
                del ldict["IAU_name"]
            else:
                name2=""
            deflist.append(Source(defname, **ldict, name2=name2))
            comments=[]
        else:
            if(line[0]=="*" and len(line)>1):
                comments.append(line)
    for d in deflist:
        vex_sec.add(d)
    return vex_sec

def Read_antlines(lines):
    vex_sec = VEX_Antenna()
    deflist=[]
    comments=[]
    for line in lines:
        if(len(line)==2):
            ldict=dict()
            defname=line[0]
            antenna_motion=[]
            pointing_sector=[]
            for ll in line[1]:
                if(ll[0]=="*" and len(ll)>1):
                    comments.append(ll)     
                elif(ll[0]!="*"):
                    if(ll.split("=")[0].strip()=="antenna_motion"):
                        antenna_motion.append(ll.split("=")[1].strip())
                    elif(ll.split("=")[0].strip()=="pointing_sector"):
                        pointing_sector.append(ll.split("=")[1].strip())
                    else:
                        ldict[ll.split("=")[0].replace(' ', '')]=ll.split("=")[1].strip()
            ldict["antenna_motion"]=antenna_motion
            ldict["pointing_sector"]=pointing_sector
            ldict["comment"]="\n".join(comments)
            deflist.append(Antenna(defname=defname,**ldict))
            comments=[]
        else:
            if(line[0]=="*" and len(line)>1):
                comments.append(line)
    for d in deflist:
        vex_sec.add(d)
    return vex_sec

def Read_sitelines(lines):
    vex_sec = VEX_Site()
    deflist=[]
    comments=[]
    for line in lines:
        if(len(line)==2):
            ldict=dict()
            defname=line[0]
            for ll in line[1]:
                if(ll[0]=="*" and len(ll)>1):
                    comments.append(ll)
                elif(ll[0]!="*"):
                    ldict[ll.split("=")[0].replace(' ', '')]=ll.split("=")[1].strip()
            ldict["comment"]="\n".join(comments)
            deflist.append(Site(defname=defname,**ldict))
            comments=[]
        else:
            if(line[0]=="*" and len(line)>1):
                comments.append(line)
    for d in deflist:
        vex_sec.add(d)
    return vex_sec

def Read_schedlines(lines):
    vex_sec = VEX_SCHED()
    deflist=[]
    comments=[]
    for line in lines:
        if(len(line)==2):
            ldict=dict()
            defname=line[0]
            station=[]
            for ll in line[1]:
                if(ll[0]=="*" and len(ll)>1):
                    comments.append(ll)
                elif(ll[0]!="*"):
                    if(ll.split("=")[0].replace(' ', '')=="station"):
                        station.append(ll.split("=")[1].strip())
                    else:
                        ldict[ll.split("=")[0].replace(' ', '')]=ll.split("=")[1].strip()
            ldict["comment"]="\n".join(comments)
            ldict['station'] = station
            deflist.append(Sched(defname=defname,**ldict))
            comments=[]
        else:
            if(line[0]=="*" and len(line)>1):
                comments.append(line)
    for d in deflist:
        vex_sec.add(d)
    return vex_sec


def Read_stationlines(lines):
    vex_sec = VEX_Station()
    deflist=[]
    comments=[]
    for line in lines:
        if(len(line)==2):
            #print(line)
            ldict=dict()
            defname=line[0]
            for ll in line[1]:
                if(ll[0]=="*" and len(ll)>1):
                    comments.append(ll)
                elif(ll[0]!="*"):
                    if("ref" == ll.split("=")[0].replace(' ', '')[:3]):
                        key = ll.split("=")[0].replace(' ', '')[3:].replace('$','').lower()
                        #print(key)
                        ldict[key]=ll.split("=")[1].replace(' ', '')
                    else:
                        print("No reference")
            ldict["comment"]="\n".join(comments)
            deflist.append(Station(defname=defname,**ldict))
            comments=[]
        else:
            if(line[0]=="*" and len(line)>1):
                comments.append(line)
    for d in deflist:
        vex_sec.add(d)
    return vex_sec

def Read_modelines(lines):
    vex_sec = VEX_Mode()
    deflist=[]
    comments=[]
    for line in lines:
        if(len(line)==2):
            #print(line)
            ldict=dict()
            defname=line[0]
            for ll in line[1]:
                if(ll[0]=="*" and len(ll)>1):
                    comments.append(ll)
                elif(ll[0]!="*"):
                    if("ref" == ll.split("=")[0].replace(' ', '')[:3]):
                        key = ll.split("=")[0].replace(' ', '')[3:].replace('$','').lower()
                        if(key=="if"):
                            ldict[key+"_"]=ll.split("=")[1].replace(' ', '')
                        else:
                            ldict[key]=ll.split("=")[1].replace(' ', '')
                    else:
                        print("No reference")
            ldict["comment"]="\n".join(comments)
            deflist.append(Mode(defname=defname,**ldict))
            comments=[]
        else:
            if(line[0]=="*" and len(line)>1):
                comments.append(line)
    for d in deflist:
        vex_sec.add(d)
    return vex_sec


def Read_globallines(lines):
    vex_sec = VEX_Mode()
    ldict=dict()
    #print(lines)
    for line in lines:
        #print(line)
        comments=[]
        if(line[0]=="*" and len(line)>1):
            comments.append(line)
        elif(line[0]!="*"):
            if("ref" == line.split("=")[0].replace(' ', '')[:3]):
                #print(line.split("=")[0])
                key = line.split("=")[0].replace(' ', '')[3:].replace('$','').lower()
                ldict[key]=line.split("=")[1].replace(' ', '')
            else:
                print("No reference")
    ldict["comment"]="\n".join(comments)
    #print(ldict)
    vex_sec = VEX_Global(**ldict)
    return vex_sec


##############
# Sub functions
def trans_azel(coordinate,obstime,loc):
    altaz=coordinate.transform_to(AltAz(obstime=obstime, location=loc))
    return altaz,altaz.az.deg,altaz.alt.deg

from astropy.time import TimeISO
class TimeYearDayTimeCustom(TimeISO):
    name = 'yday_custom'  # Unique format name
    subfmts = (('date_hms',
               '%Yy%jd%Hh%Mm%Ss',
               '{year:d}y{yday:03d}d{hour:02d}h{min:02d}m{sec:02d}s'),
              ('date_hm',
               '%Y-%jT%H:%M',
               '{year:d}-{yday:03d}T{hour:02d}:{min:02d}'),
              ('date',
               '%Y-%j',
               '{year:d}-{yday:03d}'))

def Query_Simbad(name):
    result_table = Simbad.query_object(name)
    return result_table

def Query_VLBAcalib(c_target, f_th=0.1, sep_min=0.32, sep_max=2.2):
    from calibrator_catalog import search_catalog
    return search_catalog(c_target, f_th, sep_min, sep_max)

def _earthlocation_to_altaz(location, reference_location):
    # See
    # https://docs.astropy.org/en/stable/coordinates/common_errors.html#altaz-calculations-for-earth-based-objects
    # for why this is necessary and we cannot just do
    # `get_itrs().transform_to(AltAz())`
    itrs_cart = location.get_itrs().cartesian
    itrs_ref_cart = reference_location.get_itrs().cartesian
    local_itrs = ITRS(itrs_cart - itrs_ref_cart, location=reference_location)
    return local_itrs.transform_to(AltAz(location=reference_location))
def earth_location_to_local_enu(location, reference_location):
    altaz = _earthlocation_to_altaz(location, reference_location)
    ned_coords =  altaz.cartesian.xyz
    enu_coords = ned_coords[1], ned_coords[0], -ned_coords[2]
    return enu_coords
def enu_to_local_altaz(enu_baselines, distance):
    azimuth = np.arctan2(enu_baselines[0], enu_baselines[1])
    elevation = np.arcsin(enu_baselines[2]/distance) 
    return azimuth, elevation
def calc_R(H,dec):
    if np.isscalar(H):
        H = np.array([H])
    R = np.array([[np.sin(H), np.cos(H), np.zeros_like(H)],\
        [-np.sin(dec)*np.cos(H), np.sin(dec)*np.sin(H), np.cos(dec) * np.ones_like(H)],\
        [np.cos(dec)*np.cos(H), -np.cos(dec)*np.sin(H), np.sin(dec) * np.ones_like(H)]])
    return R
def calc_ant_center(sites):
    x,y,z=[],[],[]
    for site in sites:
        x.append(site.x.to(u.m).value)
        y.append(site.y.to(u.m).value)
        z.append(site.z.to(u.m).value)
    mean_pos = EarthLocation(np.mean(x)*u.m, np.mean(y)*u.m, np.mean(z)*u.m)
    return mean_pos
