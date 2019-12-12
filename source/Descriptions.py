import L5k.L5k as L5k
import rockwell_types.rockwell_types
import re
import pandas as pd


#print(sample_routine)

class routine():
    def __init__(self,routine_string):
        self.routine_string = routine_string
        self.name = self.get_phase_name()

    def get_start_of_seq(self):
        '''
        Helper function to find start of Sequence Logic
        :return:
        '''
        string_replaced = self.clean_routine_string()
        #print("Number of lines in routine: ",len(string_replaced))
        seq_str = r"Sequence Step Transition Logic"
        strt = 0
        for i,string in enumerate(string_replaced):
            #m = steps_start_str.match(string)
            m = re.search(seq_str,string)
            #print(i, string)
            if m is not None:
                strt = i
                break

        if strt > 0:
            return strt
        else:
            return 0

    def clean_routine_string(self):
        '''
        This routine cleans up the carriage return,tabs and new lines and resplits the string on
        semi colon since this demarks a rung end.
        :return: List of rungs' text
        '''
        string_replaced = self.routine_string.replace("\t",'').replace("\n",'').replace("\r",'')
        string_replaced = string_replaced.split(';')
        return string_replaced

    def get_phase_name(self):
        '''

        :return: The Phase Tag name
        '''
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


    def build_step_dict(self,debug=0):
        '''
         This method builds a dictionary of step descriptions for the routine.
         It looks for rungs starting with "RC:" which denote Rung Comments and then associates these
         with the active step number found in the next rung.
         :param debug: set this to 1 to print debug messages
         :return: Returns a dictionary where the key is the step description number and the value is the step description
        '''

        #Shorten Routine Rung List to only Sequence Rungs
        routine_lines_seq = self.clean_routine_string()[self.get_start_of_seq():]

        #Regular Expression to get Active Step number
        step_match_str = r'StepActive\[(\d+)\]'
        step_match = re.compile(step_match_str)

        #Regular Expression to pull out description
        desc_match_str = r'\"([a-zA-Z0-9-,. \$]*)\"'
        desc_match = re.compile(desc_match_str.strip())

        step_dict = {}
        for i,line in enumerate(routine_lines_seq):
            if line.startswith("RC:"):
                #line = line.split("\"")
                if debug:
                    print("\nLine:" ,line)
                m = desc_match.search(line)

                if m is not None:
                    if debug:
                        print("Groups : ", m.groups())
                    if m.group(1)[-2] is '$':
                        step_comment = m.group(1)[:-2]
                    else:
                        step_comment = m.group(1)
                    step = routine_lines_seq[i+1]

                m = step_match.search(step)
                #print(step)
                if m is not None:
                    step_num = m.group(1)
                    if debug:
                        print("Step # {} , Step Comment: {} ".format(step_num,step_comment))
                    step_dict[step_num] = step_comment

        return step_dict

    def phase_step_descriptions_to_excel(self,path):
        '''
        Writes the step descriptions to an excel file.
        :param path: Path where the file should be saved. The file will be named the phase name
        :return:
        '''
        #For Each Routine:
        phase_name = self.get_phase_name()
        print("Phase Name: ", phase_name)


        #Build the step dictionary
        step_dict = self.build_step_dict()
        #print(step_dict.keys())

        #convert Dict to Dataframe and Write to File
        steps_df = pd.DataFrame.from_dict(step_dict,orient='index')
        #path = '..\data\\'+phase_name +'.xlsx'
        print("Writing to: ",path)
        steps_df.to_excel(path,sheet_name=phase_name)





