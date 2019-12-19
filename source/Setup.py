import Descriptions as ds
import L5k.L5k as L5k
import pandas as pd
import csv

#TODO: Create commandline interface to run this as a script

fname = r"C:\Users\Yaseen.Ali\OneDrive - Callisto Integration\Documents\Python Scripts and Training\Archestra_Desc_Generator\data\SOFTCENTERS_Pack_Dev_20191219.L5K"

plc = L5k.L5kObject(fname)

input_phase_list_path = "..\data\Input_phase_list.xlsx"
galaxy_load_template_path = "..\data\\test_phase.csv"




def galaxy_load_builder(input_phase_list_path,galaxy_load_template_path):

        #Read in Excel File
        data = pd.read_excel(input_phase_list_path,sheet_name="Sheet1")
        programs = data["Program"].unique()
        routines = data["Routine"].unique() #List of routines in the input phase list


        #Read in Galaxy load  template
        df_galaxy = pd.read_csv(galaxy_load_template_path)

        #Create temp_df to write to
        df_temp = df_galaxy.iloc[:1,:].copy()

        template_desc_list = (df_galaxy.iloc[1,1]).split(',') #Getting current template step descriptions (list of len 100)
        template_desc_list.insert(0,'Step Description 0') #Adding in a dummy Step 0 description so the list lines up with Archestra's array starting at 1
        #Later we will drop the first 0 step desc

        for routine in routines:
                routine_text = plc['CONTROLLER']['PROGRAM '+ programs[0]]['ROUTINE ' + routine]['text']
                rtne = ds.routine(routine_text) #Instantiating routine class
                #print(rtne.name)
                step_dict = rtne.build_step_dict() #building step dict. To debug pass in debug=1 as a parameter
                desc_list = template_desc_list.copy() #Create a copy of the template to make changes to
                for key in step_dict:
                        desc_list[int(key)] = step_dict[key] #Update the new description list with descriptions from the dict

                #Append Line

                df_temp_line = pd.DataFrame([[rtne.name,(',').join(desc_list[1:])]],columns=df_galaxy.columns)
                #print(df_temp_line)
                df_temp = df_temp.append(df_temp_line,ignore_index=True)

        return df_temp


galaxy_load_file = galaxy_load_builder(input_phase_list_path,galaxy_load_template_path)

galaxy_load_file.to_csv("..\data\\test_phase_mod.csv",index=None)

print(galaxy_load_file)






