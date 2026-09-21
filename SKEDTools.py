from schedule_text import normalize_text
from astropy.coordinates import SkyCoord, ICRS, Galactic, FK4, FK5, EarthLocation, AltAz
from astropy.coordinates import get_sun
import astropy.units as u
import numpy as np
from astropy.time import Time, TimeDelta
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import dates as mdates
from astroquery.simbad import Simbad
import pickle
from pathlib import Path

plt.rcParams['font.size'] = 12
plt.rcParams['xtick.direction'] = 'in'
plt.rcParams['ytick.direction'] = 'in'

#matplotlib.use("svg")
matplotlib.use("Agg")

class DRG:
    def __init__(self, exper=None, source=None, sked=None, station=None):
        self.exper = exper
        self.source = source
        self.sked = sked
        self.station = station
        
    def add(self,*args):
        for arg in args:
            if('SKD_Exper' in str(type(arg))):
                self.exper=arg
            if('SKD_Source' in str(type(arg))):
                self.source=arg
            elif('SKD_Sked' in str(type(arg))):
                self.sked=arg   
            elif('SKD_Station' in str(type(arg))):
                self.station=arg
        self.adjust()
        
    def read(self, filename):
        with open(filename, encoding="utf-8-sig") as stream:
            self.readtxt(stream.read())

    def readtxt(self, text):
        text = normalize_text(text)
        for section in ("$EXPER", "$SOURCES", "$SKED", "$STATIONS"):
            if section not in text:
                raise ValueError("Missing section: " + section)
        candidate = DRG()
        candidate._readtxt(text)
        self.__dict__.update(candidate.__dict__)

    def _readtxt(self, text):
        alllines = text.splitlines()
        lines = Read_drg(alllines,"EXPER",readcomment=True)
        self.exper = Read_experline(lines)
        lines = Read_drg(alllines,"SOURCES")
        self.source = Read_sources(lines)
        lines = Read_drg(alllines,"SKED")
        self.sked = Read_skeds(lines)
        lines = Read_drg(alllines,"STATIONS")
        self.station = Read_stations(lines)
        self.adjust()

    def output(self):
        alllines = []
        lines = self.exper.output()
        for line in lines:
        #    print(line)
            alllines.append(line)
        #print("$PARAM\nSYNCHRONIZE OFF")
        alllines.append("$PARAM\nSYNCHRONIZE OFF")
        lines = self.source.output()
        for line in lines:
            alllines.append(line)
        #    print(line)
        lines = self.station.output()
        for line in lines:
            alllines.append(line)
        #    print(line)  
        lines = self.sked.output()
        for line in lines:
            alllines.append(line)
        #    print(line) 
        #print("$HEAD\n*")
        alllines.append("$HEAD\n*")
        #print("$CODES\n*")
        alllines.append("$CODES\n*")
        return "\n".join(alllines)
        
    def write(self, filename):
        text = self.output()
        if hasattr(filename, "write"):
            filename.write(text + "\n")
        else:
            Path(filename).write_text(text + "\n", encoding="utf-8")

    def check(self):
        #Check Az, El limit and slew speed. Only at the beginning an end of each scan.
        # sourcelist = self.source
        # antennalist = self.station
        prevtime=0
        numerror = 0
        msg = []
        for sked in self.sked.skeds:
            antprev_tmp = []
            i=0
            for sked_antenna in sked.antennas:
                altaz_i = sked.source.coord.transform_to(AltAz(obstime=sked.start, location=sked_antenna.coord))
                altaz_e = sked.source.coord.transform_to(AltAz(obstime=sked.start+sked.dur, location=sked_antenna.coord))
                #sunaltaz_i= get_sun(obstime=sked.start).transform_to(AltAz(obstime=sked.start,location=sked_antenna.coord))
                #sunaltaz_e= get_sun(obstime=sked.start).transform_to(AltAz(obstime=sked.start+sked.dur,location=sked_antenna.coord))
                #print(altaz_i.alt.deg,sked_antenna.lim[1][0],sked_antenna.lim[1][1])
                if(altaz_i.alt.deg < float(sked_antenna.lim[1][0]) or float(sked_antenna.lim[1][1]) < altaz_i.alt.deg):
                    msg.append("antenna elevation limit, el ={}, {}, {}, {}".format(altaz_i.alt.deg, sked.source.name, sked.start, sked_antenna.name))
                    numerror+=1
                if(altaz_e.alt.deg < float(sked_antenna.lim[1][0]) or float(sked_antenna.lim[1][1]) < altaz_e.alt.deg):
                    msg.append("antenna elevation limit, el ={}, {}, {}, {}".format(altaz_i.alt.deg, sked.source.name, sked.start+sked.dur, sked_antenna.name))
                    numerror+=1
                if(abs(sked_antenna.lim[0][1]-sked_antenna.lim[0][0])< 360.):
                    if(altaz_i.az.deg < float(sked_antenna.lim[0][0]) or float(sked_antenna.lim[0][1]) < altaz_i.az.deg):
                        msg.append("antenna azimuth limit, az = {}, {}, {}, {}".format(altaz_i.az.deg, sked.source.name, sked.start, sked_antenna.name))
                        #print("antenna azimuth limit, az = ",altaz_i.az.deg, sked_source.name, sked.start, sked_antenna.name)
                        numerror+=1
                    if(altaz_e.az.deg < float(sked_antenna.lim[0][0]) or float(sked_antenna.lim[0][1]) < altaz_e.az.deg):
                        msg.append("antenna azimuth limit, az = {}, {}, {}, {}".format(altaz_i.az.deg, sked.source.name, sked.start+sked.dur, sked_antenna.name))
                        #print("antenna azimuth limit, az = ",altaz_i.az.deg, sked_source.name, sked.start+dur, sked_antenna.name)
                        numerror+=1
                antprev_tmp.append(altaz_e)
                if(prevtime!=0):
                    if(abs(sked_antenna.lim[0][1]-sked_antenna.lim[0][0])< 360.):
                        if(np.abs((prevpos[i].az.deg - altaz_i.az.deg)/float(sked_antenna.rate[0])) > (sked.start - prevtime).sec/60.):
                            msg.append("antenna slew time error (az), {}, {}".format(sked.start, sked_antenna.name))
                            numerror+=1
                        if(np.abs(prevpos[i].alt.deg - altaz_i.alt.deg)/float(sked_antenna.rate[1]) > (sked.start - prevtime).sec/60.):
                            msg.append("antenna slew time error (el), {}, {}".format(sked.start, sked_antenna.name))
                            numerror+=1
                    else:
                        azdiff = np.abs(prevpos[i].az.deg - altaz_i.az.deg)
                        if(azdiff > 180.):
                            azdiff = 360.-azdiff
                        if(azdiff/float(sked_antenna.rate[0]) > (sked.start - prevtime).sec/60.):
                            msg.append("antenna slew time error (az), {}, {}".format(sked.start, sked_antenna.name))
                            numerror+=1
                        if(np.abs(prevpos[i].alt.deg - altaz_i.alt.deg)/float(sked_antenna.rate[1]) > (sked.start - prevtime).sec/60.):
                            msg.append("antenna slew time error (el), {}, {}".format(sked.start, sked_antenna.name))
                            numerror+=1
                i+=1
                #    if(np.abs(prevpos[i].az.deg - altaz_i.az.deg)/float(sked_antenna.rate[0]) > (sked.start - prevtime).sec/60.):
                #        msg.append("antenna slew error (az), {}, {}".format(sked.start, sked_antenna.name))
                #        numerror+=1
                #    if(np.abs(prevpos[i].alt.deg - altaz_i.alt.deg)/float(sked_antenna.rate[1]) > (sked.start - prevtime).sec/60.):
                #        msg.append("antenna slew error (el), {}, {}".format(sked.start, sked_antenna.name))
                #        numerror+=1
                #    prevantpos[i]
                #prevantpos.append(altaz_e)
            prevtime = sked.start+sked.dur
            prevpos = antprev_tmp
        if(numerror==0):
            msg.append("check: OK")
            #print("OK")
        else:
            msg.append("End. NumError="+str(numerror))
            #print("End. NumError=",numerror)
        return msg
            
    def deepcheck(self,dt=30.,sunseplim=2.1, sunseplim_slew=1.1):
        # Check Az, El limit and slew speed, and position of the sun with time bin of dt.
        # dt: time bin (second)
        # sunseplim: separation angle limit between the sun and a target to omit warning message.
        # sunseplim_slew: separation angle limit during the slew time
        self.adjust()
        dt_time=TimeDelta(dt*u.second)
        on_source=[True for i in range(len(self.sked.skeds[0].antennas))]
        az = [180. for i in range(len(self.sked.skeds[0].antennas))]
        el = [85. for i in range(len(self.sked.skeds[0].antennas))]
        azellist = [list() for i in range(len(self.sked.skeds[0].antennas))]
        azellim = [antenna.lim for antenna in self.sked.skeds[0].antennas]
        az_det = [True if abs(self.sked.skeds[0].antennas[i].lim[0][1]-self.sked.skeds[0].antennas[i].lim[0][0])< 360. else False for i in range(len(self.sked.skeds[0].antennas))]
        azlim_det = [False for i in range(len(self.sked.skeds[0].antennas))]
        ellim_det = [False for i in range(len(self.sked.skeds[0].antennas))]
        msg=[]
        #df = [pd.DataFrame(columns=['source', 'time', '[85. for i in range(len(self.sked.skeds[0].antennas))]antenna az','antenna el','sun az','sun el']) for i in range(len(self.sked.skeds[0].antennas))]
        #df_warn = [pd.DataFrame(columns=['source', 'time', 'antenna az','antenna el','sun az','sun el']) for i in range(len(self.sked.skeds[0].antennas))]
        for i, sked in enumerate(self.sked.skeds):
            starttime=sked.start
            endtime=sked.start+sked.dur
            # If the tracking doesn't arrive in time
            if(False in on_source):
                for j,antenna in enumerate(sked.antennas):
                    altaz=AltAz(az=str(az[j])+"d",alt=str(el[j])+"d",obstime=obstime,location=antenna.coord)
                    sunaltaz,sunaz,sunel=trans_azel(get_sun(obstime),obstime,antenna.coord)
                    sunsep=altaz.separation(sunaltaz)
                    if(sunsep.deg<=sunseplim):
                        msg.append("Warning: Sun separation = {:.3f} deg, #{}, {}, {}, {}".format(sunsep.deg, i+1, sked.name, obstime,antenna.name))
                        #print("Warning: separation = ","{:.3f}".format(sunsep.deg),"deg","#",i+1,sked.name,obstime,antenna.name)
                        #df_warn[j]=df_warn[j].append({'source':skdlist[i], 'time':obstime.datetime, 'antenna az':az,'antenna el':el,'sun az':sunaz,'sun el':sunel},ignore_index=True)
                    #df[j]=df[j].append({'source':skdlist[i], 'time':obstime.datetime, 'antenna az':az,'antenna el':el,'sun az':sunaz,'sun el':sunel},ignore_index=True)
                    azellist[j].append([obstime.datetime,az[j],el[j]])
                while(False in on_source):
                    for j,antenna in enumerate(sked.antennas):
                        if(not on_source[j]):
                            msg.append("Tracking delay! #{}, {}, {}, {}".format(i+1,sked.name,obstime,antenna.name))
                    #print("Tracking delay!","#",i+1,sked.name,obstime,antenna.name)
                    time2end=endtime-obstime
                    nextobstime=obstime+dt_time
                    if(int(time2end.sec) >  int(dt)):
                        for j,antenna in enumerate(sked.antennas):
                            nextaltaz,nextaz,nextel=trans_azel(sked.source.coord,nextobstime,antenna.coord)
                            az[j],el[j],on_source[j],azlim_det[j],ellim_det[j]=ant_slew(az[j],el[j],nextaz,nextel,antenna.rate[0],antenna.rate[1],dt,az_det[j],azellim[j])
                        if(False not in on_source):
                            starttime=starttime+dt_time
                            break
                        obstime=nextobstime
                        for j,antenna in enumerate(sked.antennas):
                            altaz=AltAz(az=str(az[j])+"d",alt=str(el[j])+"d",obstime=obstime,location=antenna.coord)
                            sunaltaz,sunaz,sunel=trans_azel(get_sun(obstime),obstime,antenna.coord)
                            sunsep=altaz.separation(sunaltaz)
                            if(sunsep.deg<=sunseplim):
                                msg.append("Warning: Sun separation = {:.3f} deg, #{}, {}, {}, {}".format(sunsep.deg, i+1, sked.name, obstime,antenna.name))
                                #print("Warning: separation = ","{:.3f}".format(sunsep.deg),"deg","#",i+1,sked.name,obstime,antenna.name)
                                #df_warn=df_warn.append({'source':skdlist[i], 'time':obstime.datetime, 'antenna az':az,'antenna el':el,'sun az':sunaz,'sun el':sunel},ignore_index=True)
    #                         df=df.append({'source':skdlist[i], 'time':obstime.datetime, 'antenna az':az,'antenna el':el,'sun az':sunaz,'sun el':sunel},ignore_index=True)
                            azellist[j].append([obstime.datetime,az[j],el[j]])
                        starttime=starttime+dt_time
                    else:
                        nextobstime=obstime+time2end
                        for j,antenna in enumerate(sked.antennas):
                            nextaltaz,nextaz,nextel=trans_azel(sked.source.coord,nextobstime,antenna.coord)
                            az[j],el[j],on_source[j],azlim_det[j],ellim_det[j]=ant_slew(az[j],el[j],nextaz,nextel,antenna.rate[0],antenna.rate[1],time2end.sec,az_det[j],azellim[j])
                        obstime=nextobstime
                        for j,antenna in enumerate(sked.antennas):
                            altaz=AltAz(az=str(az[j])+"d",alt=str(el[j])+"d",obstime=obstime,location=antenna.coord)
                            sunaltaz,sunaz,sunel=trans_azel(get_sun(obstime),obstime,antenna.coord)
                            sunsep=altaz.separation(sunaltaz)
                            if(sunsep.deg<=sunseplim):
                                msg.append("Warning: Sun separation = {:.3f} deg, #{}, {}, {}, {}".format(sunsep.deg, i+1, sked.name, obstime,antenna.name))
                                #print("Warning: separation = ","{:.3f}".format(sunsep.deg),"deg","#",i+1,sked.name,obstime,antenna.name)
                                #df_warn=df_warn.append({'source':skdlist[i], 'time':obstime.datetime, 'antenna az':az,'antenna el':el,'sun az':sunaz,'sun el':sunel},ignore_index=True)
                        #df=df.append({'source':skdlist[i], 'time':obstime.datetime, 'antenna az':az,'antenna el':el,'sun az':sunaz,'sun el':sunel},ignore_index=True)
                            azellist[j].append([obstime.datetime,az[j],el[j]])
                        starttime=endtime
                        break                  
            # Normal Tracking
            if(False not in on_source):
                obstime = starttime
                time2end=endtime-obstime
                while(int(time2end.sec) >= int(dt)):
                    for j,antenna in enumerate(sked.antennas):
                        nextaltaz,nextaz,nextel=trans_azel(sked.source.coord,obstime,antenna.coord)
                        if(False not in on_source):
                            az[j],el[j],azlim_det[j],ellim_det[j],on_source[j] = checkantlim(nextaz,nextel,az_det[j],azellim[j])
                            if(azlim_det[j]):
                                msg.append("Azimuth limit #{}, {}, {}, {}".format(i+1,sked.name,obstime,antenna.name))
                            if(ellim_det[j]):
                                msg.append("Elevation limit #{}, {}, {}, {}".format(i+1,sked.name,obstime,antenna.name))
                        # if not tracking because of antenna limit
                        else:
                            az[j],el[j],on_source[j],azlim_det[j],ellim_det[j]=ant_slew(az[j],el[j],nextaz,nextel,antenna.rate[0],antenna.rate[1],dt,az_det[j],azellim[j])
                        altaz=AltAz(az=str(az[j])+"d",alt=str(el[j])+"d",obstime=obstime,location=antenna.coord)
                        sunaltaz,sunaz,sunel=trans_azel(get_sun(obstime),obstime,antenna.coord)
                        sunsep=altaz.separation(sunaltaz)
                        if(sunsep.deg<=sunseplim):
                            msg.append("Warning: Sun separation = {:.3f} deg, #{}, {}, {}, {}".format(sunsep.deg, i+1, sked.name, obstime,antenna.name))
                        azellist[j].append([obstime.datetime,az[j],el[j]])
                    obstime = obstime+dt_time
                    time2end=endtime-obstime
                if(int(time2end.sec)>0):
                    for j,antenna in enumerate(sked.antennas):
                        nextaltaz,nextaz,nextel=trans_azel(sked.source.coord,obstime,antenna.coord)
                        if(False not in on_source):
                            az[j],el[j],azlim_det[j],ellim_det[j],on_source[j] = checkantlim(nextaz,nextel,az_det[j],azellim[j])
                            if(azlim_det[j]):
                                msg.append("Azimuth limit #{}, {}, {}, {}".format(i+1,sked.name,obstime,antenna.name))
                            if(ellim_det[j]):
                                msg.append("Elevation limit #{}, {}, {}, {}".format(i+1,sked.name,obstime,antenna.name))
                        # if not tracking because of antenna limit
                        else:
                            az[j],el[j],on_source[j],azlim_det[j],ellim_det[j]=ant_slew(az[j],el[j],nextaz,nextel,antenna.rate[0],antenna.rate[1],time2end.sec,az_det[j],azellim[j])
                        altaz=AltAz(az=str(az[j])+"d",alt=str(el[j])+"d",obstime=obstime,location=antenna.coord)
                        sunaltaz,sunaz,sunel=trans_azel(get_sun(obstime),obstime,antenna.coord)
                        sunsep=altaz.separation(sunaltaz)
                        if(sunsep.deg<=sunseplim):
                            msg.append("Warning: Sun separation = {:.3f} deg, #{}, {}, {}, {}".format(sunsep.deg, i+1, sked.name, obstime,antenna.name))
                            #print("Warning: separation = ","{:.3f}".format(sunsep.deg),"deg","#",i+1,sked.name,obstime,antenna.name)
                            #df_warn=df_warn.append({'source':skdlist[i], 'time':obstime.datetime, 'antenna az':az,'antenna el':el,'sun az':sunaz,'sun el':sunel},ignore_index=True)
                        azellist[j].append([obstime.datetime,az[j],el[j]])
                    obstime = obstime+time2end
                for j,antenna in enumerate(sked.antennas):
                    nextaltaz,nextaz,nextel=trans_azel(sked.source.coord,obstime,antenna.coord)
                    if(False not in on_source):
                        az[j],el[j],azlim_det[j],ellim_det[j],on_source[j] = checkantlim(nextaz,nextel,az_det[j],azellim[j])
                        if(azlim_det[j]):
                            msg.append("Azimuth limit #{}, {}, {}, {}".format(i+1,sked.name,obstime,antenna.name))
                        if(ellim_det[j]):
                            msg.append("Elevation limit #{}, {}, {}, {}".format(i+1,sked.name,obstime,antenna.name))
                    # if not tracking because of antenna limit
                    else:
                        az[j],el[j],on_source[j],azlim_det[j],ellim_det[j]=ant_slew(az[j],el[j],nextaz,nextel,antenna.rate[0],antenna.rate[1],time2end.sec,az_det[j],azellim[j])
                    altaz=AltAz(az=str(az[j])+"d",alt=str(el[j])+"d",obstime=obstime,location=antenna.coord)
                    sunaltaz,sunaz,sunel=trans_azel(get_sun(obstime),obstime,antenna.coord)
                    sunsep=altaz.separation(sunaltaz)
                    if(sunsep.deg<=sunseplim):
                        msg.append("Warning: Sun separation = {:.3f} deg, #{}, {}, {}, {}".format(sunsep.deg, i+1, sked.name, obstime,antenna.name))
                    azellist[j].append([obstime.datetime,az[j],el[j]])
            # Antenna slew part
            if(i<len(self.sked.skeds)-1):
                time2next=self.sked.skeds[i+1].start-obstime
                while(int(time2next.sec) > int(dt_time.sec)):
                    nextobstime=obstime+dt_time
                    for j,antenna in enumerate(sked.antennas):
                        nextaltaz,nextaz,nextel=trans_azel(self.sked.skeds[i+1].source.coord,nextobstime,antenna.coord)
                        az[j],el[j],on_source[j],azlim_det[j],ellim_det[j]=ant_slew(az[j],el[j],nextaz,nextel,antenna.rate[0],antenna.rate[1],dt,az_det[j],azellim[j])
                    obstime=nextobstime
                    for j,antenna in enumerate(sked.antennas):
                        altaz=AltAz(az=str(az[j])+"d",alt=str(el[j])+"d",obstime=obstime,location=antenna.coord)
                        sunaltaz,sunaz,sunel=trans_azel(get_sun(obstime),obstime,antenna.coord)
                        sunsep=altaz.separation(sunaltaz)
                        if(sunsep.deg<=sunseplim_slew):
                            msg.append("Warning: Sun separation = {:.3f} deg, slew from [#{} {}] to [#{} {}], {}, {}".format(sunsep.deg, i+1, self.sked.skeds[i].name, i+2, self.sked.skeds[i+1].name, obstime,antenna.name))
                        azellist[j].append([obstime.datetime,az[j],el[j]])
                    time2next=self.sked.skeds[i+1].start-obstime
                nextobstime=obstime+time2next
                for j,antenna in enumerate(sked.antennas):
                    nextaltaz,nextaz,nextel=trans_azel(self.sked.skeds[i+1].source.coord,nextobstime,antenna.coord)
                    az[j],el[j],on_source[j],azlim_det[j],ellim_det[j]=ant_slew(az[j],el[j],nextaz,nextel,antenna.rate[0],antenna.rate[1],time2next.sec,az_det[j],azellim[j])
                obstime=nextobstime
        if(len(msg)==0):
            msg.append("deepcheck: OK")
        return msg, azellist
    
    def azelplot(self):
        msg, azellists = self.deepcheck()
        fig=plt.figure(figsize=(4,3*len(azellists)))
        ax=[]
        for ax_i,azellist in enumerate(azellists):
            azellist = np.array(azellist)
            ax.append(fig.add_subplot(len(azellists), 1, ax_i+1))
            ax[-1].plot(azellist[:,1],azellist[:,2])
            ax[-1].set_xlabel("Azimuth [deg]")
            ax[-1].set_ylabel("Elevation [deg]")
            ax[-1].set_title(self.sked.skeds[0].antennas[ax_i].name)
        fig.tight_layout()
        return msg, fig
        
    def shift(self,timedelta):
        self.sked.shift(timedelta)
    def dayshift(self,days):
        self.sked.dayshift(days)
    def sourceplot(self,coord="equitorial",showlabel=True):
        fig=self.source.plot(coord,showlabel)
        return fig
    def el_plot(self,srcnames=[],refant="",timezone="lst",ellim=[],timelim=[]):
        # If timezone="lst", timelim must be float (or numeric) object. If timezone = 'ut' or like that, timelim must be datetime object.
        locations = [antenna for antenna in self.station.stations]
        if(refant!=""):
            for i,location in enumerate(locations):
                if(location.code==refant):
                    tmplocation = locations[0]
                    locations[0] = location
                    locations[i] = tmplocation                    
        refantname=locations[0].name
        srcs =[]
        for selsrcname in srcnames:
            for source in self.source.sources:
                if(source.name1==selsrcname or source.name2==selsrcname):
                    srcs.append(source)
        try:
            obsdate = self.sked.skeds[0].start.iso.split()[0]
        except:
            obsdate = '2023-04-01'
        start_time = Time(obsdate+'T00:00:0.0',location=locations[0].coord)
        time_length = 24.
        num=100
        dt=time_length*3600./num
        dt_time = TimeDelta(dt, format='sec')
        #if(timezone=="lst"):
        fig=plt.figure(figsize=(4,3*len(srcs)))
        ax=[]
        for ax_i,src in enumerate(srcs):
            j=0
            ax.append(fig.add_subplot(len(srcs), 1, ax_i+1))
            timelist = []
            for loc_i,location in enumerate(locations):
                #for index in range(len(objnames)):
                el_array = []
                obstime = start_time
                for i in range(int(time_length*60*60/dt)):
                    altaz,az,el=trans_azel(src.coord,obstime,location.coord)
                    #el_array.append([el])
                    el_array.append(el)
                    if(j==0):
                        #print(ax_i,"check",timezone)
                        if(timezone=='lst'.casefold()):
                            #print("lst_check")
                            lsttime=obstime.sidereal_time('apparent')
                            timelist.append(lsttime.to_value())
                        elif(timezone=='ut'.casefold() or timezone=='utc'.casefold()):
                            timelist.append(obstime.datetime)
                        elif(timezone=='jst'.casefold()):
                            timelist.append((obstime+TimeDelta(9.*u.hour)).datetime)
                    obstime = obstime+dt_time
                #ax.scatter(timelist, el_array,label=locnames[loc_i]+" "+objnames[index])
                #print(timelist,el_array,location.name)
                #ax[-1].scatter(timelist, el_array,label=location.name)
                ax[-1].scatter(timelist, np.ma.masked_outside(el_array,0.5,90.),label=location.name)
                j+=1
            # ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            # ax.set_title("Start Time: "+str(start_time.utc))
            ax[-1].set_title(src.name)
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
        
    def adjust(self,delete=False):
        useantennas = []
        usesources = []
        if(delete):
            for sked in self.sked.skeds:
                for sked_antenna in sked.stations:
                    if(sked_antenna not in useantennas):
                        useantennas.append(sked_antenna)
                if(sked.name not in usesources):
                    usesources.append(sked.name)
            for antenna in self.station.stations:
                if(antenna.code not in useantennas):
                    self.station.delete(antenna)
            for source in self.source.sources:
                if(source.name not in usesources):
                    self.source.delete(source)
        if(self.source!= None and self.sked!=None and self.station!=None):
            # corresponding source
            start_list=[]
            for sked in self.sked.skeds:
                start_list.append(sked.start.mjd)
                name = sked.name
                sked_source=None
                for source in self.source.sources:
                    if(name == source.name):
                        sked_source = source
                        continue
                if(sked_source==None):
                    raise ValueError("No corresponding source: " + name)
                stations = sked.stations
                sked_antennas=[]
                for station in stations:
                    for antenna in self.station.stations:
                        if(station == antenna.code):
                            sked_antennas.append(antenna)
                            continue
                if(len(sked_antennas)!=len(stations)):
                    raise ValueError("No corresponding antenna(s)")
                sked.source = sked_source
                sked.antennas = sked_antennas
            sorted_list=sorted(start_list)
            if(start_list!=sorted_list):
                arglist=np.argsort(start_list)
                self.sked.skeds = [self.sked.skeds[i] for i in arglist]
                print("Changed sked order")

