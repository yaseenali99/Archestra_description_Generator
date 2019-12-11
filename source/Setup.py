import Descriptions as ds
import L5k.L5k as L5k
import pandas as pd
import csv

fname = r"C:\Users\Yaseen.Ali\OneDrive - Callisto Integration\Documents\Python Scripts and Training\Archestra_Desc_Generator\data\SOFTCENTERS_Pack_Dev_20191209.L5K"

plc = L5k.L5kObject(fname)

#Read in Excel File
data = pd.read_excel("..\data\Input_phase_list.xlsx",sheet_name="Sheet1")
programs = data["Program"].unique()
routines = data["Routine"].unique()


#Read in Galaxy load file
df_galaxy = pd.read_csv("..\data\\test_phase_mod.csv")
desc_list = (df_galaxy.iloc[1,1]).split(',') #Getting current step descriptions (list of len 100)
object_name = df_galaxy.iloc[0,1]


for routine in routines:
        routine_text = plc['CONTROLLER']['PROGRAM '+ programs[0]]['ROUTINE ' + routine]['text']
        stp = ds.routine(routine_text) #Instantiating routine class
        step_dict = stp.build_step_dict() #building step dict
        for key in step_dict:
                desc_list[int(key)] = step_dict[key] #Update description list with description from dict

        #prepare line to be appended to
        df_galaxy.iloc[1,1] = (',').join(desc_list)
        df_galaxy.to_csv("..\data\\test_phase_mod.csv",index=None,quoting=csv.QUOTE_NONE,quotechar='',  escapechar="\\")
        #print(stp.get_phase_name(), step_dict.items())







