import re
#re.DOTALL = True	# Turn on setting so that . matches newline as well as any character

import argparse
from collections import OrderedDict
from os import path
import codecs
import sys
import rockwell_types.rockwell_types

debug = False


"""
KNOWN BUGS:
- QualityCheck doesn't traverse AOI Data types

"""


# Identifiers and their type
identifiers = {
	'CONTROLLER': None,
	'DATATYPE': None,
	'MODULE': None,
	'ADD_ON_INSTRUCTION_DEFINITION': None,
	'PARAMETERS': None,
	'LOCAL_TAGS': None,
	'TAG': None,
	'PROGRAM': None,
	'ROUTINE': None,
	'FBD_ROUTINE': None,
	'TASK': None,
	'CONFIG': None,
	'CHILD_PROGRAMS': None,
	'ST_ROUTINE': None,
	'ENCODED_DATA': None,
	'SFC_ROUTINE': None,
	'STEP': 'ID',
	'ACTION': 'ID',
	'BODY': 'NoName',
	'TRANSITION': 'ID',
	'CONDITION': 'NoName',
	'BRANCH': 'ID',
	'LEG': 'ID',
	'DIRECTED_LINK': 'ID'
}

standardtypes = \
	{'STRING',
	 'BOOL',
	 'ALARM',
	 'ALARM_ANALOG',
	 'ALARM_DIGITAL',
	 'AUX_VALVE_CONTROL',
	 'AXIS_CIP_DRIVE',
	 'AXIS_CONSUMED',
	 'AXIS_GENERIC',
	 'AXIS_GENERIC_DRIVE',
	 'AXIS_SERVO',
	 'AXIS_SERVO_DRIVE',
	 'AXIS_VIRTUAL',
	 'CAM',
	 'CAM_PROFILE',
	 'CAMSHAFT_MONITOR',
	 'CB_CONTINUOUS_MODE',
	 'CB_CRANKSHAFT_POS_MONITOR',
	 'CB_INCH_MODE',
	 'CB_SINGLE_STROKE_MODE',
	 'CC',
	 'CONFIGURABLE_ROUT',
	 'CONNECTION_STATUS',
	 'CONTROL',
	 'COORDINATE_SYSTEM',
	 'COUNTER',
	 'DATALOG_INSTRUCTION',
	 'DCA_INPUT',
	 'DCAF_INPUT',
	 'DCI_MONITOR',
	 'DCI_START',
	 'DCI_STOP',
	 'DCI_STOP_TEST',
	 'DCI_STOP_TEST_LOCK',
	 'DCI_STOP_TEST_MUTE',
	 'DEADTIME',
	 'DERIVATIVE',
	 'EMERGENCY_STOP',
	 'PID',
	 'REDUNDANT_INPUT',
	 'LEAD_LAG',
	 'SELECT',
	 'HL_LIMIT',
	 'FBD_TRUNCATE',
	 'FBD_MATH',
	 'FBD_MATH_ADVANCED',
	 'FBD_COMPARE',
	 'COUNTER',
	 'SCALE',
	 'INT',
	 'REAL',
	 'BIT',
	 'DINT',
	 'TIMER',
	 'SINT'
	 }

# csv splitter.  This works better than csv module and is able to handle situations like 'some text "more, text"'
# See here: https://stackoverflow.com/questions/16710076/python-split-a-string-respect-and-preserve-quotes
# This matches sequences of non-delimiters(,") and quoted strings and strings in [].  The last one was to support
# multi dimensional arrays that have commas in them.
csvsplit_string = r'(?:[^,"\[]|"(?:\\.|[^"])*"|\[(?:\\.|[^\]])*\])+'
csvsplit = re.compile(csvsplit_string, flags=re.DOTALL|re.M)

# This matches sequences of non-delimiters (,"') and double quoted strings and single quoted string
semisplit_string = r'(?:[^;"\']|"(?:\\.|[^"])*"|\'(?:\\.|[^\'])*\')+'
semisplit = re.compile(semisplit_string, flags=re.DOTALL|re.M)

def check_for_array(inputtype):
	if "[" in inputtype:
		match = re.match(r"([^\[]+)\[([^\]]+)\]", inputtype)
		if match is not None:
			type = match.group(1)
			size = match.group(2)
			return (type,size)
		else:
			print( "Failed: " + inputtype)
			type = match.group(1)
	else:
		return None