class Source:
    def __init__(self, name1, coordinates,name2="$"):
        self.name = name1
        self.name1 = name1
        self.name2 = name2
        self.coord = coordinates
    def __str__(self):
        name1 = self.name1
        name2 = self.name2
        ra = self.coord.icrs.ra.hms
        dec = self.coord.icrs.dec.dms
        dec_sign = "-" if self.coord.icrs.dec.deg < 0 else "+"
        return "{:<.8s} {:<.8s} {:02d} {:02d} {:08.5f} {}{:02d} {:02d} {:07.4f} 2000.0  0  0  0  0".format(name1, name2,int(ra[0]),int(ra[1]),ra[2],dec_sign, int(abs(dec[0])),int(abs(dec[1])),abs(dec[2]))

class SKD_Source:
    def __init__(self):
        self.sources = []
    def __str__(self):
        lines=""
        for source in self.sources:
            name1 = source.name1
            name2 = source.name2
            ra = source.coord.icrs.ra.hms
            dec = source.coord.icrs.dec.dms
            dec_sign = "-" if source.coord.icrs.dec.deg < 0 else "+"
            lines+="{:<8.8s} {:<8.8s} {:02d} {:02d} {:08.5f} {}{:02d} {:02d} {:07.4f} 2000.0  0  0  0  0\n".format(name1, name2,int(ra[0]),int(ra[1]),ra[2],dec_sign, int(abs(dec[0])),int(abs(dec[1])),abs(dec[2]))
        return lines
    def add(self, source):
        self.sources.append(source)
    def delete(self, source):
        self.sources.remove(source)
    def output(self):
        lines=[]
        lines.append("$SOURCES")
        for source in self.sources:
            name1 = source.name1
            name2 = source.name2
            ra = source.coord.icrs.ra.hms
            dec = source.coord.icrs.dec.dms
            dec_sign = "-" if source.coord.icrs.dec.deg < 0 else "+"
            outline = "{:<8.8s} {:<8.8s} {:02d} {:02d} {:08.5f} {}{:02d} {:02d} {:07.4f} 2000.0  0  0  0  0".format(name1, name2,int(ra[0]),int(ra[1]),ra[2], dec_sign, int(abs(dec[0])),int(abs(dec[1])),abs(dec[2]))
            #print(dec)
            #print("{:<.8s} {:<.8s} {:02d} {:02d} {:08.5f} {}{:02d} {:02d} {:07.4f} 2000.0  0  0  0  0".format(name1, name2,int(ra[0]),int(ra[1]),ra[2],dec_sign, int(abs(dec[0])),int(abs(dec[1])),abs(dec[2])))
            #outline = "{:-8s} {:-8s} {:2d} {:2d} {:07.5f} {:+2d} {:2d} {:06.4f} 2000.0  0  0  0  0".format(name1, name2,ra[0],ra[1],ra[2],ra[0],ra[1],ra[2])
            lines.append(outline)
        lines.append("*")
        return lines
    def plot(self,coord="equitorial",showlabel=True):
        fig=plt.figure(figsize=(8,6))
        ax = fig.add_subplot(111, projection="mollweide")
        ax.grid(True)
        for source in self.sources:
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

