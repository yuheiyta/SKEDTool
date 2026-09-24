from threading import RLock
from astronomy_helpers import simbad_coordinate
from schedule_validation import validate_schedule
from schedule_io import show_paste, show_outputs, prepare_iers, plot_action
from vex_templates import CUSTOM_DIR, load_template, apply_template, parse_template
from vera_import import vera_only_text
import SKEDTools_vex
import flet as ft
from flet import Page
from flet.matplotlib_chart import MatplotlibChart
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time, TimeDelta
import matplotlib
import matplotlib.pyplot as plt

import numpy as np
from pathlib import Path
TEMPLATE_DIR = str(Path(__file__).resolve().parent / "template") + "/"

#from memory_profiler import profile

#global src_row,src_table
matplotlib.use("Agg")

def main(page: Page):

    event_lock = RLock()
    event_depth = 0

    def error_handler(func):
        def wrapper(*args, **kwargs):
            nonlocal event_depth
            if not event_lock.acquire(blocking=False):
                return None  # Ignore clicks while this session is processing.
            event_depth += 1
            try:
                return func(*args, **kwargs)
            except Exception as error:
                if event_depth > 1:
                    raise
                bannertext.value = str(error)
                page.banner.open = True
                page.update()
            finally:
                event_depth -= 1
                event_lock.release()
        return wrapper

    # Pick files dialog
    @error_handler
    def pick_file_result(e: ft.FilePickerResultEvent):
        if(e.files!=None):
            path = e.files[0].path
            import_vera(Path(path).read_text(encoding='utf-8-sig'))
            obscode = path.split("/")[-1]
            selected_file.value = obscode
            #selected_file.update()
            all_update(selected_index=0)
        else:
            print("Cancelled!")

    @error_handler 
    def exp_update():
        exp_cont_name.value = vex.exper.list[0].name
        exp_cont_description.value = vex.exper.list[0].description
        exp_cont_piname.value = vex.exper.list[0].pi_name
        exp_cont_email.value = vex.exper.list[0].pi_email
        try:
            start = (vex.sched.list[0].start-20*u.min).yday.replace(".000","").split(":")
            stop = (vex.sched.list[-1].start+vex.sched.list[-1].dur+15*u.min).yday.replace(".000","").split(":")
            vex.exper.list[0].start = start[0]+"y"+start[1]+"d"+start[2]+"h"+start[3]+"m"+start[4]+"s"
            vex.exper.list[0].stop = stop[0]+"y"+stop[1]+"d"+stop[2]+"h"+stop[3]+"m"+stop[4]+"s"
        except:
            pass
        #exp_cont_comment.value = vex.exper.comment
        lines = vex.exper.output()
        exp_cont_output.value = lines
        #exp_cont_output.value = "\n".join(lines)
        save_file_dialog.file_name =vex.exper.list[0].defname+".VEX"
        #save_file_path.value = drg.exper.obscode+".DRG_"

    @error_handler        
    def sta_update():
        lines = vex.station.output()
        #sta_cont_output.value = lines
        #sta_cont_output.value = "\n".join(lines)

    @error_handler        
    def src_update():
        nonlocal src_table, src_tab, selected_src
        src_row = []
        selected_src=[]
        if(vex.source is not None):
            for i,source in enumerate(vex.source.list):
                src_row.append(ft.DataRow([ft.DataCell(ft.Text(i+1)),
                                           ft.DataCell(ft.Text(source.name)),
                                           ft.DataCell(ft.Text(source.coord.icrs.ra.to_string(u.hour))),
                                           ft.DataCell(ft.Text(source.coord.icrs.dec.to_string(u.degree, pad=True,alwayssign=True)))], 
                                          selected=False,
                                          on_select_changed=src_select))
                                          
                                          #print(e.control.cells[0].content.value, e.control.cells[1].content.value,e.data)))
        src_table = ft.DataTable(show_checkbox_column=True, columns=[ft.DataColumn(ft.Text("ID")),
                                                                     ft.DataColumn(ft.Text("Name")),
                                                                     ft.DataColumn(ft.Text("RA")),
                                                                     ft.DataColumn(ft.Text("Dec"))], rows=src_row)
        skd_source1.options = []
        skd_source2.options = []
        skd_uvplot_srcname.options = []
        for source in vex.source.list:
            skd_source1.options.append(ft.dropdown.Option(source.name))
            skd_source2.options.append(ft.dropdown.Option(source.name))
            skd_uvplot_srcname.options.append(ft.dropdown.Option(source.name))
        lines = vex.source.output()
        #src_cont_output.value = "\n".join(lines)
        src_cont_output.value =lines
        src_table = ft.Column([src_table],height=200,scroll=ft.ScrollMode.ALWAYS)
        src_col = ft.Column([txt_space,inputtxt,src_name_row,src_coord_row,src_frame_row,src_button_row,src_table,src_button_select_row,src_button_plot_row,outputtxt, src_cont_output_cont],scroll=ft.ScrollMode.ALWAYS)
        src_container = ft.Container(src_col, alignment=ft.alignment.top_center)
        src_tab =ft.Tab(text="SOURCE",content=src_container)
        #print(src_table)

    @error_handler 
    def skd_update():
        nonlocal skd_table, skd_tab,selected_skd,dualbeam
        selected_skd = []
        skd_row = []
        if(vex.sched is not None):
            for i,sked in enumerate(vex.sched.list):
                #print(sked.name)
                #start = sked.start.yday.split(":")
                start = sked.start.yday.replace(".000","").split(":")
                startlist = start[0]+"y"+start[1]+"d"+start[2]+"h"+start[3]+"m"+start[4]+"s"
                #start_c = int(start[0][2:4]+start[1]+start[2]+start[3]):02d}{int(float(start[4])):02d}"
                dur = int(sked.dur.sec)
                dur = f"{dur:>4d}"
                if (dualbeam==False):
                    skd_row.append(ft.DataRow([ft.DataCell(ft.Text(i+1)),
                                            ft.DataCell(ft.Text(sked.name)),
                                            ft.DataCell(ft.Text(startlist)),
                                            ft.DataCell(ft.Text(dur)),
                                            ft.DataCell(ft.Text(", ".join(sked.stations))),
                                            ft.DataCell(ft.Text(sked.mode))], 
                                            selected=False,
                                            on_select_changed=skd_select))
                else:
                    skd_row.append(ft.DataRow([ft.DataCell(ft.Text(i+1)),
                                            ft.DataCell(ft.Text(sked.source1)),
                                            ft.DataCell(ft.Text(sked.source2)),
                                            ft.DataCell(ft.Text(startlist)),
                                            ft.DataCell(ft.Text(dur)),
                                            ft.DataCell(ft.Text(", ".join(sked.stations))),
                                            ft.DataCell(ft.Text(sked.mode))], 
                                            selected=False,
                                            on_select_changed=skd_select))
                                          #print(e.control.cells[0].content.value, e.control.cells[1].content.value,e.data)))
            if(dualbeam==False):
                skd_table = ft.DataTable(show_checkbox_column=True, 
                                        columns=[ft.DataColumn(ft.Text("ID")),
                                                                        ft.DataColumn(ft.Text("Source1")),
                                                                        ft.DataColumn(ft.Text("Start")),
                                                                        ft.DataColumn(ft.Text("Duration")),
                                                                        ft.DataColumn(ft.Text("Stations")),
                                                                        ft.DataColumn(ft.Text("Mode"))],
                                        sort_column_index=2, sort_ascending=True,rows=skd_row)
            else:
                skd_table = ft.DataTable(show_checkbox_column=True, 
                                        columns=[ft.DataColumn(ft.Text("ID")),
                                                                        ft.DataColumn(ft.Text("Source1")),
                                                                        ft.DataColumn(ft.Text("Source2")),
                                                                        ft.DataColumn(ft.Text("Start")),
                                                                        ft.DataColumn(ft.Text("Duration")),
                                                                        ft.DataColumn(ft.Text("Stations")),
                                                                        ft.DataColumn(ft.Text("Mode"))],
                                        sort_column_index=2, sort_ascending=True,rows=skd_row)
            lines = vex.sched.output()
            skd_cont_output.value = lines
            #skd_cont_output.value = "\n".join(lines)
        #skd_table = src_table
        if(dualbeam):
            skd_source2.disabled = False
        else:
            skd_source2.value=""
            skd_source2.disabled = True
        skd_table = ft.Column([skd_table],height=250,scroll=ft.ScrollMode.ALWAYS)
        skd_col = ft.Column([txt_space,inputtxt,skd_row1,skd_row2,skd_mode, skd_inputbutton_row,skd_table, skd_selectbutton_row, skd_uvplot_txt, skd_uvplot_row, outputtxt, skd_cont_output_cont], scroll=ft.ScrollMode.ALWAYS)
        skd_container = ft.Container(skd_col, alignment=ft.alignment.top_center)
        skd_tab =ft.Tab(text="SCHED",content=skd_container)
        #print(skd_table)

    @error_handler    
    def mode_update():
        nonlocal dualbeam
        if("1BEAM" in vex.glob.procedures):
            dualbeam=False
            skd_source2.value=""
            skd_source2.disabled=True
        elif("2BEAM" in vex.glob.procedures):
            dualbeam=True
            skd_source2.disabled=False
        mode_cont_output.value = vex.header.output()+"\n"+vex.freq.output()+"\n"+vex.mode.output()
        skd_modetable=[]
        for mode in vex.mode.list:
            skd_modetable.append(ft.dropdown.Option(key=mode.defname, text=mode.defname))
        skd_mode.options=skd_modetable

    @error_handler
    def plt_update(fig):
        previous = mpl.figure
        mpl.figure = fig
        if previous is not fig:
            plt.close(previous)


    @error_handler 
    def file_timeshift(e):
        timetxt = file_input_timeshift.value.strip()
        if(timetxt == ""):
            raise ValueError("Time Delta is empty")
        timed=0
        sign=1.0
        if(timetxt[0]=="-"):
            sign=-1.0
            timetxt=timetxt.strip("-")
        if('y' in timetxt):
            inputt=timetxt.split("y")
            timed+=float(inputt[0])*u.year
            timetxt = inputt[1]
        if('d' in timetxt):
            inputt=timetxt.split("d")
            timed+=float(inputt[0])*u.day
            timetxt = inputt[1]
        if('h' in timetxt):
            inputt=timetxt.split("h")
            timed+=float(inputt[0])*u.hour
            timetxt = inputt[1]
        if('m' in timetxt):
            inputt=timetxt.split("m")
            timed+=float(inputt[0])*u.min
            timetxt = inputt[1]
        if('s' in timetxt):
            inputt=timetxt.split("s")
            timed+=float(inputt[0])*u.second
            timetxt = inputt[1]     
        vex.shift(sign*timed)
        all_update(selected_index=0)

    @error_handler     
    def file_lstshift(e):
        vex.dayshift(float(file_input_lstshift.value))
        all_update(selected_index=0)

    @error_handler     
    def src_simbadquery(e):
        tab = SKEDTools_vex.Query_Simbad(src_name1.value)
        if(tab is not None):
            c = simbad_coordinate(tab).to_string('hmsdms').split()
            src_ra.value = c[0]
            src_dec.value = c[1]
            page.update()
        else:
            pass

    @error_handler 
    def src_select(e):
        e.control.selected = not e.control.selected
        if(e.control.selected):
            selected_src.append(e.control.cells[0].content.value)
        else:
            selected_src.remove(e.control.cells[0].content.value)
        if(len(selected_src)>0):
            skd_source1.value=vex.source.list[selected_src[0]-1].name
        else:
            skd_source1.value=""
        selected_src.sort()
        #print(selected_src)
        page.update()
    
    @error_handler 
    def sta_select(e):
        e.control.selected = not e.control.selected
        if(e.control.selected):
            selected_sta.append(e.control.cells[1].content.value)
        else:
            selected_sta.remove(e.control.cells[1].content.value)
        #print(selected_sta)
        selected_sta.sort()
        page.update()

    @error_handler     
    def skd_select(e):
        e.control.selected = not e.control.selected
        if(e.control.selected):
            selected_skd.append(e.control.cells[0].content.value)
        else:
            selected_skd.remove(e.control.cells[0].content.value)
        selected_skd.sort()
        #print(selected_skd)
        page.update()

    @error_handler
    def sta_add(e):
        vex.station=SKEDTools_vex.SKD_Station()
        if(selected_sta!=[]):
            vex.station.inputcodes(selected_sta)
        sta_update()
        page.update()

    @error_handler     
    def exp_add(e):
        if(exp_cont_name.value!=""):
            vex.exper.list[0].name = exp_cont_name.value
            vex.exper.list[0].defname = exp_cont_name.value
            vex.glob.exper = exp_cont_name.value
        if(exp_cont_description.value!=""):
            vex.exper.list[0].description = exp_cont_description.value
        if(exp_cont_piname.value!=""):
            vex.exper.list[0].pi_name = exp_cont_piname.value
        if(exp_cont_email.value!=""):
            vex.exper.list[0].pi_email = exp_cont_email.value
        #if(exp_cont_comment.value!=""):
        #    vex.exper.comment = exp_cont_comment.value
        exp_update()
        page.update()

    @error_handler    
    def src_add(e):
        name1 = src_name1.value
        if(src_frame.value !=""):
            if(src_equinox.value != ""):
                c=SkyCoord(src_ra.value,src_dec.value,frame=src_frame.value,equinox=src_equinox.value)
            else:
                c=SkyCoord(src_ra.value,src_dec.value,frame=src_frame.value)
        elif(src_equinox.value != ""):
            c=SkyCoord(src_ra.value,src_dec.value,equinox=src_equinox.value)
        else:
            c=SkyCoord(src_ra.value,src_dec.value)
        if(src_name2.value != ""):
            name2=src_name2.value
            #newsrc = SKEDTools_vex.Source(name1,c,name2=name2)
            newsrc = SKEDTools_vex.Source(name1,name1,ra=c.icrs.ra.to_string('hour'),dec=c.icrs.dec.to_string('deg'),ref_coord_frame="J2000",name2=name2)
        else:
            #newsrc = SKEDTools_vex.Source(name1,c)
            #print(c.ra.to_string())
            newsrc = SKEDTools_vex.Source(name1,name1,ra=c.icrs.ra.to_string('hour'),dec=c.icrs.dec.to_string('deg'),ref_coord_frame="J2000")
        #print(vex.source, newsrc)
        vex.source.add(newsrc)
        src_update()
        page_update(selected_index=src_index)
    
    @error_handler 
    def skd_add(e):
        nonlocal dualbeam
        source1=skd_source1.value
        if(dualbeam):
            source2=skd_source2.value
        else:
            source2=""
        mode = skd_mode.value
        start = skd_start.value
        dur=skd_dur.value
        antcodes = veraantlist
        station=[]
        for antcode in antcodes:
            station.append(f"{antcode}:    0 sec:   {dur} sec:     0 sec:   :   : :    : 1;")
        #stationtxt="\n".join(station)
        #antcodes=skd_sta.value.replace(' ', '').split(",")
        sked = SKEDTools_vex.Sched(defname="No00001", mode=mode, start=start, source1=source1, station=station, source2=source2)

        vex.sched.add(sked)
        vex.adjust()
        skd_update()
        exp_update()
        page_update(selected_index=skd_index)

    @error_handler         
    def skd_change(e):
        nonlocal selected_skd, dualbeam
        if(len(selected_skd)==0):
            pass
        elif(len(selected_skd)>1):
            page.snack_bar = ft.SnackBar(ft.Text("Please select only one row"))
            page.snack_bar.open = True
            page.update()
        elif(len(selected_skd)==1):
            index=selected_skd[0]-1
            source1=skd_source1.value
            if(dualbeam):
                source2=skd_source2.value
            else:
                source2=""
            mode = skd_mode.value
            start = skd_start.value
            dur=skd_dur.value
            antcodes = veraantlist
            station=[]
            for antcode in antcodes:
                station.append(f"{antcode}:    0 sec:   {dur} sec:     0 sec:   :   : :    : 1;")
        #stationtxt="\n".join(station)
        #antcodes=skd_sta.value.replace(' ', '').split(",")
            sked = SKEDTools_vex.Sched(defname="No00001", mode=mode, start=start, source1=source1, station=station, source2=source2)
            vex.sched.list[index] = sked
            vex.adjust()
            skd_update()
            exp_update()
            page_update(selected_index=skd_index)
   
    @error_handler 
    def src_clear(e):
        src_name1.value = ""
        src_name2.value = ""
        src_ra.value = ""
        src_dec.value = ""
        src_frame.value = ""
        src_equinox.value = ""
        page.update()

    @error_handler    
    def skd_clear(e):
        skd_source1.value = ""
        skd_start.value = ""
        skd_dur.value = ""
        skd_source2.value = ""
        page.update()

    @error_handler        
    def src_rem(e):
        nonlocal selected_src
        for i in reversed(selected_src):
            vex.source.delete(vex.source.list[i-1])
        src_update()
        page_update(selected_index=src_index)

    @error_handler     
    def skd_rem(e):
        nonlocal selected_skd
        #print(vex.sked.skeds,len(vex.sked.skeds))
        for i in reversed(selected_skd):
            vex.sched.delete(vex.sched.list[i-1])
        vex.adjust()
        skd_update()
        exp_update()
        page_update(selected_index=skd_index)

    @error_handler         
    def skd_edit(e):
        nonlocal selected_skd
        if(len(selected_skd)==0 or len(selected_skd)>1):
            page.snack_bar = ft.SnackBar(ft.Text("Please select one row"))
            page.snack_bar.open = True
            page.update()
        elif(len(selected_skd)==1):
            index=selected_skd[0]-1
            sked = vex.sched.list[index]
            source1 = sked.source1
            start = sked.start.yday.replace(".000","").split(":")
            start = start[0]+"y"+start[1]+"d"+start[2]+"h"+start[3]+"m"+start[4]+"s"
            dur = int(sked.dur.sec)
            dur = f"{dur:>4d}"
            source2 = sked.source2
            mode = sked.mode
            #sta = ", ".join(sked.stations)
            skd_source1.value = source1
            skd_start.value = start
            skd_dur.value = dur
            skd_source2.value = source2
            skd_mode.value = mode
            page.update()

    #@profile
    @error_handler     
    @plot_action(page)
    def skd_azel(e):
        prepare_iers(page, iers_text, validate_schedule(vex, vera=True))
        def check_slewspeed(altaz_p,altaz_i,sked_antenna,timed):
            if(abs(sked_antenna.lim[0][1]-sked_antenna.lim[0][0])< 360.):
                if(np.abs((altaz_p.az.deg - altaz_i.az.deg)/float(sked_antenna.rate[0])) > (timed).sec/60.):
                    msg.append("Error: Tracking delay at {} (Az)".format(sked_antenna.name))
                if(np.abs(altaz_p.alt.deg - altaz_i.alt.deg)/float(sked_antenna.rate[1]) > (timed).sec/60.):
                    msg.append("Error: Tracking delay at {} (El)".format(sked_antenna.name))
            else:
                azdiff = np.abs(altaz_p.az.deg - altaz_i.az.deg)
                if(azdiff > 180.):
                    azdiff = 360.-azdiff
                if(azdiff/float(sked_antenna.rate[0]) > (timed).sec/60.):
                    msg.append("Error: Tracking delay at {} (Az)".format(sked_antenna.name))
                if(np.abs(altaz_p.alt.deg - altaz_i.alt.deg)/float(sked_antenna.rate[1]) > (timed).sec/60.):
                    msg.append("Error: Tracking delay at {} (El)".format(sked_antenna.name))
        def check_azellimit(altaz_i,altaz_e,sked_antenna):
            if(abs(sked_antenna.lim[0][1]-sked_antenna.lim[0][0])< 360.):
                if(altaz_i.az.deg < float(sked_antenna.lim[0][0]) or float(sked_antenna.lim[0][1]) < altaz_i.az.deg):
                    msg.append("Error: Azimuth limit at {} (START)".format(sked_antenna.name))
                elif(altaz_e.az.deg < float(sked_antenna.lim[0][0]) or float(sked_antenna.lim[0][1]) < altaz_e.az.deg):
                    msg.append("Error: Azimuth limit at {} (END)".format(sked_antenna.name))
            if(altaz_i.alt.deg < float(sked_antenna.lim[1][0]) or float(sked_antenna.lim[1][1]) < altaz_i.alt.deg):
                msg.append("Error: Elevation limit at {} (START)".format(sked_antenna.name))
            elif(altaz_e.alt.deg < float(sked_antenna.lim[1][0]) or float(sked_antenna.lim[1][1]) < altaz_e.alt.deg):
                msg.append("Error: Elevation limit at {} (END)".format(sked_antenna.name))
        lines=[]
        msg=[]
        for idx in selected_skd:
            skd = vex.sched.list[idx-1]
            lines.append(" (Az, El) at {}".format(skd.start.yday))
            if(idx==1):
                head=""
                azel=""
                msg=[]
                for i,antenna in enumerate(skd.antennas):
                    altaz_cur,az_cur,el_cur = SKEDTools_vex.trans_azel(skd.src[0].coord,skd.start,antenna.coord)
                    altaz_end,az_end,el_end = SKEDTools_vex.trans_azel(skd.src[0].coord,skd.start+skd.dur,antenna.coord)
                    head+=" {:^16} |".format(antenna.name)
                    azel+="  ({:>5.1f}, {:4.1f})   |".format(altaz_cur.az.deg,altaz_cur.alt.deg)
                    check_azellimit(altaz_cur,altaz_end,antenna)
                lines.append(head)
                lines.append(azel)
                lines=lines+msg
            elif(idx>1):
                skd_prev = vex.sched.list[idx-2]
                endtime_prev = skd_prev.start +skd_prev.dur
                head=""
                azel=""
                msg=[]
                for i,antenna in enumerate(skd.antennas):
                    altaz_prev,az_prev,el_prev = SKEDTools_vex.trans_azel(skd_prev.src[0].coord,endtime_prev,antenna.coord)
                    altaz_cur,az_cur,el_cur = SKEDTools_vex.trans_azel(skd.src[0].coord,skd.start,antenna.coord)
                    altaz_end,az_end,el_end = SKEDTools_vex.trans_azel(skd.src[0].coord,skd.start+skd.dur,antenna.coord)
                    head+=" {:^16} |".format(antenna.name)
                    azel+="  ({:>5.1f}, {:4.1f})   |".format(altaz_cur.az.deg,altaz_cur.alt.deg)
                    check_slewspeed(altaz_prev,altaz_cur,antenna,(skd.start-endtime_prev))
                    check_azellimit(altaz_cur,altaz_end,antenna)
                lines.append(head)
                lines.append(azel)
                lines=lines+msg
        bstxt.value="\n".join(lines)
        bs.open = True
        bs.update()

    def close_bs(e):
        bs.open = False
        bs.update()

    def close_banner(e):
        page.banner.open = False
        page.update()

    bannertext = ft.Text("")
    page.banner = ft.Banner(
        bgcolor=ft.colors.AMBER_100,
        leading=ft.Icon(ft.icons.WARNING_AMBER_ROUNDED, color=ft.colors.AMBER, size=40),
        content=bannertext,
        actions=[ft.TextButton("Close", on_click=close_banner)])

    #@profile
    @error_handler 
    @plot_action(page)
    def sourceplot(e):
        fig = vex.sourceplot()
        #fig.savefig("assets/tmpfig.png")
        #mpl.src="/tmpfig.png"
        #mpl.update()
        #mpl.figure=fig
        #page.update()
        #mpl.update()
        plt_update(fig)
        page_update(plt_index)

    #@profile
    @error_handler        
    @plot_action(page)
    def lst_elplot(e):
        prepare_iers(page, iers_text, validate_schedule(vex, vera=True))
        srcnames=[]
        for i in selected_src:
            srcnames.append(vex.source.list[i-1].name)
        fig = vex.el_plot(srcnames=srcnames)
        #image_widget = embed_matplotlib_figure(fig)
        #mpl.figure=fig
        #fig.savefig("testfig.png")
        plt_update(fig)
        page_update(plt_index)

    @error_handler           
    @plot_action(page)
    def ut_elplot(e):
        prepare_iers(page, iers_text, validate_schedule(vex, vera=True))
        srcnames=[]
        for i in selected_src:
            srcnames.append(vex.source.list[i-1].name)
        fig = vex.el_plot(srcnames=srcnames,timezone="ut")
        plt_update(fig)
        page_update(plt_index)
        
    @error_handler
    @plot_action(page)
    def jst_elplot(e):
        prepare_iers(page, iers_text, validate_schedule(vex, vera=True))
        srcnames=[]
        for i in selected_src:
            srcnames.append(vex.source.list[i-1].name)
        fig = vex.el_plot(srcnames=srcnames,timezone="jst")
        plt_update(fig)
        page_update(plt_index)    
 
    @error_handler
    @plot_action(page)
    def skd_uvplot(e):
        prepare_iers(page, iers_text, validate_schedule(vex, vera=True))
        if(skd_uvplot_sta.value != ""):
            antcodes = [antcode.strip() for antcode in skd_uvplot_sta.value.split(",") if antcode.strip()]
            fig = vex.uvplot(skd_uvplot_srcname.value, antcodes=antcodes)
        else:
            fig = vex.uvplot(skd_uvplot_srcname.value)
        plt_update(fig)
        page_update(plt_index)

    @error_handler         
    def all_update(selected_index=1):
        exp_update()
        mode_update()
        sta_update()
        src_update()
        skd_update()
        page_update(selected_index)

    @error_handler    
    def page_update(selected_index=1):
        nonlocal selected_src, selected_skd
        selected_src=[]
        selected_skd=[]
        #print("page updating")
        tabs=[file_tab,mode_tab, exp_tab,src_tab,skd_tab,plt_tab]
        t = ft.Tabs(selected_index=selected_index,animation_duration=300,tabs=tabs,expand=1)
        page.controls[:] = [t]
        page.update()

    @error_handler  
    def beam_changed(e):
        vex.glob.procedures = beamselect.value
        page.update()

    @error_handler
    def mode_changed(e):
        apply_template(vex, observing_templates[modeselect.value])
        skd_mode.value = None
        mode_update()
        page.update()

    @error_handler    
    def vex_check(e):
        scans = validate_schedule(vex, vera=True)
        file_output_text.value = ""
        prepare_iers(page, iers_text, scans)
        file_output_text.value="Processing..."
        page.update()
        msg = vex.check()
        #print(msg)
        file_output_text.value= "\n".join(msg)
        page.update()

    @error_handler     
    @plot_action(page)
    def vex_deepcheck(e):
        scans = validate_schedule(vex, vera=True)
        file_output_text.value = ""
        prepare_iers(page, iers_text, scans)
        file_output_text.value="Processing..."
        page.update()
        msg, fig = vex.azelplot()
        file_output_text.value= "\n".join(msg)
        plt_update(fig)
        page.update()

    @error_handler    
    def copy_clip(e):
        validate_schedule(vex, vera=True)
        show_outputs(page, {"schedule.vex": vex.output()})



    #@error_handler    
    def vlba_search(e):
        def calib_select(e):
            for i, row in enumerate(cands_table.rows):
                if i+1 == e.control.cells[0].content.value:
                    row.selected = True
                else:
                    row.selected = False
            selected_index = e.control.cells[0].content.value-1
            calib_input(selected_index)
        def calib_input(index):
            src_name1.value = cands[index][2]
            src_name2.value = ""
            src_ra.value = cands[index][5]
            src_dec.value = cands[index][6]
            src_frame.value = ""
            page.update()
        def close_dlg(e):
            dlg.open = False
            page.update()
        #print(vex.source.sources, selected_src)
        msg, cands = SKEDTools_vex.Query_VLBAcalib(vex.source.list[selected_src[0]-1].coord)
        cands_row = []
        for i,cand in enumerate(cands): 
            #print(cand[0])
            if(i==0):
                selected_calib=True
                calib_input(i)
            else:
                selected_calib=False
            cands_row.append(ft.DataRow([ft.DataCell(ft.Text(i+1)),
                                        ft.DataCell(ft.Text(cand[0])),
                                        ft.DataCell(ft.Text(cand[2])),
                                        ft.DataCell(ft.Text(cand[7])),
                                        ft.DataCell(ft.Text(cand[8])),
                                        ft.DataCell(ft.Text(cand[9])),
                                        ft.DataCell(ft.Text(cand[10])),
                                        ft.DataCell(ft.Text(cand[11])),
                                        ft.DataCell(ft.Text(cand[12])),
                                        ft.DataCell(ft.Text(cand[15])),
                                        ft.DataCell(ft.Text(cand[16])),
                                        ft.DataCell(ft.Text(cand[20]))],
                                        selected=selected_calib,
                                        on_select_changed=calib_select))
                                        
            cands_table = ft.DataTable(show_checkbox_column=True, 
                                        columns=[ft.DataColumn(ft.Text("ID")),
                                                 ft.DataColumn(ft.Text("Separation"),tooltip="Unit: degree",),
                                                 ft.DataColumn(ft.Text("Name1")),
                                                 ft.DataColumn(ft.Text("F_Ss"),tooltip="Flux density at S-band (2.2 GHz), Short baseline (400 km), Unit: Jy"),
                                                 ft.DataColumn(ft.Text("F_Sl"),tooltip="Flux density at S-band (2.2 GHz), Long baseline (5000 km), Unit: Jy"),
                                                 ft.DataColumn(ft.Text("F_Cs"),tooltip="Flux density at C-band (4.8 GHz), Short baseline (400 km), Unit: Jy"),
                                                 ft.DataColumn(ft.Text("F_Cl"),tooltip="Flux density at C-band (4.8 GHz), Long baseline (5000 km), Unit: Jy"),
                                                 ft.DataColumn(ft.Text("F_Xs"),tooltip="Flux density at X-band (8.6 GHz), Short baseline (400 km), Unit: Jy"),
                                                 ft.DataColumn(ft.Text("F_Xl"),tooltip="Flux density at X-band (8.6 GHz), Long baseline (5000 km), Unit: Jy"),
                                                 ft.DataColumn(ft.Text("F_Ks"),tooltip="Flux density at K-band (23 GHz), Short baseline (400 km), Unit: Jy"),
                                                 ft.DataColumn(ft.Text("F_Kl"),tooltip="Flux density at K-band (23 GHz), Long baseline (5000 km), Unit: Jy"),
                                                 ft.DataColumn(ft.Text("Ref"),tooltip="Position reference")],
                                                 #multi_select=False,
                                                 rows=cands_row,
                                                 column_spacing=15,
                                                 data_text_style = ft.TextStyle(size=13,color=ft.colors.BLACK),
                                                 heading_text_style = ft.TextStyle(size=13,color=ft.colors.BLACK))

        cands_table_col = ft.Column([cands_table],height=250,width='90%',scroll=ft.ScrollMode.ALWAYS)
        dlgtxt = ft.Text(msg)
        dlgcont = ft.Column([dlgtxt,cands_table_col])
        dlg = ft.AlertDialog(content = dlgcont, actions=[
            ft.TextButton("Close", on_click=close_dlg)
        ],)
        page.dialog = dlg
        dlg.open = True
        page.update()

    def search_fringesrc(e):
        def close_dlg(e):
            dlg.open = False
            page.update()
        def fringe_select(e):
            #nonlocal selected_index
            for i, row in enumerate(cands_table.rows):
                if i+1 == e.control.cells[0].content.value:
                    row.selected = True
                else:
                    row.selected = False
            #selected_index = e.index
            src_name1.value = e.control.cells[1].content.value
            src_name2.value = ""
            src_ra.value = e.control.cells[2].content.value
            src_dec.value = e.control.cells[3].content.value
            src_frame.value = ""
            page.update()
        #selected_index = None
        fringe_catalog = TEMPLATE_DIR + "Fringe_Finder_list.txt"
        with open(fringe_catalog)as f:
            alllines= f.readlines()
        lines = SKEDTools_vex.Ext_section(alllines,"SOURCE",readcomment=True)
        fringesrc = SKEDTools_vex.Read_srclines(lines)
        cands_row = []
        for i,source in enumerate(fringesrc.list): 
            cands_row.append(ft.DataRow([ft.DataCell(ft.Text(i+1)),
                                           ft.DataCell(ft.Text(source.name)),
                                           ft.DataCell(ft.Text(source.coord.icrs.ra.to_string(u.hour))),
                                           ft.DataCell(ft.Text(source.coord.icrs.dec.to_string(u.degree, pad=True,alwayssign=True)))], 
                                          selected=False,
                                          on_select_changed=fringe_select))
        cands_table = ft.DataTable(show_checkbox_column=True, columns=[ft.DataColumn(ft.Text("ID")),
                                                                     ft.DataColumn(ft.Text("Name")),
                                                                     ft.DataColumn(ft.Text("RA")),
                                                                     ft.DataColumn(ft.Text("Dec"))], rows=cands_row, on_select_all=None)

        cands_col_table = ft.Column([cands_table],height=500,width='90%',scroll=ft.ScrollMode.ALWAYS)
        #dlgtxt = ft.Text(msg)
        dlgcont = ft.Column([cands_col_table])
        dlg = ft.AlertDialog(content = dlgcont, actions=[
            ft.TextButton("Close", on_click=close_dlg)
        ],)
        page.dialog = dlg
        dlg.open = True
        page.update()
        

    def import_fromtxt(e):
        def apply(text):
            nonlocal event_depth
            with event_lock:
                event_depth += 1
                try:
                    import_vera(text)
                    selected_file.value = vex.glob.exper
                    all_update(selected_index=0)
                finally:
                    event_depth -= 1
        show_paste(page, apply)

    def import_vera(text):
        filtered, removed = vera_only_text(text)
        vex.readtxt(filtered)
        if removed:
            page.snack_bar = ft.SnackBar(ft.Text('Imported VERA stations only. Removed: ' + ', '.join(removed)))
            page.snack_bar.open = True

    page.title = "SKEDTool_JP — VERA"  # アプリタイトル
    src_index, skd_index, plt_index = 3,4,5
    observing_templates = {}
    for path in sorted(CUSTOM_DIR.glob('*.json')):
        data = load_template(path.read_text(encoding='utf-8'))
        if data['name'] in observing_templates:
            raise ValueError(f"Duplicate template display name: {data['name']}")
        observing_templates[data['name']] = data
    default_template = 'K_Cont_1B_SingP_1G'
    vex, _ = parse_template(observing_templates[default_template]['vex'])
    vex.exper.list[0].name = 'template'
    vex.exper.list[0].correlator = 'VERA'

    veraantlist = ["Vm","Vr","Vo","Vs"]
    dualbeam=False

    #drg.read("u23168a.DRG") # for debug
    selected_src=[]
    selected_sta=[]
    selected_skd=[]

    outputfont = "Consolas"
    
    import_file_dialog = ft.FilePicker(on_result=pick_file_result)
    make_skd_dialog = ft.FilePicker()
    make_xml_dialog = ft.FilePicker()
    selected_file = ft.Text()

    bstxt = ft.Text("",font_family=outputfont, color=ft.colors.BLACK, selectable=True)
    bs = ft.BottomSheet(ft.Container(ft.Column([bstxt,ft.ElevatedButton("Close", on_click=close_bs)],tight=True),padding=10),open=False)
    page.overlay.append(bs)

    # Save file dialog
    @error_handler 
    def save_file_result(e: ft.FilePickerResultEvent):
        if(e.path!=None):
            validate_schedule(vex, vera=True)
            path = e.path
            #path = e.files[0].path
            #print(path)
            vex.write(path)
            exp_txt.value = "Saved at " + str(path)
            page.update()
            #exp_txt.update()
            #selected_file.value = obscode
            #selected_file.update()
            #all_update(selected_index=0)
        else:
            print("Cancelled!")

    save_file_dialog = ft.FilePicker(on_result=save_file_result)
    exp_txt = ft.Text()

    
    page.overlay.extend([import_file_dialog, save_file_dialog,make_skd_dialog,make_xml_dialog])

    file_txt = ft.Text("File Manager")
    file_imp = ft.ElevatedButton(text="Import",disabled=page.web, icon=ft.icons.UPLOAD_FILE,on_click=lambda _: import_file_dialog.pick_files())
    file_imp_paste = ft.ElevatedButton(text="Import from text",on_click=import_fromtxt)
    file_imp_row = ft.Row([file_imp,file_imp_paste, selected_file])
    file_exp = ft.ElevatedButton(text="Export",disabled=page.web,icon=ft.icons.SAVE,on_click=lambda _: save_file_dialog.save_file())
    file_clip = ft.ElevatedButton(text="Copy Clipboard",on_click=copy_clip)
    file_exp_row = ft.Row([file_exp,file_clip,exp_txt])
    
    txt_space = ft.Text("",size=3)
    
    file_txt_check = ft.Text("Validation")
    iers_text = ft.Text("IERS: Not checked (checked before validation and plots)", selectable=True)
    file_button_check = ft.ElevatedButton(text="Check",on_click=vex_check)
    file_button_deepcheck = ft.ElevatedButton(text="deepCheck",on_click=vex_deepcheck)
    #file_row_check = ft.Row([file_button_check,file_button_deepcheck])
    file_row_check = ft.Row([file_button_check])
    file_output_text = ft.Text("    ", font_family=outputfont, color=ft.colors.BLACK, selectable=True)
    file_output_check = ft.Column([file_output_text],height=70,scroll=ft.ScrollMode.ALWAYS)
    file_cont_output_check = ft.Container(file_output_check, bgcolor=ft.colors.WHITE, padding=10, border=ft.border.all(1), alignment=ft.alignment.top_left)
    
    file_txt_lstshift = ft.Text("Day shift with the same LST")
    file_input_lstshift = ft.TextField(label = "Day Delta", hint_text="ex) 1",helper_text="Unitless value\n")
    file_button_lstshift = ft.ElevatedButton(text="Shift",on_click=file_lstshift)
    file_row_lstshift = ft.Row([file_txt_lstshift,file_button_lstshift])
    file_col_lstshift = ft.Column([file_row_lstshift,file_input_lstshift])
    file_txt_timeshift = ft.Text("Time shift by the specific value")
    file_input_timeshift = ft.TextField(label = "Time Delta", hint_text="ex) 0y0d23h56m4s",helper_text="Do not change the order of the unit.\nBe careful if the input Time Delta is large.")
    file_button_timeshift = ft.ElevatedButton(text="Shift",on_click=file_timeshift)
    file_row_timeshift = ft.Row([file_txt_timeshift,file_button_timeshift])
    file_col_timeshift = ft.Column([file_row_timeshift,file_input_timeshift])
    file_row_shift =ft.Row([file_col_lstshift,file_col_timeshift],spacing=50)
    
    file_make_txt = ft.Text("Make auxiliary files from saved \".VEX\" file (must be in the current directory.)")
    file_make_skd = ft.ElevatedButton(text=".skd",on_click=lambda _: make_skd_dialog.pick_files())
    file_make_xml = ft.ElevatedButton(text=".xml",on_click=lambda _: make_xml_dialog.pick_files())
    #file_xml_freq = ft.TextField(label = "Freq.", hint_text="ex) C",helper_text="C or X",width=14*6)
    file_xml_freq = ft.Dropdown(label="Frequency",width=14*10,options=[ft.dropdown.Option("C"),ft.dropdown.Option("X")],helper_text=" ")
    #file_xml_rec = ft.TextField(label = "Recorder", hint_text="ex) vsrec",helper_text="vsrec or octadisk",width=14*10)
    file_xml_rec = ft.Dropdown(label="Recorder",width=14*10,options=[ft.dropdown.Option("vsrec"),ft.dropdown.Option("octadisk")],helper_text=" ")
    file_xml_scan = ft.TextField(label = "Scan", hint_text="ex) 1",helper_text="fringe-finder",width=14*8)
    file_xml_length = ft.TextField(label = "Length", hint_text="ex) 1",helper_text="integ. time (sec)",width=14*9)
    file_xml_fft = ft.TextField(label = "FFT", hint_text="ex) 1024",helper_text="FFT points",width=14*8)
    file_xml_row1 =ft.Row([file_xml_freq,file_xml_rec,file_xml_scan,file_xml_length,file_xml_fft])
    file_xml_delay = ft.TextField(label = "Delay", hint_text="ex) 0",value="0",width=14*8,helper_text="If necessary")#helper_text="FFT points"
    file_xml_rate = ft.TextField(label = "Rate", hint_text="ex) 0",value="0",width=14*8,helper_text="If necessary")
    file_xml_row2 =ft.Row([file_xml_delay,file_xml_rate])
    file_xml_col = ft.Column([file_xml_row1,file_xml_row2])
    file_xml_row =ft.Row([file_make_xml,file_xml_col])
    file_make_out = ft.Text("")

    
    #file_col = ft.Column([file_txt,file_imp_row,file_exp_row,file_txt_check,iers_text,file_row_check,file_cont_output_check, file_txt_lstshift,file_row_lstshift,file_txt_timeshift,file_row_timeshift],scroll=ft.ScrollMode.ALWAYS)
    #file_col = ft.Column([txt_space,file_txt,file_imp_row,file_exp_row,txt_space,file_txt_check,iers_text,file_row_check,file_cont_output_check, txt_space,file_row_shift,file_make_txt,file_make_skd,file_xml_row,file_make_out],scroll=ft.ScrollMode.ALWAYS)
    file_col = ft.Column([txt_space,file_txt,file_imp_row,file_exp_row,txt_space,file_txt_check,iers_text,file_row_check,file_cont_output_check, txt_space,file_row_shift],scroll=ft.ScrollMode.ALWAYS)
    file_container = ft.Container(file_col, alignment=ft.alignment.top_center)
    file_tab = ft.Tab(text="Overview",content=file_container)
    
    #import astropy.config.paths
    #selected_file.value = astropy.config.paths.get_cache_dir()

    
    # inputtxt = ft.Text("Input")
    # exp_cont_code = ft.TextField(label="*Observation Code",hint_text="ex) U23001A")
    # exp_cont_name = ft.TextField(label="*PI Name",hint_text="ex) Y.Iwata")
    # exp_cont_corr = ft.TextField(label="*Correlator",hint_text="ex) GICO3")
    # exp_cont_comment = ft.TextField(label="Comment",multiline=True,min_lines=1,max_lines=3)
    # exp_cont_add = ft.ElevatedButton(text="Update",on_click=exp_add)
    # outputtxt = ft.Text("Output")
    # #exp_txt_output = ft.Text("Output")
    # exp_cont_output = ft.Text("$EXPER         \n*P.I.:        \n*Correlator:        \n*", font_family=outputfont, color=ft.colors.BLACK, selectable=True)

    # exp_cont_output_cont = ft.Container(exp_cont_output, bgcolor=ft.colors.WHITE, padding=10, border=ft.border.all(1), alignment=ft.alignment.top_left)
    # exp_col = ft.Column([txt_space,inputtxt,exp_cont_code,exp_cont_name,exp_cont_corr,exp_cont_comment,exp_cont_add,outputtxt,exp_cont_output_cont],scroll=ft.ScrollMode.ALWAYS,alignment=ft.alignment.center)
    # #exp_container = ft.Container(exp_content, alignment=ft.alignment.center)
    # exp_container = ft.Container(exp_col, alignment=ft.alignment.top_center)
    # exp_tab =ft.Tab(text="EXPER",content=exp_container)

    inputtxt = ft.Text("Input")

    #beamtxt = ft.Text("Beam Mode")
    #beamselect = ft.RadioGroup(content=ft.Row([ft.Radio(value="STD_1BEAM", label="STD_1BEAM"),
    #ft.Radio(value="STD_2BEAM", label="STD_2BEAM")]), on_change=beam_changed)
    #beam_col = ft.Column([beamtxt,beamselect])
    exp_cont_name = ft.TextField(value = "r24125a", label="*Obs Code",hint_text="ex) r24125a") 
    exp_cont_description = ft.TextField(label="*Exper Description",hint_text="ex) M87 Q-band pol")
    exp_cont_piname = ft.TextField(label="*PI Name",hint_text="ex) Vera User")
    exp_cont_email = ft.TextField(label="*PI E-mail",hint_text="ex) vera@sample.jp")
    #exp_cont_corr = ft.TextField(label="*Correlator",hint_text="ex) GICO3")
    #exp_cont_comment = ft.TextField(label="Comment",multiline=True,min_lines=1,max_lines=3)
    exp_cont_add = ft.ElevatedButton(text="Update",on_click=exp_add)
    outputtxt = ft.Text("Output")
    exp_txt_output = vex.exper.output()
    exp_cont_output = ft.Text(exp_txt_output, font_family=outputfont, color=ft.colors.BLACK, selectable=True)

    exp_cont_output_cont = ft.Container(exp_cont_output, bgcolor=ft.colors.WHITE, padding=10, border=ft.border.all(1), alignment=ft.alignment.top_left)
    exp_col = ft.Column([txt_space,inputtxt,exp_cont_name, exp_cont_description,exp_cont_piname,exp_cont_email,exp_cont_add,outputtxt,exp_cont_output_cont],scroll=ft.ScrollMode.ALWAYS,alignment=ft.alignment.center)
    #exp_container = ft.Container(exp_content, alignment=ft.alignment.center)
    exp_container = ft.Container(exp_col, alignment=ft.alignment.top_center)
    exp_tab =ft.Tab(text="EXPER",content=exp_container)

    #antennasrc = SKEDTools_vex.Read_antennasch("antenna.sch")
    # sta_txt = ft.Text("Stations (Read from antenna.sch)")
    # sta_row = []
    # #temporary
    # #for antenna in antennasrc:
    # #    sta_row.append(ft.DataRow([ft.DataCell(ft.Text(antenna.name)),
    # #                               ft.DataCell(ft.Text(antenna.code))], 
    # #                              selected=False,
    # #                              on_select_changed=sta_select))
    # sta_row.append(ft.DataRow([ft.DataCell(ft.Text("tmpname")),
    #                                ft.DataCell(ft.Text("tmpcode"))], 
    #                               selected=False,
    #                               on_select_changed=sta_select))
    # sta_table = ft.DataTable(show_checkbox_column=True, columns=[ft.DataColumn(ft.Text("Name")),
    #                                                              ft.DataColumn(ft.Text("Code"))], rows=sta_row)
    # sta_add = ft.ElevatedButton(text="Update",on_click=sta_add)
    
    # sta_cont_output = ft.Text("$STATIONS\n* ANTENNA INFORMATION\n* STATION POSITION INFORMATION\n*", font_family=outputfont, color=ft.colors.BLACK, selectable=True)
    # sta_cont_output_cont = ft.Container(sta_cont_output, bgcolor=ft.colors.WHITE, padding=10, border=ft.border.all(1), alignment=ft.alignment.top_left)
    
    # sta_col = ft.Column([txt_space,sta_txt,sta_table,sta_add,outputtxt,sta_cont_output_cont],scroll=ft.ScrollMode.ALWAYS)
    # sta_container = ft.Container(sta_col, alignment=ft.alignment.top_center)
    # sta_tab =ft.Tab(text="STATION",content=sta_container)


    
    
    src_name1 = ft.TextField(label="*Source Name", hint_text="ex) SGR_A",capitalization="CHARACTERS")#helper_text="ex) SGR_A"
    src_name2 = ft.TextField(label="Source Name 2", hint_text="ex) SGR_A",capitalization="CHARACTERS")#,helper_text="Optional")
    src_cont_inq = ft.ElevatedButton(text="Simbad query",on_click=src_simbadquery)
    #src_name_row = ft.Row([src_name1,src_name2,src_cont_inq])
    src_name_row = ft.Row([src_name1,src_cont_inq])
    src_ra = ft.TextField(label="*Coordinate (RA)",hint_text="ex) 17h45m40.03599s")#,helper_text="ex) 17h45m40.03599s")
    src_dec = ft.TextField(label="*Coordinate (Dec)",hint_text="ex) -29d00m28.1699s")#,helper_text="ex) -29d00m28.1699s")
    src_coord_row = ft.Row([src_ra,src_dec])
    src_frame = ft.TextField(label="Frame",hint_text="icrs",helper_text="If not icrs. ex) galactic")
    src_equinox = ft.TextField(label="Equinox",hint_text="J2000.0",helper_text="If not J2000.0. ex) B1950.0")
    src_frame_row = ft.Row([src_frame,src_equinox])

    #src_cont_sta = ft.TextField(label="*Station Codes")
    src_inputbutton_add = ft.ElevatedButton(text="Add",on_click=src_add)
    src_inputbutton_clear = ft.ElevatedButton(text="Clear",on_click=src_clear)
    src_cont_fringesrc = ft.ElevatedButton(text="Fringe Finder List",on_click=search_fringesrc)  
    src_cont_srcplot = ft.ElevatedButton(text="Source Plot",on_click=sourceplot)
    src_button_row = ft.Row([src_inputbutton_add,src_inputbutton_clear,src_cont_fringesrc, src_cont_srcplot])
    
    #src_table = ft.DataTable()
    src_table = ft.Column([ft.DataTable( columns=[ft.DataColumn(ft.Text("ID")),
                                                                     ft.DataColumn(ft.Text("Name")),
                                                                     ft.DataColumn(ft.Text("RA")),
                                                                     ft.DataColumn(ft.Text("Dec"))])],scroll=ft.ScrollMode.ALWAYS) #height is defined in src_update()
    src_remove = ft.ElevatedButton(text="Remove",on_click=src_rem)
    src_vlba = ft.ElevatedButton(text="VLBA Calibrator Search",on_click=vlba_search)
    src_button_select_row = ft.Row([src_remove, src_vlba]) 
    src_lst_el = ft.ElevatedButton(text="LST-EL Plot",on_click=lst_elplot)
    src_ut_el = ft.ElevatedButton(text="UT-EL Plot",on_click=ut_elplot)
    src_jst_el = ft.ElevatedButton(text="JST-EL Plot",on_click=jst_elplot)
    src_button_plot_row = ft.Row([src_lst_el,src_ut_el,src_jst_el])
    
    #src_cont_output = ft.Text("$SOURCES\n*", style=ft.TextStyle(font_family="Roboto Mono"),color=ft.colors.BLACK, selectable=True)
    
    src_cont_output = ft.Text("$SOURCES\n*", font_family=outputfont, color=ft.colors.BLACK, selectable=True)
    src_cont_output_cont = ft.Container(src_cont_output, bgcolor=ft.colors.WHITE, padding=10, border=ft.border.all(1), alignment=ft.alignment.top_left)
    src_col = ft.Column([txt_space,inputtxt,src_name_row,src_coord_row,src_frame_row,src_button_row,src_table,src_button_select_row,src_button_plot_row,outputtxt, src_cont_output_cont], scroll=ft.ScrollMode.ALWAYS)
    src_container = ft.Container(src_col, alignment=ft.alignment.top_center)
    src_tab =ft.Tab(text="SOURCE",content=src_container)
    
    #skd_source1 = ft.TextField(label="Source Name 1",hint_text="ex) SGR_A")
    skd_source1 = ft.Dropdown([], width=300)
    #skd_source2 = ft.TextField(label="Source Name 2",hint_text="ex) SGR_A", disabled=True)
    skd_source2 = ft.Dropdown([], width=300, disabled=True)
    #skd_sta = ft.TextField(label="Stations (Antenna codes)", hint_text="ex) K, H")
    skd_row1 = ft.Row([skd_source1,skd_source2])
    skd_start = ft.TextField(label="Start Time ([YEAR]y[DOY]d[HH]h[MM]m[SS]s)]",hint_text="ex) 2024y001d00h00m00s")
    skd_dur = ft.TextField(label="Duration [sec]", hint_text="ex) 300")
    skd_row2 = ft.Row([skd_start,skd_dur])
    skd_modetable = []
    for mode in vex.mode.list:
        skd_modetable.append(ft.dropdown.Option(key=mode.defname, text=mode.defname))
    skd_mode = ft.Dropdown(label="Mode",options=skd_modetable, width=300)
    skd_inputbutton_azel = ft.ElevatedButton(text="AzEl Check",on_click=skd_azel)
    #skd_inputbutton_change = ft.ElevatedButton(text="Change",on_click=skd_change)
    #skd_inputbutton_clear = ft.ElevatedButton(text="Clear",on_click=skd_clear)
    skd_inputbutton_add = ft.ElevatedButton(text="Add",on_click=skd_add)
    skd_inputbutton_change = ft.ElevatedButton(text="Change",on_click=skd_change)
    skd_inputbutton_clear = ft.ElevatedButton(text="Clear",on_click=skd_clear)
    skd_inputbutton_row = ft.Row([skd_inputbutton_add,skd_inputbutton_change,skd_inputbutton_clear])
    
    #skd_table = ft.DataTable()
    skd_table = ft.Column([ft.DataTable(columns=[ft.DataColumn(ft.Text("ID")),
                                                                        ft.DataColumn(ft.Text("Source1")),
                                                                        ft.DataColumn(ft.Text("Start")),
                                                                        ft.DataColumn(ft.Text("Duration")),
                                                                        ft.DataColumn(ft.Text("Stations")),
                                                                        ft.DataColumn(ft.Text("Mode"))],)],scroll=ft.ScrollMode.ALWAYS) #height is defined in skd_update()
        
    skd_selectbutton_edit = ft.ElevatedButton(text="Edit",on_click=skd_edit)
    skd_selectbutton_remove = ft.ElevatedButton(text="Remove",on_click=skd_rem)
    skd_selectbutton_row = ft.Row([skd_inputbutton_azel,skd_selectbutton_edit,skd_selectbutton_remove])

    skd_uvplot_txt = ft.Text("Plot UV Coverage") 
    skd_uvplot_srcname = ft.Dropdown([], width=300)
    skd_uvplot_sta = ft.TextField(label="Station codes (if limited)", hint_text="ex) Vm, Vo, Vs")
    skd_uvplot_plot = ft.ElevatedButton(text="UV plot",on_click=skd_uvplot)
    skd_uvplot_row = ft.Row([skd_uvplot_srcname,skd_uvplot_sta,skd_uvplot_plot])

    skd_cont_output = ft.Text("$SCHED\n*", font_family=outputfont, color=ft.colors.BLACK, selectable=True)
    skd_cont_output_cont = ft.Container(skd_cont_output, bgcolor=ft.colors.WHITE, padding=10, border=ft.border.all(1), alignment=ft.alignment.top_left)
    skd_col = ft.Column([txt_space,inputtxt,skd_row1,skd_row2,skd_mode, skd_inputbutton_row,skd_table,skd_selectbutton_row,skd_uvplot_txt,skd_uvplot_row, outputtxt, skd_cont_output_cont], scroll=ft.ScrollMode.ALWAYS)
    skd_container = ft.Container(skd_col, alignment=ft.alignment.top_center)
    skd_tab =ft.Tab(text="SCHED",content=skd_container)

    modetable = [ft.dropdown.Option(key=name, text=name) for name in observing_templates]
    band_order = {'C': 0, 'K': 1, 'Q': 2, 'KQ': 3}
    modetable.sort(key=lambda option: (
        band_order.get(option.text.split('_')[0], 4),
        tuple(option.text.split('_'))))
    select_txt = ft.Text("Select from templates")
    modeselect = ft.Dropdown(value=default_template, options=modetable, width=650, on_change=mode_changed, helper_text = "ex) K_Maser_2B_SingP_1G => K band, Maser (& continuum), 2 Beam, Single Polarization, 1 Gbps")
    mode_txt_output = vex.header.output()+vex.freq.output()+vex.mode.output()
    mode_cont_output = ft.Text(mode_txt_output, font_family=outputfont, color=ft.colors.BLACK, selectable=True)
    mode_cont_output_cont = ft.Container(mode_cont_output, bgcolor=ft.colors.WHITE, padding=10, border=ft.border.all(1), alignment=ft.alignment.top_left)
    mode_col = ft.Column([txt_space,select_txt, modeselect,
        ft.Text('Apply templates before adding scans. Display names do not change VEX MODE identifiers.'),
        mode_cont_output_cont], scroll=ft.ScrollMode.ALWAYS)
    mode_container = ft.Container(mode_col, alignment=ft.alignment.top_center)
    mode_tab =ft.Tab(text="Mode",content=mode_container)

    initfig = plt.figure()
    # ax=initfig.add_subplot()
    # x=np.arange(0,100)
    # y=x*2
    # ax.plot(x,y)
    # ax.set_ylim(30,)
    # ax.set_xlim(0,)
    mpl = MatplotlibChart(figure=initfig,expand=True,original_size=False)
    #mpl = ft.Image(src=f"/tmpfig.png",width=500,height=500,fit=ft.ImageFit.CONTAIN,)
    #mpl.transparency=True
    
    #mpl = ft.Image()
    #plt_exp = ft.ElevatedButton(text="Export",icon=ft.icons.SAVE,on_click=lambda _: save_file_dialog.save_file(),disabled=page.web)
    #plt_col =ft.Column([mpl],scroll=ft.ScrollMode.ALWAYS)
    plt_cont =ft.Container(mpl,  alignment=ft.alignment.top_center)
    plt_tab = ft.Tab(text="Plot",content=plt_cont)  
    
    tabs=[file_tab,mode_tab,exp_tab,src_tab,skd_tab,plt_tab]
    t = ft.Tabs(selected_index=0,animation_duration=300,tabs=tabs,expand=1)
    
    page.add(t)
#ft.app(target=main, port=8000,view=ft.WEB_BROWSER)
if __name__ == "__main__":
    ft.app(target=main)
