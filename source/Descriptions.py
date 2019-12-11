import L5k.L5k as L5k
import rockwell_types.rockwell_types
import re
import pandas as pd


#print(sample_routine)

class routine():
    def __init__(self,routine_string):
        self.routine_string = routine_string

    def get_start_of_seq(self):
        string_replaced = self.clean_routine_string()
        #print("Number of lines in routine: ",len(string_replaced))
        seq_str = r"Sequence Step Transition Logic"
        strt = 0
        for i,string in enumerate(string_replaced):
            #m = steps_start_str.match(string)
            m = re.search(seq_str,string)
            #print(i, string)
            if m is not None:
                # print("Start of Sequence is on Line: ",i)
                # print("Match group: ",m.group(0))
                # print(string)
                strt = i
                break

        if strt > 0:
            return strt
        else:
            return 0

    def clean_routine_string(self):
        string_replaced = self.routine_string.replace("\t",'').replace("\n",'').replace("\r",'')
        string_replaced = string_replaced.split(';')
        return string_replaced

    def get_phase_name(self):

        string_replaced = self.clean_routine_string()
        #print("Number of lines in routine: ",len(string_replaced))
        seq_str = r"GM_FM_PhaseSeq"
        strt = 0
        for i,string in enumerate(string_replaced):
            #m = steps_start_str.match(string)
            m = re.search(seq_str,string)
            #print(i, string)
            if m is not None:
                phs_name = string
                break
        phs_match_string = r'\((\S*)_AOI'
        phs_match = re.compile(phs_match_string)
        m = phs_match.search(string)
        if m is not None:
            return m.group(1)
        else:
            print("No match found")


    def build_step_dict(self):

        #Shorten Routine Rung List to only Sequence Rungs
        routine_lines_seq = self.clean_routine_string()[self.get_start_of_seq():]

        step_match_str = r'StepActive\[(\d+)\]'
        step_match = re.compile(step_match_str)

        desc_match_str = r'\"([a-zA-Z \$]*)\"'
        desc_match = re.compile(desc_match_str.strip())

        step_dict = {}
        for i,line in enumerate(routine_lines_seq):
            if line.startswith("RC:"):
                #line = line.split("\"")
                #print("\nLine:" ,line)
                m = desc_match.search(line)

                if m is not None:
                   # print("Groups : ", m.groups())
                    if m.group(1)[-2] is '$':
                        step_comment = m.group(1)[:-2]
                    else:
                        step_comment = m.group(1)
                    step = routine_lines_seq[i+1]

                m = step_match.search(step)
                #print(step)
                if m is not None:
                    step_num = m.group(1)
                    #print("Step # {} , Step Comment: {} ".format(step_num,step_comment))
                    step_dict[step_num] = step_comment

        return step_dict

    def get_phase_step_descriptions(self):
        #For Each Routine:
        phase_name = self.get_phase_name()
        print("Phase Name: ", phase_name)


        #Build the step dictionary
        step_dict = self.build_step_dict()
        print(step_dict.keys())

        #convert Dict to Dataframe and Write to File
        steps_df = pd.DataFrame.from_dict(step_dict,orient='index')
        path = '..\data\\'+phase_name +'.xlsx'
        print("Writing to: ",path)
        steps_df.to_excel(path,sheet_name=phase_name)


##Setup

# fname = r"C:\Users\Yaseen.Ali\OneDrive - Callisto Integration\Documents\Python Scripts and Training\Archestra_Desc_Generator\data\SOFTCENTERS_Pack_Dev_20191209.L5K"
#
# plc = L5k.L5kObject(fname)
#
# #Read in Excel File
# data = pd.read_excel("..\data\Input_phase_list.xlsx",sheet_name="Sheet1")
# programs = data["Program"].unique()
# routines = data["Routine"].unique()
#
# for item in routines:
#         routine = plc['CONTROLLER']['PROGRAM '+ programs[0]]['ROUTINE ' + item]['text']
#         ds = routine(item)
#         step_dict = ds.build_step_dict()
#         step_dict.keys()