class Antenna:
    def __init__(self, code, name, x, y, z, axis, offset, rate1, cst1, lim1, lim2, rate2, cst2, lim3, lim4, diam, termid, twol, altname, sunanglelim=""):
        #LTRCODE ANTENNA  X(METERS) Y(METERS)     Z(METERS)   AXIS  OFFSET RATE1 CST1 LIM1 LIM2  RATE2 CST2 LIM3 LIM4 DIAM TERMID 2-L ALTNAME SUNANGLELIM
        # RATE: (deg/min)
        self.code = code
        self.name = name                                                                                                                 
        self.coord = EarthLocation(x=float(x)*u.m, y=float(y)*u.m, z=float(z)*u.m)
        self.axis = axis
        self.offset = float(offset)                                                                                                     
        self.rate = [float(rate1),float(rate2)]
        self.cst = [float(cst1),float(cst2)]
        self.lim = [[float(lim1),float(lim2)],[float(lim3),float(lim4)]]
        self.diam = float(diam)
        self.termid = termid
        self.twol = twol
        self.altname = altname
        self.sunanglelim = sunanglelim    
        
class SKD_Station:
    def __init__(self):
        self.stations = []
    def add(self, antenna):
        self.stations.append(antenna)
    def delete(self, antenna):
        self.stations.remove(antenna)
    def inputcodes(self,antennacodes):
        for code in antennacodes:
            for antenna in antennasrc:
                    if(code == antenna.code):
                        self.add(antenna)
    def output(self):
        lines=[]
        lines.append("$STATIONS")
        lines.append("* ANTENNA INFORMATION")
        for antenna in self.stations:
            code = antenna.code
            name = antenna.name                                                                                                         
            coord = antenna.coord
            axis = antenna.axis
            offset = antenna.offset                                                                                                     
            rate = antenna.rate
            cst = antenna.cst
            lim = antenna.lim
            diam = antenna.diam
            termid = antenna.termid
            twol = antenna.twol
            altname = antenna.altname
            sunanglelim = antenna.sunanglelim
            #A  T TAKAHAGI AZEL   0.00   4.5    0.0    11.0  349.0   4.5    0.0    5.0   75.0   32.0 TA TA
            outline = "A  {:1s} {:<8.8s} {:4s}   {:.2f}   {:>3.1f}    {:.1f}    {:.1f}  {:.1f}   {:>3.1f}    {:.1f}    {:.1f}   {:.1f}   {:.1f} {:2s} {:2s}".format(
                code,name,axis, offset, rate[0], cst[0], lim[0][0], lim[0][1], rate[1], cst[1], lim[1][0], lim[1][1], diam, termid, twol)
            lines.append(outline)
        lines.append("* STATION POSITION INFORMATION")
        for antenna in self.stations:
            name = antenna.name                                                      
            coord = antenna.coord
            twol = antenna.twol
            outline = "P {:2s} {:<.8s} {:.4f}  {:.4f}  {:.4f} 00000000".format(twol,name,coord.x.value,coord.y.value,coord.z.value)
            lines.append(outline)
        lines.append("*")
        return lines
         