class Tag(object):

	def __init__(self, name='', type='BOOL', reference=None):
		self.name = name
		self.type = type
		self.reference = reference	# only if alias
		self.dim = None 			# only if tag
		self.value = None			# only if tag
		self.parms = OrderedDict()

	def __repr__(self):
		return 'TAG : {} - {}'.format(self.name, self.type)


	def build_from_l5k(self, l5kText):
		# AC_Alarm : BOOL (Description := "Air Conditioner Faulted Alarm Bit", RADIX := Decimal) := 0;
		tagmatch_string = r'(\S+)\s*:\s*(\S+)\s*(?:\((.*?)\s*\))?\s*(?::=\s*(.+?))?;'
		tagmatch = re.compile(tagmatch_string, flags=re.DOTALL|re.M)

		# Alarm_Horn OF Local:1:O.Data.4 (Description := "Alarm Horn Output", RADIX := Decimal);
		aliasmatch_string = r'(\S+)\s*OF\s*(\S+)\s*(?:\((.*?)\s*\))?\s*(?::=\s*(.+?))?;'
		aliasmatch = re.compile(aliasmatch_string, flags=re.DOTALL|re.M)

		m = tagmatch.match(l5kText.strip())

		# Tag Match
		if m is not None:
			output = check_for_array(m.group(2))
			if output is not None:
				self.type = output[0]
				self.dim = output[1]
			else:
				self.type = m.group(2)
		else:
			m = aliasmatch.match(l5kText.strip())
			self.type = "Alias"
			if m is not None:
				self.reference = m.group(2)

		if m is None:
			raise ValueError("Failed to match pattern in string: {}".format(l5kText))

		self.name = m.group(1)
		#print self.name
		#print l5kText.strip()
		# Retrieve parameters from group(2)
		if m.group(3) is not None:

			templist = csvsplit.findall(m.group(3).strip())

			for item in templist:
				tmpvalues = item.split(':=',1)
				if len(tmpvalues) != 2:
					raise ValueError("Failed to parse tag parameter: {} in {}".format(item, l5kText))

				self.parms[tmpvalues[0].strip()] = tmpvalues[1].strip()

		# Retrieve value from group(4)
		if m.group(4) is not None:
			self.value = m.group(4)


class DataTypeTag(object):

	def __init__(self, name=''):
		self.name = name
		self.type = None
		self.dim = None
		self.parms = OrderedDict()

	def __repr__(self):
		return 'DataTypeTag : {} - {}'.format(self.name, self.type)

	def build_from_l5k(self, l5kText):
		# BIT DownloadHandshakeFdbk ZZZZZZZZZZMESTransac1 : 4 (Description := "Handshake to ArchestrA (Not For External Use)");
		tagmatch_string = r'(\S+)\s*(\S+)\s*(?:\S+\s*:\s*\S+\s*)?(?:\((.*?)\s*\))?\s*;'
		tagmatch = re.compile(tagmatch_string, flags=re.DOTALL | re.M)

		m = tagmatch.match(l5kText.strip())

		if m is None:
			raise ValueError("Failed to match pattern in string: {}".format(l5kText))

		self.type = m.group(1)
		if self.type == 'BIT':
			self.type = 'BOOL'

		self.name = m.group(2)
		output = check_for_array(m.group(2))
		if output is not None:
			self.name = output[0]
			self.dim = output[1]

		# Retrieve parameters from group(3)
		if m.group(3) is not None:

			templist = csvsplit.findall(m.group(3).strip())

			for item in templist:
				tmpvalues = item.split(':=')
				if len(tmpvalues) != 2:
					print( "warning: Failed to parse tag parameter: {} in {}".format(item, l5kText))
					#raise ValueError("Failed to parse tag parameter: {} in {}".format(item, l5kText))
					return
				self.parms[tmpvalues[0].strip()] = tmpvalues[1].strip()