class Sked:
    def __init__(self, name, start, dur, stations, source=None,antennas=None):
        # stations: code [L, H]
        # source and antennas are Source and Antenna objects.
        self.name = name
        self.start = start
        self.dur = dur
        self.stations = stations
        self.source=source
        self.antennas=antennas
        
class SKD_Exper:
    def __init__(self, obscode, name="", correlator="", comment=""):
        self.obscode = obscode
        self.name = name
        self.correlator = correlator
        self.comment = comment
    def output(self):
        lines=[]
        lines.append(f"$EXPER {self.obscode:s}")
        lines.append(f"*P.I.: {self.name:s}")
        lines.append(f"*Correlator: {self.correlator:s}")
        #for i in range (len(self.args)):
        #    lines.append(self.args[i])
        if(self.comment!=""):
            for arg in self.comment.split("\n"):
                lines.append("*"+arg)
        lines.append("*")
        return lines

class SKD_Sked:
    def __init__(self):
        self.skeds = []
    def add(self, sked):
        self.skeds.append(sked)
    def delete(self, sked):
        self.skeds.remove(sked)
    def shift(self,timedelta):
        for sked in self.skeds:
            sked.start = sked.start+timedelta
    def dayshift(self,days):
        lstday = TimeDelta((23*u.hour)+(56*u.min)+(4*u.second))
        timed = days*lstday
        self.shift(timed)       
    def output(self):
        lines=[]
        lines.append("$SKED")
        lines.append("*SOURCES CAL FR          START     DUR       IDLE       STATIONS  TAPE")
        for sked in self.skeds:
            name = sked.name
            start = sked.start.yday.split(":")
            dur = int(sked.dur.sec)
            if(len(str(dur))>=5):
                print("duration is too long")
                return -1
            stations = sked.stations
            staline=""
            for station in stations:
                staline=staline+station+"-"
            tapeline=""
            for i in range(len(stations)):
                tapeline = tapeline+"1F00000 "
            tapeline = tapeline+"YNNN"
            outline = f"{name:<8.8s}  10 S2  PREOB {int(start[0][2:4]):02d}{int(start[1]):03d}{int(start[2]):02d}{int(start[3]):02d}{int(float(start[4])):02d} {dur:>4d}  MIDOB 0 POSTOB {staline:s} {tapeline:s}"
            lines.append(outline)
        lines.append("*")
        return lines


def Read_drg(lines,section,readcomment=False):
    if section not in ["EXPER","PARAM","SOURCES","STATIONS","SKED","HEAD","CODES"]:
        print("Parameter %s is not correct. Please check if it is capitalized."%(section))
        return -1
    sectionlines=[]
    readmode=False
    section="$"+section
    for line in lines:
        line=line.rstrip()
        if not line:
            continue
        if(readmode):
            if(line[0]=="$"):
                readmode=False
                continue
            if(line[0]=="*"):
                if(readcomment):
                    sectionlines.append(line)
                    continue
                else:
                    continue
            else:
                sectionlines.append(line)
        else:
            if(line[0]=="$" and section in line):
                readmode=True
                if(readcomment):
                    sectionlines.append(line)
    return sectionlines

def Read_srcline(line):
    try:
        lines = line.split()
        name1 = lines[0]
        name2 = lines[1]
        ra = lines[2] + "h" + lines[3] + "m" + lines[4] + "s"
        dec = lines[5] + "d" + lines[6] + "m" + lines[7] + "s"
        equinox = lines[8]
        if (equinox != "2000.0"):
            equinox = "B" + equinox
        else:
            equinox = "J2000.0"
        coord = SkyCoord(ra, dec, equinox=equinox)
        return Source(name1, coord, name2)
    except ValueError:
        print("Error reading source line: %s" % line)
        return None