class L5kObject(OrderedDict):
	def __init__(self, filename):
		OrderedDict.__init__(self, L5kRead(filename).items())

	def containsProgram(self,programName):
		if 'PROGRAM ' + programName in self['CONTROLLER'].keys():
			return True
		else:
			return False

	def containsRoutine(self, routineName, programName='MainProgram', checkjsr=True):

		#Program path
		if 'PROGRAM ' + programName not in self['CONTROLLER'].keys():
			print( "Program: {} does not exist".format(programName))
			return False
		checkpath = self['CONTROLLER']['PROGRAM ' + programName]

		# Check routine
		if "ROUTINE " + routineName not in checkpath.keys():
			print( "Error: Routine not found: {}".format(routineName))
			return False

		if not checkjsr:
			return True

		# Find MainRoutine
		if 'MAIN' in checkpath.parms.keys():
			mainroutine = checkpath.parms['MAIN'].strip("\" ")
		else:
			print("Program: {} does not have main routine specified".format(programName))
			return False

		# Check for JSR
		routinetext = checkpath['ROUTINE ' + mainroutine]
		if "JSR(" + routineName not in routinetext:
			print("Error: Routine is missing JSR: {}".format(routineName))
			return False

		return True

	def qualityCheck(self, tagPath, type=None):

		parsing_std_types = False

		if tagPath.startswith('Local'):
			tagmembers = [tagPath]
		else:
			tagmembers = tagPath.split('.')

		i = 0
		checkpath = self['CONTROLLER']['TAG']

		for tagmember in tagmembers:

			# Get name and dim of tagmember
			output = check_for_array(tagmember)
			requested_dim = None
			if output is not None:
				tagmember, requested_dim = output
				requested_dim = int(requested_dim)

			# Case insensitive / array removing key match on tag dict
			nocasekeys = {}
			for k in checkpath.keys():
				out = check_for_array(k)
				if out is not None:
					key = out[0].lower()
				else:
					key = k.lower()
				nocasekeys[key] = k

			if tagmember.startswith('Local:'):
				digmatch_string = r'Local:(\d+):([IO]).Data.\d+'
				diggmatch = re.compile(digmatch_string)

				aimatch_string = r'Local:(\d+):([IO]).Ch\d+Data'
				aimatch = re.compile(aimatch_string)

				m = diggmatch.match(tagmember)
				if m is not None:
					if type is None or type == 'BOOL':
						return True
				else:
					m = aimatch.match(tagmember)
					if m is not None and type is None or type == 'INT':
						return True
				print("{} : Alias failed to match requested type of : {}".format(tagmember, type))
				return False

			elif tagmember.lower() in nocasekeys:

				tagmatchkey = nocasekeys[tagmember.lower()]

				if not parsing_std_types:
					tagmembertype = checkpath[tagmatchkey].type
					tagmemberdim = checkpath[tagmatchkey].dim

				else:
					tagmembertype = checkpath[tagmatchkey]
					tagmemberdim = None
					output = check_for_array(tagmembertype)
					if output is not None:
						tagmember, tagmemberdim = output

				if tagmemberdim is not None:
					tagmemberdim = int(tagmemberdim)

				if i == len(tagmembers) - 1:
					if tagmembertype == 'Alias':
						ref = checkpath[tagmatchkey].reference
						return self.qualityCheck(ref,type)

					if type is not None and tagmembertype != type:
						print( "{} : requested type: {} does not match controller tag type: {}".format(tagPath, type, tagmembertype))
						return False
					if (requested_dim is None) != (tagmemberdim is None):
						print("{} : Dimension in controller does not match requested index: {} != {}".format(tagPath, tagmemberdim, requested_dim))
						return False
					elif requested_dim and tagmemberdim and requested_dim > tagmemberdim - 1:
						print("{} : index out of range of tag type: {}[{}]".format(tagPath, tagmembertype, str(tagmemberdim)))
						return False

					return True
				else:
					if parsing_std_types:
						checkpath = checkpath[tagmatchkey]
					elif tagmembertype in standardtypes:
						parsing_std_types = True
						if tagmembertype in rockwell_types.standard_dict.keys():
							checkpath = rockwell_types.standard_dict[tagmembertype]
						else:
							print("Tag path references a standard Rockwell Type that is not defined: {}".format(tagPath))
							return False
					else:
						if 'DATATYPE ' + tagmembertype in self['CONTROLLER'].keys():
							checkpath = self['CONTROLLER']['DATATYPE ' + tagmembertype]
						elif 'ADD_ON_INSTRUCTION_DEFINITION ' + tagmembertype in self['CONTROLLER'].keys():
							checkpath = self['CONTROLLER']['ADD_ON_INSTRUCTION_DEFINITION ' + tagmembertype]['PARAMETERS']
						else:
							print("Failed to find datatype: {}".format(tagmembertype))
							return False
			else:
				print("Tag path not found in controller: {}".format(tagPath))
				return False

			i += 1