def Read_sources(readlines):
    srcline = SKD_Source()
    for line in readlines:
        try:
            lines = line.split()
            name1 = lines[0]
            name2 = lines[1]
            ra = lines[2] + "h" + lines[3] + "m" + lines[4] + "s"
            dec = lines[5] + "d" + lines[6] + "m" + lines[7] + "s"
            equinox = lines[8]
            if (equinox != "2000.0"):
                equinox = "B" + equinox
            else:
                equinox = "J2000.0"
            coord = SkyCoord(ra, dec, equinox=equinox)
            src = Source(name1, coord, name2)
            srcline.add(src)
        except ValueError:
            print("Error reading source line: %s" % line)
            return None
    return srcline

def Read_skedline(line):
    lines=line.split()
    name=lines[0]
    timeline = "20"+lines[4][0:2]+":"+lines[4][2:5]+":"+lines[4][5:7]+":"+lines[4][7:9]+":"+lines[4][9:11]+".0"
    #print(timeline)
    starttime=Time(timeline)
    #print(starttime.iso)
    #return Source(name1,coord,name2)
    dur = TimeDelta(lines[5],format='sec')
    antennas=lines[9].split("-")
    if(antennas[-1]==""):
        del(antennas[-1])
    #print(name,starttime,dur,antennas)
    return Sked(name,starttime,dur,antennas)

def Read_skeds(lines):
    skedlines = SKD_Sked()
    for line in lines:
        skd = Read_skedline(line)
        skedlines.add(skd)
    return skedlines

def Read_stations(readlines):
    antennas = SKD_Station()
    for line in readlines:
        try:
            lines = line.split()
            if(lines[0]=="A"):
                for antenna in antennasrc:
                    if(antenna.code == lines[1]):
                        antennas.add(antenna)
        except ValueError:
            print("Error reading source line: %s" % line)
            return None
    return antennas

def Read_experline(readlines):
    args=[]
    for line in readlines:
        lines=line.split()
        if(lines[0][0]=="$"):
            obscode=lines[1]
        elif("P.I." in lines[0]):
            name = line[7:]
        elif("Correlator" in lines[0]):
            correlator = line[13:]
        elif(len(lines[0])!=1):
            args.append(line)
    return SKD_Exper(obscode,name,correlator,*args)

def Read_antennasch(filename):
    antennas = []
    header=True
    with open(filename,"r") as f:
        lines = f.readlines()
        for line in lines:
            if(line[0]!="*"):
                ll=line.split()
                if(len(ll[0])==1):
                    antenna = Antenna(ll[0],ll[1],ll[2],ll[3],ll[4],ll[5],ll[6],ll[7],ll[8],ll[9],ll[10],ll[11],ll[12],ll[13],ll[14],ll[15],ll[16],ll[17],ll[18])
                    antennas.append(antenna)
    return antennas