def L5kRead(fileref, point=0):
	filelines = []
	if isinstance(fileref, str): #or isinstance(fileref, unicode):
		if path.isfile(fileref):
			with codecs.open(fileref, 'r', 'utf-8') as inputfile:
				filelines = inputfile.readlines()
		else:
			print("L5k File Not Found: " + fileref)
	elif isinstance(fileref, list):
		filelines = fileref
	else:		
		raise TypeError("Input must be name of a file or a list of strings")

	initialpoint = point
	returndict = OrderedDict()
	contents = []
	linewords = []
	itemtype = ""
	starttrigger = ""
	endtrigger = ""
	newstarttrigger = ""

	if point < len(filelines):
		linewords = filelines[point].strip().split(None)

	if len(linewords) >= 1 and linewords[0] in identifiers.keys():
		itemtype = linewords[0]
		name = ""
		if len(linewords) == 1 or identifiers[itemtype] == 'NoName' or identifiers[itemtype] == 'ID':
			starttrigger = itemtype

		else:
			if itemtype == "CONFIG":
				name = linewords[1].split("(")[0]
			else:
				name = linewords[1]
			starttrigger = itemtype + " " + name

		endtrigger = "END_" + linewords[0]

	firstloop = True

	while point < len(filelines):
		line = filelines[point].strip()
		linewords = line.split(None)
		if len(linewords) == 0 and point != len(filelines) - 1:
			point += 1
			firstloop = False
			continue

		# Check for new identifier (i.e. not the first call) newstarttrigger = identifier + name
		if firstloop == False and len(linewords) >= 1 and linewords[0] in identifiers.keys():
			# print("made it here")
			newtype = linewords[0]
			newname = ""
			if len(linewords) == 1 or identifiers[newtype] == 'NoName':
				newstarttrigger = newtype
			elif identifiers[newtype] == 'ID':
				matchstring = r'.*ID := (\d+)[,\)]\s*'
				m = re.match(matchstring, line)
				if m is not None:
					newstarttrigger = newtype + " " + m.group(1)
				else:
					print("Error: Could not find id in identifier: {}".format(line))
					exit(1)
			else:
				if newtype == "CONFIG":
					newname = linewords[1].split("(")[0]
				else:
					newname = linewords[1]
				newstarttrigger = newtype + " " + newname

		# retrieve any relevant content in current line. Exclude start and end triggers.
		if newstarttrigger == "":
			tmpstart = 0
			tmpend = len(filelines[point])
			if firstloop == True and "CONTROLLER" not in starttrigger and starttrigger != "" and filelines[
				point].strip().startswith(starttrigger):
				tmpstart = filelines[point].find(starttrigger) + len(starttrigger)
			if endtrigger != "" and endtrigger in filelines[point]:
				tmpend = filelines[point].find(endtrigger, tmpstart)
			if (firstloop == True and starttrigger != "" and filelines[point].strip().startswith(
					starttrigger)) or endtrigger in filelines[point]:
				additionalcontent = filelines[point][tmpstart:tmpend]
			else:
				additionalcontent = filelines[point]
			contents.append(additionalcontent)

		if endtrigger != "" and endtrigger in filelines[point] or point == len(filelines) - 1:
			if debug:
				print(endtrigger)
			point += 1

			# NOTE:  Probably need to do this for more than just DATATYPE.  Also will eventually
			#		need to store this data not just throw it away

			parms = OrderedDict()
			if contents[0].strip().startswith('('):

				done = False
				while not done and len(contents) > 0:

					if contents[0].strip().endswith(')'):
						done = True
					addstring = contents.pop(0)
					addstring = addstring.strip().lstrip('(').rstrip(',)')
					addlist = addstring.split(':=')
					parms[addlist[0].strip()] = addlist[1].strip()


			contentstring = "".join(contents)
			contentstring = contentstring.strip()

			# Add new Tag object and parse L5k using built in function
			if itemtype == "TAG" or itemtype == "PARAMETERS" or itemtype == "LOCAL_TAGS":
				tagdict = OrderedDict()
				#taglist = contentstring.split(";")[:-1]
				taglist = semisplit.findall(contentstring.strip())

				for tag in taglist:
					if tag.isspace():
						continue
					#print "found tag"
					#print tag
					newtag = Tag('newtag')
					newtag.build_from_l5k(tag + ';')
					tagdict[newtag.name] = newtag

				if initialpoint == 0:
					return tagdict
				else:
					return tagdict, point

			elif itemtype == 'DATATYPE':

				tagdict = OrderedDict()
				# taglist = contentstring.split(";")[:-1]
				taglist = semisplit.findall(contentstring.strip())

				for tag in taglist:
					tag = tag.strip()

					if tag.isspace():
						continue
					newtag = DataTypeTag('newtag')
					newtag.build_from_l5k(tag + ';')
					tagdict[newtag.name] = newtag

				tagdict.parms = parms

				if initialpoint == 0:
					return tagdict
				else:
					return tagdict, point

			elif itemtype == 'MODULE':
				returndict = OrderedDict()
				returndict.parms = parms

				returndict['header'] = contentstring

				if initialpoint == 0:
					return returndict
				else:
					return returndict, point

			else:
				returndict['text'] = contentstring
				returndict.parms = parms
				if initialpoint == 0:

					return returndict
				else:

					return returndict, point


		if newstarttrigger != "":
			if newstarttrigger.startswith('CONTROLLER '):
				newstarttrigger = "CONTROLLER"

			if debug:
				print(newstarttrigger)

			output = L5kRead(filelines, point)
			returndict[newstarttrigger], point = output

			# After returning you must clear out the fact that you are entering a new item
			newstarttrigger = ""

			if point >= len(filelines):
				contentstring = "".join(contents)
				returndict['text'] = contentstring
				return returndict

		else:
			point += 1
		firstloop = False