antennasrc = Read_antennasch(Path(__file__).resolve().parent / "antenna.sch")

def Read_station(filename):
    # args=[]
    # for line in readlines:
    #     lines=line.split()
    #     if(lines[0][0]=="$"):
    #         obscode=lines[1]
    #     elif("P.I." in lines[0]):
    #         name = lines[1]
    #     elif("Correlator" in lines[0]):
    #         correlator = lines[1]
    #     elif(len(lines[0])!=1):
    #         args.append(line)
    # header=True
    antennas = []
    with open(filename,"r") as f:
        lines = f.readlines()
        for line in lines:
            if(line[0]!="*"):
                ll=line.split()
                if(len(ll[0])==1):
                    antenna = Antenna(ll[0],ll[1],ll[2],ll[3],ll[4],ll[5],ll[6],ll[7],ll[8],ll[9],ll[10],ll[11],ll[12],ll[13],ll[14],ll[15],ll[16],ll[17],ll[18])
                    antennas.append(antenna)
    return antennas

def Query_Simbad(name):
    result_table = Simbad.query_object(name)
    return result_table

def Query_VLBAcalib(c_target, f_th=0.1, sep_th=2.):
    from calibrator_catalog import search_catalog
    return search_catalog(c_target, f_th, 0, sep_th, expand=True)

##############
# For ELplot func.
def trans_azel(coordinate,obstime,loc):
    altaz=coordinate.transform_to(AltAz(obstime=obstime, location=loc))
    return altaz,altaz.az.deg,altaz.alt.deg

def trans_timelist(timelist):
    return Time("20"+timelist[0]+":"+timelist[1]+":"+timelist[2][0:2]+":"+timelist[2][2:4]+":"+timelist[2][4:6]+".000",format="yday")

def calc_lst(location, datetime_):
    localtime = Time(datetime_, format='datetime', location=location)
    return localtime.sidereal_time('apparent')
# For antenna slew calc.
def ant_slew_old(az,el,nextaz,nextel,antspeed_az,antspeed_el,dt):
    antspeed_az = antspeed_az/60.
    antspeed_el = antspeed_el/60.
    if(abs(nextaz-az)<(antspeed_az*dt) and abs(nextel-el)<(antspeed_el*dt)):
        on_source=True
        return nextaz,nextel,on_source
    else:
        on_source=False
        if(abs(nextaz-az) <= (antspeed_az*dt)):
            az=nextaz
        elif(az<nextaz):
            az=az+(antspeed_az*dt)
        elif(az>nextaz):
            az=az-(antspeed_az*dt)
        if(abs(nextel-el) <= (antspeed_el*dt)):
            el=nextel
        elif(el<nextel):
            el=el+(antspeed_el*dt)
        elif(el>nextel):
            el=el-(antspeed_el*dt)
        return az,el,on_source
        
def checkantlim(az,el,az_det,lim):
    azlim=False
    ellim=False
    if(el>float(lim[1][1])):
        nextel = lim[1][1]
        ellim=True
    elif(el<float(lim[1][0])):
        nextel = lim[1][0]
        ellim=True
    else:
        nextel = el
    if(az_det):
        if(az < float(lim[0][0])):
            nextaz = lim[0][0]
            azlim=True
        elif(az > float(lim[0][1])):
            nextaz = lim[0][1]
            azlim=True
        else:
            nextaz = az
    else:
        nextaz = az
    if(ellim or azlim):
        on_source=False
    else:
        on_source=True
    return nextaz,nextel,azlim,ellim,on_source

def ant_slew(az,el,nextaz,nextel,antspeed_az,antspeed_el,dt,az_det,lim):
    antspeed_az = antspeed_az/60.
    antspeed_el = antspeed_el/60.
    nextaz,nextel,azlim,ellim,on_source = checkantlim(nextaz,nextel,az_det,lim)
    if((not ellim) and (not azlim) and (abs(nextaz-az)<(antspeed_az*dt) and abs(nextel-el)<(antspeed_el*dt))):
        on_source=True
        return nextaz,nextel,on_source,azlim,ellim
    else:
        on_source=False
        if(abs(nextaz-az) <= (antspeed_az*dt)):
            az=nextaz
        elif(az<nextaz):
            az=az+(antspeed_az*dt)
        elif(az>nextaz):
            az=az-(antspeed_az*dt)
        if(abs(nextel-el) <= (antspeed_el*dt)):
            el=nextel
        elif(el<nextel):
            el=el+(antspeed_el*dt)
        elif(el>nextel):
            el=el-(antspeed_el*dt)
        return az,el,on_source,azlim,ellim
